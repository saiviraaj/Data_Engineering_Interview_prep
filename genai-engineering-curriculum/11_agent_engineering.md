# Module 11 — Agent Engineering

> Agents are LLMs that can take actions, observe results, and iterate. This module covers the theory and production implementation of single-agent systems.

---

## Table of Contents

1. [What Is an Agent?](#1-what-is-an-agent)
2. [ReAct — Reasoning + Acting](#2-react--reasoning--acting)
3. [Tool Design Principles](#3-tool-design-principles)
4. [Tool Execution Engine](#4-tool-execution-engine)
5. [Agent Memory Architectures](#5-agent-memory-architectures)
6. [Planning Patterns](#6-planning-patterns)
7. [Structured Output Agents](#7-structured-output-agents)
8. [Error Handling and Recovery](#8-error-handling-and-recovery)
9. [Agent Security](#9-agent-security)
10. [Production Single-Agent Patterns](#10-production-single-agent-patterns)
11. [Complete Example — Data Analysis Agent](#11-complete-example--data-analysis-agent)
12. [Interview Questions](#12-interview-questions)

---

## 1. What Is an Agent?

An agent is an LLM-powered system that:
1. Receives a goal
2. Decides what action to take (tool call, reasoning, final answer)
3. Executes the action
4. Observes the result
5. Repeats until the goal is achieved

```
┌─────────────────────────────────────────────────────────┐
│                    AGENT LOOP                           │
│                                                         │
│  Goal → [Thought] → [Action] → [Observation] → Repeat  │
│           LLM          Tool         Tool Result        │
└─────────────────────────────────────────────────────────┘
```

### Agents vs Chains

| Chains | Agents |
|---|---|
| Fixed execution path | Dynamic, decided at runtime |
| Deterministic flow | LLM chooses next step |
| Fast and predictable | Flexible and open-ended |
| Simple to debug | Complex to debug |
| No external actions | Can call APIs, run code |
| Example: RAG pipeline | Example: research assistant |

### When to Use Agents

- The task is open-ended and the steps can't be predetermined
- Multiple tools may be needed, in unknown order
- The agent needs to adapt based on results
- You need the LLM to decide when it's done

### When NOT to Use Agents

- The task is well-defined with known steps → use a chain
- Latency is critical → agents are slower (multiple LLM calls)
- Reliability is paramount → agents can go off-script
- Simple Q&A → direct LLM call or RAG

---

## 2. ReAct — Reasoning + Acting

ReAct (Yao et al., 2022) is the foundational agent architecture. The LLM interleaves Thought, Action, and Observation steps.

### ReAct Trace Example

```
Human: What is the population of the top 3 most populous countries?

Thought: I need to find the top 3 most populous countries and their populations.
Action: web_search("top 3 most populous countries 2024")
Observation: China (1.4B), India (1.44B), USA (331M)

Thought: I now have all the information needed.
Action: FINAL ANSWER
The top 3 most populous countries are:
1. India: ~1.44 billion
2. China: ~1.40 billion  
3. USA: ~331 million
```

### ReAct System Prompt

```python
REACT_SYSTEM_PROMPT = """You are a helpful assistant with access to tools. 

AVAILABLE TOOLS:
{tools_description}

INSTRUCTIONS:
Use the following format for your responses:

Thought: Reason step-by-step about what to do
Action: tool_name
Action Input: {{"param": "value"}}

After observing the tool result, either continue with another thought/action or provide the final answer:

Final Answer: [your complete response to the human]

Begin!"""

def build_tools_description(tools: list) -> str:
    parts = []
    for tool in tools:
        params = tool.args_schema.schema().get("properties", {}) if tool.args_schema else {}
        param_str = ", ".join(f"{k}: {v.get('description', v.get('type', 'str'))}" 
                              for k, v in params.items())
        parts.append(f"- {tool.name}({param_str}): {tool.description}")
    return "\n".join(parts)
```

### Custom ReAct Agent

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
import json, re

@tool
def web_search(query: str) -> str:
    """Search the web for current information."""
    # Real: integrate Tavily or SerpAPI
    return f"Search results for '{query}': [3 relevant results found]"

@tool
def python_repl(code: str) -> str:
    """Execute Python code and return the output."""
    try:
        import io, contextlib
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(code, {})
        return output.getvalue() or "Code executed successfully (no output)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"

@tool
def read_file(filepath: str) -> str:
    """Read the contents of a file."""
    try:
        with open(filepath) as f:
            return f.read()[:5000]  # Limit output
    except Exception as e:
        return f"Error reading file: {e}"

tools = [web_search, python_repl, read_file]
tool_map = {t.name: t for t in tools}
llm = ChatOpenAI(model="gpt-4o", temperature=0)

def parse_action(response_text: str):
    """Parse Action and Action Input from ReAct-style response."""
    # Check for final answer
    if "Final Answer:" in response_text:
        final = response_text.split("Final Answer:")[-1].strip()
        return "final_answer", final
    
    # Parse action
    action_match = re.search(r"Action:\s*(.+?)(?:\n|$)", response_text)
    input_match = re.search(r"Action Input:\s*(.+?)(?:\n\n|$)", response_text, re.DOTALL)
    
    if not action_match:
        return "final_answer", response_text
    
    action_name = action_match.group(1).strip()
    action_input_str = input_match.group(1).strip() if input_match else "{}"
    
    try:
        action_input = json.loads(action_input_str)
    except json.JSONDecodeError:
        # Handle non-JSON input
        action_input = {"input": action_input_str}
    
    return action_name, action_input

def run_react_agent(goal: str, max_iterations: int = 10) -> str:
    """Run a ReAct agent loop."""
    tools_description = build_tools_description(tools)
    system = REACT_SYSTEM_PROMPT.format(tools_description=tools_description)
    
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=goal)
    ]
    
    for iteration in range(max_iterations):
        # Get LLM response
        response = llm.invoke(messages)
        response_text = response.content
        messages.append(AIMessage(content=response_text))
        
        # Parse the action
        action_name, action_input = parse_action(response_text)
        
        # Check if done
        if action_name == "final_answer":
            return action_input
        
        # Execute tool
        if action_name in tool_map:
            try:
                observation = str(tool_map[action_name].invoke(action_input))
            except Exception as e:
                observation = f"Tool execution error: {type(e).__name__}: {e}"
        else:
            observation = f"Unknown tool: {action_name}. Available: {list(tool_map.keys())}"
        
        # Add observation to messages
        messages.append(HumanMessage(
            content=f"Observation: {observation[:2000]}"
        ))
    
    return "Max iterations reached. Unable to complete the task."
```

---

## 3. Tool Design Principles

The quality of your agent is heavily determined by the quality of your tools. Well-designed tools enable agents to solve complex problems reliably.

### Tool Design Checklist

```python
from langchain_core.tools import tool, BaseTool, StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, Type

# ✅ GOOD: Clear name, detailed docstring, typed inputs
class SearchInput(BaseModel):
    query: str = Field(description="The specific search query")
    num_results: int = Field(default=5, ge=1, le=20, description="Number of results (1-20)")
    date_filter: Optional[str] = Field(
        default=None,
        description="Filter by date: 'past_day', 'past_week', 'past_month'"
    )

@tool(args_schema=SearchInput)
def web_search_v2(query: str, num_results: int = 5, date_filter: Optional[str] = None) -> str:
    """
    Search the web for current information and news.
    
    Use this when you need:
    - Current events or news
    - Facts that may have changed recently
    - Information about specific people, places, or products
    
    Do NOT use for:
    - Mathematical calculations (use calculator)
    - Code execution (use python_repl)
    - Reading local files (use read_file)
    """
    # Implementation
    return f"Results for '{query}'"

# ❌ BAD: Vague name, no description, untyped
@tool
def search(q):
    """Search."""
    return search_api(q)
```

### Atomic vs Composite Tools

```python
# Atomic tools (preferred) — one thing, done well
@tool
def get_stock_price(ticker: str) -> str:
    """Get the current stock price for a ticker symbol like AAPL or GOOGL."""
    return f"${get_price(ticker):.2f}"

@tool
def calculate_portfolio_value(holdings: dict) -> str:
    """Calculate total portfolio value given a dict of {ticker: shares}."""
    total = sum(float(get_price(t)) * s for t, s in holdings.items())
    return f"Total portfolio value: ${total:,.2f}"

# Composite tool (avoid when possible) — hard to test, debug
@tool
def analyze_portfolio(tickers: list) -> str:
    """Look up prices AND calculate value AND compare to benchmark AND suggest rebalancing."""
    # Too much — hard to unit test, hard to debug agent failures
    pass
```

### Error-Resilient Tool Design

```python
from pydantic import BaseModel, validator
import traceback

class SafeToolWrapper(BaseTool):
    """Wrapper that catches all exceptions and returns error messages."""
    
    name: str = "safe_tool"
    description: str = "A safe tool wrapper"
    inner_tool: BaseTool
    
    def _run(self, *args, **kwargs):
        try:
            result = self.inner_tool.run(*args, **kwargs)
            return result
        except ValueError as e:
            return f"VALIDATION_ERROR: {e}"
        except ConnectionError as e:
            return f"NETWORK_ERROR: {e}. Please retry."
        except Exception as e:
            # Don't expose full traceback to LLM
            return f"TOOL_ERROR: {type(e).__name__}: {str(e)[:200]}"
    
    async def _arun(self, *args, **kwargs):
        try:
            return await self.inner_tool.arun(*args, **kwargs)
        except Exception as e:
            return f"TOOL_ERROR: {type(e).__name__}: {str(e)[:200]}"
```

---

## 4. Tool Execution Engine

```python
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from typing import Any
import asyncio, json, logging

logger = logging.getLogger(__name__)

class ToolExecutionEngine:
    """
    Production tool execution engine with:
    - Parallel async execution
    - Timeout handling
    - Error recovery
    - Audit logging
    """
    
    def __init__(self, tools: list[BaseTool], default_timeout: float = 30.0):
        self.tool_map = {t.name: t for t in tools}
        self.default_timeout = default_timeout
        self.execution_log = []
    
    async def execute_tool_call(self, tool_call: dict, timeout: float = None) -> ToolMessage:
        """Execute a single tool call asynchronously with timeout."""
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]
        tool_call_id = tool_call["id"]
        timeout = timeout or self.default_timeout
        
        log_entry = {
            "tool": tool_name,
            "input": tool_input,
            "success": False,
            "result": None,
            "error": None,
        }
        
        if tool_name not in self.tool_map:
            error = f"Tool '{tool_name}' not found. Available: {list(self.tool_map.keys())}"
            log_entry["error"] = error
            self.execution_log.append(log_entry)
            return ToolMessage(content=error, tool_call_id=tool_call_id)
        
        try:
            tool = self.tool_map[tool_name]
            result = await asyncio.wait_for(
                tool.arun(tool_input),
                timeout=timeout
            )
            result_str = str(result)[:5000]  # Limit output size
            log_entry["success"] = True
            log_entry["result"] = result_str[:200]
            logger.info(f"Tool {tool_name} succeeded")
            
            return ToolMessage(content=result_str, tool_call_id=tool_call_id)
        
        except asyncio.TimeoutError:
            error = f"Tool {tool_name} timed out after {timeout}s"
            log_entry["error"] = error
            logger.warning(error)
            return ToolMessage(content=error, tool_call_id=tool_call_id)
        
        except Exception as e:
            error = f"Tool {tool_name} failed: {type(e).__name__}: {str(e)[:200]}"
            log_entry["error"] = error
            logger.error(f"Tool execution error: {e}", exc_info=True)
            return ToolMessage(content=error, tool_call_id=tool_call_id)
        
        finally:
            self.execution_log.append(log_entry)
    
    async def execute_all(self, ai_message: AIMessage) -> list[ToolMessage]:
        """Execute all tool calls in an AIMessage in parallel."""
        if not ai_message.tool_calls:
            return []
        
        tasks = [
            self.execute_tool_call(tool_call)
            for tool_call in ai_message.tool_calls
        ]
        
        return await asyncio.gather(*tasks)
```

---

## 5. Agent Memory Architectures

Agents need different types of memory for different purposes:

```
Memory Types:
├── Working Memory (short-term)
│   └── Current conversation messages — the context window
├── Episodic Memory (session-level)
│   └── Full conversation history — Redis, Postgres
├── Semantic Memory (long-term facts)
│   └── Learned facts about user/domain — vector DB
└── Procedural Memory (how-to)
    └── Learned tool usage patterns — prompt optimization
```

### Working Memory Management

```python
from langchain_core.messages import trim_messages, BaseMessage

def manage_working_memory(
    messages: list[BaseMessage],
    max_tokens: int = 8000,
    keep_system: bool = True,
) -> list[BaseMessage]:
    """Trim conversation history to fit in context window."""
    return trim_messages(
        messages,
        max_tokens=max_tokens,
        strategy="last",           # Keep most recent messages
        token_counter=ChatOpenAI(model="gpt-4o-mini"),
        include_system=keep_system,
        allow_partial=False,
        start_on="human",
    )
```

### Semantic Memory with Vector DB

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

class AgentSemanticMemory:
    """Long-term semantic memory for agents."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = Chroma(
            collection_name=f"agent_memory_{agent_id}",
            embedding_function=self.embeddings,
        )
    
    def remember(self, fact: str, metadata: dict = None):
        """Store a fact in long-term memory."""
        self.vectorstore.add_texts(
            texts=[fact],
            metadatas=[{"agent_id": self.agent_id, **(metadata or {})}]
        )
    
    def recall(self, query: str, k: int = 5) -> list[str]:
        """Retrieve relevant memories."""
        docs = self.vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
    
    def recall_as_context(self, query: str, k: int = 3) -> str:
        """Format memories as system context."""
        memories = self.recall(query, k=k)
        if not memories:
            return ""
        formatted = "\n".join(f"- {m}" for m in memories)
        return f"Relevant memories:\n{formatted}"

# Usage in agent
memory = AgentSemanticMemory(agent_id="agent_viru_001")
memory.remember("User prefers Python code examples over pseudocode")
memory.remember("User is a Senior Data Engineer with GCP expertise")

# In agent system prompt
memories_context = memory.recall_as_context("What kind of examples does the user prefer?")
system_prompt = f"You are a helpful assistant.\n\n{memories_context}"
```

### Episodic Memory (Full Session History)

```python
from langchain_community.chat_message_histories import RedisChatMessageHistory, PostgresChatMessageHistory

def get_agent_history(session_id: str, backend: str = "redis") -> BaseChatMessageHistory:
    """Get persistent message history for a session."""
    if backend == "redis":
        return RedisChatMessageHistory(
            session_id=session_id,
            url=os.environ["REDIS_URL"],
            ttl=86400  # 24-hour TTL
        )
    elif backend == "postgres":
        return PostgresChatMessageHistory(
            connection_string=os.environ["DATABASE_URL"],
            session_id=session_id,
        )
    else:
        return InMemoryChatMessageHistory()
```

---

## 6. Planning Patterns

### Plan-and-Execute

The LLM first creates a complete plan, then executes each step:

```python
PLANNER_PROMPT = """Given the user's goal, create a detailed step-by-step plan.
Each step should be concrete and actionable.
Return JSON: {{"steps": ["step1", "step2", ...], "expected_outcome": "..."}}

Goal: {goal}"""

EXECUTOR_PROMPT = """You are executing step {step_num} of {total_steps} in a plan.

Full plan:
{full_plan}

Current step: {current_step}
Previous results:
{previous_results}

Execute this step using available tools. Be specific and thorough."""

class PlanAndExecuteAgent:
    """Two-phase agent: plan first, then execute step by step."""
    
    def __init__(self, tools: list[BaseTool]):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.tools = tools
        self.executor = ToolExecutionEngine(tools)
    
    def plan(self, goal: str) -> list[str]:
        """Generate execution plan."""
        response = self.llm.invoke([
            HumanMessage(content=PLANNER_PROMPT.format(goal=goal))
        ])
        import json
        try:
            plan = json.loads(response.content)
            return plan.get("steps", [goal])
        except Exception:
            return [goal]
    
    async def execute(self, goal: str) -> str:
        """Plan then execute."""
        steps = self.plan(goal)
        results = []
        
        for i, step in enumerate(steps):
            context = "\n".join(f"Step {j+1} result: {r}" for j, r in enumerate(results))
            
            response = self.llm.bind_tools(self.tools).invoke([
                SystemMessage(content="You are an execution agent. Use tools to complete each step."),
                HumanMessage(content=EXECUTOR_PROMPT.format(
                    step_num=i+1,
                    total_steps=len(steps),
                    full_plan="\n".join(f"{j+1}. {s}" for j, s in enumerate(steps)),
                    current_step=step,
                    previous_results=context or "None yet"
                ))
            ])
            
            # Execute any tool calls
            if response.tool_calls:
                tool_results = await self.executor.execute_all(response)
                step_result = "\n".join(r.content for r in tool_results)
            else:
                step_result = response.content
            
            results.append(step_result)
        
        # Final synthesis
        final = self.llm.invoke([
            SystemMessage(content="Synthesize the results into a coherent final answer."),
            HumanMessage(content=f"Goal: {goal}\nStep results:\n{chr(10).join(f'{i+1}. {r}' for i, r in enumerate(results))}")
        ])
        
        return final.content
```

### Tree of Thoughts (ToT)

```python
# Simplified Tree of Thoughts — explore multiple paths, select best
class TreeOfThoughtsAgent:
    
    def __init__(self, branching_factor: int = 3, max_depth: int = 3):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.branching_factor = branching_factor
        self.max_depth = max_depth
    
    def generate_thoughts(self, state: str, n: int) -> list[str]:
        """Generate n possible next thoughts."""
        response = self.llm.invoke([HumanMessage(
            content=f"Given: {state}\nGenerate {n} distinct next steps. Return as JSON array."
        )])
        import json
        try:
            return json.loads(response.content)
        except Exception:
            return [response.content]
    
    def evaluate_thought(self, goal: str, state: str, thought: str) -> float:
        """Score a thought for promise (0-1)."""
        response = self.llm.invoke([HumanMessage(
            content=f"Goal: {goal}\nCurrent state: {state}\nProposed step: {thought}\n"
                    f"Score this step 0-10 for likely success. Return just the number."
        )])
        try:
            return float(response.content.strip()) / 10.0
        except Exception:
            return 0.5
    
    def solve(self, goal: str) -> str:
        """Breadth-first ToT search."""
        paths = [{"state": goal, "steps": [], "score": 1.0}]
        
        for depth in range(self.max_depth):
            new_paths = []
            for path in paths:
                thoughts = self.generate_thoughts(path["state"], self.branching_factor)
                for thought in thoughts:
                    score = self.evaluate_thought(goal, path["state"], thought)
                    new_paths.append({
                        "state": f"{path['state']}\n→ {thought}",
                        "steps": path["steps"] + [thought],
                        "score": path["score"] * score
                    })
            
            # Keep top paths
            paths = sorted(new_paths, key=lambda p: p["score"], reverse=True)[:self.branching_factor]
        
        # Return best path's final synthesis
        best_path = paths[0]
        final = self.llm.invoke([HumanMessage(
            content=f"Goal: {goal}\nPath taken:\n{chr(10).join(best_path['steps'])}\n\nProvide final answer."
        )])
        return final.content
```

---

## 7. Structured Output Agents

Use structured outputs to make agents more reliable and easier to parse:

```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class ToolCallDecision(BaseModel):
    reasoning: str = Field(description="Step-by-step reasoning")
    next_action: str = Field(description="'tool' or 'final_answer'")
    tool_name: Optional[str] = Field(default=None, description="Tool to use if action is 'tool'")
    tool_args: Optional[dict] = Field(default=None, description="Arguments for the tool")
    final_answer: Optional[str] = Field(default=None, description="Final answer if done")
    confidence: float = Field(ge=0, le=1, description="Confidence in this decision")

llm_structured = ChatOpenAI(model="gpt-4o").with_structured_output(ToolCallDecision)

def structured_agent_step(state: AgentState) -> ToolCallDecision:
    """Agent step that always returns structured output."""
    system = SystemMessage(content=f"""You are a helpful agent. 
Available tools: {build_tools_description(tools)}
Reason step-by-step and decide the next action.""")
    
    return llm_structured.invoke([system] + state["messages"])
```

---

## 8. Error Handling and Recovery

```python
class SelfHealingAgent:
    """Agent that recovers from tool errors by retrying with corrected inputs."""
    
    def __init__(self, tools: list[BaseTool]):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.llm_with_tools = self.llm.bind_tools(tools)
        self.tools = {t.name: t for t in tools}
    
    def run_with_recovery(self, goal: str, max_retries: int = 3) -> str:
        messages = [
            SystemMessage(content="You are a helpful agent. If a tool fails, analyze the error and try a different approach."),
            HumanMessage(content=goal)
        ]
        
        error_count = 0
        
        for iteration in range(20):
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)
            
            if not response.tool_calls:
                return response.content
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["args"]
                
                try:
                    result = self.tools[tool_name].invoke(tool_input)
                    messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"]
                    ))
                    error_count = max(0, error_count - 1)  # Reduce error count on success
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"Tool failed: {e}. Try a different approach."
                    messages.append(ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call["id"]
                    ))
                    
                    if error_count >= max_retries:
                        # Ask LLM to take a completely different approach
                        messages.append(HumanMessage(
                            content=f"You've encountered {error_count} errors. Please take a fundamentally different approach."
                        ))
                        error_count = 0
        
        return "Unable to complete task after maximum iterations."
```

---

## 9. Agent Security

Agents that take real-world actions require security hardening:

```python
from typing import Set
import re

class AgentSecurityGuard:
    """Security layer for agent tool execution."""
    
    def __init__(
        self,
        allowed_tools: Set[str] = None,
        blocked_tools: Set[str] = None,
        require_confirmation_for: Set[str] = None,
        max_file_size_bytes: int = 10 * 1024 * 1024,
    ):
        self.allowed_tools = allowed_tools  # None = allow all
        self.blocked_tools = blocked_tools or set()
        self.require_confirmation_for = require_confirmation_for or set()
        self.max_file_size_bytes = max_file_size_bytes
    
    def validate_tool_call(self, tool_name: str, tool_args: dict) -> tuple[bool, str]:
        """Return (allowed, reason)."""
        
        # Check blocked list
        if tool_name in self.blocked_tools:
            return False, f"Tool '{tool_name}' is not allowed in this context"
        
        # Check allowed list
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return False, f"Tool '{tool_name}' is not in the allowed tool list"
        
        # Check for prompt injection in tool arguments
        if self._detect_prompt_injection(str(tool_args)):
            return False, "Potential prompt injection detected in tool arguments"
        
        # Tool-specific validation
        if tool_name == "python_repl":
            if self._dangerous_code(tool_args.get("code", "")):
                return False, "Dangerous code patterns detected"
        
        if tool_name == "read_file":
            filepath = tool_args.get("filepath", "")
            if ".." in filepath or filepath.startswith("/etc"):
                return False, "Path traversal or system file access not allowed"
        
        return True, "OK"
    
    def _detect_prompt_injection(self, text: str) -> bool:
        """Detect common prompt injection patterns."""
        injection_patterns = [
            r"ignore previous instructions",
            r"forget everything",
            r"you are now",
            r"new system prompt",
            r"override your",
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in injection_patterns)
    
    def _dangerous_code(self, code: str) -> bool:
        """Detect dangerous Python code patterns."""
        dangerous_patterns = [
            r"import\s+os",      # OS operations
            r"import\s+subprocess",
            r"__import__",
            r"eval\(",
            r"exec\(",
            r"open\(",           # File operations
            r"shutil",
            r"socket",           # Network
        ]
        return any(re.search(p, code) for p in dangerous_patterns)
```

---

## 10. Production Single-Agent Patterns

### Rate-Limited Agent

```python
import time
from collections import deque

class RateLimitedAgent:
    """Agent with per-user and global rate limiting."""
    
    def __init__(self, max_calls_per_minute: int = 10):
        self.max_calls = max_calls_per_minute
        self.user_call_times: dict[str, deque] = {}
    
    def check_rate_limit(self, user_id: str) -> bool:
        now = time.time()
        if user_id not in self.user_call_times:
            self.user_call_times[user_id] = deque()
        
        # Remove calls older than 60 seconds
        queue = self.user_call_times[user_id]
        while queue and now - queue[0] > 60:
            queue.popleft()
        
        if len(queue) >= self.max_calls:
            return False
        
        queue.append(now)
        return True
    
    def run(self, user_id: str, goal: str) -> str:
        if not self.check_rate_limit(user_id):
            return "Rate limit exceeded. Please wait before making another request."
        return run_react_agent(goal)
```

---

## 11. Complete Example — Data Analysis Agent

```python
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
import json

@tool
def load_csv(filepath: str) -> str:
    """Load a CSV file and return a summary of its contents."""
    import pandas as pd
    try:
        df = pd.read_csv(filepath)
        return json.dumps({
            "shape": list(df.shape),
            "columns": list(df.columns),
            "dtypes": dict(df.dtypes.astype(str)),
            "head": df.head(3).to_dict(),
            "null_counts": dict(df.isnull().sum()),
        }, default=str)
    except Exception as e:
        return f"Error loading CSV: {e}"

@tool
def run_pandas_query(code: str) -> str:
    """Execute pandas code to analyze data. Variable 'df' is available."""
    try:
        import pandas as pd, io, contextlib
        # Security: only allow pandas/numpy operations
        safe_globals = {"pd": pd, "__builtins__": {"print": print, "len": len, "range": range}}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(f"import pandas as pd\n{code}", safe_globals)
        return output.getvalue() or "Query executed (no output)"
    except Exception as e:
        return f"Query error: {e}"

@tool
def create_visualization(data: dict, chart_type: str, title: str) -> str:
    """Create a visualization description from data."""
    return f"Created {chart_type} chart titled '{title}' with {len(data)} data points"

@tool
def statistical_summary(values: list) -> str:
    """Get statistical summary of a list of numbers."""
    import statistics
    if not values:
        return "Empty list"
    return json.dumps({
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
        "min": min(values),
        "max": max(values),
    })

# Build agent
tools = [load_csv, run_pandas_query, create_visualization, statistical_summary]

data_analyst = create_react_agent(
    model=ChatOpenAI(model="gpt-4o", temperature=0),
    tools=tools,
    state_modifier=SystemMessage(content="""You are an expert data analyst.
When analyzing data:
1. First load and understand the data structure
2. Explore relevant columns and relationships
3. Run queries to answer the question
4. Provide a clear, quantitative answer with insights"""),
    checkpointer=MemorySaver(),
)

result = data_analyst.invoke(
    {"messages": [HumanMessage(content="Analyze sales.csv and tell me which product category has the highest average revenue")]},
    config={"configurable": {"thread_id": "analysis_1"}}
)
print(result["messages"][-1].content)
```

---

## 12. Interview Questions

**Q1: What is the ReAct pattern and why is it effective for agents?**

ReAct (Reasoning + Acting) interleaves reasoning traces with tool actions. The LLM produces a Thought (reasoning about what to do), then an Action (tool call), then observes the result before reasoning again. This is effective because: (1) explicit reasoning reduces hallucination — the LLM must justify each step; (2) it enables course correction based on tool results; (3) the reasoning trace is auditable and debuggable. Without the reasoning step, agents tend to misuse tools or fail at multi-step tasks.

**Q2: What are the key considerations when designing tools for agents?**

Five principles: (1) Single responsibility — each tool does one thing; (2) Rich descriptions — the docstring is read by the LLM, make it explain when to use and when NOT to use the tool; (3) Typed inputs — use Pydantic schemas with field descriptions; (4) Error-resilient — return human-readable error messages, never raise exceptions that stop the loop; (5) Limited output size — cap tool output at 2-5K tokens to avoid context explosion.

**Q3: How do you prevent a production agent from running indefinitely or going off-task?**

Four guardrails: (1) Hard iteration limit — stop after N steps and return best answer so far; (2) Timeout per tool call and per full agent run; (3) Task relevance check — periodically verify the agent is still working toward the original goal; (4) Human-in-the-loop for high-stakes actions — pause before irreversible actions (API calls, deletions, purchases). In LangGraph, implement all of these via conditional edges and `interrupt_before`.

**Q4: What is the difference between an agent with episodic memory and one with semantic memory?**

Episodic memory stores the full sequence of past interactions (conversation history) — it's indexed by time. Good for maintaining conversation coherence and referring to what was said earlier. Semantic memory stores distilled facts about users, context, or domain — indexed by meaning. Good for long-term personalization ("user prefers Python") and context that shouldn't expire. Production agents need both: episodic for within-session coherence, semantic for cross-session personalization.

---

*Next: Module 12 — Multi-Agent Systems*
