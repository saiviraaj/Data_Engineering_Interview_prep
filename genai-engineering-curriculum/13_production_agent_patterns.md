# Module 13 — Production Agent Patterns

> Building agents for demos is easy. Building agents that work reliably in production at scale is an engineering discipline.

---

## Table of Contents

1. [Production Agent Challenges](#1-production-agent-challenges)
2. [Reliability Patterns](#2-reliability-patterns)
3. [Guardrails — Input and Output Safety](#3-guardrails)
4. [Long-Running Agents](#4-long-running-agents)
5. [Agent Checkpointing and Recovery](#5-agent-checkpointing-and-recovery)
6. [Approval Workflows](#6-approval-workflows)
7. [Cost Management](#7-cost-management)
8. [Observability for Agents](#8-observability-for-agents)
9. [Testing Agents](#9-testing-agents)
10. [Deployment Patterns](#10-deployment-patterns)
11. [Interview Questions](#11-interview-questions)

---

## 1. Production Agent Challenges

| Challenge | Description | Pattern |
|---|---|---|
| Non-determinism | Same input, different outputs | Structured output, temperature=0 |
| Infinite loops | Agent never terminates | Hard iteration limit, timeout |
| Tool failures | External APIs fail | Retry, fallback, graceful degradation |
| Cost explosion | Too many LLM calls | Token budget, early termination |
| Prompt injection | User injects malicious instructions | Input sanitization, strict parsing |
| Hallucinated tool calls | LLM invents non-existent tools | Strict tool binding, validation |
| Context overflow | History grows too large | Summarization, sliding window |
| Irreversible actions | Agent takes actions that can't be undone | Human approval, dry-run mode |

---

## 2. Reliability Patterns

### Retry with Exponential Backoff

```python
import asyncio
import time
import random
from typing import Callable, TypeVar, Any

T = TypeVar("T")

class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

async def with_retry(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
    """Execute async function with exponential backoff retry."""
    delay = config.initial_delay
    
    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            if attempt == config.max_attempts - 1:
                raise  # Last attempt — propagate
            
            actual_delay = min(delay, config.max_delay)
            if config.jitter:
                actual_delay *= (0.5 + random.random() * 0.5)
            
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {actual_delay:.1f}s...")
            await asyncio.sleep(actual_delay)
            delay *= config.multiplier

# Usage
retry_config = RetryConfig(max_attempts=3, initial_delay=1.0, multiplier=2.0)

async def call_llm_with_retry(prompt: str) -> str:
    async def _call():
        return await async_llm.ainvoke(prompt)
    return await with_retry(_call, retry_config)
```

### Circuit Breaker

```python
from enum import Enum
import threading
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """
    Prevents cascading failures when a dependency is down.
    CLOSED → OPEN after N failures in window
    OPEN → HALF_OPEN after timeout
    HALF_OPEN → CLOSED on success, OPEN on failure
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time: datetime = None
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if datetime.now() - self._last_failure_time > timedelta(seconds=self.recovery_timeout):
                    self._state = CircuitState.HALF_OPEN
                    self._successes = 0
            return self._state
    
    def record_success(self):
        with self._lock:
            self._failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._successes += 1
                if self._successes >= self.success_threshold:
                    self._state = CircuitState.CLOSED
    
    def record_failure(self):
        with self._lock:
            self._failures += 1
            self._last_failure_time = datetime.now()
            if self._failures >= self.failure_threshold or self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            raise Exception(f"Circuit breaker OPEN — {func.__name__} is temporarily disabled")
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

# Usage
openai_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

async def safe_llm_call(prompt: str) -> str:
    return await openai_circuit.call(async_llm.ainvoke, prompt)
```

### Fallback Chain

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

class FallbackLLMChain:
    """Try primary LLM, fall back to alternatives on failure."""
    
    def __init__(self):
        self.primary = ChatOpenAI(model="gpt-4o", temperature=0)
        self.fallback_1 = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.fallback_2 = ChatAnthropic(model="claude-haiku-4-5-20251001")
    
    async def invoke(self, messages: list) -> Any:
        for llm in [self.primary, self.fallback_1, self.fallback_2]:
            try:
                return await llm.ainvoke(messages)
            except Exception as e:
                print(f"LLM {llm.model_name} failed: {e}, trying next...")
        
        raise Exception("All LLMs failed")

# Or use LangChain's built-in fallback:
robust_llm = (
    ChatOpenAI(model="gpt-4o")
    .with_fallbacks([
        ChatOpenAI(model="gpt-4o-mini"),
        ChatAnthropic(model="claude-haiku-4-5-20251001"),
    ])
)
```

---

## 3. Guardrails

### Input Guardrails

```python
import re
from pydantic import BaseModel

class InputGuardrails:
    """Validate and sanitize agent inputs before processing."""
    
    def __init__(
        self,
        max_input_length: int = 5000,
        blocked_patterns: list[str] = None,
        require_safe_characters: bool = True,
    ):
        self.max_input_length = max_input_length
        self.blocked_patterns = blocked_patterns or [
            r"ignore (all |previous )?(instructions|rules|guidelines)",
            r"you are now",
            r"pretend (you are|to be)",
            r"jailbreak",
            r"DAN mode",
            r"<script",
            r"javascript:",
        ]
        self.require_safe_characters = require_safe_characters
    
    def validate(self, user_input: str) -> tuple[bool, str]:
        """Return (is_safe, rejection_reason)."""
        
        # Length check
        if len(user_input) > self.max_input_length:
            return False, f"Input exceeds maximum length of {self.max_input_length} characters"
        
        # Empty check
        if not user_input.strip():
            return False, "Input cannot be empty"
        
        # Prompt injection check
        for pattern in self.blocked_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return False, "Input contains potentially unsafe content"
        
        return True, "OK"
    
    def sanitize(self, user_input: str) -> str:
        """Clean input without blocking it."""
        # Truncate to max length
        if len(user_input) > self.max_input_length:
            user_input = user_input[:self.max_input_length] + "...[truncated]"
        
        # Remove null bytes and control characters
        user_input = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', user_input)
        
        return user_input.strip()

class OutputGuardrails:
    """Validate agent outputs before returning to user."""
    
    def __init__(self, llm=None):
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.blocked_content_patterns = [
            r"\b(password|secret|api_key|token)\s*[:=]\s*\S+",  # Credential leaks
        ]
    
    def check_pii_leakage(self, output: str) -> bool:
        """Detect potential PII in output."""
        pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",          # SSN
            r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b",  # Credit card
            r"\b[\w._%+-]+@[\w.-]+\.[A-Z]{2,}\b",  # Email
        ]
        return any(re.search(p, output, re.IGNORECASE) for p in pii_patterns)
    
    def validate(self, output: str, original_query: str) -> tuple[bool, str]:
        """Return (is_safe, reason)."""
        
        if not output.strip():
            return False, "Empty output"
        
        # PII check
        if self.check_pii_leakage(output):
            return False, "Output may contain sensitive information"
        
        # Credential patterns
        for pattern in self.blocked_content_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return False, "Output contains potentially sensitive data"
        
        return True, "OK"
    
    async def llm_safety_check(self, output: str, query: str) -> tuple[bool, str]:
        """Use LLM to check output safety (higher quality, slower)."""
        response = await self.llm.ainvoke([
            HumanMessage(content=f"""Is this response safe to show to a user?
Check for: harmful content, sensitive data, inappropriate material.
Respond: {{"safe": true/false, "reason": "..."}}

Query: {query[:200]}
Response: {output[:500]}""")
        ])
        import json
        try:
            result = json.loads(response.content)
            return result.get("safe", True), result.get("reason", "")
        except Exception:
            return True, "Check failed"
```

### Structured Safety Envelope

```python
from pydantic import BaseModel

class SafeAgentResponse(BaseModel):
    """Every agent response goes through this envelope."""
    answer: str
    confidence: float
    sources: list[str]
    requires_human_review: bool
    refusal_reason: str = ""

    @classmethod
    def refuse(cls, reason: str) -> "SafeAgentResponse":
        return cls(
            answer=f"I cannot process this request: {reason}",
            confidence=1.0,
            sources=[],
            requires_human_review=False,
            refusal_reason=reason
        )

class GuardedAgent:
    """Agent with complete input/output guardrail pipeline."""
    
    def __init__(self, base_agent, input_guard: InputGuardrails, output_guard: OutputGuardrails):
        self.agent = base_agent
        self.input_guard = input_guard
        self.output_guard = output_guard
    
    async def run(self, user_input: str) -> SafeAgentResponse:
        # 1. Input validation
        is_safe, reason = self.input_guard.validate(user_input)
        if not is_safe:
            return SafeAgentResponse.refuse(reason)
        
        # 2. Sanitize
        clean_input = self.input_guard.sanitize(user_input)
        
        # 3. Run agent
        try:
            raw_output = await self.agent.run(clean_input)
        except Exception as e:
            return SafeAgentResponse(
                answer="An error occurred processing your request.",
                confidence=0,
                sources=[],
                requires_human_review=True,
                refusal_reason=str(e)
            )
        
        # 4. Output validation
        output_safe, out_reason = self.output_guard.validate(raw_output, clean_input)
        if not output_safe:
            return SafeAgentResponse(
                answer="I cannot provide this response due to content policy.",
                confidence=1.0,
                sources=[],
                requires_human_review=True,
                refusal_reason=out_reason
            )
        
        return SafeAgentResponse(
            answer=raw_output,
            confidence=0.9,
            sources=[],
            requires_human_review=False
        )
```

---

## 4. Long-Running Agents

For agents that need to run for hours or process thousands of items:

```python
from typing import AsyncIterator
import asyncio

class LongRunningAgentJob:
    """Agent designed for hour-long, large-scale processing jobs."""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = "pending"
        self.progress = 0
        self.total_items = 0
        self.results = []
        self.errors = []
        self.start_time = None
        self.end_time = None
    
    async def process_items(
        self,
        items: list[dict],
        agent_fn: Callable,
        concurrency: int = 5,
        checkpoint_every: int = 10,
    ) -> "LongRunningAgentJob":
        """Process many items with concurrency, checkpointing, and error recovery."""
        import time
        
        self.total_items = len(items)
        self.status = "running"
        self.start_time = time.time()
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_one(item: dict, idx: int) -> dict:
            async with semaphore:
                try:
                    result = await agent_fn(item)
                    return {"idx": idx, "item_id": item.get("id"), "result": result, "success": True}
                except Exception as e:
                    return {"idx": idx, "item_id": item.get("id"), "error": str(e), "success": False}
        
        tasks = [process_one(item, i) for i, item in enumerate(items)]
        
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            result = await coro
            
            if result["success"]:
                self.results.append(result)
            else:
                self.errors.append(result)
            
            self.progress = i + 1
            
            # Checkpoint periodically
            if self.progress % checkpoint_every == 0:
                await self.checkpoint()
        
        self.status = "completed"
        self.end_time = time.time()
        return self
    
    async def checkpoint(self):
        """Save progress to durable storage."""
        checkpoint_data = {
            "job_id": self.job_id,
            "progress": self.progress,
            "total_items": self.total_items,
            "results_count": len(self.results),
            "errors_count": len(self.errors),
        }
        # Save to Redis/DB/GCS
        print(f"Checkpoint: {self.progress}/{self.total_items} items processed")
    
    def estimated_completion(self) -> float:
        """Estimate seconds to completion."""
        import time
        if self.progress == 0:
            return float("inf")
        elapsed = time.time() - self.start_time
        rate = self.progress / elapsed  # items/sec
        remaining = self.total_items - self.progress
        return remaining / rate if rate > 0 else float("inf")
```

### Incremental Context Compression

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

async def compress_history(messages: list[BaseMessage], llm) -> list[BaseMessage]:
    """Summarize old messages to prevent context overflow."""
    if len(messages) <= 10:
        return messages
    
    # Keep system message + last 5 messages
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    recent_messages = messages[-5:]
    middle_messages = messages[len(system_messages):-5]
    
    if not middle_messages:
        return messages
    
    # Summarize the middle section
    history_text = "\n".join(
        f"{type(m).__name__.replace('Message', '')}: {m.content[:200]}"
        for m in middle_messages
    )
    
    summary_response = await llm.ainvoke([
        SystemMessage(content="Summarize this conversation history concisely, preserving key facts and decisions."),
        HumanMessage(content=history_text)
    ])
    
    summary_message = SystemMessage(content=f"[Conversation summary]: {summary_response.content}")
    
    return system_messages + [summary_message] + recent_messages
```

---

## 5. Agent Checkpointing and Recovery

```python
import json
import pickle
from pathlib import Path
from datetime import datetime

class AgentCheckpointer:
    """Durable checkpoint storage for long-running agents."""
    
    def __init__(self, storage_dir: str = "./agent_checkpoints"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def save(self, agent_id: str, state: dict, step: int) -> str:
        """Save agent state at a checkpoint."""
        checkpoint_id = f"{agent_id}_{step:06d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        checkpoint_path = self.storage_dir / f"{checkpoint_id}.json"
        
        # Serialize state (handle non-JSON-serializable objects)
        serializable_state = {}
        for key, value in state.items():
            try:
                json.dumps(value)
                serializable_state[key] = value
            except (TypeError, ValueError):
                serializable_state[key] = str(value)
        
        with open(checkpoint_path, "w") as f:
            json.dump({
                "agent_id": agent_id,
                "step": step,
                "timestamp": datetime.now().isoformat(),
                "state": serializable_state
            }, f, indent=2)
        
        return checkpoint_id
    
    def load_latest(self, agent_id: str) -> dict | None:
        """Load the most recent checkpoint for an agent."""
        checkpoints = sorted(
            self.storage_dir.glob(f"{agent_id}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not checkpoints:
            return None
        
        with open(checkpoints[0]) as f:
            return json.load(f)
    
    def resume_from_checkpoint(self, agent_id: str, graph, config: dict) -> bool:
        """Resume a LangGraph agent from saved checkpoint."""
        checkpoint = self.load_latest(agent_id)
        if not checkpoint:
            return False
        
        # Restore state to LangGraph
        graph.update_state(config, checkpoint["state"])
        print(f"Resumed from checkpoint at step {checkpoint['step']}")
        return True
    
    def list_checkpoints(self, agent_id: str) -> list[dict]:
        """List all checkpoints for an agent."""
        checkpoints = sorted(self.storage_dir.glob(f"{agent_id}_*.json"))
        result = []
        for cp in checkpoints:
            with open(cp) as f:
                data = json.load(f)
                result.append({
                    "checkpoint_id": cp.stem,
                    "step": data["step"],
                    "timestamp": data["timestamp"]
                })
        return result
```

---

## 6. Approval Workflows

### Action Classification and Approval Routing

```python
from enum import Enum
from pydantic import BaseModel

class ActionRisk(Enum):
    LOW = "low"        # Auto-approve
    MEDIUM = "medium"  # Log and approve
    HIGH = "high"      # Require human approval
    CRITICAL = "critical"  # Block unless explicitly authorized

class ActionApprovalRequest(BaseModel):
    action_type: str
    action_description: str
    affected_resources: list[str]
    estimated_cost: float
    reversible: bool
    risk_level: ActionRisk

class ApprovalWorkflow:
    """Route agent actions through appropriate approval gates."""
    
    # Define risk levels for different action types
    ACTION_RISK_MAP = {
        "web_search": ActionRisk.LOW,
        "read_file": ActionRisk.LOW,
        "send_email": ActionRisk.HIGH,
        "delete_file": ActionRisk.HIGH,
        "api_call": ActionRisk.MEDIUM,
        "database_write": ActionRisk.HIGH,
        "charge_payment": ActionRisk.CRITICAL,
        "deploy_code": ActionRisk.CRITICAL,
    }
    
    def __init__(self, approvers: list[str] = None):
        self.approvers = approvers or ["admin@company.com"]
        self.approval_log = []
    
    def classify_action(self, tool_name: str, tool_args: dict) -> ActionRisk:
        """Determine risk level of a proposed action."""
        base_risk = self.ACTION_RISK_MAP.get(tool_name, ActionRisk.MEDIUM)
        
        # Escalate based on arg analysis
        if tool_name == "api_call":
            if "delete" in str(tool_args).lower():
                base_risk = ActionRisk.HIGH
            if tool_args.get("amount", 0) > 1000:
                base_risk = ActionRisk.CRITICAL
        
        return base_risk
    
    async def request_approval(
        self,
        request: ActionApprovalRequest,
        approver_id: str = None
    ) -> bool:
        """Request human approval for high-risk actions."""
        
        # For LOW risk: auto-approve
        if request.risk_level == ActionRisk.LOW:
            self.approval_log.append({**request.dict(), "approved": True, "auto": True})
            return True
        
        # For CRITICAL: require explicit approval from admin
        if request.risk_level == ActionRisk.CRITICAL:
            if approver_id not in self.approvers:
                return False
        
        # For MEDIUM/HIGH: use LangGraph interrupt pattern
        # (In real system, send to approval UI/Slack/email)
        print(f"⚠️  APPROVAL REQUIRED: {request.action_description}")
        print(f"Risk: {request.risk_level.value}, Reversible: {request.reversible}")
        
        # Simulate async approval channel
        approved = await self._wait_for_approval(request)
        
        self.approval_log.append({**request.dict(), "approved": approved, "auto": False})
        return approved
    
    async def _wait_for_approval(self, request: ActionApprovalRequest) -> bool:
        """Wait for human approval via interrupt."""
        # In LangGraph context, use interrupt()
        from langgraph.types import interrupt
        decision = interrupt({
            "type": "approval_request",
            "action": request.action_description,
            "risk": request.risk_level.value,
            "reversible": request.reversible,
            "prompt": "Type 'approve' or 'reject':"
        })
        return str(decision).lower().strip() == "approve"
```

### Dry-Run Mode

```python
class DryRunToolWrapper:
    """Wraps tools to simulate execution without side effects."""
    
    def __init__(self, real_tools: list[BaseTool], dry_run: bool = False):
        self.dry_run = dry_run
        self.real_tools = {t.name: t for t in real_tools}
        self.simulated_calls = []
    
    def get_tool(self, tool_name: str) -> BaseTool:
        """Return real or simulated tool based on dry_run mode."""
        if not self.dry_run:
            return self.real_tools.get(tool_name)
        
        # Create dry-run wrapper
        real_tool = self.real_tools.get(tool_name)
        if not real_tool:
            return None
        
        class SimulatedTool(BaseTool):
            name: str = real_tool.name
            description: str = real_tool.description
            
            def _run(self_inner, **kwargs):
                self.simulated_calls.append({
                    "tool": tool_name,
                    "args": kwargs,
                    "mode": "dry_run"
                })
                return f"[DRY RUN] Would execute {tool_name} with args: {kwargs}"
        
        return SimulatedTool()
    
    def get_dry_run_summary(self) -> str:
        """Show what actions would have been taken."""
        if not self.simulated_calls:
            return "No actions would be taken"
        return "\n".join(
            f"- {c['tool']}({c['args']})"
            for c in self.simulated_calls
        )
```

---

## 7. Cost Management

```python
from dataclasses import dataclass, field
from typing import Optional

MODEL_COSTS_PER_1K_TOKENS = {
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini": {"input": 0.000150, "output": 0.000600},
    "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
}

@dataclass
class TokenBudget:
    """Track and enforce token/cost budgets for agent runs."""
    max_total_tokens: int = 100_000
    max_cost_usd: float = 1.0
    
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    
    model: str = "gpt-4o-mini"
    
    def record_usage(self, input_tokens: int, output_tokens: int):
        """Record token usage and cost."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        costs = MODEL_COSTS_PER_1K_TOKENS.get(self.model, {"input": 0.001, "output": 0.002})
        self.total_cost_usd += (
            input_tokens / 1000 * costs["input"] +
            output_tokens / 1000 * costs["output"]
        )
    
    def is_budget_exceeded(self) -> tuple[bool, str]:
        """Check if any budget is exceeded."""
        total_tokens = self.total_input_tokens + self.total_output_tokens
        if total_tokens >= self.max_total_tokens:
            return True, f"Token budget exceeded: {total_tokens} >= {self.max_total_tokens}"
        if self.total_cost_usd >= self.max_cost_usd:
            return True, f"Cost budget exceeded: ${self.total_cost_usd:.4f} >= ${self.max_cost_usd}"
        return False, ""
    
    def budget_remaining_pct(self) -> float:
        total = self.total_input_tokens + self.total_output_tokens
        token_pct = 1 - (total / self.max_total_tokens)
        cost_pct = 1 - (self.total_cost_usd / self.max_cost_usd)
        return min(token_pct, cost_pct)

class BudgetEnforcedAgent:
    """Agent that stops when cost/token budget is exceeded."""
    
    def __init__(self, base_agent, budget: TokenBudget):
        self.agent = base_agent
        self.budget = budget
    
    async def run(self, goal: str) -> str:
        # Check before each LLM call
        exceeded, reason = self.budget.is_budget_exceeded()
        if exceeded:
            return f"Agent stopped: {reason}. Partial results: {self.get_partial_results()}"
        
        # Inject budget awareness into system prompt
        budget_context = f"\n\nIMPORTANT: You have {self.budget.budget_remaining_pct():.0%} of your processing budget remaining. Be concise and focused."
        
        return await self.agent.run(goal + budget_context)
    
    def get_partial_results(self) -> str:
        return "Results gathered before budget exceeded"
```

---

## 8. Observability for Agents

```python
import time
import json
import uuid
from dataclasses import dataclass, field

@dataclass  
class AgentTrace:
    """Structured trace for one complete agent run."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    status: str = "running"  # running, completed, failed, timeout
    
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    llm_calls: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    final_answer: str = ""
    
    def record_llm_call(self, model: str, input_tokens: int, output_tokens: int, latency_ms: float):
        self.llm_calls += 1
        self.total_tokens += input_tokens + output_tokens
        costs = MODEL_COSTS_PER_1K_TOKENS.get(model, {"input": 0.001, "output": 0.002})
        self.total_cost_usd += input_tokens/1000 * costs["input"] + output_tokens/1000 * costs["output"]
    
    def record_tool_call(self, tool_name: str, args: dict, result: str, success: bool, latency_ms: float):
        self.tool_calls.append({
            "tool": tool_name,
            "args": {k: str(v)[:100] for k, v in args.items()},
            "success": success,
            "latency_ms": latency_ms,
            "result_preview": result[:100] if result else ""
        })
    
    def complete(self, answer: str = ""):
        self.end_time = time.time()
        self.status = "completed"
        self.final_answer = answer
    
    def fail(self, error: str):
        self.end_time = time.time()
        self.status = "failed"
        self.errors.append(error)
    
    @property
    def duration_s(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time
    
    def to_log_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "goal": self.goal[:200],
            "status": self.status,
            "duration_s": round(self.duration_s, 2),
            "llm_calls": self.llm_calls,
            "tool_calls_count": len(self.tool_calls),
            "tool_errors": sum(1 for tc in self.tool_calls if not tc["success"]),
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "errors": self.errors[:3],
        }
```

---

## 9. Testing Agents

### Unit Testing Tools

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_web_search_tool():
    """Test tool returns expected format."""
    result = await web_search_tool.arun({"query": "test query"})
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio  
async def test_tool_error_handling():
    """Test tool gracefully handles errors."""
    with patch("requests.get", side_effect=ConnectionError("Network error")):
        result = await web_search_tool.arun({"query": "test"})
        assert "error" in result.lower() or "failed" in result.lower()
```

### Integration Testing with Deterministic Mocks

```python
class DeterministicAgentTester:
    """Test agent logic by mocking LLM responses."""
    
    def __init__(self, agent_graph):
        self.graph = agent_graph
    
    def test_with_scripted_llm(self, goal: str, llm_script: list[str]) -> dict:
        """
        Run agent with pre-scripted LLM responses.
        llm_script: list of responses in order of LLM calls.
        """
        call_idx = 0
        
        def mock_llm_call(messages):
            nonlocal call_idx
            if call_idx < len(llm_script):
                response = AIMessage(content=llm_script[call_idx])
                call_idx += 1
                return response
            return AIMessage(content="Final Answer: Task completed.")
        
        with patch("langchain_openai.ChatOpenAI.invoke", side_effect=mock_llm_call):
            result = self.graph.invoke({"messages": [HumanMessage(content=goal)]})
        
        return result

# Example test
def test_agent_handles_tool_failure():
    """Test that agent recovers when a tool fails."""
    tester = DeterministicAgentTester(agent_graph)
    
    # Script: first try tool, tool fails, agent asks differently, final answer
    script = [
        'Action: web_search\nAction Input: {"query": "test"}',  # First attempt
        'Observation tells us the search failed. Let me try differently.\nFinal Answer: Based on my knowledge...'
    ]
    
    result = tester.test_with_scripted_llm("What is Python?", script)
    assert result.get("final_answer") or result.get("messages")

### Golden Dataset Testing
def create_agent_eval_suite() -> list[dict]:
    return [
        {
            "input": "What is 2+2?",
            "expected_behavior": "direct_answer",
            "expected_answer_contains": ["4"],
            "should_use_tools": False,
            "max_iterations": 2,
        },
        {
            "input": "Search for current weather in Mumbai",
            "expected_behavior": "tool_use",
            "expected_tools_used": ["web_search"],
            "max_iterations": 5,
        },
    ]
```

---

## 10. Deployment Patterns

### Agent as FastAPI Service

```python
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import asyncio, uuid

app = FastAPI()

class AgentRequest(BaseModel):
    goal: str
    session_id: str = ""
    max_iterations: int = 10
    timeout_seconds: float = 60.0

class AgentJobStatus(BaseModel):
    job_id: str
    status: str  # queued, running, completed, failed
    result: str = ""
    error: str = ""

# In-memory job store (use Redis in production)
jobs: dict[str, AgentJobStatus] = {}

@app.post("/agent/sync")
async def run_agent_sync(request: AgentRequest) -> dict:
    """Synchronous agent endpoint (short tasks only)."""
    try:
        result = await asyncio.wait_for(
            run_react_agent_async(request.goal),
            timeout=request.timeout_seconds
        )
        return {"status": "completed", "result": result}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Agent timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/async")
async def run_agent_async(request: AgentRequest, background_tasks: BackgroundTasks) -> dict:
    """Asynchronous agent endpoint for long tasks."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = AgentJobStatus(job_id=job_id, status="queued")
    
    async def run_job():
        jobs[job_id].status = "running"
        try:
            result = await run_react_agent_async(request.goal)
            jobs[job_id].status = "completed"
            jobs[job_id].result = result
        except Exception as e:
            jobs[job_id].status = "failed"
            jobs[job_id].error = str(e)
    
    background_tasks.add_task(run_job)
    return {"job_id": job_id, "status": "queued"}

@app.get("/agent/jobs/{job_id}")
async def get_job_status(job_id: str) -> AgentJobStatus:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.post("/agent/stream")
async def stream_agent(request: AgentRequest):
    """Streaming SSE endpoint."""
    from fastapi.responses import StreamingResponse
    
    async def generate():
        async for chunk in agent_graph.astream_events(
            {"messages": [HumanMessage(content=request.goal)]},
            version="v2"
        ):
            if chunk["event"] == "on_chat_model_stream":
                token = chunk["data"]["chunk"].content
                if token:
                    yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 11. Interview Questions

**Q1: What are the most important guardrails to implement for a production agent?**

Six categories: (1) Input validation — length limits, prompt injection detection, PII stripping; (2) Output validation — PII leakage check, hallucination detection, policy compliance; (3) Tool access control — allowlist/denylist, require approval for irreversible actions; (4) Iteration limits — hard stop after N steps; (5) Cost budgets — token and dollar limits per request; (6) Rate limiting — per-user and global to prevent abuse. Start with iteration limits and tool allowlisting — they prevent the most common production failures.

**Q2: How would you build a system for agent approval workflows that doesn't break the agent's reasoning chain?**

Use LangGraph's `interrupt()` mechanism: the agent can continue reasoning up to the sensitive action, then call `interrupt({...})` which pauses execution and serializes state to the checkpoint store. The UI or notification system reads the interrupt payload and presents it to the approver. When the approver responds, `graph.invoke(Command(resume=decision), config=config)` restores state and continues from the exact point of interruption — the agent's reasoning context is fully preserved.

**Q3: How do you handle context window overflow in a long-running agent?**

Three complementary strategies: (1) Sliding window — keep only the last N messages in working memory; (2) Incremental summarization — periodically have the LLM summarize older portions of the conversation into a compact SystemMessage; (3) Episodic memory — extract key facts/decisions into a semantic memory store (vector DB) and inject relevant memories at each step rather than keeping full history. The right balance depends on the task — customer support agents need more history than single-task data analysis agents.

**Q4: What metrics would you monitor for a production agent system?**

Seven critical metrics: (1) Success rate — % of runs that reach final answer without error; (2) Average and P99 latency per run; (3) Average iterations per successful run — increasing trend signals degrading performance; (4) Tool error rate by tool — which tools are unreliable; (5) Token cost per run — detect cost regressions; (6) Human review rate — how often agent escalates; (7) User satisfaction (thumbs up/down). Alert on: success rate < 95%, P99 > 30s, cost per run > 2x baseline, tool error rate > 10%.

---

*Next: Module 14 — HuggingFace Ecosystem*
