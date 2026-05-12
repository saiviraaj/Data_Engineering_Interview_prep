# Module 12 — Multi-Agent Systems

> When one agent isn't enough. Multi-agent systems divide complex tasks across specialized agents, enabling parallelism, specialization, and scalability.

---

## Table of Contents

1. [Why Multi-Agent Systems?](#1-why-multi-agent-systems)
2. [Multi-Agent Architectures](#2-multi-agent-architectures)
3. [Supervisor-Worker Pattern](#3-supervisor-worker-pattern)
4. [Peer-to-Peer Agent Communication](#4-peer-to-peer-agent-communication)
5. [Shared State vs Message Passing](#5-shared-state-vs-message-passing)
6. [Hierarchical Agent Systems](#6-hierarchical-agent-systems)
7. [Specialized Agent Teams](#7-specialized-agent-teams)
8. [Debate and Critique Patterns](#8-debate-and-critique-patterns)
9. [Agent Coordination Protocols](#9-agent-coordination-protocols)
10. [Production Multi-Agent Patterns](#10-production-multi-agent-patterns)
11. [Complete Example — Research Team](#11-complete-example--research-team)
12. [Interview Questions](#12-interview-questions)

---

## 1. Why Multi-Agent Systems?

Single agents hit practical limits:

| Problem | Single Agent Failure | Multi-Agent Solution |
|---|---|---|
| Context window | 100K+ token tasks overflow context | Each agent handles a slice |
| Specialization | Generalist prompts are mediocre | Domain expert agents |
| Parallelism | Sequential tool calls = slow | Parallel agent execution |
| Verification | Self-checking is unreliable | Separate critic agent |
| Role separation | Mixed concerns in one prompt | Clean responsibility separation |

### When Multi-Agent Is Appropriate

- Tasks that naturally decompose into parallel subtasks
- Tasks requiring different expertise at different stages
- Tasks where a critic/validator improves quality
- Long-running workflows that exceed single context windows
- Systems where different agents need different tool access levels

### Multi-Agent Complexity Cost

Multi-agent systems are harder to debug, more expensive (more LLM calls), and can exhibit emergent failure modes. Start with a single agent and add agents only when you hit clear bottlenecks.

---

## 2. Multi-Agent Architectures

### Architecture Taxonomy

```
1. SUPERVISOR-WORKER
   Supervisor assigns tasks → Workers execute → Supervisor synthesizes

2. PIPELINE (Sequential)
   Agent A → Agent B → Agent C → Output
   Each agent processes output of previous

3. PARALLEL DISPATCH
   Orchestrator → [Agent A, Agent B, Agent C] → Merge
   Agents run simultaneously on different aspects

4. PEER-TO-PEER (Mesh)
   Agents communicate with each other directly
   Used in debate/critique patterns

5. HIERARCHICAL
   Manager → Team Leads → Worker Agents
   Enterprise-scale decomposition
```

---

## 3. Supervisor-Worker Pattern

The most common multi-agent pattern. A supervisor LLM decides which worker to call next.

```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
import operator

# ── State ─────────────────────────────────────────────────────────────
class SupervisorState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    next_agent: str       # Which agent the supervisor wants to call next
    task_results: Annotated[list[dict], operator.add]  # Accumulated results
    final_answer: str

# ── Define Workers ─────────────────────────────────────────────────────
WORKERS = ["researcher", "coder", "writer", "critic"]

llm = ChatOpenAI(model="gpt-4o", temperature=0)

SUPERVISOR_PROMPT = """You are a supervisor managing a team of agents.
Given the conversation and the work done so far, decide which agent should act next.

Available agents:
- researcher: Searches for information and facts
- coder: Writes and executes code
- writer: Drafts documents and reports
- critic: Reviews and critiques work for quality

Respond with ONLY one of: researcher, coder, writer, critic, FINISH

Current task: {task}
Work done: {work_summary}"""

def supervisor_node(state: SupervisorState) -> dict:
    """Supervisor decides next agent."""
    task = state["messages"][0].content
    work_summary = "\n".join(
        f"- {r.get('agent', '?')}: {r.get('result', '')[:100]}"
        for r in state.get("task_results", [])
    )
    
    response = llm.invoke([
        SystemMessage(content=SUPERVISOR_PROMPT.format(
            task=task, work_summary=work_summary or "No work done yet"
        ))
    ])
    
    next_agent = response.content.strip().lower()
    if next_agent not in WORKERS + ["finish"]:
        next_agent = "researcher"  # Default
    
    return {"next_agent": next_agent}

def route_from_supervisor(state: SupervisorState) -> str:
    """Route to the chosen worker or END."""
    agent = state.get("next_agent", "finish")
    if agent == "finish":
        return "synthesizer"
    return agent

# ── Worker Nodes ───────────────────────────────────────────────────────
def make_worker(role: str, description: str, tools: list = None):
    """Factory for worker nodes."""
    worker_llm = llm.bind_tools(tools) if tools else llm
    
    def worker_node(state: SupervisorState) -> dict:
        system = SystemMessage(content=f"You are an expert {role}. {description}")
        response = worker_llm.invoke([system] + state["messages"][-5:])
        
        result = {"agent": role, "result": response.content}
        
        return {
            "messages": [AIMessage(content=f"[{role.upper()}] {response.content}")],
            "task_results": [result],
        }
    
    worker_node.__name__ = f"{role}_node"
    return worker_node

researcher_node = make_worker(
    "researcher",
    "Find accurate, up-to-date information. Cite sources. Be specific."
)
coder_node = make_worker(
    "coder",
    "Write clean, well-commented code. Include error handling. Test edge cases."
)
writer_node = make_worker(
    "writer",
    "Write clear, professional prose. Structure well. Be concise."
)
critic_node = make_worker(
    "critic",
    "Identify flaws, inaccuracies, and areas for improvement. Be constructive."
)

def synthesizer_node(state: SupervisorState) -> dict:
    """Synthesize all agent outputs into final answer."""
    results_text = "\n\n".join(
        f"[{r['agent']}]:\n{r['result']}"
        for r in state.get("task_results", [])
    )
    
    response = llm.invoke([
        SystemMessage(content="Synthesize the following team outputs into a coherent final answer."),
        HumanMessage(content=f"Original task: {state['messages'][0].content}\n\nTeam outputs:\n{results_text}")
    ])
    
    return {
        "messages": [response],
        "final_answer": response.content
    }

# ── Build Graph ────────────────────────────────────────────────────────
from langgraph.checkpoint.memory import MemorySaver

supervisor_graph = StateGraph(SupervisorState)

# Add nodes
supervisor_graph.add_node("supervisor", supervisor_node)
supervisor_graph.add_node("researcher", researcher_node)
supervisor_graph.add_node("coder", coder_node)
supervisor_graph.add_node("writer", writer_node)
supervisor_graph.add_node("critic", critic_node)
supervisor_graph.add_node("synthesizer", synthesizer_node)

# Edges
supervisor_graph.add_edge(START, "supervisor")
supervisor_graph.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "researcher": "researcher",
        "coder": "coder",
        "writer": "writer",
        "critic": "critic",
        "synthesizer": "synthesizer",
    }
)

# All workers report back to supervisor
for worker in WORKERS:
    supervisor_graph.add_edge(worker, "supervisor")

supervisor_graph.add_edge("synthesizer", END)

multi_agent = supervisor_graph.compile(checkpointer=MemorySaver())
```

### Supervisor with Max Rounds Guard

```python
MAX_ROUNDS = 8

def supervisor_with_limit(state: SupervisorState) -> dict:
    rounds = len(state.get("task_results", []))
    
    if rounds >= MAX_ROUNDS:
        return {"next_agent": "finish"}
    
    # Normal supervisor logic
    return supervisor_node(state)
```

---

## 4. Peer-to-Peer Agent Communication

In P2P patterns, agents can directly invoke each other using LangGraph's `Send` mechanism.

```python
from langgraph.types import Send
from typing import TypedDict, Annotated
import operator

class P2PAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    peer_requests: list[dict]  # [{to_agent, message}]
    completed_by: Annotated[list[str], operator.add]

def analyst_node(state: P2PAgentState) -> dict:
    """Analyst that may request help from coder."""
    response = llm.invoke([
        SystemMessage(content="You are a data analyst. If you need code written, request the coder."),
        *state["messages"]
    ])
    
    # Parse if analyst needs coder help
    if "need_code" in response.content.lower():
        return {
            "messages": [response],
            "peer_requests": [{"to": "coder", "task": "Write analysis code"}],
            "completed_by": ["analyst"]
        }
    
    return {
        "messages": [response],
        "completed_by": ["analyst"]
    }

def dispatch_peer_requests(state: P2PAgentState) -> list[Send] | str:
    """Fan out to peer agents based on requests."""
    requests = state.get("peer_requests", [])
    if not requests:
        return "synthesize"
    
    return [
        Send(req["to"], {"messages": [HumanMessage(content=req["task"])], "peer_requests": [], "completed_by": []})
        for req in requests
    ]
```

---

## 5. Shared State vs Message Passing

### Shared State (LangGraph approach)

All agents read from and write to the same state object. Good for tightly coupled workflows.

```python
class SharedWorkflowState(TypedDict):
    # Shared inputs
    task: str
    documents: list[dict]
    
    # Shared accumulator (all agents contribute)
    research_notes: Annotated[list[str], operator.add]
    code_snippets: Annotated[list[str], operator.add]
    
    # Final outputs
    draft: str
    reviewed_draft: str
    final_answer: str
    
    # Coordination
    step_completed: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
```

### Message Passing (Queue-based)

For decoupled, distributed agents:

```python
import asyncio
from asyncio import Queue
from dataclasses import dataclass

@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str
    message_type: str  # "task", "result", "error", "broadcast"
    content: dict
    correlation_id: str

class MessageBus:
    """Simple in-process message bus for agent communication."""
    
    def __init__(self):
        self.queues: dict[str, Queue] = {}
        self.broadcast_subscribers: list[str] = []
    
    def register_agent(self, agent_id: str):
        self.queues[agent_id] = Queue()
    
    async def send(self, message: AgentMessage):
        """Send message to specific agent."""
        if message.to_agent in self.queues:
            await self.queues[message.to_agent].put(message)
    
    async def broadcast(self, message: AgentMessage):
        """Send to all registered agents."""
        for agent_id, queue in self.queues.items():
            if agent_id != message.from_agent:
                await queue.put(message)
    
    async def receive(self, agent_id: str, timeout: float = 5.0) -> AgentMessage:
        """Receive next message for an agent."""
        return await asyncio.wait_for(
            self.queues[agent_id].get(),
            timeout=timeout
        )

class MessagePassingAgent:
    """Agent that communicates via message bus."""
    
    def __init__(self, agent_id: str, role: str, bus: MessageBus):
        self.id = agent_id
        self.role = role
        self.bus = bus
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        bus.register_agent(agent_id)
    
    async def run(self):
        """Main agent loop — process messages."""
        while True:
            try:
                message = await self.bus.receive(self.id, timeout=10.0)
                
                if message.message_type == "task":
                    result = await self.process_task(message.content)
                    await self.bus.send(AgentMessage(
                        from_agent=self.id,
                        to_agent=message.from_agent,
                        message_type="result",
                        content={"result": result},
                        correlation_id=message.correlation_id,
                    ))
            except asyncio.TimeoutError:
                break  # No messages, done
    
    async def process_task(self, task: dict) -> str:
        response = self.llm.invoke([
            SystemMessage(content=f"You are a {self.role} agent."),
            HumanMessage(content=str(task))
        ])
        return response.content
```

---

## 6. Hierarchical Agent Systems

For enterprise-scale tasks requiring deep decomposition:

```python
class HierarchicalState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    task: str
    subtasks: list[dict]
    subtask_results: Annotated[list[dict], operator.add]
    team_summaries: Annotated[list[str], operator.add]
    final_report: str

def project_manager_node(state: HierarchicalState) -> dict:
    """L1: Project manager breaks task into sub-projects."""
    response = llm.invoke([
        SystemMessage(content="""You are a project manager. Break the task into 2-4 major work streams.
Return JSON: {"subtasks": [{"id": "1", "name": "...", "description": "...", "team": "research|engineering|design"}]}"""),
        HumanMessage(content=state["task"])
    ])
    
    import json
    try:
        data = json.loads(response.content)
        subtasks = data.get("subtasks", [])
    except Exception:
        subtasks = [{"id": "1", "name": "Main task", "description": state["task"], "team": "research"}]
    
    return {"messages": [response], "subtasks": subtasks}

def dispatch_to_teams(state: HierarchicalState) -> list[Send]:
    """Fan out subtasks to team leaders."""
    return [
        Send(
            f"team_leader_{subtask['team']}",
            {"messages": [HumanMessage(content=subtask["description"])], "subtasks": [subtask], "subtask_results": [], "team_summaries": []}
        )
        for subtask in state.get("subtasks", [])
    ]

def team_leader_node(role: str):
    """L2: Team leader executes with own workers."""
    def node(state: HierarchicalState) -> dict:
        subtask = state["subtasks"][0]
        
        # Team leader uses its specialized workers
        worker_responses = []
        for i in range(2):  # 2 workers per team
            response = llm.invoke([
                SystemMessage(content=f"You are a {role} expert (worker {i+1})."),
                HumanMessage(content=subtask["description"])
            ])
            worker_responses.append(response.content)
        
        # Team leader synthesizes worker outputs
        synthesis = llm.invoke([
            SystemMessage(content=f"You are the {role} team leader. Synthesize these worker outputs."),
            HumanMessage(content=f"Worker outputs:\n{chr(10).join(worker_responses)}")
        ])
        
        return {
            "subtask_results": [{"team": role, "subtask_id": subtask["id"], "result": synthesis.content}],
            "team_summaries": [f"{role} team: {synthesis.content[:200]}"]
        }
    return node

def executive_summary_node(state: HierarchicalState) -> dict:
    """L0: Executive synthesizes all team outputs."""
    team_work = "\n\n".join(
        f"[{r['team']} team]:\n{r['result']}"
        for r in state.get("subtask_results", [])
    )
    
    response = llm.invoke([
        SystemMessage(content="You are a C-level executive. Create an executive summary from team reports."),
        HumanMessage(content=f"Task: {state['task']}\n\nTeam reports:\n{team_work}")
    ])
    
    return {"messages": [response], "final_report": response.content}

# Build hierarchical graph
h_graph = StateGraph(HierarchicalState)
h_graph.add_node("project_manager", project_manager_node)
h_graph.add_node("team_leader_research", team_leader_node("research"))
h_graph.add_node("team_leader_engineering", team_leader_node("engineering"))
h_graph.add_node("team_leader_design", team_leader_node("design"))
h_graph.add_node("executive_summary", executive_summary_node)

h_graph.add_edge(START, "project_manager")
h_graph.add_conditional_edges("project_manager", dispatch_to_teams)
for team in ["research", "engineering", "design"]:
    h_graph.add_edge(f"team_leader_{team}", "executive_summary")
h_graph.add_edge("executive_summary", END)
```

---

## 7. Specialized Agent Teams

Effective team composition by capability:

```python
# Team pattern: each specialist handles one aspect
# Then an integrator combines their outputs

class AnalysisTeamState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    data: str
    statistical_analysis: str
    business_insights: str
    technical_notes: str
    recommendations: str
    final_report: str

def statistical_analyst_node(state: AnalysisTeamState) -> dict:
    """Specialist: statistical analysis."""
    response = llm.invoke([
        SystemMessage(content="You are a statistician. Analyze the data for statistical patterns, distributions, and significance."),
        HumanMessage(content=f"Data:\n{state['data']}")
    ])
    return {"statistical_analysis": response.content, "messages": [response]}

def business_analyst_node(state: AnalysisTeamState) -> dict:
    """Specialist: business implications."""
    response = llm.invoke([
        SystemMessage(content="You are a business analyst. Focus on business implications, KPIs, and strategic insights."),
        HumanMessage(content=f"Data:\n{state['data']}\nStatistical analysis:\n{state.get('statistical_analysis', '')}")
    ])
    return {"business_insights": response.content, "messages": [response]}

def technical_expert_node(state: AnalysisTeamState) -> dict:
    """Specialist: technical implementation."""
    response = llm.invoke([
        SystemMessage(content="You are a technical expert. Focus on data quality, methodology, and technical limitations."),
        HumanMessage(content=f"Data:\n{state['data']}")
    ])
    return {"technical_notes": response.content, "messages": [response]}

def report_writer_node(state: AnalysisTeamState) -> dict:
    """Integrator: synthesize all specialist outputs."""
    response = llm.invoke([
        SystemMessage(content="You are a senior analyst. Write a comprehensive report integrating all specialist analyses."),
        HumanMessage(content=f"""Statistical analysis: {state.get('statistical_analysis', '')}
Business insights: {state.get('business_insights', '')}
Technical notes: {state.get('technical_notes', '')}

Write a well-structured report with Executive Summary, Key Findings, and Recommendations.""")
    ])
    return {"final_report": response.content, "messages": [response]}

# Fan-out graph: run specialists in parallel, then integrate
analysis_graph = StateGraph(AnalysisTeamState)
analysis_graph.add_node("stats", statistical_analyst_node)
analysis_graph.add_node("business", business_analyst_node)
analysis_graph.add_node("technical", technical_expert_node)
analysis_graph.add_node("reporter", report_writer_node)

# Parallel specialist execution
analysis_graph.add_edge(START, "stats")
analysis_graph.add_edge(START, "technical")
# Business analyst needs stats first (sequential dependency)
analysis_graph.add_edge("stats", "business")

# All converge at reporter
analysis_graph.add_edge("business", "reporter")
analysis_graph.add_edge("technical", "reporter")
analysis_graph.add_edge("reporter", END)
```

---

## 8. Debate and Critique Patterns

### Generator-Critic Pattern

```python
class DebateState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    question: str
    current_answer: str
    critiques: Annotated[list[str], operator.add]
    revisions: Annotated[list[str], operator.add]
    rounds: int
    max_rounds: int
    final_answer: str

def generator_node(state: DebateState) -> dict:
    """Generate or revise an answer."""
    if state.get("critiques"):
        last_critique = state["critiques"][-1]
        prompt = f"""Original question: {state['question']}
Your previous answer: {state.get('current_answer', '')}
Critique: {last_critique}

Revise your answer to address the critique."""
    else:
        prompt = f"Answer this question thoroughly: {state['question']}"
    
    response = llm.invoke([
        SystemMessage(content="You are an expert analyst. Provide well-reasoned, thorough answers."),
        HumanMessage(content=prompt)
    ])
    
    return {
        "current_answer": response.content,
        "revisions": [response.content],
        "rounds": state.get("rounds", 0) + 1,
        "messages": [response]
    }

def critic_node(state: DebateState) -> dict:
    """Critique the current answer."""
    response = llm.invoke([
        SystemMessage(content="""You are a critical reviewer. Find flaws, gaps, and inaccuracies.
Be specific and constructive. If the answer is satisfactory, respond with "APPROVED"."""),
        HumanMessage(content=f"Question: {state['question']}\nAnswer to critique:\n{state['current_answer']}")
    ])
    
    return {
        "critiques": [response.content],
        "messages": [response]
    }

def route_after_critique(state: DebateState) -> str:
    """Continue debating or accept if critique approves or max rounds reached."""
    if state.get("rounds", 0) >= state.get("max_rounds", 3):
        return "finalize"
    
    last_critique = state.get("critiques", [""])[-1]
    if "APPROVED" in last_critique.upper():
        return "finalize"
    
    return "revise"

def finalize_node(state: DebateState) -> dict:
    return {"final_answer": state.get("current_answer", "")}

# Build debate graph
debate_graph = StateGraph(DebateState)
debate_graph.add_node("generator", generator_node)
debate_graph.add_node("critic", critic_node)
debate_graph.add_node("finalize", finalize_node)

debate_graph.add_edge(START, "generator")
debate_graph.add_edge("generator", "critic")
debate_graph.add_conditional_edges(
    "critic",
    route_after_critique,
    {"revise": "generator", "finalize": "finalize"}
)
debate_graph.add_edge("finalize", END)

debate = debate_graph.compile()
```

### Multi-Perspective Debate

```python
def multi_perspective_debate(question: str, perspectives: list[str]) -> str:
    """Have multiple agents argue different perspectives, then synthesize."""
    
    perspective_responses = {}
    
    # Parallel argument generation
    for perspective in perspectives:
        response = llm.invoke([
            SystemMessage(content=f"You argue from the {perspective} perspective. Be convincing."),
            HumanMessage(content=f"Question: {question}")
        ])
        perspective_responses[perspective] = response.content
    
    # Synthesis
    debate_text = "\n\n".join(
        f"[{p.upper()} perspective]: {r}"
        for p, r in perspective_responses.items()
    )
    
    synthesis = llm.invoke([
        SystemMessage(content="You are a balanced analyst. Synthesize multiple perspectives into a nuanced view."),
        HumanMessage(content=f"Question: {question}\n\nPerspectives:\n{debate_text}")
    ])
    
    return synthesis.content
```

---

## 9. Agent Coordination Protocols

### Blackboard Pattern

A shared "blackboard" that any agent can read from and write to:

```python
from threading import Lock
from datetime import datetime

class Blackboard:
    """Shared knowledge store for multi-agent coordination."""
    
    def __init__(self):
        self._data: dict = {}
        self._history: list = []
        self._lock = Lock()
    
    def write(self, key: str, value, agent_id: str):
        with self._lock:
            self._data[key] = value
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "agent": agent_id,
                "action": "write",
                "key": key,
            })
    
    def read(self, key: str):
        with self._lock:
            return self._data.get(key)
    
    def get_snapshot(self) -> dict:
        with self._lock:
            return dict(self._data)
    
    def get_history_summary(self, n: int = 10) -> str:
        recent = self._history[-n:]
        return "\n".join(f"{h['timestamp'][:19]} [{h['agent']}] {h['action']} {h['key']}" for h in recent)
```

### Contract Net Protocol

Agents bid for tasks based on capability:

```python
@dataclass
class TaskBid:
    agent_id: str
    task_id: str
    confidence: float  # 0-1
    estimated_time_s: float
    capabilities_match: list[str]

def request_bids(task: str, available_agents: list) -> list[TaskBid]:
    """Ask all agents to bid on a task."""
    bids = []
    for agent in available_agents:
        bid_prompt = f"""You are agent '{agent.id}' with capabilities: {agent.capabilities}.
Task: {task}
Rate your confidence (0-1) and estimated time. Return JSON: {{"confidence": 0.8, "time": 5, "capabilities": ["cap1"]}}"""
        
        response = llm.invoke([HumanMessage(content=bid_prompt)])
        try:
            import json
            data = json.loads(response.content)
            bids.append(TaskBid(
                agent_id=agent.id,
                task_id=task[:20],
                confidence=data.get("confidence", 0.5),
                estimated_time_s=data.get("time", 10),
                capabilities_match=data.get("capabilities", [])
            ))
        except Exception:
            pass
    
    return sorted(bids, key=lambda b: b.confidence, reverse=True)

def assign_task(task: str, agents: list) -> str:
    """Assign task to most confident agent."""
    bids = request_bids(task, agents)
    if not bids:
        return agents[0].id
    return bids[0].agent_id  # Highest confidence wins
```

---

## 10. Production Multi-Agent Patterns

### Idempotent Agent Execution

```python
import hashlib

def get_task_hash(task: str, inputs: dict) -> str:
    """Deterministic hash for deduplication."""
    content = f"{task}:{sorted(inputs.items())}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]

class IdempotentMultiAgentSystem:
    """Ensures tasks aren't executed twice (e.g., on retry)."""
    
    def __init__(self):
        self.completed_tasks: dict[str, dict] = {}
    
    async def run_task(self, task_id: str, task: str, inputs: dict) -> dict:
        task_hash = get_task_hash(task, inputs)
        
        # Check if already completed
        if task_hash in self.completed_tasks:
            return self.completed_tasks[task_hash]
        
        # Execute
        result = await execute_agent_task(task, inputs)
        
        # Cache result
        self.completed_tasks[task_hash] = result
        return result
```

### Agent Health Monitoring

```python
import time
from dataclasses import dataclass, field

@dataclass
class AgentMetrics:
    agent_id: str
    calls: int = 0
    errors: int = 0
    total_latency: float = 0.0
    last_error: str = ""
    
    @property
    def avg_latency(self) -> float:
        return self.total_latency / self.calls if self.calls > 0 else 0
    
    @property
    def error_rate(self) -> float:
        return self.errors / self.calls if self.calls > 0 else 0

class MonitoredMultiAgentSystem:
    """Multi-agent system with per-agent health metrics."""
    
    def __init__(self, agents: dict):
        self.agents = agents
        self.metrics = {agent_id: AgentMetrics(agent_id=agent_id) for agent_id in agents}
    
    async def call_agent(self, agent_id: str, input_data: dict) -> dict:
        metrics = self.metrics[agent_id]
        start = time.time()
        
        try:
            result = await self.agents[agent_id](input_data)
            metrics.calls += 1
            metrics.total_latency += time.time() - start
            return result
        except Exception as e:
            metrics.errors += 1
            metrics.last_error = str(e)
            raise
    
    def get_health_report(self) -> dict:
        return {
            agent_id: {
                "calls": m.calls,
                "error_rate": f"{m.error_rate:.1%}",
                "avg_latency": f"{m.avg_latency:.2f}s",
                "status": "healthy" if m.error_rate < 0.1 else "degraded"
            }
            for agent_id, m in self.metrics.items()
        }
```

---

## 11. Complete Example — Research Team

```python
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
import operator, json

# ── Tools ──────────────────────────────────────────────────────────────
@tool
def search_web(query: str) -> str:
    """Search the web for information on a topic."""
    return f"Web search results for '{query}': [Simulated results with key facts]"

@tool
def search_academic(topic: str) -> str:
    """Search academic databases for research papers."""
    return f"Academic results for '{topic}': [3 peer-reviewed papers found]"

@tool
def fact_check(claim: str) -> str:
    """Verify a factual claim."""
    return f"Fact check: '{claim}' - [Verified/Disputed with sources]"

# ── State ──────────────────────────────────────────────────────────────
class ResearchTeamState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    research_question: str
    research_plan: Optional[list[str]]
    web_findings: Annotated[list[str], operator.add]
    academic_findings: Annotated[list[str], operator.add]
    fact_checks: Annotated[list[str], operator.add]
    draft_report: Optional[str]
    reviewed_report: Optional[str]
    final_report: Optional[str]
    quality_score: float

# ── Nodes ──────────────────────────────────────────────────────────────
llm = ChatOpenAI(model="gpt-4o", temperature=0)

def research_planner(state: ResearchTeamState) -> dict:
    """Plan the research approach."""
    response = llm.invoke([
        SystemMessage(content="You are a research director. Create a focused research plan."),
        HumanMessage(content=f"Research question: {state['research_question']}\n\nCreate a JSON plan: {{\"tasks\": [\"specific_task_1\", \"task_2\", ...]}}")
    ])
    try:
        plan = json.loads(response.content).get("tasks", [state["research_question"]])
    except Exception:
        plan = [state["research_question"]]
    
    return {"research_plan": plan, "messages": [response]}

def web_researcher(state: ResearchTeamState) -> dict:
    """Web-focused researcher."""
    lm = llm.bind_tools([search_web])
    
    questions = state.get("research_plan", [state["research_question"]])[:2]
    findings = []
    
    for q in questions:
        response = lm.invoke([
            SystemMessage(content="Search the web for information. Use the search_web tool."),
            HumanMessage(content=q)
        ])
        if response.tool_calls:
            for tc in response.tool_calls:
                result = search_web.invoke(tc["args"])
                findings.append(f"Q: {q}\nFindings: {result}")
    
    return {"web_findings": findings, "messages": [AIMessage(content=f"Web research completed: {len(findings)} findings")]}

def academic_researcher(state: ResearchTeamState) -> dict:
    """Academic-focused researcher."""
    lm = llm.bind_tools([search_academic])
    
    question = state.get("research_plan", [state["research_question"]])[0]
    response = lm.invoke([
        SystemMessage(content="Search academic databases for peer-reviewed research."),
        HumanMessage(content=question)
    ])
    
    findings = []
    if response.tool_calls:
        for tc in response.tool_calls:
            result = search_academic.invoke(tc["args"])
            findings.append(result)
    
    return {"academic_findings": findings, "messages": [AIMessage(content=f"Academic research completed: {len(findings)} papers")]}

def fact_checker_agent(state: ResearchTeamState) -> dict:
    """Fact-checking agent."""
    all_findings = (
        state.get("web_findings", []) +
        state.get("academic_findings", [])
    )
    
    if not all_findings:
        return {"fact_checks": ["No findings to verify"]}
    
    # Extract and verify key claims
    claims_resp = llm.invoke([
        SystemMessage(content="Extract 3 key factual claims from these research findings. Return JSON: {\"claims\": [...]}"),
        HumanMessage(content="\n".join(all_findings[:3]))
    ])
    
    try:
        claims = json.loads(claims_resp.content).get("claims", [])
    except Exception:
        claims = ["Main research claim"]
    
    checks = [fact_check.invoke({"claim": c}) for c in claims]
    return {"fact_checks": checks}

def report_writer(state: ResearchTeamState) -> dict:
    """Write the research report."""
    context = f"""Web findings:\n{chr(10).join(state.get('web_findings', []))}

Academic findings:\n{chr(10).join(state.get('academic_findings', []))}

Fact checks:\n{chr(10).join(state.get('fact_checks', []))}"""
    
    response = llm.invoke([
        SystemMessage(content="""You are a research writer. Write a comprehensive report with:
1. Executive Summary (3-4 sentences)
2. Key Findings (5-7 bullet points)
3. Methodology Notes
4. Conclusions and Implications"""),
        HumanMessage(content=f"Research question: {state['research_question']}\n\nSources:\n{context}")
    ])
    
    return {"draft_report": response.content, "messages": [response]}

def quality_reviewer(state: ResearchTeamState) -> dict:
    """Review and score the draft report."""
    response = llm.invoke([
        SystemMessage(content="""Review this research report for quality.
Score 0-10 on: accuracy, completeness, clarity.
Return JSON: {"score": 8.5, "issues": ["issue1"], "suggestions": ["suggestion1"]}"""),
        HumanMessage(content=f"Report:\n{state.get('draft_report', '')}")
    ])
    
    try:
        review = json.loads(response.content)
        score = review.get("score", 7) / 10.0
        issues = review.get("issues", [])
    except Exception:
        score = 0.7
        issues = []
    
    return {
        "quality_score": score,
        "reviewed_report": state.get("draft_report", ""),
        "messages": [response]
    }

def report_finalizer(state: ResearchTeamState) -> dict:
    """Finalize or request revision based on quality score."""
    if state.get("quality_score", 0) >= 0.75:
        return {"final_report": state.get("reviewed_report", state.get("draft_report", ""))}
    
    # Low quality — refine
    response = llm.invoke([
        SystemMessage(content="Improve this report. Make it more comprehensive and accurate."),
        HumanMessage(content=state.get("reviewed_report", ""))
    ])
    return {"final_report": response.content}

def route_after_review(state: ResearchTeamState) -> str:
    score = state.get("quality_score", 0)
    if score >= 0.75:
        return "finalize"
    return "revise"

# ── Build Graph ────────────────────────────────────────────────────────
team_graph = StateGraph(ResearchTeamState)

team_graph.add_node("planner", research_planner)
team_graph.add_node("web_researcher", web_researcher)
team_graph.add_node("academic_researcher", academic_researcher)
team_graph.add_node("fact_checker", fact_checker_agent)
team_graph.add_node("writer", report_writer)
team_graph.add_node("reviewer", quality_reviewer)
team_graph.add_node("finalizer", report_finalizer)

# Flow: plan → parallel research → fact check → write → review → finalize
team_graph.add_edge(START, "planner")
# Parallel research after planning
team_graph.add_edge("planner", "web_researcher")
team_graph.add_edge("planner", "academic_researcher")
# Both converge at fact checker
team_graph.add_edge("web_researcher", "fact_checker")
team_graph.add_edge("academic_researcher", "fact_checker")
team_graph.add_edge("fact_checker", "writer")
team_graph.add_edge("writer", "reviewer")
team_graph.add_conditional_edges("reviewer", route_after_review, {"finalize": "finalizer", "revise": "writer"})
team_graph.add_edge("finalizer", END)

research_team = team_graph.compile(checkpointer=MemorySaver())

# Run
if __name__ == "__main__":
    result = research_team.invoke(
        {
            "research_question": "What are the environmental impacts of large language model training?",
            "messages": [],
        },
        config={"configurable": {"thread_id": "research_001"}}
    )
    print(result.get("final_report", "No report generated"))
```

---

## 12. Interview Questions

**Q1: When would you use a supervisor-worker pattern vs a pipeline pattern?**

Pipeline is best when tasks have clear sequential dependencies and each stage's output feeds the next — e.g., load → preprocess → analyze → report. Supervisor-worker is best when the task requires dynamic orchestration: the supervisor sees results and decides what to do next; different iterations may call different workers; the number of steps isn't fixed. Pipelines are simpler and more predictable; supervisors are more flexible but harder to debug.

**Q2: How do you prevent a multi-agent system from looping indefinitely?**

Multiple guards: (1) Maximum round counter in state, check in routing function before re-entering any loop; (2) Termination condition check — verify the supervisor is making progress by comparing outputs across rounds; (3) Timeout at the overall workflow level; (4) Human-in-the-loop interrupt after N rounds; (5) Track "supervisor decisions" — if it's choosing the same agent N times consecutively, force termination. In LangGraph, implement via conditional edges that check iteration count.

**Q3: How do you handle state consistency when multiple agents write to shared state in parallel?**

LangGraph's reducer functions (Annotated with operator.add) handle concurrent writes to list fields safely — each node's output is appended, not overwritten. For non-list fields, the last-write-wins rule applies. Design state so that parallel agents write to different keys (e.g., `web_findings` vs `academic_findings`) rather than the same key. For fields that need merge logic, write a custom reducer function.

**Q4: What is the Generator-Critic pattern and when does it improve output quality?**

Generator-Critic uses two agents: one generates output, one critiques it, and they iterate. It improves quality when: (1) single-pass LLM responses are good but not great, and self-review would be biased; (2) the task requires identifying logical gaps, factual errors, or missing coverage; (3) you have 2-3 iterations budget. It's overkill for simple tasks and can introduce excessive hedging if the critic is too harsh. Cap iterations at 3 and detect "APPROVED" to avoid unnecessary rounds.

---

*Next: Module 13 — Production Agent Patterns*
