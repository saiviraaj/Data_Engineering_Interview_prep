# Module 18 — GenAI System Design Interviews

> Ten complete design walkthroughs at senior/staff engineer level. Each covers the full 35-minute interview arc: requirements → high-level design → deep dive → tradeoffs.

---

## Design 1: Build ChatGPT (Conversational AI at Scale)

### Requirements Clarification

```
Scale: 100M users, 10M concurrent, 1B messages/day
Latency: < 500ms TTFT, streaming response
Features: Multi-turn conversation, code execution, plugins/tools
Models: Multiple (GPT-4, GPT-4o, o1), user-selectable
Data: No user data used for training without consent
SLA: 99.9% availability
```

### High-Level Design

```
Users
  ↓
CDN (static assets, edge caching)
  ↓
API Gateway (auth, rate limiting, SSL termination)
  ↓
Load Balancer
  ↓
Conversation Service (FastAPI)
├── Session Manager (Redis — active sessions)
├── History Service (PostgreSQL — full history)
├── Tool/Plugin Router
└── LLM Router
    ├── OpenAI Service (GPT-4o)
    ├── Reasoning Service (o1)
    └── Code Execution Service (sandboxed)
  ↓
Response Streamer (SSE/WebSocket)
  ↓
Observability Stack
```

### Deep Dive: Conversation History

```
Challenge: 100M users × 50 messages/conversation = 5B messages stored

Storage Architecture:
- Hot storage: Redis (last 20 messages per active session, TTL 24h)
- Warm storage: PostgreSQL (last 3 months, indexed by user_id)
- Cold storage: S3 (archived conversations, Parquet format)

Session Management:
- session_id → Redis key → last 20 messages (list)
- On cache miss → load from PostgreSQL → repopulate Redis
- Context window management: trim to model's max context (8K/128K)

Schema:
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(200),
    model VARCHAR(50),
    created_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ
);

CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations,
    role VARCHAR(20),  -- user/assistant/system
    content TEXT,
    token_count INT,
    latency_ms INT,
    created_at TIMESTAMPTZ
);

CREATE INDEX idx_conv_user ON conversations(user_id, last_message_at DESC);
CREATE INDEX idx_msg_conv ON messages(conversation_id, created_at);
```

### Deep Dive: Streaming at Scale

```python
# Token streaming with backpressure handling
async def stream_response(
    user_id: str,
    conversation_id: str,
    message: str,
    model: str,
) -> AsyncIterator[str]:
    
    # 1. Load context from Redis/DB
    history = await load_conversation_history(conversation_id, max_messages=20)
    
    # 2. Build messages with trim
    messages = build_messages(history, message, model_context_limit=128000)
    
    # 3. Stream from LLM
    full_response = ""
    async for chunk in llm_router.astream(messages, model=model):
        token = chunk.content
        full_response += token
        yield f"data: {json.dumps({'token': token})}\n\n"
    
    # 4. Persist response (async, don't block streaming)
    asyncio.create_task(
        persist_message(conversation_id, "assistant", full_response)
    )
    
    yield f"data: [DONE]\n\n"
```

### Scale Numbers

```
1B messages/day = 11,574 messages/second peak (assume 3x peak factor = 35K/s)
Avg message: 500 input tokens + 300 output tokens = 800 tokens
Token throughput needed: 35K × 800 = 28M tokens/second

OpenAI GPT-4o limit: ~10K requests/min per org key
Need: 35K × 60 = 2.1M req/min → 210+ API keys with org-level pooling

Storage:
1B messages × 800 avg tokens × 4 bytes = 3.2TB/day
→ Compress messages (gzip 70%): ~1TB/day
→ Move to cold storage after 90 days
```

### Tradeoffs

```
Streaming SSE vs WebSocket:
→ SSE chosen for chat (server→client only), simpler, better CDN support
→ WebSocket needed if adding voice/real-time collaboration features

Redis vs pure DB for session:
→ Redis: sub-millisecond reads, TTL management, but memory cost
→ DB only: simpler but 10ms+ per read, can't handle 10M concurrent sessions

Token limit strategy:
→ Option A: Hard truncate old messages (fast but loses context)
→ Option B: Summarize old messages with LLM (expensive but better UX)
→ Decision: Truncate by default, summarize for Pro tier
```

---

## Design 2: Enterprise RAG for Legal Document Search

### Requirements

```
Scale: 50 enterprise clients, 10K lawyers, 500K documents per client
Latency: < 3s for complex legal queries
Accuracy: High precision mandatory — hallucinations cause liability
Compliance: SOC2, HIPAA-adjacent; data never leaves client's VPC
Features: Semantic search + citation with exact quotes + multi-doc synthesis
```

### Architecture

```
Client VPC (each):
  Document Pipeline:
    SharePoint/GDrive → Parser (AWS Textract / Azure DI) →
    Legal-specific chunker (section-aware) →
    Embedding service (local: bge-large) →
    pgvector (RDS PostgreSQL)
  
  Query Pipeline:
    User Query →
    Query expansion (HyDE for rare legal terms) →
    Hybrid retrieval (semantic + boolean) →
    Cross-encoder rerank →
    Context assembly with exact quote extraction →
    LLM generation (private endpoint: Azure OpenAI in VNet) →
    Citation validation (regex check that quotes exist in sources) →
    Response
```

### Legal-Specific Design Decisions

```
1. Section-aware chunking:
   - Split on legal section headers (§, "SECTION", "Article")
   - Keep sections intact — never split a clause
   - Chunk size: up to 2000 tokens per section
   - Parent-child: return full section but index at paragraph level

2. Exact quote extraction:
   - After retrieval, use regex to find verbatim quotes in source
   - Every citation must have a verifiable source span
   - Reject responses where citations can't be verified
   - "According to [Section 4.2, page 12]: 'exact text here'"

3. Confidence scoring:
   - Calculate: retrieval score × LLM confidence
   - Low confidence (< 0.7): return "Insufficient information — consult senior counsel"
   - Never hallucinate legal citations

4. Audit trail:
   - Every query and response logged with:
     source document IDs, chunks used, user ID, timestamp
   - Immutable audit log (append-only S3 + CloudTrail)
```

### Anti-Hallucination Guards

```python
class LegalRAGGuard:
    """Strict anti-hallucination guard for legal RAG."""
    
    def validate_response(self, response: str, source_docs: list[str]) -> dict:
        """Verify all quotes in response exist in sources."""
        import re
        
        quotes = re.findall(r'"([^"]{20,})"', response)
        validation = {"passed": True, "unverified_quotes": []}
        
        for quote in quotes:
            found = any(quote in doc for doc in source_docs)
            if not found:
                validation["passed"] = False
                validation["unverified_quotes"].append(quote[:80])
        
        return validation
    
    async def safe_generate(self, question: str, docs: list) -> dict:
        doc_texts = [d.page_content for d in docs]
        
        response = await llm.ainvoke(
            self.build_legal_prompt(question, doc_texts)
        )
        
        validation = self.validate_response(response.content, doc_texts)
        
        if not validation["passed"]:
            # Regenerate without the unverified quotes
            response = await llm.ainvoke(
                self.build_strict_prompt(question, doc_texts)
            )
        
        return {
            "answer": response.content,
            "citations": [{"source": d.metadata["source"], "page": d.metadata.get("page")} for d in docs],
            "validation_passed": validation["passed"],
        }
```

---

## Design 3: Multi-Agent Research System

### Requirements

```
Task: Given any research question, produce a comprehensive report with citations
Scale: 1000 research tasks/day, each taking 2-10 minutes
Quality: Comparable to a junior analyst's research
Features: Web search, academic papers, data analysis, chart generation
```

### Agent Architecture

```
Orchestrator (LangGraph Supervisor)
├── Research Planner Agent
│   → Creates structured research plan with 3-7 sub-questions
├── Research Worker Agents (parallel, up to 5)
│   ├── Web Search Agent (Tavily)
│   ├── Academic Search Agent (Semantic Scholar API)
│   ├── Data Analyst Agent (Python REPL)
│   └── Fact Checker Agent
├── Writer Agent
│   → Synthesizes all findings into report
└── Editor Agent
    → Quality check, consistency, citations

State: LangGraph TypedDict with PostgreSQL checkpointer
Coordination: LangGraph Send() for parallel dispatch
Recovery: Resume from checkpoint on failure
```

### Key Design Patterns

```python
# Hierarchical task decomposition with parallel execution
class ResearchOrchestrator:
    
    async def research(self, question: str) -> Report:
        # Phase 1: Plan (sequential)
        plan = await self.planner.create_plan(question)
        
        # Phase 2: Research (parallel)
        tasks = [
            self.research_worker.research(subtask)
            for subtask in plan.subtasks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Phase 3: Write (sequential, needs all results)
        draft = await self.writer.synthesize(question, results)
        
        # Phase 4: Edit (sequential)
        return await self.editor.review_and_finalize(draft)
    
    def estimate_cost(self, plan: ResearchPlan) -> float:
        cost_per_subtask = 0.05  # GPT-4o-mini for search, 4o for write
        write_cost = 0.15
        return len(plan.subtasks) * cost_per_subtask + write_cost
```

### Fault Tolerance

```
Worker failures:
- Retry up to 3 times with exponential backoff
- On persistent failure: mark subtask as "partial" and continue
- Report clearly states: "Data unavailable for [subtask]"

Checkpoint strategy:
- Save state after every phase completion
- Allow resume from any phase checkpoint
- Long-running (> 5 min): send heartbeat to caller

Cost controls:
- Maximum 20 LLM calls per research task
- Token budget: 100K tokens per task
- If budget exceeded: use faster/cheaper model for remaining calls
```

---

## Design 4: Customer Support AI

### Requirements

```
Scale: 500K customer queries/day (peak 50K/hour)
Languages: English, Spanish, French, German
Channels: Web chat, mobile, email, voice
Latency: < 1s for chat, < 5s for email
Escalation: Auto-escalate to human when confidence < 0.75
Integration: CRM (Salesforce), ticketing (Jira), knowledge base
```

### Architecture

```
Channels
├── Web Chat → WebSocket → Chat Service
├── Mobile → REST → Chat Service
├── Email → Email Processor → Async Queue
└── Voice → STT (Whisper) → Chat Service

Chat Service:
├── Language Detector → Route to language-specific pipeline
├── Intent Classifier (fast, separate model) → Route type:
│   ├── FAQ → Direct RAG answer
│   ├── Account issue → CRM lookup + RAG
│   ├── Technical → Deep agent reasoning
│   └── Complaint → Escalate immediately
├── RAG Pipeline (product knowledge base)
├── CRM Integration (order status, account data)
├── Escalation Engine (confidence < 0.75)
└── Response Generator

Agent Queue (human escalation):
├── Priority: VIP > Escalated > Standard
└── Context handoff: full conversation + AI summary
```

### Confidence Scoring and Escalation

```python
class EscalationEngine:
    """Decide when to escalate to human agent."""
    
    def __init__(self, escalation_threshold: float = 0.75):
        self.threshold = escalation_threshold
    
    async def should_escalate(
        self,
        query: str,
        ai_response: str,
        retrieval_scores: list[float],
        sentiment: str,
    ) -> tuple[bool, str]:
        """Return (should_escalate, reason)."""
        
        # Rule-based triggers (always escalate)
        escalation_keywords = ["cancel", "refund", "legal", "lawyer", "lawsuit", "fraud"]
        if any(kw in query.lower() for kw in escalation_keywords):
            return True, "sensitive_topic"
        
        # Negative sentiment with unresolved issue
        if sentiment == "very_negative":
            return True, "customer_frustration"
        
        # Low retrieval confidence
        if retrieval_scores and max(retrieval_scores) < 0.6:
            return True, "low_retrieval_confidence"
        
        # LLM self-assessment
        confidence_score = await self.assess_response_confidence(query, ai_response)
        if confidence_score < self.threshold:
            return True, f"low_confidence_{confidence_score:.2f}"
        
        return False, "resolved"
    
    async def assess_response_confidence(self, query: str, response: str) -> float:
        """LLM rates its own confidence."""
        result = await llm.ainvoke([HumanMessage(
            content=f"""Rate confidence 0-10 that this response fully resolves the customer's issue.
Query: {query}
Response: {response}
Return ONLY a number."""
        )])
        try:
            return float(result.content.strip()) / 10.0
        except Exception:
            return 0.5
```

### Multi-Language Design

```
Approach: Translate-then-generate vs native multilingual

Option A: Translate → English RAG → Translate back
  + One knowledge base, one embedding model
  - Translation latency (200ms), quality loss

Option B: Multilingual embeddings (BAAI/bge-m3)
  + No translation overhead
  + Single index handles all languages
  - Slightly lower quality than English-only embeddings

Recommendation: Option B with BAAI/bge-m3 for < 5 language coverage
→ Store original language content
→ Multilingual embeddings for cross-lingual retrieval
→ Native language generation (LLM handles multilingual natively)
```

---

## Design 5: AI Coding Assistant (GitHub Copilot-like)

### Requirements

```
Scale: 1M developers, 10M code completions/day
Latency: < 100ms for single-line completion, < 500ms for block
Context: Current file, open files, repository structure
Privacy: Code never stored, no training on private repos
Features: Inline completion, chat, explain code, fix bugs
```

### Architecture

```
IDE Plugin (VS Code, JetBrains)
  ↓
Local Cache (recent completions)
  ↓ [cache miss]
Debouncer (wait 50ms for typing to pause)
  ↓
Context Collector:
├── Current file content (before/after cursor)
├── File type and language
├── Imported modules/types
├── Recent edits (sliding window)
└── Repository structure (file tree, relevant files via BM25)
  ↓
Context Compressor (trim to 2048 tokens)
  ↓
API Gateway → Load Balancer
  ↓
Completion Service:
├── Small model (< 100ms): StarCoder-3B or Phi-3.5
└── Large model (< 500ms): GPT-4o / Claude Sonnet
  ↓
Response Streamer (token-by-token)
  ↓
IDE Renderer
```

### Fill-in-the-Middle (FIM) Prompting

```python
# Special prompt format for code completion
def build_fim_prompt(
    prefix: str,       # Code before cursor
    suffix: str,       # Code after cursor
    language: str,
) -> str:
    """Build Fill-in-the-Middle prompt."""
    return f"<fim_prefix>{prefix}<fim_suffix>{suffix}<fim_middle>"
    # Model fills in the middle section

# Context window allocation
def allocate_context(
    current_file: str,
    cursor_position: int,
    related_files: list[str],
    max_tokens: int = 2048,
) -> dict:
    prefix = current_file[:cursor_position]
    suffix = current_file[cursor_position:]
    
    # Most recent context matters most
    prefix_tokens = min(1024, max_tokens // 2)
    suffix_tokens = min(256, max_tokens // 4)
    cross_file_tokens = max_tokens - prefix_tokens - suffix_tokens
    
    return {
        "prefix": prefix[-prefix_tokens * 4:],   # ~4 chars/token
        "suffix": suffix[:suffix_tokens * 4],
        "cross_file_context": "\n".join(related_files)[:cross_file_tokens * 4],
    }
```

### Latency Optimization

```
Speculative Decoding:
- Small draft model (3B) proposes 4-8 tokens in parallel
- Large verifier model accepts/rejects in one forward pass
- Result: 2-3x throughput with same quality as large model

Request Deduplication:
- Hash context window → if same as in-flight request, share result
- Prevents thundering herd when multiple developers type same code

Prefix Caching:
- Common library imports, class definitions never change
- Cache their KV activations across requests
- 30-50% token reduction for typical code files
```

---

## Design 6: Document Intelligence Platform

### Requirements

```
Scale: Process 10M documents/day (PDFs, Word, Excel, images)
Document types: Invoices, contracts, financial reports, medical records
Output: Structured JSON extraction with confidence scores
Latency: < 30s per document (async OK), < 5s for real-time
Accuracy: 99%+ for structured fields (amounts, dates, names)
```

### Architecture

```
Document Upload (S3)
  ↓
Document Classifier (FastAPI + lightweight model)
  → routes to specialized pipeline
  ├── Invoice pipeline
  ├── Contract pipeline
  ├── Financial report pipeline
  └── Medical record pipeline
  ↓
Pre-processor:
├── PDF → text (PyMuPDF for digital, OCR for scanned)
├── Image → OCR (AWS Textract / Google DI)
├── Excel → structured data
└── Word → sections + tables
  ↓
Field Extractor (multimodal LLM: GPT-4o-vision)
├── Page-level extraction (parallel)
└── Field-level confidence scoring
  ↓
Post-processor:
├── Field validation (regex, lookup tables)
├── Cross-field consistency checks
└── Confidence aggregation
  ↓
Output: Structured JSON + confidence scores
  ↓
Human Review Queue (for low-confidence extractions)
```

### Multimodal Extraction

```python
import base64
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

class InvoiceData(BaseModel):
    vendor_name: str = Field(description="Vendor/supplier name")
    invoice_number: str = Field(description="Invoice number/ID")
    invoice_date: str = Field(description="Invoice date (YYYY-MM-DD)")
    total_amount: float = Field(description="Total invoice amount")
    currency: str = Field(description="Currency code (USD, EUR, etc.)")
    line_items: list[dict] = Field(description="List of line items with description, qty, amount")
    
class ExtractionResult(BaseModel):
    data: InvoiceData
    confidence: float = Field(ge=0, le=1)
    extraction_method: str

async def extract_invoice(pdf_page_image: bytes) -> ExtractionResult:
    """Extract structured data from invoice image using GPT-4o vision."""
    
    image_b64 = base64.b64encode(pdf_page_image).decode()
    
    vision_llm = ChatOpenAI(model="gpt-4o").with_structured_output(InvoiceData)
    
    result = await vision_llm.ainvoke([
        HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}",
                    "detail": "high"
                }
            },
            {
                "type": "text",
                "text": "Extract all invoice fields. Be exact with numbers and dates."
            }
        ])
    ])
    
    # Calculate confidence based on completeness
    required_fields = ["vendor_name", "invoice_number", "total_amount"]
    filled = sum(1 for f in required_fields if getattr(result, f, None))
    confidence = filled / len(required_fields)
    
    return ExtractionResult(
        data=result,
        confidence=confidence,
        extraction_method="gpt4o_vision"
    )
```

---

## Design 7: AI Observability Platform

### Requirements

```
Scale: Monitor 1000+ AI applications, 1B+ LLM calls/day
Features: Trace collection, metric aggregation, alerting, evaluation
Latency: Traces visible within 30s of generation
Storage: Retain 90-day hot + 2-year cold
```

### Architecture

```
SDK (LangChain callback, OpenTelemetry)
  ↓
Trace Collector (Kafka: 10K events/sec per partition)
  ↓
Stream Processor (Flink/Dataflow):
├── Real-time metrics (latency, cost, error rate)
├── Anomaly detection (latency spikes)
├── Evaluation triggers (sample 1% for LLM eval)
└── Alert evaluation
  ↓
Storage:
├── Hot (Elasticsearch): last 30 days, full-text + filter
├── Warm (BigQuery): last 90 days, aggregated metrics
└── Cold (GCS Parquet): 2-year archive
  ↓
API Layer (FastAPI):
├── Trace search and replay
├── Metric dashboards
├── Alert management
└── Eval dataset management
```

### Trace Schema

```python
@dataclass
class LLMTrace:
    trace_id: str
    parent_span_id: Optional[str]
    span_type: str  # llm_call | chain | retrieval | tool
    
    # Timing
    start_time: datetime
    end_time: datetime
    latency_ms: float
    ttft_ms: float  # Time to first token
    
    # LLM specifics
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    
    # Content (hashed for privacy)
    input_hash: str
    output_hash: str
    
    # Context
    user_id: str
    session_id: str
    app_name: str
    app_version: str
    
    # Quality
    eval_scores: dict  # Async evaluation results
    user_feedback: Optional[float]  # -1, 0, 1
    
    # Error
    error: Optional[str]
    finish_reason: str  # stop | length | content_filter | error
```

---

## Design 8: Semantic Search Engine

### Requirements

```
Scale: 1B documents, 100M queries/day
Latency: < 100ms p99
Features: Hybrid search (semantic + keyword), faceted filtering, personalization
Multilingual: 50+ languages
Freshness: New docs indexed within 5 minutes
```

### Architecture

```
Indexing Pipeline:
  Documents →
  Language Detection →
  Translation to English (optional, keep original) →
  Multilingual Embedding (BAAI/bge-m3) →
  Shard-based Vector Index (Qdrant cluster, 20 shards) →
  Keyword Index (Elasticsearch, BM25) →
  Metadata Store (PostgreSQL, facets)

Query Pipeline:
  Query →
  Intent Classification (filter? semantic? hybrid?) →
  ┌─────────────────────────────────┐
  │ Parallel retrieval:             │
  │  - Vector search (Qdrant, k=50) │
  │  - BM25 (Elastic, k=50)         │
  └──────────────┬──────────────────┘
              RRF Fusion (→ top 100)
                 ↓
  Personalization Re-ranker
  (user embedding similarity)
                 ↓
  LLM-powered snippet extraction
                 ↓
  Results (10 per page)
```

### Embedding at Billion-Scale

```
Index size: 1B docs × 1024D float32 = 4TB embedding storage

Optimization: Scalar quantization (int8) → 1TB storage, 0.5% quality loss

Sharding strategy:
- 20 shards × 50M docs each
- Consistent hashing on document_id
- Replication factor: 3 (HA, no data loss)

Query routing:
- Broadcast to all 20 shards
- Merge top-K from each shard
- Total latency = max(shard_latency) + merge time
- Shard latency target: < 50ms
```

---

## Design 9: Voice AI Assistant

### Requirements

```
Scale: 10M users, 100M voice queries/day
Latency: < 800ms end-to-end (wake word to first audio byte)
Languages: 30 languages
Features: Streaming STT, LLM reasoning, TTS, interrupt handling, tool calling
```

### Architecture

```
Audio Stream (mic)
  ↓
Wake Word Detection (on-device, < 5ms)
  ↓
Streaming STT (Whisper streaming)
├── Partial transcript updates (every 500ms)
└── Final transcript when silence detected
  ↓
Intent Pre-classification (fast, 20ms)
├── Simple query → cached response
└── Complex query → LLM
  ↓
LLM (streaming generation)
├── Tool calls (calendar, weather, smart home)
└── Text response
  ↓
Streaming TTS (ElevenLabs / Google Cloud TTS)
├── Convert first sentence as soon as available
└── Stream audio before full response ready
  ↓
Audio Output
```

### Latency Breakdown

```
Target: 800ms end-to-end
- Wake word: 5ms (on-device)
- STT (streaming partial): 200ms to first partial
- LLM TTFT: 300ms (gpt-4o-mini)
- TTS first byte: 250ms
- Network: 50ms
Total: 805ms (barely over target)

Optimization to hit < 800ms:
1. Start TTS on first LLM sentence (not full response)
2. Use local TTS model (< 50ms) vs cloud (250ms) → saves 200ms
3. Cache common responses (weather, time, etc.) → 5ms
```

---

## Design 10: Enterprise Embedding Pipeline

### Requirements

```
Scale: Ingest 1M documents/day, 100B tokens total corpus
Sources: S3, GCS, SharePoint, databases
Freshness: Changed docs re-embedded within 1 hour
Deduplication: Skip unchanged documents
Multi-tenancy: Isolated namespaces, access control
```

### Architecture

```
Source Systems → Change Detection →
  ┌────────────────────────────────────┐
  │  INGESTION QUEUE (Pub/Sub/Kafka)   │
  └───────────────┬────────────────────┘
                  ↓
  ┌────────────────────────────────────┐
  │  DOCUMENT PROCESSOR (Cloud Run)    │
  │  - Parse (PDF, Word, HTML, etc.)   │
  │  - Extract text + metadata         │
  │  - Content hash (dedup check)      │
  └───────────────┬────────────────────┘
                  ↓ [new/changed docs only]
  ┌────────────────────────────────────┐
  │  CHUNKER (Cloud Run)               │
  │  - Recursive text splitter          │
  │  - Parent-child for long docs      │
  │  - Store chunks in PostgreSQL      │
  └───────────────┬────────────────────┘
                  ↓
  ┌────────────────────────────────────┐
  │  EMBEDDING WORKER (GKE + GPU)      │
  │  - Batch embed (32 chunks/call)    │
  │  - Local model: bge-large (free)   │
  │  - Fallback: OpenAI API            │
  └───────────────┬────────────────────┘
                  ↓
  ┌────────────────────────────────────┐
  │  VECTOR STORE WRITER               │
  │  - Upsert to Qdrant/pgvector       │
  │  - Update chunk → embedding index  │
  │  - Delete stale embeddings         │
  └────────────────────────────────────┘
```

### Change Detection and Deduplication

```python
class ChangeDetectionService:
    """Only re-process documents that have actually changed."""
    
    def __init__(self, db):
        self.db = db
    
    async def get_documents_to_process(self, source_documents: list[dict]) -> list[dict]:
        """Filter to only changed or new documents."""
        to_process = []
        
        for doc in source_documents:
            content_hash = hashlib.sha256(doc["content"].encode()).hexdigest()
            
            # Check if we've seen this exact content before
            existing = await self.db.fetch_one(
                "SELECT id FROM documents WHERE content_hash = $1 AND tenant_id = $2",
                content_hash, doc["tenant_id"]
            )
            
            if existing:
                # Unchanged — skip
                continue
            
            # Check if it's an update to existing source URL
            existing_by_url = await self.db.fetch_one(
                "SELECT id FROM documents WHERE source_url = $1 AND tenant_id = $2",
                doc["source_url"], doc["tenant_id"]
            )
            
            if existing_by_url:
                doc["operation"] = "update"
                doc["old_document_id"] = existing_by_url["id"]
            else:
                doc["operation"] = "insert"
            
            doc["content_hash"] = content_hash
            to_process.append(doc)
        
        return to_process
    
    async def delete_stale_chunks(self, old_document_id: str, tenant_id: str):
        """Remove old embeddings when document is updated."""
        await self.db.execute(
            "DELETE FROM chunks WHERE document_id = $1 AND tenant_id = $2",
            old_document_id, tenant_id
        )
        # Also remove from vector store
        await self.vectorstore.delete(
            filter={"document_id": old_document_id, "tenant_id": tenant_id}
        )
```

### Cost Optimization for Large-Scale Embedding

```python
EMBEDDING_COST_COMPARISON = {
    "openai_3_small": {
        "cost_per_1M_tokens": 0.02,
        "daily_cost_1B_tokens": 20.00,
        "latency_ms": 50,
        "quality_score": 85,
    },
    "bge_large_local_a100": {
        "cost_per_1M_tokens": 0.001,  # GPU rental cost
        "daily_cost_1B_tokens": 1.00,
        "latency_ms": 15,
        "quality_score": 83,
    },
    "bge_small_local_gpu": {
        "cost_per_1M_tokens": 0.0002,
        "daily_cost_1B_tokens": 0.20,
        "latency_ms": 5,
        "quality_score": 78,
    }
}

# At 1B tokens/day: Local bge-large is 20x cheaper than OpenAI
# At 100K tokens/day: OpenAI API wins (no GPU cost)
# Crossover point: ~10M tokens/day
```

---

*Next: Module 19 — Advanced and Emerging Topics*
