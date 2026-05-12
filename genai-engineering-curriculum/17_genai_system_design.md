# Module 17 — GenAI System Design

> System design for AI applications follows the same principles as distributed systems design — but with unique constraints around non-determinism, latency profiles, and evaluation. This module is a reference for senior engineering interviews.

---

## Table of Contents

1. [GenAI System Design Framework](#1-framework)
2. [Core Architecture Components](#2-core-architecture-components)
3. [RAG System Design](#3-rag-system-design)
4. [Agent System Design](#4-agent-system-design)
5. [Multi-Tenant AI Platform Design](#5-multi-tenant-ai-platform-design)
6. [Streaming Architecture](#6-streaming-architecture)
7. [Feedback and Improvement Loop](#7-feedback-and-improvement-loop)
8. [Scalability Patterns](#8-scalability-patterns)
9. [Data Architecture for AI](#9-data-architecture-for-ai)
10. [Design Tradeoffs Reference](#10-design-tradeoffs-reference)
11. [Interview Questions](#11-interview-questions)

---

## 1. Framework

When approaching a GenAI system design question, follow this framework:

### 5-Step Approach

```
1. CLARIFY REQUIREMENTS (3-5 min)
   - Scale: How many users/requests/day?
   - Latency: Real-time (<500ms), near-real-time (<5s), batch?
   - Quality: Accuracy requirements? Acceptable hallucination rate?
   - Data: Proprietary data? Sensitive/regulated? Size?
   - Deployment: Cloud? On-prem? Edge?

2. IDENTIFY THE CORE PIPELINE (2-3 min)
   - Is this RAG, agents, pure generation, or hybrid?
   - What's the data flow: user query → X → Y → response?

3. DESIGN THE COMPONENTS (10-15 min)
   - Ingestion pipeline (if any)
   - Retrieval layer
   - Generation layer
   - Response delivery

4. ADDRESS NON-FUNCTIONAL REQUIREMENTS (5-7 min)
   - Scalability: How does this handle 10x load?
   - Reliability: What fails? How to recover?
   - Cost: Estimate tokens/day and cost
   - Observability: How do you know it's working?

5. DISCUSS TRADEOFFS (2-3 min)
   - What did you simplify? What would you change with more time/budget?
```

---

## 2. Core Architecture Components

### Component Catalog

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GENAI SYSTEM COMPONENTS                         │
├─────────────────┬───────────────────────────────────────────────────┤
│ INGESTION       │ Document loaders, parsers, chunkers               │
│                 │ ETL pipelines (Airflow, Cloud Composer)           │
│                 │ Change data capture for live data                 │
├─────────────────┼───────────────────────────────────────────────────┤
│ INDEXING        │ Vector stores (Pinecone, Weaviate, pgvector)      │
│                 │ BM25/keyword index (Elasticsearch, Typesense)     │
│                 │ Metadata stores (PostgreSQL, Firestore)           │
├─────────────────┼───────────────────────────────────────────────────┤
│ RETRIEVAL       │ Dense retrieval (ANN search)                      │
│                 │ Sparse retrieval (BM25)                           │
│                 │ Hybrid (RRF fusion)                               │
│                 │ Re-ranking (cross-encoder)                        │
├─────────────────┼───────────────────────────────────────────────────┤
│ GENERATION      │ LLM API (OpenAI, Anthropic, Gemini)               │
│                 │ Self-hosted (vLLM, Ollama)                        │
│                 │ LLM router/proxy (LiteLLM)                        │
├─────────────────┼───────────────────────────────────────────────────┤
│ CACHING         │ Exact cache (Redis)                               │
│                 │ Semantic cache (vector similarity)                │
│                 │ KV cache (vLLM PagedAttention)                    │
├─────────────────┼───────────────────────────────────────────────────┤
│ ORCHESTRATION   │ LangChain/LCEL (chains)                           │
│                 │ LangGraph (stateful agents)                       │
│                 │ Temporal/Airflow (long workflows)                 │
├─────────────────┼───────────────────────────────────────────────────┤
│ OBSERVABILITY   │ LangSmith/Langfuse (LLM-specific tracing)        │
│                 │ OpenTelemetry (general distributed tracing)       │
│                 │ Evaluation datasets + automated scoring           │
├─────────────────┼───────────────────────────────────────────────────┤
│ DELIVERY        │ REST API (FastAPI)                                │
│                 │ WebSocket (real-time bidirectional)               │
│                 │ SSE (Server-Sent Events for streaming)            │
└─────────────────┴───────────────────────────────────────────────────┘
```

### Request Flow Template

```
User Request
    ↓
API Gateway (auth, rate limit, routing)
    ↓
Cache Check (Redis exact → semantic)
    ↓ [cache miss]
Pre-processing (PII redaction, guardrails, query rewrite)
    ↓
Retrieval (vector search + keyword + rerank)
    ↓
Context Assembly (format docs, truncate to budget)
    ↓
LLM Router (model selection based on cost/complexity)
    ↓
LLM Inference (with timeout, retry)
    ↓
Post-processing (output guardrails, format, citations)
    ↓
Cache Write (store result)
    ↓
Response Delivery (streaming SSE or REST)
    ↓
Observability (trace log, cost record, eval trigger)
```

---

## 3. RAG System Design

### Architecture Diagram

```
OFFLINE (Ingestion Pipeline):
                                                        
  Data Sources                                          
  ┌──────────┐  ┌──────────┐  ┌──────────┐            
  │  PDFs    │  │ Databases│  │  APIs    │            
  └────┬─────┘  └────┬─────┘  └────┬─────┘            
       └──────────────┴──────────────┘                 
                      ↓                                
              Document Loader                          
                      ↓                                
              Text Chunker                             
          (recursive + semantic)                       
                      ↓                                
          ┌───────────┴────────────┐                   
          │    Embedding Model     │                   
          │  (text-embedding-3)    │                   
          └───────────┬────────────┘                   
                      ↓                                
          ┌───────────┴────────────┐                   
          │     Vector Store       │ ← BM25 Index      
          │  (Pinecone / pgvector) │                   
          └────────────────────────┘                   

ONLINE (Query Pipeline):
                                                        
  User Query                                           
       ↓                                               
  Query Rewriting  ← [LLM: expand/rephrase]            
       ↓                                               
  ┌────┴────┐                                          
  │  Dense  │  ← Vector search (k=50)                  
  │  Sparse │  ← BM25 keyword (k=50)                   
  └────┬────┘                                          
       ↓                                               
  RRF Fusion (merge results)                           
       ↓                                               
  Re-Ranker  ← cross-encoder (→ top k=5)               
       ↓                                               
  Context Assembly + Prompt                            
       ↓                                               
  LLM Generation                                       
       ↓                                               
  Response + Citations                                 
```

### RAG Design Decisions

```python
RAG_DESIGN_CHOICES = {
    "chunking": {
        "question": "How to chunk documents?",
        "options": {
            "fixed_size": "Simple, fast. Good for homogeneous content.",
            "recursive_char": "Respects natural boundaries. Best default.",
            "semantic": "Groups semantically related content. Best quality, 3x slower.",
            "parent_child": "Indexes small chunks, returns large parent. Best for dense text.",
        },
        "recommendation": "recursive_char for most cases; parent_child for PDFs and reports"
    },
    "embedding_model": {
        "options": {
            "text-embedding-3-small": "Cheap, fast, 1536D. Good for high volume.",
            "text-embedding-3-large": "Best OpenAI quality, 3072D. Use for high-stakes.",
            "BAAI/bge-large-en": "Local, free, 1024D. Good quality, no API cost.",
        },
        "recommendation": "text-embedding-3-small for cost-sensitive; bge-large for privacy"
    },
    "retrieval_strategy": {
        "options": {
            "dense_only": "Simple. Misses exact keyword matches.",
            "sparse_only": "Good for technical docs. Misses semantic similarity.",
            "hybrid": "Best quality. 20-30% latency overhead.",
            "hybrid_with_rerank": "Best quality. 50-100ms overhead. Worth it for complex queries.",
        },
        "recommendation": "hybrid_with_rerank for production; dense_only for < 10ms budget"
    },
    "context_window_management": {
        "options": {
            "stuff": "All docs in one prompt. Simple but limited context.",
            "map_reduce": "Summarize each doc, combine. Good for many docs.",
            "refine": "Iteratively refine answer with each doc. Best but slowest.",
        },
        "recommendation": "stuff with top-k=5 for most cases"
    },
}
```

### Production RAG Architecture Code Sketch

```python
from dataclasses import dataclass

@dataclass
class RAGSystemConfig:
    # Ingestion
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunking_strategy: str = "recursive"  # "recursive" | "semantic" | "parent_child"
    
    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_cache: bool = True
    
    # Retrieval
    retrieval_strategy: str = "hybrid"  # "dense" | "sparse" | "hybrid"
    top_k_retrieval: int = 50  # Fetch more for reranking
    top_k_final: int = 5       # After reranking
    use_reranker: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Generation
    llm_model: str = "gpt-4o-mini"
    max_context_tokens: int = 8000
    temperature: float = 0
    
    # Caching
    use_exact_cache: bool = True
    use_semantic_cache: bool = True
    cache_ttl_seconds: int = 3600
    
    # Observability
    langsmith_project: str = "rag-production"
    eval_on_percentage: float = 0.01  # 1% of requests get evaluated


def estimate_rag_latency(config: RAGSystemConfig) -> dict:
    """Estimate latency breakdown for a RAG configuration."""
    
    latency_breakdown = {
        "query_embedding_ms": 50 if config.embedding_model.startswith("text-") else 10,
        "vector_search_ms": 20,
        "bm25_search_ms": 5 if config.retrieval_strategy in ["sparse", "hybrid"] else 0,
        "reranking_ms": 80 if config.use_reranker else 0,
        "context_assembly_ms": 5,
        "llm_ttft_ms": 300 if "mini" in config.llm_model else 500,
        "llm_generation_ms": 500,  # Depends on output length
    }
    
    total_ms = sum(latency_breakdown.values())
    cache_hit_ms = 5  # Redis lookup
    
    return {
        **latency_breakdown,
        "total_p50_ms": total_ms,
        "total_with_cache_ms": cache_hit_ms,
        "recommendation": "Consider semantic cache if p50 > 2000ms" if total_ms > 2000 else "Latency acceptable"
    }
```

---

## 4. Agent System Design

### ReAct Agent Architecture

```
User Goal
    ↓
Context Injection
(system prompt + memory + tools list)
    ↓
┌─────────────────────────────────────┐
│          AGENT LOOP                 │
│                                     │
│   LLM Reasoning (Thought)           │
│       ↓                             │
│   Decision Gate ─────── Final Answer → User
│       │                             │
│   Tool Selection                    │
│       ↓                             │
│   ┌───┴──────────────────────┐      │
│   │   Tool Execution Engine  │      │
│   │  ┌────┐ ┌────┐ ┌────┐   │      │
│   │  │ T1 │ │ T2 │ │ T3 │  │      │
│   │  └────┘ └────┘ └────┘   │      │
│   │  (parallel, timeout)     │      │
│   └───┬──────────────────────┘      │
│       ↓                             │
│   Tool Results → Context Update     │
│       ↓                             │
│   Check Limits (iter, cost, time)   │
└─────────────────────────────────────┘
    ↓
Checkpointer (PostgreSQL)
(Save state for recovery)
```

### Agent System Capacity Planning

```python
def estimate_agent_cost(
    avg_iterations_per_task: float,
    llm_tokens_per_iteration: int,
    tool_calls_per_iteration: float,
    daily_tasks: int,
    model: str = "gpt-4o",
) -> dict:
    """Estimate costs for an agent system."""
    
    cost_per_1k = {"gpt-4o": 0.005, "gpt-4o-mini": 0.000375, "claude-sonnet-4-5": 0.009}
    cost = cost_per_1k.get(model, 0.005)
    
    llm_cost_per_task = (avg_iterations_per_task * llm_tokens_per_iteration / 1000) * cost
    
    daily_cost = daily_tasks * llm_cost_per_task
    monthly_cost = daily_cost * 30
    
    avg_task_latency = avg_iterations_per_task * 2.5  # ~2.5s per iteration
    
    return {
        "model": model,
        "avg_iterations": avg_iterations_per_task,
        "llm_cost_per_task_usd": round(llm_cost_per_task, 4),
        "daily_cost_usd": round(daily_cost, 2),
        "monthly_cost_usd": round(monthly_cost, 2),
        "avg_task_latency_s": round(avg_task_latency, 1),
        "note": f"At {daily_tasks}/day × ${llm_cost_per_task:.4f}/task"
    }

# Example: Research agent
print(estimate_agent_cost(
    avg_iterations_per_task=8,
    llm_tokens_per_iteration=2000,
    tool_calls_per_iteration=2,
    daily_tasks=1000,
    model="gpt-4o",
))
# {'daily_cost_usd': 80.00, 'monthly_cost_usd': 2400.00, 'avg_task_latency_s': 20.0}
```

---

## 5. Multi-Tenant AI Platform Design

```
                      ┌─────────────────────────────┐
                      │    API GATEWAY               │
                      │  (Auth, rate limit, routing)  │
                      └──────────┬──────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
     Tenant A │         Tenant B │         Tenant C │
              ↓                  ↓                  ↓
    ┌─────────────────┐  ┌────────────────┐  ┌─────────────────┐
    │  Tenant Context │  │ Tenant Context │  │ Tenant Context  │
    │  - Prompt vers. │  │ - Custom model │  │ - Data filter   │
    │  - Budget       │  │ - Budget       │  │ - Budget        │
    └────────┬────────┘  └───────┬────────┘  └────────┬────────┘
             │                   │                    │
             └───────────────────┼────────────────────┘
                                 ↓
                   ┌─────────────────────────┐
                   │    LLM ROUTER            │
                   │  (LiteLLM Proxy)         │
                   │  - Load balancing        │
                   │  - Fallback chains       │
                   │  - Cost tracking         │
                   └────────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ↓                 ↓                  ↓
        OpenAI API        Anthropic API      vLLM (self-hosted)
```

### Tenant Isolation Patterns

```python
class MultiTenantRAGService:
    """RAG service with complete tenant isolation."""
    
    def __init__(self, vectorstore_factory, llm_factory):
        self.vectorstore_factory = vectorstore_factory
        self.llm_factory = llm_factory
        self._tenant_stores: dict = {}
    
    def get_tenant_vectorstore(self, tenant_id: str):
        """Each tenant gets isolated vector namespace."""
        if tenant_id not in self._tenant_stores:
            # Strategy 1: Namespace isolation (same cluster, different namespace)
            self._tenant_stores[tenant_id] = self.vectorstore_factory(
                namespace=f"tenant_{tenant_id}",
                metadata_filter={"tenant_id": tenant_id}
            )
        return self._tenant_stores[tenant_id]
    
    async def query(self, tenant_id: str, question: str, user_id: str) -> dict:
        # 1. Tenant-specific retrieval
        store = self.get_tenant_vectorstore(tenant_id)
        docs = store.similarity_search(
            question,
            k=5,
            filter={"tenant_id": tenant_id}  # Double-check isolation
        )
        
        # 2. Tenant-specific LLM config
        llm = self.llm_factory(
            model=self.get_tenant_model(tenant_id),
            max_tokens=self.get_tenant_token_limit(tenant_id),
        )
        
        # 3. Generate with tenant context
        response = await llm.ainvoke(self.build_prompt(question, docs, tenant_id))
        
        # 4. Track cost per tenant
        self.cost_tracker.record(tenant_id, response.usage_metadata)
        
        return {"answer": response.content, "sources": len(docs)}
    
    def get_tenant_model(self, tenant_id: str) -> str:
        """Tenant can configure their own model tier."""
        tier_models = {
            "enterprise": "gpt-4o",
            "pro": "gpt-4o-mini",
            "free": "gpt-4o-mini",
        }
        tier = self.get_tenant_tier(tenant_id)
        return tier_models.get(tier, "gpt-4o-mini")
```

### Vector Store Isolation Strategies

```
Strategy 1: Namespace Isolation (Pinecone)
  - All tenants share one index, different namespaces
  - Pro: Cost-efficient (1 index), instant tenant provisioning
  - Con: Single point of failure, shared throughput limits
  - Use when: < 100 tenants, cost-sensitive

Strategy 2: Collection Isolation (Qdrant/Chroma)
  - Each tenant has separate collection
  - Pro: Complete isolation, independent scaling
  - Con: More expensive at scale
  - Use when: Tenants have strict data isolation requirements

Strategy 3: Cluster Isolation
  - Each enterprise tenant gets dedicated cluster
  - Pro: Complete isolation, custom config
  - Con: Very expensive
  - Use when: Regulated industries (healthcare, finance)

Strategy 4: Metadata Filtering (pgvector)
  - Single table, tenant_id in metadata
  - Filter every query with tenant_id
  - Pro: SQL-based, flexible querying
  - Con: Must never forget the filter
  - Use when: Building on existing Postgres infrastructure
```

---

## 6. Streaming Architecture

```
Client                    API Gateway              LLM Service
  │                           │                        │
  │ POST /chat/stream          │                        │
  │──────────────────────────►│                        │
  │                           │ Start async job        │
  │                           │───────────────────────►│
  │◄──────────────────────────│                        │
  │ 200 OK (SSE connection)   │                        │
  │                           │    Token 1             │
  │                           │◄───────────────────────│
  │◄──────────────────────────│                        │
  │ data: Hello               │                        │
  │                           │    Token 2             │
  │                           │◄───────────────────────│
  │◄──────────────────────────│                        │
  │ data: World               │                        │
  │                           │    [DONE]              │
  │                           │◄───────────────────────│
  │◄──────────────────────────│                        │
  │ data: [DONE]              │                        │
```

### FastAPI SSE Implementation

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import asyncio, json

app = FastAPI()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

@app.post("/chat/stream")
async def stream_chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")
    session_id = body.get("session_id", "default")
    
    async def generate_events():
        """Generate SSE events from LLM stream."""
        try:
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
            
            # Stream tokens
            token_count = 0
            async for chunk in llm.astream([HumanMessage(content=user_message)]):
                if chunk.content:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                    token_count += 1
                    
                    # Heartbeat every 50 tokens (prevent timeout)
                    if token_count % 50 == 0:
                        yield f": heartbeat\n\n"
            
            # Send completion event with metadata
            yield f"data: {json.dumps({'type': 'done', 'tokens': token_count})}\n\n"
        
        except asyncio.CancelledError:
            # Client disconnected
            yield f"data: {json.dumps({'type': 'cancelled'})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)[:100]})}\n\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
```

### WebSocket for Bidirectional Communication

```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            # Stream response back
            async for chunk in llm.astream([HumanMessage(content=message)]):
                if chunk.content:
                    await websocket.send_json({
                        "type": "token",
                        "content": chunk.content
                    })
            
            # Signal completion
            await websocket.send_json({"type": "done"})
    
    except WebSocketDisconnect:
        pass
```

---

## 7. Feedback and Improvement Loop

```
User Interaction
      ↓
  [Implicit signals]  [Explicit signals]
  - Session length    - Thumbs up/down
  - Copy events       - Corrections
  - Follow-up Qs      - Ratings
      ↓                    ↓
  Feedback Collector (LangSmith / custom)
              ↓
  ┌───────────────────────────────────┐
  │        ANALYSIS PIPELINE         │
  │  - Cluster poor answers by topic │
  │  - Identify retrieval gaps       │
  │  - Detect prompt regressions     │
  └───────────────┬───────────────────┘
                  │
       ┌──────────┼──────────┐
       ↓          ↓          ↓
  Add to       Fine-tune   Improve
  eval set      LoRA       chunking/
                           retrieval
       ↓          ↓          ↓
    Automated  Deploy new  A/B test
    regression   adapter     new
    test          ↓          ↓
                Monitor   Compare
                quality   metrics
```

```python
class FeedbackLoop:
    """Automated pipeline from user feedback to system improvement."""
    
    def __init__(self, eval_dataset, eval_pipeline, langsmith_client):
        self.eval_dataset = eval_dataset
        self.eval_pipeline = eval_pipeline
        self.ls_client = langsmith_client
    
    async def process_negative_feedback(self, run_id: str, user_correction: str):
        """When user provides correction, add to training data."""
        run = self.ls_client.read_run(run_id)
        
        new_example = {
            "input": run.inputs,
            "output": {"answer": user_correction},
            "metadata": {
                "source": "user_correction",
                "original_run_id": run_id,
                "original_score": 0
            }
        }
        
        # Add to evaluation dataset
        self.ls_client.create_examples(
            inputs=[new_example["input"]],
            outputs=[new_example["output"]],
            dataset_id=self.eval_dataset.id,
        )
        
        # If we have enough corrections, trigger fine-tuning
        correction_count = self.get_correction_count_last_week()
        if correction_count >= 100:
            await self.trigger_fine_tuning_job()
    
    async def trigger_fine_tuning_job(self):
        """Trigger OpenAI fine-tuning when enough corrections collected."""
        # Export correction examples as fine-tuning data
        examples = list(self.ls_client.list_examples(
            dataset_id=self.eval_dataset.id,
            metadata={"source": "user_correction"}
        ))
        
        # Format as JSONL for OpenAI fine-tuning
        training_data = [
            {
                "messages": [
                    {"role": "user", "content": ex.inputs["question"]},
                    {"role": "assistant", "content": ex.outputs["answer"]}
                ]
            }
            for ex in examples
        ]
        
        # Submit fine-tuning job (OpenAI API)
        print(f"Submitting fine-tuning job with {len(training_data)} examples")
```

---

## 8. Scalability Patterns

### Horizontal Scaling

```
Auto-scaling LLM Service:
  - Scale on: GPU utilization > 70%, queue depth > 10, P99 > 5s
  - Scale in: GPU utilization < 30% for 10 minutes
  - Minimum instances: 2 (for HA)
  - Maximum instances: Based on budget

Load Balancing:
  - Layer 7 (application): Route by tenant, user, model type
  - Sticky sessions: NOT recommended for LLMs (stateless preferred)
  - Health check: GET /health, expect 200 within 5s

Caching for Scale:
  - Exact cache (Redis): handles 1M+ ops/sec, scale horizontally with clustering
  - Embedding cache: prevents re-computing embeddings for same text chunks
  - Prefix cache (vLLM): 40-60% token reduction for shared system prompts
```

### Async Processing for High Volume

```python
from fastapi import FastAPI, BackgroundTasks
import asyncio
from asyncio import Queue

app = FastAPI()

class AsyncLLMQueue:
    """Queue-based system for high-volume async LLM processing."""
    
    def __init__(self, max_concurrency: int = 20):
        self.queue: Queue = Queue()
        self.results: dict = {}
        self.semaphore = asyncio.Semaphore(max_concurrency)
    
    async def submit(self, request_id: str, query: str) -> str:
        """Submit job and return immediately."""
        await self.queue.put({"id": request_id, "query": query})
        return request_id
    
    async def get_result(self, request_id: str, timeout: float = 30.0) -> dict:
        """Poll for result with timeout."""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            if request_id in self.results:
                return self.results.pop(request_id)
            await asyncio.sleep(0.1)
        return {"error": "timeout"}
    
    async def worker(self):
        """Background worker processing queue."""
        while True:
            job = await self.queue.get()
            async with self.semaphore:
                try:
                    response = await llm.ainvoke([HumanMessage(content=job["query"])])
                    self.results[job["id"]] = {"answer": response.content}
                except Exception as e:
                    self.results[job["id"]] = {"error": str(e)}
                finally:
                    self.queue.task_done()
```

---

## 9. Data Architecture for AI

### Schema Design for RAG

```sql
-- Documents table (source of truth)
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    source_url TEXT,
    title TEXT,
    content_hash VARCHAR(64) UNIQUE,  -- Dedup by hash
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_tenant (tenant_id),
    INDEX idx_hash (content_hash)
);

-- Chunks table (processed for retrieval)
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    token_count INT,
    metadata JSONB,  -- Page number, section header, etc.
    embedding_model VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE chunks ADD COLUMN embedding vector(1536);

-- HNSW index for fast ANN search
CREATE INDEX chunks_embedding_hnsw ON chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Tenant-filtered search function
CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(1536),
    p_tenant_id VARCHAR(100),
    p_top_k INT DEFAULT 10
)
RETURNS TABLE (chunk_id UUID, content TEXT, similarity FLOAT, metadata JSONB)
LANGUAGE SQL AS $$
    SELECT id, content, 1 - (embedding <=> query_embedding) AS similarity, metadata
    FROM chunks
    WHERE tenant_id = p_tenant_id
    ORDER BY embedding <=> query_embedding
    LIMIT p_top_k;
$$;
```

### Event-Driven Ingestion

```python
import asyncio
from dataclasses import dataclass

@dataclass
class DocumentIngestionEvent:
    document_id: str
    tenant_id: str
    source_url: str
    content: str

class EventDrivenIngestionPipeline:
    """Process documents as they arrive via Pub/Sub or Kafka."""
    
    def __init__(self, chunker, embedder, vectorstore):
        self.chunker = chunker
        self.embedder = embedder
        self.vectorstore = vectorstore
    
    async def process_event(self, event: DocumentIngestionEvent):
        """Process a single document ingestion event."""
        
        # 1. Deduplicate
        content_hash = hashlib.sha256(event.content.encode()).hexdigest()
        if await self.already_processed(content_hash):
            return {"status": "duplicate", "hash": content_hash}
        
        # 2. Chunk
        chunks = self.chunker.split_text(event.content)
        
        # 3. Embed (batch for efficiency)
        embeddings = await self.embedder.aembed_documents(
            [c for c in chunks]
        )
        
        # 4. Store with tenant isolation
        await self.vectorstore.aadd_embeddings(
            texts=chunks,
            embeddings=embeddings,
            metadatas=[{
                "document_id": event.document_id,
                "tenant_id": event.tenant_id,
                "chunk_index": i,
                "source": event.source_url,
            } for i in range(len(chunks))]
        )
        
        # 5. Update document record
        await self.update_document_status(event.document_id, "indexed", len(chunks))
        
        return {"status": "success", "chunks": len(chunks)}
```

---

## 10. Design Tradeoffs Reference

| Decision | Option A | Option B | Tradeoff |
|---|---|---|---|
| Chunking | Fixed size | Semantic | A: predictable, fast. B: better coherence, 3x slower |
| Retrieval | Dense only | Hybrid | A: simple, 1 index. B: 10-20% better recall, 2x components |
| Reranking | No | Yes | A: fast. B: 40-80ms overhead, 5-15% better precision |
| LLM | GPT-4o | GPT-4o-mini | A: better quality. B: 30x cheaper, often good enough |
| Caching | None | Tiered | A: always fresh. B: 60-80% cost reduction, stale risk |
| Agent memory | None | Episodic | A: stateless, simple. B: contextual, privacy risk |
| Serving | OpenAI API | vLLM | A: no infra. B: 3x cheaper at scale, GPU needed |
| Multi-tenant isolation | Namespace | Cluster | A: cheap, some risk. B: full isolation, 10x cost |

---

## 11. Interview Questions

**Q1: Design a RAG system for a company's internal knowledge base (50K documents, 1000 users)**

Architecture: Offline ingestion pipeline (Cloud Composer) extracting documents from GCS, chunking with recursive splitter (1000 tokens / 200 overlap), embedding with text-embedding-3-small, storing in pgvector on Cloud SQL. Online pipeline: hybrid retrieval (pgvector ANN + PostgreSQL FTS), cross-encoder reranking to top-5, gpt-4o-mini generation with source citations. Scale: 1000 users × 20 queries/day = 20K/day, well within single Cloud SQL instance. Latency: ~2s p50 acceptable for knowledge search. Cost: ~$50/day at 500 tokens/response. Key decisions: pgvector over Pinecone (existing Postgres infrastructure, no extra service), hybrid over dense-only (technical docs with code snippets need keyword matching).

**Q2: How does your architecture change if the RAG system needs sub-500ms latency?**

Three changes: (1) Embedding cache — pre-compute and cache embeddings for common queries, Redis lookup in < 1ms vs 50ms API call; (2) Remove reranker — 80ms savings, compensate by improving retrieval quality (more diverse queries via MultiQueryRetriever, better chunking); (3) Semantic cache — 95%+ similarity threshold, serves cached answer in < 20ms for paraphrased queries. For hardware: move embedding model to local GPU (10ms vs 50ms), deploy vLLM for generation (eliminates OpenAI TTFT variability). Expected result: p50 drops from 2000ms to 400ms.

**Q3: How would you design a system to automatically improve a RAG pipeline over time?**

Flywheel: (1) Instrument everything — log every query, retrieved docs, and LLM response with a unique trace ID; (2) Collect implicit feedback — track whether users click "thumbs up," ask follow-up questions (suggesting incomplete answer), or rephrase the same question (suggesting bad answer); (3) Active sampling — weekly, cluster low-satisfaction queries by embedding similarity to find systematic gaps; (4) Curate corrections — annotators review gap clusters and write gold-standard answers; (5) Automated eval — new answers go into LangSmith dataset, CI fails if RAGAS scores drop; (6) Pipeline updates — add missing documents to corpus, adjust chunking for problematic content types, fine-tune reranker on labeled pairs. Cadence: daily automated evals, weekly human review, monthly corpus updates.

---

*Next: Module 18 — GenAI System Design Interviews (10 Deep Walkthroughs)*
