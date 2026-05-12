# Module 16 — Production AI Engineering

> Building AI features that work in a demo is 10% of the work. Making them reliable, secure, cost-effective, and observable in production is the remaining 90%.

---

## Table of Contents

1. [Production AI Engineering Maturity Model](#1-maturity-model)
2. [LLM Observability Stack](#2-llm-observability-stack)
3. [Evaluation Infrastructure](#3-evaluation-infrastructure)
4. [Caching Strategies](#4-caching-strategies)
5. [Security and Access Control](#5-security-and-access-control)
6. [Prompt Management and Governance](#6-prompt-management-and-governance)
7. [Cost Optimization](#7-cost-optimization)
8. [Reliability and SLAs](#8-reliability-and-slas)
9. [A/B Testing for LLM Applications](#9-ab-testing)
10. [Production Incident Response](#10-production-incident-response)
11. [Interview Questions](#11-interview-questions)

---

## 1. Maturity Model

| Level | Description | Capabilities |
|---|---|---|
| L0: Prototype | Demo works | Manual testing, no monitoring |
| L1: Production | Users rely on it | Basic logging, error alerts |
| L2: Reliable | SLAs enforced | Structured observability, eval CI, retries |
| L3: Governed | Audit-ready | Prompt versioning, RBAC, cost controls |
| L4: Optimized | Continuously improving | A/B testing, automated evals, fine-tuning pipeline |

Most teams stop at L1. Production-grade starts at L2.

---

## 2. LLM Observability Stack

### What to Instrument

```
Every LLM call should record:
├── Request
│   ├── model_name, model_version
│   ├── input_tokens (prompt)
│   ├── temperature, max_tokens
│   ├── system_prompt_hash
│   └── user_id, session_id, request_id
├── Response
│   ├── output_tokens (completion)
│   ├── finish_reason (stop | length | content_filter)
│   ├── latency_ms (total, TTFT)
│   └── cost_usd
└── Context
    ├── application_version
    ├── feature_flag_variants
    └── retrieval_context (for RAG)
```

### Structured Logging

```python
import logging
import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class LLMCallLog:
    request_id: str
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    ttft_ms: float
    finish_reason: str
    cost_usd: float
    
    # Context
    user_id: str = ""
    session_id: str = ""
    feature: str = ""
    environment: str = "production"
    
    # Quality
    cached: bool = False
    error: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))

# Costs per 1K tokens
MODEL_COSTS = {
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini": {"input": 0.000150, "output": 0.000600},
    "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.00025, "output": 0.00125},
}

def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = MODEL_COSTS.get(model, {"input": 0.001, "output": 0.002})
    return (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])

class ObservableLLMClient:
    """LLM client with full observability."""
    
    def __init__(self, llm, logger=None):
        self.llm = llm
        self.logger = logger or logging.getLogger(__name__)
    
    async def ainvoke(self, messages: list, context: dict = None) -> tuple:
        """Invoke LLM with full observability."""
        request_id = str(uuid.uuid4())
        start = time.time()
        first_token_time = None
        
        try:
            response = await self.llm.ainvoke(messages)
            end = time.time()
            
            usage = response.usage_metadata if hasattr(response, "usage_metadata") else {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            model_name = self.llm.model_name
            
            log = LLMCallLog(
                request_id=request_id,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round((end - start) * 1000, 2),
                ttft_ms=0,  # Not available for non-streaming
                finish_reason="stop",
                cost_usd=round(compute_cost(model_name, input_tokens, output_tokens), 6),
                **(context or {}),
            )
            
            self.logger.info(log.to_json())
            return response, log
        
        except Exception as e:
            log = LLMCallLog(
                request_id=request_id,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                model=getattr(self.llm, "model_name", "unknown"),
                input_tokens=0, output_tokens=0,
                latency_ms=round((time.time() - start) * 1000, 2),
                ttft_ms=0, finish_reason="error",
                cost_usd=0,
                error=str(e)[:200],
                **(context or {}),
            )
            self.logger.error(log.to_json())
            raise
```

### Langfuse (Open Source Observability)

```python
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com",
)

# LangChain integration (automatic tracing)
langfuse_handler = CallbackHandler()

chain = prompt | llm | StrOutputParser()
result = chain.invoke(
    {"question": "What is RAG?"},
    config={"callbacks": [langfuse_handler]}
)

# Manual span creation
trace = langfuse.trace(name="rag_pipeline", user_id="user_123")

with langfuse.span(trace_id=trace.id, name="retrieval") as span:
    docs = retriever.invoke(query)
    span.update(
        output={"doc_count": len(docs)},
        metadata={"retriever_type": "hybrid"}
    )

# Score a trace
langfuse.score(
    trace_id=trace.id,
    name="user_satisfaction",
    value=1.0,
    comment="User marked as helpful"
)
```

### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup OTel (integrates with Datadog, Jaeger, etc.)
provider = TracerProvider()
exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317")
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("ai-application")

async def traced_llm_call(prompt: str) -> str:
    with tracer.start_as_current_span("llm_call") as span:
        span.set_attribute("llm.model", "gpt-4o-mini")
        span.set_attribute("llm.prompt_tokens", len(prompt.split()))
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        span.set_attribute("llm.output_tokens", len(response.content.split()))
        span.set_attribute("llm.finish_reason", "stop")
        
        return response.content
```

---

## 3. Evaluation Infrastructure

### Continuous Evaluation Pipeline

```python
from dataclasses import dataclass
from typing import Callable
import asyncio, statistics

@dataclass
class EvalExample:
    id: str
    input: dict
    expected_output: dict
    metadata: dict = None

@dataclass
class EvalResult:
    example_id: str
    actual_output: dict
    scores: dict[str, float]
    latency_ms: float
    error: str = ""

class ContinuousEvalPipeline:
    """Automated evaluation that runs on every deployment."""
    
    def __init__(
        self,
        predict_fn: Callable,
        eval_dataset: list[EvalExample],
        evaluators: list[Callable],
        threshold: dict[str, float],
    ):
        self.predict_fn = predict_fn
        self.dataset = eval_dataset
        self.evaluators = evaluators
        self.threshold = threshold  # {"correctness": 0.8, "latency_p99_ms": 3000}
    
    async def run_single(self, example: EvalExample) -> EvalResult:
        import time
        start = time.time()
        try:
            actual = await self.predict_fn(example.input)
            latency = (time.time() - start) * 1000
            
            scores = {}
            for evaluator in self.evaluators:
                score_name, score = evaluator(example, actual)
                scores[score_name] = score
            
            return EvalResult(
                example_id=example.id,
                actual_output=actual,
                scores=scores,
                latency_ms=latency
            )
        except Exception as e:
            return EvalResult(
                example_id=example.id,
                actual_output={},
                scores={},
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    async def run_all(self, concurrency: int = 5) -> dict:
        """Run eval with concurrency control."""
        sem = asyncio.Semaphore(concurrency)
        
        async def bounded_run(example):
            async with sem:
                return await self.run_single(example)
        
        results = await asyncio.gather(*[bounded_run(ex) for ex in self.dataset])
        return self.summarize(results)
    
    def summarize(self, results: list[EvalResult]) -> dict:
        successful = [r for r in results if not r.error]
        
        if not successful:
            return {"status": "failed", "error_rate": 1.0}
        
        # Aggregate scores
        all_score_keys = set().union(*[r.scores.keys() for r in successful])
        aggregated_scores = {}
        for key in all_score_keys:
            scores = [r.scores[key] for r in successful if key in r.scores]
            aggregated_scores[key] = {
                "mean": statistics.mean(scores),
                "p50": sorted(scores)[len(scores)//2],
            }
        
        latencies = [r.latency_ms for r in successful]
        
        return {
            "status": "completed",
            "total": len(results),
            "successful": len(successful),
            "error_rate": 1 - len(successful)/len(results),
            "scores": aggregated_scores,
            "latency": {
                "mean_ms": statistics.mean(latencies),
                "p99_ms": sorted(latencies)[int(len(latencies)*0.99)],
            },
            "passed_thresholds": self.check_thresholds(aggregated_scores, latencies),
        }
    
    def check_thresholds(self, scores: dict, latencies: list) -> dict:
        passed = {}
        for metric, min_val in self.threshold.items():
            if metric == "latency_p99_ms":
                actual = sorted(latencies)[int(len(latencies)*0.99)]
                passed[metric] = actual <= min_val
            elif metric in scores:
                passed[metric] = scores[metric]["mean"] >= min_val
        return passed
```

### LLM-as-Judge Evaluators

```python
from langchain_openai import ChatOpenAI
import json

judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)

def correctness_evaluator(example: EvalExample, actual: dict) -> tuple[str, float]:
    """LLM judge for factual correctness."""
    judge_prompt = f"""Score the answer for correctness (0-10).

Question: {example.input.get('question', '')}
Reference answer: {example.expected_output.get('answer', '')}
Actual answer: {actual.get('answer', '')}

Return ONLY JSON: {{"score": 8, "reasoning": "..."}}"""
    
    response = judge_llm.invoke([HumanMessage(content=judge_prompt)])
    result = json.loads(response.content)
    return "correctness", result["score"] / 10.0

def groundedness_evaluator(example: EvalExample, actual: dict) -> tuple[str, float]:
    """Check if answer is grounded in context (for RAG)."""
    context = actual.get("context", "")
    answer = actual.get("answer", "")
    
    if not context:
        return "groundedness", 0.5  # Can't evaluate without context
    
    judge_prompt = f"""Does this answer contain ONLY information from the context?
Score 0-10 where 10=fully grounded, 0=complete hallucination.

Context: {context[:1000]}
Answer: {answer}

Return ONLY JSON: {{"score": 8, "hallucinated_claims": []}}"""
    
    response = judge_llm.invoke([HumanMessage(content=judge_prompt)])
    try:
        result = json.loads(response.content)
        return "groundedness", result["score"] / 10.0
    except Exception:
        return "groundedness", 0.5

def format_compliance_evaluator(example: EvalExample, actual: dict) -> tuple[str, float]:
    """Check if output follows required format."""
    answer = actual.get("answer", "")
    required_format = example.metadata.get("required_format", "")
    
    if not required_format:
        return "format_compliance", 1.0
    
    # Simple heuristics
    if required_format == "json":
        try:
            json.loads(answer)
            return "format_compliance", 1.0
        except Exception:
            return "format_compliance", 0.0
    
    if required_format == "bullet_list":
        has_bullets = any(line.strip().startswith(("-", "*", "•")) for line in answer.split("\n"))
        return "format_compliance", 1.0 if has_bullets else 0.0
    
    return "format_compliance", 1.0
```

---

## 4. Caching Strategies

### Three-Tier Cache Architecture

```
Tier 1: Exact Cache (Redis)
→ Exact input hash match
→ Instant response (< 1ms)
→ Works for repeated identical queries
→ TTL: hours to days

Tier 2: Semantic Cache (Vector DB)
→ Cosine similarity above threshold (>0.95)
→ Works for paraphrased identical queries
→ Latency: 5-20ms for lookup
→ TTL: hours

Tier 3: Prefix Cache (vLLM built-in)
→ System prompt KV cache reuse
→ Reduces TTFT for shared prefixes
→ Automatic in vLLM
→ TTL: per-session
```

### Exact Cache (Redis)

```python
import hashlib
import json
import redis
from typing import Optional

class ExactLLMCache:
    """Cache LLM responses by exact input hash."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl: int = 3600):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, messages: list, model: str, temperature: float) -> str:
        content = json.dumps({
            "messages": messages,
            "model": model,
            "temperature": temperature,
        }, sort_keys=True)
        return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"
    
    def get(self, messages: list, model: str, temperature: float) -> Optional[str]:
        key = self._make_key(messages, model, temperature)
        cached = self.redis.get(key)
        if cached:
            self.hits += 1
            return json.loads(cached)
        self.misses += 1
        return None
    
    def set(self, messages: list, model: str, temperature: float, response: str):
        key = self._make_key(messages, model, temperature)
        self.redis.setex(key, self.ttl, json.dumps(response))
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
```

### Semantic Cache

```python
from langchain_openai import OpenAIEmbeddings
import numpy as np

class SemanticLLMCache:
    """Cache LLM responses based on semantic similarity of queries."""
    
    def __init__(
        self,
        embeddings_model: OpenAIEmbeddings,
        similarity_threshold: float = 0.96,
        max_entries: int = 10000,
        ttl_seconds: int = 3600,
    ):
        self.embeddings = embeddings_model
        self.threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl = ttl_seconds
        
        # In-memory cache (use Qdrant/Chroma for production)
        self.cache_keys: list[str] = []        # Original queries
        self.cache_embeddings: list = []        # Query embeddings
        self.cache_responses: list[str] = []    # LLM responses
        self.cache_timestamps: list[float] = [] # For TTL
    
    def _cosine_similarity(self, a: list, b: list) -> float:
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
    
    def get(self, query: str) -> Optional[str]:
        """Find semantically similar cached response."""
        import time
        now = time.time()
        
        if not self.cache_embeddings:
            return None
        
        query_emb = self.embeddings.embed_query(query)
        
        # Find most similar non-expired entry
        best_score = 0
        best_idx = -1
        
        for i, (emb, ts) in enumerate(zip(self.cache_embeddings, self.cache_timestamps)):
            if now - ts > self.ttl:
                continue
            score = self._cosine_similarity(query_emb, emb)
            if score > best_score:
                best_score = score
                best_idx = i
        
        if best_score >= self.threshold and best_idx >= 0:
            return self.cache_responses[best_idx]
        
        return None
    
    def set(self, query: str, response: str):
        """Cache a query-response pair."""
        import time
        
        query_emb = self.embeddings.embed_query(query)
        
        if len(self.cache_keys) >= self.max_entries:
            # Evict oldest entry
            self.cache_keys.pop(0)
            self.cache_embeddings.pop(0)
            self.cache_responses.pop(0)
            self.cache_timestamps.pop(0)
        
        self.cache_keys.append(query)
        self.cache_embeddings.append(query_emb)
        self.cache_responses.append(response)
        self.cache_timestamps.append(time.time())

class TieredLLMCache:
    """Combines exact + semantic caching."""
    
    def __init__(self, exact_cache: ExactLLMCache, semantic_cache: SemanticLLMCache):
        self.exact = exact_cache
        self.semantic = semantic_cache
    
    async def get_or_generate(
        self,
        messages: list,
        model: str,
        temperature: float,
        llm,
    ) -> tuple[str, str]:
        """Return (response, cache_status)."""
        
        # Try exact cache first
        exact_result = self.exact.get(messages, model, temperature)
        if exact_result:
            return exact_result, "exact_hit"
        
        # Try semantic cache (for non-zero temperature — still can reuse)
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        semantic_result = self.semantic.get(last_user_msg)
        if semantic_result:
            return semantic_result, "semantic_hit"
        
        # Cache miss — generate
        response = await llm.ainvoke(messages)
        answer = response.content
        
        # Store in both caches
        self.exact.set(messages, model, temperature, answer)
        self.semantic.set(last_user_msg, answer)
        
        return answer, "miss"
```

---

## 5. Security and Access Control

### RBAC for LLM Features

```python
from enum import Enum
from pydantic import BaseModel
from functools import wraps

class LLMPermission(Enum):
    BASIC_CHAT = "basic_chat"
    ADVANCED_MODELS = "advanced_models"  # GPT-4o, Claude Sonnet
    TOOL_EXECUTION = "tool_execution"
    AGENT_USE = "agent_use"
    CUSTOM_PROMPTS = "custom_prompts"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    "free_user": {LLMPermission.BASIC_CHAT},
    "pro_user": {LLMPermission.BASIC_CHAT, LLMPermission.ADVANCED_MODELS, LLMPermission.TOOL_EXECUTION},
    "developer": {
        LLMPermission.BASIC_CHAT, LLMPermission.ADVANCED_MODELS,
        LLMPermission.TOOL_EXECUTION, LLMPermission.AGENT_USE,
        LLMPermission.CUSTOM_PROMPTS
    },
    "admin": {p for p in LLMPermission},
}

class AuthContext(BaseModel):
    user_id: str
    role: str
    tenant_id: str

def require_permission(permission: LLMPermission):
    """Decorator to enforce LLM feature permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, auth: AuthContext = None, **kwargs):
            if auth is None:
                raise PermissionError("Authentication required")
            
            user_permissions = ROLE_PERMISSIONS.get(auth.role, set())
            if permission not in user_permissions:
                raise PermissionError(
                    f"Permission '{permission.value}' required. Your role '{auth.role}' "
                    f"does not have this permission."
                )
            return await func(*args, auth=auth, **kwargs)
        return wrapper
    return decorator

@require_permission(LLMPermission.AGENT_USE)
async def run_agent(goal: str, auth: AuthContext) -> str:
    return await agent.run(goal)

@require_permission(LLMPermission.ADVANCED_MODELS)
async def chat_gpt4o(message: str, auth: AuthContext) -> str:
    return await gpt4o_llm.ainvoke([HumanMessage(content=message)])
```

### PII Detection and Redaction

```python
import re
from dataclasses import dataclass

@dataclass
class PIIRedactionResult:
    original: str
    redacted: str
    found_pii: list[dict]

class PIIRedactor:
    """Detect and redact PII before sending to LLM APIs."""
    
    PATTERNS = {
        "SSN": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
        "CREDIT_CARD": (r"\b(?:\d{4}[\s-]){3}\d{4}\b", "[CC_REDACTED]"),
        "EMAIL": (r"\b[\w._%+-]+@[\w.-]+\.[A-Z]{2,}\b", "[EMAIL_REDACTED]"),
        "PHONE_US": (r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
        "IP_ADDRESS": (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP_REDACTED]"),
        "DOB": (r"\b(?:0?[1-9]|1[0-2])[/\-](?:0?[1-9]|[12]\d|3[01])[/\-]\d{4}\b", "[DOB_REDACTED]"),
    }
    
    def redact(self, text: str) -> PIIRedactionResult:
        redacted = text
        found_pii = []
        
        for pii_type, (pattern, replacement) in self.PATTERNS.items():
            matches = re.findall(pattern, redacted, re.IGNORECASE)
            if matches:
                found_pii.append({"type": pii_type, "count": len(matches)})
                redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
        
        return PIIRedactionResult(
            original=text,
            redacted=redacted,
            found_pii=found_pii
        )
    
    def redact_messages(self, messages: list[dict]) -> list[dict]:
        """Redact PII from a list of chat messages."""
        redacted_messages = []
        for msg in messages:
            result = self.redact(msg.get("content", ""))
            redacted_messages.append({**msg, "content": result.redacted})
        return redacted_messages

# Production usage
pii_redactor = PIIRedactor()

async def safe_llm_invoke(messages: list[dict]) -> str:
    # Redact PII before sending to external API
    clean_messages = pii_redactor.redact_messages(messages)
    response = await llm.ainvoke(clean_messages)
    return response.content
```

### Audit Logging

```python
import json
import logging
from datetime import datetime

audit_logger = logging.getLogger("ai_audit")
audit_logger.setLevel(logging.INFO)

class AuditEvent:
    """Immutable audit event for compliance."""
    
    def __init__(
        self,
        event_type: str,
        user_id: str,
        tenant_id: str,
        model: str,
        action: str,
        input_hash: str,
        output_hash: str,
        metadata: dict = None,
    ):
        self.record = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": user_id,
            "tenant_id": tenant_id,
            "model": model,
            "action": action,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "metadata": metadata or {},
        }
    
    def log(self):
        # Write to append-only log — never delete
        audit_logger.info(json.dumps(self.record))

def hash_content(content: str) -> str:
    """Hash content for audit (not reversible — privacy safe)."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]

async def audited_llm_call(messages: list, user_id: str, tenant_id: str) -> str:
    input_str = json.dumps(messages)
    
    response = await llm.ainvoke(messages)
    output = response.content
    
    AuditEvent(
        event_type="llm_call",
        user_id=user_id,
        tenant_id=tenant_id,
        model=llm.model_name,
        action="text_generation",
        input_hash=hash_content(input_str),
        output_hash=hash_content(output),
        metadata={"input_tokens": len(input_str.split())},
    ).log()
    
    return output
```

---

## 6. Prompt Management and Governance

### Prompt Registry

```python
from pydantic import BaseModel
from datetime import datetime
import hashlib

class PromptVersion(BaseModel):
    version: str
    template: str
    variables: list[str]
    created_by: str
    created_at: datetime
    tags: list[str]
    description: str
    checksum: str

    @classmethod
    def create(cls, template: str, version: str, created_by: str, **kwargs) -> "PromptVersion":
        return cls(
            version=version,
            template=template,
            variables=cls._extract_variables(template),
            created_by=created_by,
            created_at=datetime.utcnow(),
            checksum=hashlib.md5(template.encode()).hexdigest(),
            **kwargs
        )
    
    @staticmethod
    def _extract_variables(template: str) -> list[str]:
        import re
        return re.findall(r"\{(\w+)\}", template)
    
    def render(self, **kwargs) -> str:
        missing = set(self.variables) - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        return self.template.format(**kwargs)

class PromptRegistry:
    """Version-controlled prompt registry."""
    
    def __init__(self):
        self._registry: dict[str, dict[str, PromptVersion]] = {}
    
    def register(self, name: str, version: PromptVersion):
        if name not in self._registry:
            self._registry[name] = {}
        self._registry[name][version.version] = version
    
    def get(self, name: str, version: str = "latest") -> PromptVersion:
        if name not in self._registry:
            raise KeyError(f"Prompt '{name}' not found")
        
        if version == "latest":
            versions = sorted(self._registry[name].keys())
            version = versions[-1]
        
        return self._registry[name][version]
    
    def list_versions(self, name: str) -> list[str]:
        return sorted(self._registry.get(name, {}).keys())

# Usage
registry = PromptRegistry()

registry.register("rag_qa", PromptVersion.create(
    template="""Answer based ONLY on the context below. Cite sources.
If the context doesn't contain the answer, say "I don't have information about this."

Context:
{context}

Question: {question}""",
    version="v2.1",
    created_by="viru",
    description="RAG QA with strict grounding",
    tags=["production", "rag"],
))

# Use in production (pin to specific version)
prompt = registry.get("rag_qa", version="v2.1")
formatted = prompt.render(context="...", question="What is RAG?")
```

---

## 7. Cost Optimization

### Per-Request Cost Tracking

```python
from collections import defaultdict
from datetime import datetime

class CostTracker:
    """Track LLM costs per user, feature, and time period."""
    
    def __init__(self, daily_budget_usd: float = 100.0):
        self.daily_budget = daily_budget_usd
        self.costs: dict = defaultdict(float)  # user_id → cost
        self.feature_costs: dict = defaultdict(float)
        self.daily_total = 0.0
        self.date = datetime.today().date()
    
    def _reset_if_new_day(self):
        today = datetime.today().date()
        if today != self.date:
            self.daily_total = 0.0
            self.date = today
    
    def record(self, user_id: str, feature: str, model: str, input_tokens: int, output_tokens: int):
        self._reset_if_new_day()
        
        cost = compute_cost(model, input_tokens, output_tokens)
        self.costs[user_id] += cost
        self.feature_costs[feature] += cost
        self.daily_total += cost
        
        return cost
    
    def check_budget(self, user_id: str, estimated_cost: float = 0.01) -> tuple[bool, str]:
        """Check if user/system can make another call."""
        self._reset_if_new_day()
        
        if self.daily_total + estimated_cost > self.daily_budget:
            return False, f"Daily budget ${self.daily_budget} exceeded"
        
        user_daily_limit = self.daily_budget * 0.1  # 10% per user
        if self.costs.get(user_id, 0) + estimated_cost > user_daily_limit:
            return False, f"User daily limit exceeded"
        
        return True, "OK"
    
    def get_report(self) -> dict:
        return {
            "date": str(self.date),
            "daily_total_usd": round(self.daily_total, 4),
            "daily_budget_usd": self.daily_budget,
            "utilization_pct": round(self.daily_total / self.daily_budget * 100, 1),
            "top_users": sorted(self.costs.items(), key=lambda x: x[1], reverse=True)[:5],
            "by_feature": dict(self.feature_costs),
        }

cost_tracker = CostTracker(daily_budget_usd=500.0)

# Cost-optimized model selector
def select_model_by_complexity(query: str) -> str:
    """Route to cheaper model for simple queries."""
    word_count = len(query.split())
    
    if word_count < 15 and not any(w in query.lower() for w in ["analyze", "compare", "explain", "code"]):
        return "gpt-4o-mini"   # 10x cheaper
    return "gpt-4o"
```

### Prompt Compression

```python
def compress_prompt(
    text: str,
    target_tokens: int,
    method: str = "summary"
) -> str:
    """Reduce prompt length to fit budget."""
    
    estimated_tokens = len(text.split()) * 1.3  # Rough estimate
    
    if estimated_tokens <= target_tokens:
        return text
    
    if method == "truncate":
        # Simple truncation
        words = text.split()
        max_words = int(target_tokens / 1.3)
        return " ".join(words[:max_words]) + "\n...[truncated]"
    
    elif method == "summary":
        # LLM-based summarization
        reduction_ratio = target_tokens / estimated_tokens
        target_words = int(len(text.split()) * reduction_ratio * 0.8)
        
        response = llm.invoke([HumanMessage(
            content=f"Summarize this text in approximately {target_words} words, preserving all key facts:\n\n{text}"
        )])
        return response.content
    
    return text
```

---

## 8. Reliability and SLAs

### SLA Definitions

```python
SLA_TARGETS = {
    "basic_chat": {
        "availability": 0.999,    # 99.9% uptime (8.7h downtime/year)
        "p50_latency_ms": 1000,
        "p99_latency_ms": 5000,
        "error_rate": 0.001,      # < 0.1% errors
    },
    "rag_pipeline": {
        "availability": 0.999,
        "p50_latency_ms": 2000,
        "p99_latency_ms": 10000,
        "error_rate": 0.005,
    },
    "agent": {
        "availability": 0.99,     # 99% — agents are more complex
        "p50_latency_ms": 10000,
        "p99_latency_ms": 60000,
        "error_rate": 0.02,
    },
}

class SLAMonitor:
    """Monitor SLA compliance in real time."""
    
    def __init__(self, sla_config: dict):
        self.sla = sla_config
        self.latency_window: list[float] = []
        self.errors: int = 0
        self.total_requests: int = 0
    
    def record_request(self, latency_ms: float, success: bool):
        self.total_requests += 1
        self.latency_window.append(latency_ms)
        if not success:
            self.errors += 1
        
        # Keep rolling 1000-request window
        if len(self.latency_window) > 1000:
            self.latency_window.pop(0)
    
    def current_status(self) -> dict:
        if not self.latency_window:
            return {"status": "no_data"}
        
        sorted_l = sorted(self.latency_window)
        p99 = sorted_l[int(len(sorted_l) * 0.99)]
        p50 = sorted_l[len(sorted_l)//2]
        error_rate = self.errors / self.total_requests
        
        breaches = []
        if p99 > self.sla.get("p99_latency_ms", float("inf")):
            breaches.append(f"P99 latency {p99:.0f}ms > {self.sla['p99_latency_ms']}ms SLA")
        if error_rate > self.sla.get("error_rate", 1.0):
            breaches.append(f"Error rate {error_rate:.3f} > {self.sla['error_rate']} SLA")
        
        return {
            "status": "breached" if breaches else "healthy",
            "p50_ms": round(p50, 1),
            "p99_ms": round(p99, 1),
            "error_rate": round(error_rate, 4),
            "breaches": breaches,
        }
```

---

## 9. A/B Testing

```python
import hashlib, random

class LLMExperiment:
    """A/B test different prompts, models, or configurations."""
    
    def __init__(
        self,
        experiment_id: str,
        control: dict,    # {"model": "gpt-4o-mini", "prompt_version": "v1"}
        treatment: dict,  # {"model": "gpt-4o", "prompt_version": "v2"}
        traffic_split: float = 0.5,  # 50% treatment
    ):
        self.id = experiment_id
        self.control = control
        self.treatment = treatment
        self.split = traffic_split
        self.results = {"control": [], "treatment": []}
    
    def assign_variant(self, user_id: str) -> str:
        """Deterministic assignment — same user always gets same variant."""
        hash_val = int(hashlib.md5(f"{self.id}:{user_id}".encode()).hexdigest(), 16)
        return "treatment" if (hash_val % 100) < (self.traffic_split * 100) else "control"
    
    def get_config(self, user_id: str) -> dict:
        variant = self.assign_variant(user_id)
        config = self.treatment if variant == "treatment" else self.control
        return {"variant": variant, **config}
    
    def record_outcome(self, user_id: str, metric_name: str, value: float):
        variant = self.assign_variant(user_id)
        self.results[variant].append({"metric": metric_name, "value": value})
    
    def get_results(self) -> dict:
        import statistics
        summary = {}
        for variant, outcomes in self.results.items():
            by_metric = {}
            for outcome in outcomes:
                m = outcome["metric"]
                if m not in by_metric:
                    by_metric[m] = []
                by_metric[m].append(outcome["value"])
            summary[variant] = {
                m: {"mean": statistics.mean(vals), "n": len(vals)}
                for m, vals in by_metric.items()
            }
        return summary

# Usage
experiment = LLMExperiment(
    experiment_id="prompt_v2_vs_v1",
    control={"prompt_version": "v1", "model": "gpt-4o-mini"},
    treatment={"prompt_version": "v2", "model": "gpt-4o-mini"},
    traffic_split=0.5,
)

async def handle_request(user_id: str, query: str) -> str:
    config = experiment.get_config(user_id)
    prompt = registry.get("rag_qa", version=config["prompt_version"])
    
    response = await llm.ainvoke(prompt.render(question=query, context="..."))
    return response.content
```

---

## 10. Production Incident Response

### Runbook: LLM Latency Spike

```python
class LLMIncidentDetector:
    """Automated incident detection for LLM systems."""
    
    THRESHOLDS = {
        "p99_latency_ms": 10000,    # 10s p99
        "error_rate": 0.05,          # 5% errors
        "cost_per_hour_usd": 50.0,   # $50/hr
    }
    
    async def run_diagnostics(self, window_minutes: int = 15) -> dict:
        """Automated diagnostic runbook."""
        diagnostics = {}
        
        # 1. Check LLM provider status
        diagnostics["provider_status"] = await self.check_provider_status()
        
        # 2. Check error types
        diagnostics["error_breakdown"] = await self.get_error_breakdown(window_minutes)
        
        # 3. Check if specific model is affected
        diagnostics["model_health"] = await self.check_model_health()
        
        # 4. Check cache hit rate (low cache = more LLM calls = high cost)
        diagnostics["cache_metrics"] = self.get_cache_metrics()
        
        # 5. Generate recommendation
        diagnostics["recommendation"] = self.generate_recommendation(diagnostics)
        
        return diagnostics
    
    def generate_recommendation(self, diagnostics: dict) -> str:
        if diagnostics.get("provider_status", {}).get("openai") == "degraded":
            return "FAILOVER: Switch to Anthropic or local vLLM immediately"
        
        error_types = diagnostics.get("error_breakdown", {})
        if error_types.get("rate_limit_errors", 0) > 0.1:
            return "THROTTLE: Implement request queuing, increase retry backoff"
        
        if error_types.get("timeout_errors", 0) > 0.1:
            return "TIMEOUT: Reduce max_tokens, check for runaway prompts"
        
        return "INVESTIGATE: Check LangSmith traces for error patterns"
    
    async def check_provider_status(self) -> dict:
        """Check public status pages."""
        import aiohttp
        statuses = {}
        status_urls = {
            "openai": "https://status.openai.com/api/v2/status.json",
            "anthropic": "https://status.anthropic.com/api/v2/status.json",
        }
        async with aiohttp.ClientSession() as session:
            for provider, url in status_urls.items():
                try:
                    async with session.get(url, timeout=5) as resp:
                        data = await resp.json()
                        statuses[provider] = data.get("status", {}).get("indicator", "unknown")
                except Exception:
                    statuses[provider] = "check_failed"
        return statuses
```

---

## 11. Interview Questions

**Q1: What is the three-tier caching strategy for LLM applications and when does each tier apply?**

Tier 1 (Exact cache): hash the exact input messages + model + temperature. Returns instantly for repeated identical queries. Good for FAQ bots and repeated system operations. Tier 2 (Semantic cache): embed the user query, do nearest-neighbor search above 0.95 cosine threshold. Returns cached responses for paraphrased identical queries — handles "What is RAG?" and "Can you explain RAG to me?" as the same. Tier 3 (Prefix cache): built into vLLM, caches KV activations for common prompt prefixes (system prompts). Reduces TTFT for every call sharing the same system prompt.

**Q2: How would you implement RBAC for an LLM platform serving multiple enterprise customers?**

Three layers: (1) Tenant isolation — each customer's data and prompts are isolated; requests require tenant_id in auth context; (2) Role-based feature access — map user roles to LLM permissions (basic_chat vs agent_use vs advanced_models); enforce at the API gateway level before reaching the LLM service; (3) Per-feature rate limits and cost controls — each role has token budget per day; track in Redis; block requests when budget is exceeded. Audit every LLM call with user_id, tenant_id, and hashed content for compliance without storing PII.

**Q3: What metrics would you alert on in a production LLM system?**

Six must-have alerts: (1) P99 latency > 10s for 5 consecutive minutes — SLA breach; (2) Error rate > 5% over 5 minutes — service degraded; (3) Daily cost run-rate > 2x budget — billing explosion; (4) Cache hit rate drop > 20% — usually means corpus changed, causing embedding drift; (5) Evaluation score drop > 10% from baseline — quality regression; (6) Provider status page degraded — initiate failover. Secondary: token cost per request trending up (prompt bloat), specific tool error rates (integration failures), semantic cache miss rate increasing (query distribution shift).

**Q4: How do you run A/B tests for LLM prompt changes safely?**

Four steps: (1) Define metric — what is "better"? (user satisfaction score, task completion, answer length, latency); (2) Assign variants deterministically — hash(experiment_id + user_id) ensures same user always gets same variant, avoiding confounding; (3) Statistical significance — need minimum sample size per variant (typically 200-1000 per metric type) before declaring a winner; (4) Rollback plan — monitor error rates in treatment arm; if errors spike, reroute all traffic to control in < 5 minutes. Never run A/B tests that expose 100% of users to an untested prompt — always start with 5-10% treatment.

---

*Next: Module 17 — GenAI System Design*
