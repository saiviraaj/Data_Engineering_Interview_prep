# Module 09 — LangGraph Stateful Workflows

> LangGraph is the premier framework for building stateful, multi-step AI workflows and agents. This module covers everything from basic graphs to production-grade agentic systems.

---

## Table of Contents

1. [Why LangGraph?](#1-why-langgraph)
2. [Core Concepts — State, Nodes, Edges](#2-core-concepts--state-nodes-edges)
3. [Building Your First Graph](#3-building-your-first-graph)
4. [State Management Patterns](#4-state-management-patterns)
5. [Conditional Routing](#5-conditional-routing)
6. [Cycles and Loops](#6-cycles-and-loops)
7. [Human-in-the-Loop](#7-human-in-the-loop)
8. [Parallel Execution (Branches)](#8-parallel-execution-branches)
9. [Checkpointing and Persistence](#9-checkpointing-and-persistence)
10. [Streaming in LangGraph](#10-streaming-in-langgraph)
11. [Subgraphs](#11-subgraphs)
12. [ReAct Agent with LangGraph](#12-react-agent-with-langgraph)
13. [Complete Example — Research Agent](#13-complete-example--research-agent)
14. [Interview Questions](#14-interview-questions)

---

## 1. Why LangGraph?

LangChain's LCEL is excellent for linear pipelines: A → B → C. But real-world AI systems need:

- **Loops**: retry until condition is met, iterate over a list
- **Branching**: different paths based on LLM output or state
- **Human approval**: pause and wait for human input before continuing
- **Persistence**: save and resume long-running workflows
- **Multi-agent**: coordinate multiple specialized agents

LangGraph models these as directed graphs (or cyclic graphs) with typed state:

```
LCEL:     A → B → C → D
LangGraph: A → B ←→ C → D → [human pause] → E
                ↑_______|   (loop back based on condition)
```

### Install

```bash
pip install langgraph langchain-openai
```

---

## 2. Core Concepts — State, Nodes, Edges

### State

State is a typed Python `TypedDict` that flows through the entire graph. Every node reads from and writes to the state.

```python
from typing import TypedDict, Annotated, List, Optional
import operator

class AgentState(TypedDict):
    # Annotated with operator.add → lists are APPENDED (not replaced)
    messages: Annotated[List, operator.add]
    
    # No annotation → replaced on each update
    current_task: str
    iteration_count: int
    final_answer: Optional[str]
    error: Optional[str]
```

**Key insight:** `Annotated[List, operator.add]` means multiple nodes can add to `messages` without clobbering each other. Without annotation, the last write wins.

### Nodes

Nodes are functions that take state and return a partial state update:

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def agent_node(state: AgentState) -> dict:
    """LLM reasoning step."""
    response = llm.invoke(state["messages"])
    return {
        "messages": [response],  # Appended to existing messages
        "iteration_count": state.get("iteration_count", 0) + 1,
    }

def tool_execution_node(state: AgentState) -> dict:
    """Execute tool calls from last message."""
    last_message = state["messages"][-1]
    # Execute tool calls, return results
    tool_results = execute_tools(last_message.tool_calls)
    return {"messages": tool_results}
```

### Edges

Edges define the flow between nodes:

```python
from langgraph.graph import StateGraph, START, END

# Fixed edge: always go from A to B
graph.add_edge("node_a", "node_b")

# Conditional edge: route based on state
graph.add_conditional_edges(
    "agent",
    should_continue,  # routing function → returns node name
    {
        "continue": "tools",     # if "continue" → go to tools
        "end": END,              # if "end" → terminate
    }
)

# Entry point
graph.add_edge(START, "agent")
```

---

## 3. Building Your First Graph

### Hello World Graph

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import operator

# 1. Define state
class SimpleState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

# 2. Define nodes
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def call_llm(state: SimpleState) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# 3. Build graph
graph_builder = StateGraph(SimpleState)
graph_builder.add_node("llm", call_llm)
graph_builder.add_edge(START, "llm")
graph_builder.add_edge("llm", END)

# 4. Compile
graph = graph_builder.compile()

# 5. Run
result = graph.invoke({
    "messages": [HumanMessage(content="What is LangGraph?")]
})
print(result["messages"][-1].content)
```

### Visualize the Graph

```python
# Requires graphviz or mermaid
from IPython.display import Image, display
display(Image(graph.get_graph().draw_mermaid_png()))

# Or print ASCII
print(graph.get_graph().draw_ascii())
```

---

## 4. State Management Patterns

### Reducer Functions

```python
from typing import TypedDict, Annotated
import operator

def replace_if_not_none(existing, new):
    """Only update if new value is not None."""
    return new if new is not None else existing

class WorkflowState(TypedDict):
    # Append all messages
    messages: Annotated[list, operator.add]
    
    # Append search results (deduplicated)
    search_results: Annotated[list, operator.add]
    
    # Replace only when set (custom reducer)
    final_answer: Annotated[str, replace_if_not_none]
    
    # Simple replacement (no annotation)
    status: str
    iteration: int
    
    # Track errors (append)
    errors: Annotated[list, operator.add]
```

### Complex State Objects

```python
from pydantic import BaseModel
from langchain_core.messages import BaseMessage

class ResearchResult(BaseModel):
    query: str
    sources: list[str]
    summary: str
    confidence: float

class ResearchState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    research_results: Annotated[list[ResearchResult], operator.add]
    current_query: str
    queries_completed: Annotated[list[str], operator.add]
    final_report: Optional[str]
    iteration: int
    max_iterations: int
```

### State Validation

```python
from langgraph.graph import StateGraph
from pydantic import BaseModel, validator

class ValidatedState(BaseModel):
    """Use Pydantic for state validation."""
    messages: list
    query: str
    max_iterations: int = 5
    
    @validator("max_iterations")
    def positive_iterations(cls, v):
        if v <= 0:
            raise ValueError("max_iterations must be positive")
        return v

graph = StateGraph(ValidatedState)
```

---

## 5. Conditional Routing

### Routing Function Pattern

```python
from typing import Literal
from langchain_core.messages import AIMessage

def route_after_agent(state: AgentState) -> Literal["tools", "end", "human_review"]:
    """
    Determine next step based on last message.
    Returns the name of the next node (or END).
    """
    last_message = state["messages"][-1]
    
    # If LLM wants to call tools
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    
    # If too many iterations
    if state.get("iteration_count", 0) >= 10:
        return "human_review"
    
    # Otherwise, done
    return "end"

graph.add_conditional_edges(
    "agent",
    route_after_agent,
    {
        "tools": "tool_execution",
        "end": END,
        "human_review": "human_review_node",
    }
)
```

### Router Node Pattern (LLM-Based Routing)

```python
ROUTER_PROMPT = """Given the user's query, classify it into one of these categories:
- "code": Questions about programming, debugging, code review
- "math": Mathematical calculations or proofs
- "general": Everything else

Return ONLY the category name.

Query: {query}"""

def query_router(state: AgentState) -> dict:
    """LLM-based query routing."""
    query = state["messages"][-1].content
    
    response = llm.invoke([HumanMessage(content=ROUTER_PROMPT.format(query=query))])
    category = response.content.strip().lower()
    
    return {"route": category}

def route_based_on_classification(state: AgentState) -> str:
    return state.get("route", "general")

# Need to add "route" to state
class RoutedState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    route: str

graph.add_node("router", query_router)
graph.add_conditional_edges(
    "router",
    route_based_on_classification,
    {"code": "code_agent", "math": "math_agent", "general": "general_agent"}
)
```

---

## 6. Cycles and Loops

Cycles enable iterative refinement — a pattern used in ReAct agents and agentic loops.

### Simple Agent Loop

```python
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    # Integrate with real search API
    return f"Search results for: {query}"

@tool  
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

tools = [web_search, calculator]
llm_with_tools = ChatOpenAI(model="gpt-4o").bind_tools(tools)

# Tool executor
from langchain_core.messages import ToolMessage
import json

def execute_tools(state: AgentState) -> dict:
    """Execute all tool calls from the last message."""
    last_message = state["messages"][-1]
    results = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]
        
        # Find and execute the tool
        tool_map = {t.name: t for t in tools}
        if tool_name in tool_map:
            result = tool_map[tool_name].invoke(tool_input)
        else:
            result = f"Tool {tool_name} not found"
        
        results.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))
    
    return {"messages": results}

def call_agent(state: AgentState) -> dict:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response], "iteration_count": state.get("iteration_count", 0) + 1}

def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"

# Build cyclic graph
agent_graph = StateGraph(AgentState)
agent_graph.add_node("agent", call_agent)
agent_graph.add_node("tools", execute_tools)

agent_graph.add_edge(START, "agent")
agent_graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
agent_graph.add_edge("tools", "agent")  # Loop back!

agent = agent_graph.compile()
```

### Iteration Limit Guard

```python
def should_continue_with_limit(state: AgentState) -> Literal["tools", "end", "timeout"]:
    last = state["messages"][-1]
    
    # Hard iteration limit
    if state.get("iteration_count", 0) >= 20:
        return "timeout"
    
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"

def timeout_node(state: AgentState) -> dict:
    return {
        "messages": [AIMessage(content="I've reached my iteration limit. Here's what I found so far...")],
        "final_answer": "timeout"
    }

agent_graph.add_node("timeout_handler", timeout_node)
agent_graph.add_conditional_edges(
    "agent",
    should_continue_with_limit,
    {"tools": "tools", "end": END, "timeout": "timeout_handler"}
)
agent_graph.add_edge("timeout_handler", END)
```

---

## 7. Human-in-the-Loop

Human-in-the-loop (HITL) is one of LangGraph's most powerful features. The graph can pause at any point and wait for human input before continuing.

### Interrupt Before Node

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

# Compile with interrupt_before: graph pauses before executing listed nodes
hitl_graph = agent_graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["tools"],  # Pause before any tool execution
)

# Start the graph
thread_id = "thread_001"
config = {"configurable": {"thread_id": thread_id}}

# Run until first interrupt
result = hitl_graph.invoke(
    {"messages": [HumanMessage(content="What's the weather in Hyderabad?")]},
    config=config
)

# Graph is paused — inspect the pending tool call
state = hitl_graph.get_state(config)
print("Pending tool calls:", state.values["messages"][-1].tool_calls)

# Human approves or modifies
human_approved = True  # or False to reject

if human_approved:
    # Resume from where it stopped
    result = hitl_graph.invoke(None, config=config)
else:
    # Cancel: update state with rejection message
    hitl_graph.update_state(
        config,
        {"messages": [ToolMessage(
            content="Tool execution rejected by user.",
            tool_call_id=state.values["messages"][-1].tool_calls[0]["id"]
        )]},
        as_node="tools"
    )
```

### Interrupt After Node (Review Output)

```python
# Pause after agent produces answer but before final delivery
review_graph = agent_graph.compile(
    checkpointer=checkpointer,
    interrupt_after=["agent"],  # Pause after agent responds
)

# Run to agent response
result = review_graph.invoke(initial_state, config=config)

# Human reviews
state = review_graph.get_state(config)
agent_response = state.values["messages"][-1].content

# Human can edit the response
edited_response = human_edit(agent_response)  # UI interaction

if edited_response != agent_response:
    # Overwrite with edited version
    review_graph.update_state(
        config,
        {"messages": [AIMessage(content=edited_response)]},
        as_node="agent"
    )

# Continue to delivery
review_graph.invoke(None, config=config)
```

### Dynamic Interrupts

```python
from langgraph.types import interrupt, Command

def sensitive_tool_node(state: AgentState) -> dict:
    """Dynamically interrupt when tool action is sensitive."""
    last_message = state["messages"][-1]
    
    for tool_call in last_message.tool_calls:
        if tool_call["name"] in ["delete_file", "send_email", "charge_card"]:
            # Dynamic interrupt — pause and return question to human
            human_decision = interrupt({
                "action": f"About to execute: {tool_call['name']}",
                "args": tool_call["args"],
                "question": "Do you approve this action? (yes/no)"
            })
            
            if human_decision.lower() != "yes":
                return {"messages": [AIMessage(content="Action cancelled by user.")]}
    
    # Execute tools normally
    return execute_tools(state)
```

---

## 8. Parallel Execution (Branches)

LangGraph supports parallel node execution using the `Send` API or by fanning out to multiple nodes simultaneously.

### Fan-Out to Parallel Nodes

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
import operator

class ParallelState(TypedDict):
    query: str
    messages: Annotated[list, operator.add]
    web_results: Annotated[list, operator.add]
    doc_results: Annotated[list, operator.add]
    synthesis: str

def web_search_node(state: ParallelState) -> dict:
    """Search the web."""
    # Simulate web search
    results = [f"Web result for: {state['query']}"]
    return {"web_results": results}

def doc_search_node(state: ParallelState) -> dict:
    """Search internal documents."""
    results = [f"Doc result for: {state['query']}"]
    return {"doc_results": results}

def synthesize_node(state: ParallelState) -> dict:
    """Combine web and doc results."""
    context = "\n".join(state["web_results"] + state["doc_results"])
    response = llm.invoke([HumanMessage(
        content=f"Synthesize these results for '{state['query']}':\n{context}"
    )])
    return {"synthesis": response.content}

# Build parallel graph
parallel_graph = StateGraph(ParallelState)
parallel_graph.add_node("web_search", web_search_node)
parallel_graph.add_node("doc_search", doc_search_node)
parallel_graph.add_node("synthesize", synthesize_node)

# Fan out from START to both search nodes in parallel
parallel_graph.add_edge(START, "web_search")
parallel_graph.add_edge(START, "doc_search")

# Both converge at synthesize
parallel_graph.add_edge("web_search", "synthesize")
parallel_graph.add_edge("doc_search", "synthesize")

parallel_graph.add_edge("synthesize", END)

graph = parallel_graph.compile()
result = graph.invoke({"query": "LangGraph parallel execution", "messages": []})
```

### Dynamic Parallel Dispatch with Send

```python
from langgraph.types import Send

def distribute_queries(state: ResearchState) -> list[Send]:
    """Dynamically send each query to a worker node in parallel."""
    return [
        Send("research_worker", {"query": q, "messages": []})
        for q in state["queries_to_run"]
    ]

def research_worker(state: dict) -> dict:
    """Process a single query."""
    result = do_research(state["query"])
    return {"research_results": [result]}

# Graph with dynamic fan-out
research_graph = StateGraph(ResearchState)
research_graph.add_node("planner", plan_queries_node)
research_graph.add_node("research_worker", research_worker)
research_graph.add_node("synthesizer", synthesize_results_node)

research_graph.add_edge(START, "planner")
research_graph.add_conditional_edges("planner", distribute_queries)  # Dynamic dispatch
research_graph.add_edge("research_worker", "synthesizer")
research_graph.add_edge("synthesizer", END)
```

---

## 9. Checkpointing and Persistence

Checkpointing saves state at every step, enabling: resume-after-interrupt, fault tolerance, audit trails, time-travel debugging.

### MemorySaver (Development)

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "session_abc"}}
result = graph.invoke(initial_state, config=config)

# Get current state
state = graph.get_state(config)
print(state.values)

# Get state history (time travel)
history = list(graph.get_state_history(config))
for snapshot in history:
    print(f"Step: {snapshot.metadata.get('step')}, Nodes: {snapshot.next}")
```

### PostgreSQL Checkpointer (Production)

```python
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg

DB_URL = "postgresql://user:pass@localhost:5432/langgraph"

with psycopg.connect(DB_URL) as conn:
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()  # Create tables on first run

graph = builder.compile(checkpointer=checkpointer)
```

### SQLite Checkpointer (Local Production)

```python
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
graph = builder.compile(checkpointer=checkpointer)
```

### Resume After Failure

```python
def resilient_run(graph, initial_state, thread_id: str):
    """Run graph, automatically resume if it was interrupted."""
    config = {"configurable": {"thread_id": thread_id}}
    
    # Check if there's existing state for this thread
    existing_state = graph.get_state(config)
    
    if existing_state.values:
        # Resume from existing state
        print(f"Resuming thread {thread_id} from step {existing_state.metadata.get('step', 0)}")
        return graph.invoke(None, config=config)
    else:
        # Fresh start
        return graph.invoke(initial_state, config=config)
```

---

## 10. Streaming in LangGraph

```python
# Stream mode: "values" — emit full state after each step
for state in graph.stream(initial_input, stream_mode="values"):
    print(f"State update: {list(state.keys())}")

# Stream mode: "updates" — emit only changed keys
for update in graph.stream(initial_input, stream_mode="updates"):
    for node_name, node_update in update.items():
        print(f"Node '{node_name}' updated: {list(node_update.keys())}")

# Stream mode: "messages" — stream individual LLM tokens
async def stream_tokens(graph, input_state, config):
    async for event in graph.astream_events(input_state, config=config, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"].content
            if chunk:
                yield chunk

# FastAPI SSE endpoint
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/agent/stream")
async def stream_agent(request: dict):
    config = {"configurable": {"thread_id": request.get("session_id", "default")}}
    initial = {"messages": [HumanMessage(content=request["message"])]}
    
    async def event_generator():
        async for chunk in stream_tokens(compiled_graph, initial, config):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 11. Subgraphs

Subgraphs allow composing graphs within graphs — essential for multi-agent systems.

```python
from langgraph.graph import StateGraph, START, END

# Define a reusable research subgraph
class ResearchSubState(TypedDict):
    query: str
    results: Annotated[list, operator.add]
    summary: str

def search_node(state: ResearchSubState) -> dict:
    return {"results": [web_search(state["query"])]}

def summarize_node(state: ResearchSubState) -> dict:
    summary = llm.invoke([HumanMessage(
        content=f"Summarize: {' '.join(state['results'])}"
    )]).content
    return {"summary": summary}

research_sub = StateGraph(ResearchSubState)
research_sub.add_node("search", search_node)
research_sub.add_node("summarize", summarize_node)
research_sub.add_edge(START, "search")
research_sub.add_edge("search", "summarize")
research_sub.add_edge("summarize", END)
research_subgraph = research_sub.compile()

# Parent graph using the subgraph
class ParentState(TypedDict):
    topic: str
    messages: Annotated[list, operator.add]
    research_summary: str

def prepare_research_query(state: ParentState) -> dict:
    return {}  # Potentially transform state

def use_research_in_response(state: ParentState) -> dict:
    response = llm.invoke([HumanMessage(
        content=f"Based on research: {state['research_summary']}\nAnswer about: {state['topic']}"
    )])
    return {"messages": [response]}

parent_graph = StateGraph(ParentState)
parent_graph.add_node("prepare", prepare_research_query)
parent_graph.add_node("research", research_subgraph)  # Subgraph as node
parent_graph.add_node("respond", use_research_in_response)

parent_graph.add_edge(START, "prepare")
parent_graph.add_edge("prepare", "research")
parent_graph.add_edge("research", "respond")
parent_graph.add_edge("respond", END)
```

---

## 12. ReAct Agent with LangGraph

```python
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """Search the web for current information."""
    # Real implementation: Tavily, SerpAPI, etc.
    return f"Web results for '{query}': [simulated results]"

@tool
def get_stock_price(ticker: str) -> str:
    """Get the current stock price for a ticker symbol."""
    prices = {"AAPL": 175.50, "GOOGL": 140.20, "MSFT": 380.00}
    return f"${prices.get(ticker.upper(), 'Unknown ticker')}"

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        return str(round(eval(expression), 4))
    except Exception as e:
        return f"Error: {e}"

tools = [search_web, get_stock_price, calculate]

# Built-in ReAct agent (simplest approach)
react_agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4o", temperature=0),
    tools=tools,
    state_modifier=SystemMessage(
        content="You are a helpful research assistant. Use tools to find accurate information."
    ),
    checkpointer=MemorySaver(),
)

result = react_agent.invoke(
    {"messages": [HumanMessage(content="What's the market cap of Apple if the stock is at its current price and they have 15.5B shares?")]},
    config={"configurable": {"thread_id": "research_1"}}
)
print(result["messages"][-1].content)
```

---

## 13. Complete Example — Research Agent

```python
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
import operator, json

# ── State ─────────────────────────────────────────────────────────────
class ResearchAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    research_plan: Optional[list[str]]
    gathered_info: Annotated[list[str], operator.add]
    draft_report: Optional[str]
    iteration: int
    max_iterations: int
    human_feedback: Optional[str]

# ── Tools ─────────────────────────────────────────────────────────────
@tool
def web_search(query: str) -> str:
    """Search the web for recent information."""
    return f"[WEB] Results for '{query}': Found 5 relevant articles about the topic."

@tool
def search_papers(topic: str) -> str:
    """Search academic papers on a topic."""
    return f"[PAPERS] Found 3 recent papers on '{topic}' in Nature and Science."

@tool
def summarize_source(url: str) -> str:
    """Fetch and summarize a web page."""
    return f"[SUMMARY] Key points from {url}: Main findings are..."

tools = [web_search, search_papers, summarize_source]
tool_map = {t.name: t for t in tools}

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(tools)

# ── Nodes ─────────────────────────────────────────────────────────────
def planner_node(state: ResearchAgentState) -> dict:
    """Create a research plan from the user's request."""
    system = SystemMessage(content="""You are a research planner. 
Create a structured research plan with 3-5 specific sub-queries to investigate.
Respond with JSON: {"plan": ["query1", "query2", ...], "overview": "brief description"}""")
    
    response = llm.invoke([system] + state["messages"])
    try:
        plan_data = json.loads(response.content)
        plan = plan_data.get("plan", [])
    except Exception:
        plan = ["General research on the topic"]
    
    return {
        "messages": [response],
        "research_plan": plan,
        "iteration": 0,
    }

def researcher_node(state: ResearchAgentState) -> dict:
    """Use tools to gather information."""
    system = SystemMessage(content="""You are a research assistant. 
Use the provided tools to gather information. Be thorough and specific.""")
    
    context = f"Research plan: {state.get('research_plan', [])}\nGathered so far: {len(state.get('gathered_info', []))} items"
    messages = [system, HumanMessage(content=context)] + state["messages"][-3:]
    
    response = llm_with_tools.invoke(messages)
    return {
        "messages": [response],
        "iteration": state.get("iteration", 0) + 1,
    }

def tool_executor_node(state: ResearchAgentState) -> dict:
    """Execute tool calls from researcher."""
    from langchain_core.messages import ToolMessage
    
    last_message = state["messages"][-1]
    tool_results = []
    gathered = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        if tool_name in tool_map:
            result = tool_map[tool_name].invoke(tool_call["args"])
        else:
            result = f"Tool {tool_name} not found"
        
        tool_results.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))
        gathered.append(str(result))
    
    return {"messages": tool_results, "gathered_info": gathered}

def writer_node(state: ResearchAgentState) -> dict:
    """Write the research report."""
    system = SystemMessage(content="""You are a research writer. 
Write a comprehensive, well-structured report based on the gathered information.
Include: Executive Summary, Key Findings, Analysis, Conclusions.""")
    
    gathered_text = "\n".join(state.get("gathered_info", []))
    write_prompt = HumanMessage(
        content=f"Write a research report on the user's query.\nGathered information:\n{gathered_text}"
    )
    
    response = llm.invoke([system] + state["messages"][:1] + [write_prompt])
    return {
        "messages": [response],
        "draft_report": response.content,
    }

def review_node(state: ResearchAgentState) -> dict:
    """Human review checkpoint."""
    feedback = interrupt({
        "report_preview": state.get("draft_report", "")[:500] + "...",
        "question": "Please review the draft. Type 'approve' to finalize or provide feedback."
    })
    return {"human_feedback": feedback}

def revise_node(state: ResearchAgentState) -> dict:
    """Revise report based on human feedback."""
    system = SystemMessage(content="You are a research editor. Revise the report based on the feedback.")
    revise_prompt = HumanMessage(
        content=f"Original report:\n{state['draft_report']}\n\nFeedback:\n{state['human_feedback']}\n\nProvide revised report:"
    )
    response = llm.invoke([system, revise_prompt])
    return {"messages": [response], "draft_report": response.content}

# ── Routing Functions ─────────────────────────────────────────────────
def route_researcher(state: ResearchAgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    if state.get("iteration", 0) >= state.get("max_iterations", 5):
        return "write"
    # More research needed?
    if len(state.get("gathered_info", [])) < 3:
        return "continue_research"
    return "write"

def route_after_review(state: ResearchAgentState) -> str:
    feedback = state.get("human_feedback", "").lower().strip()
    if feedback == "approve":
        return "finalize"
    return "revise"

# ── Build Graph ────────────────────────────────────────────────────────
builder = StateGraph(ResearchAgentState)

builder.add_node("planner", planner_node)
builder.add_node("researcher", researcher_node)
builder.add_node("tool_executor", tool_executor_node)
builder.add_node("writer", writer_node)
builder.add_node("human_review", review_node)
builder.add_node("reviser", revise_node)

builder.add_edge(START, "planner")
builder.add_edge("planner", "researcher")
builder.add_conditional_edges(
    "researcher",
    route_researcher,
    {
        "tools": "tool_executor",
        "continue_research": "researcher",
        "write": "writer",
    }
)
builder.add_edge("tool_executor", "researcher")
builder.add_edge("writer", "human_review")
builder.add_conditional_edges(
    "human_review",
    route_after_review,
    {
        "finalize": END,
        "revise": "reviser",
    }
)
builder.add_edge("reviser", "human_review")  # Loop until approved

# Compile with checkpointing
checkpointer = MemorySaver()
research_agent = builder.compile(checkpointer=checkpointer)

# ── Run ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "research_session_1"}}
    
    initial_state = {
        "messages": [HumanMessage(content="Research the current state of quantum computing and its potential impact on cryptography.")],
        "max_iterations": 5,
    }
    
    # Run until human review interrupt
    result = research_agent.invoke(initial_state, config=config)
    
    # Graph paused for human review
    state = research_agent.get_state(config)
    if state.next:
        print("Waiting for human review...")
        # Simulate human approval
        research_agent.invoke(
            Command(resume="approve"),
            config=config
        )
```

---

## 14. Interview Questions

**Q1: What is LangGraph's state model and how does it differ from LCEL?**

LangGraph models computation as a directed (possibly cyclic) graph where each node is a function operating on typed state. State is a TypedDict shared across all nodes — nodes return partial updates. LCEL is for linear pipelines with no shared state across calls. LangGraph adds: cycles/loops, persistence (checkpointing), human-in-the-loop interrupts, and shared mutable state. LCEL is the building block for individual nodes within a LangGraph.

**Q2: Explain the Annotated[List, operator.add] pattern in state definition.**

Without annotation, a node that returns `{"messages": [new_msg]}` replaces the entire messages list. With `Annotated[list, operator.add]`, multiple nodes can append to the same list concurrently — their outputs are merged via the `add` reducer. This is critical in parallel branches (multiple nodes write to the same state key without overwriting each other) and in agent loops (every tool result appends to history without losing previous messages).

**Q3: How does human-in-the-loop work technically in LangGraph?**

HITL requires a checkpointer. When the graph reaches an `interrupt_before` node or a `interrupt()` call, it saves the complete state to the checkpointer and raises an exception. The graph resumes when you call `invoke(None, config=config)` (with `interrupt_before`) or `invoke(Command(resume=value), config=config)` (for dynamic interrupts). The state is reloaded from the checkpoint, and execution continues from the interrupted node.

**Q4: How would you build a multi-agent system where a supervisor routes tasks to specialized subagents?**

Use LangGraph's subgraph pattern: each specialized agent (researcher, coder, analyst) is a compiled subgraph. The supervisor is a parent graph with a routing node that calls `Send()` to dispatch to the right subgraph based on task type. Each subgraph runs independently in its own state space but returns results to the parent state. Use a shared checkpointer for the parent so the full orchestration is recoverable.

---

*Next: Module 10 — LangSmith Observability*
