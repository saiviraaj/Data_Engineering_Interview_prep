# GenAI Engineering Curriculum — Master Learning Roadmap

> **Target Learner:** Software/Cloud/Data Engineer with foundational AI/ML knowledge  
> **Goal:** Production-grade GenAI engineering, RAG systems, agents, system design  
> **Depth Level:** Senior to Staff Engineer  
> **Estimated Mastery Time:** 16–20 weeks at 2–3 hours/day

---

## CURRICULUM PHILOSOPHY

> *"Learn concepts while building real systems."*

Every concept is taught through implementation. Every architecture is explained through real request flows. Every tradeoff is grounded in production engineering reality. Academic depth is minimized. Engineering intuition is maximized.

---

## CURRICULUM STRUCTURE

```
PHASE 1 — FOUNDATIONS (Weeks 1–3)
├── Module 01: LLM Application Engineering
├── Module 02: Prompt Engineering (Practical)
├── Module 03: Structured Outputs & Tool Calling
└── Module 04: Embeddings & Semantic Search

PHASE 2 — RAG ENGINEERING (Weeks 4–7)
├── Module 05: RAG Fundamentals
├── Module 06: Advanced RAG & System Design
└── Module 07: Vector Databases Deep Dive

PHASE 3 — FRAMEWORKS & ORCHESTRATION (Weeks 8–10)
├── Module 08: LangChain Core
├── Module 09: LangGraph Workflows
└── Module 10: LangSmith Observability

PHASE 4 — AGENT ENGINEERING (Weeks 11–13)
├── Module 11: Agent Engineering Fundamentals
├── Module 12: Multi-Agent Systems
└── Module 13: Production Agent Patterns

PHASE 5 — OPEN SOURCE & INFRASTRUCTURE (Weeks 14–15)
├── Module 14: Hugging Face Ecosystem
└── Module 15: Open Source LLMs & Serving

PHASE 6 — PRODUCTION AI ENGINEERING (Weeks 16–17)
└── Module 16: Production AI Engineering

PHASE 7 — SYSTEM DESIGN MASTERY (Weeks 18–20)
├── Module 17: GenAI System Design
└── Module 18: GenAI System Design Interviews

PHASE 8 — ADVANCED TOPICS (Ongoing)
└── Module 19: Advanced & Emerging Topics
```

---

## TOPIC DEPENDENCY GRAPH

```
LLM APIs
    │
    ├──► Prompt Engineering
    │         │
    │         ├──► Structured Outputs ──► Tool Calling
    │         │
    │         └──► Context Engineering
    │
    ├──► Embeddings
    │         │
    │         └──► Semantic Search ──► Vector DBs ──► RAG
    │                                                  │
    │                                     ┌────────────┤
    │                                     │            │
    │                              Basic RAG    Advanced RAG
    │                                                  │
    │                                         ┌────────┤
    │                                         │        │
    │                                    Graph RAG  Enterprise RAG
    │
    ├──► LangChain
    │         │
    │         ├──► LangGraph ──► Agents ──► Multi-Agents
    │         │
    │         └──► LangSmith ──► Observability ──► Evaluation
    │
    └──► Production Patterns
              │
              └──► System Design ──► Interviews
```

---

## LEARNING MILESTONES

### Milestone 1 — LLM Developer (End of Week 3)
**Can do:**
- Call LLM APIs with confidence
- Write effective system prompts
- Implement tool calling
- Get structured JSON outputs
- Build basic chatbots and assistants
- Manage context windows
- Handle streaming responses
- Use embeddings for semantic search

**Proof project:** Multi-tool AI assistant with streaming, structured outputs, and semantic search

---

### Milestone 2 — RAG Engineer (End of Week 7)
**Can do:**
- Design and implement complete RAG pipelines
- Chunk documents intelligently
- Build hybrid retrieval systems
- Implement rerankers
- Debug retrieval quality
- Evaluate RAG systems
- Build production ingestion pipelines
- Understand vector database tradeoffs

**Proof project:** Production RAG system over a large document corpus with evaluation framework

---

### Milestone 3 — AI Orchestration Engineer (End of Week 10)
**Can do:**
- Build complex LangChain chains
- Design LangGraph state machines
- Implement human-in-the-loop systems
- Trace and debug AI workflows with LangSmith
- Build stateful multi-turn applications
- Implement retry and fallback patterns

**Proof project:** Stateful research assistant with LangGraph, full observability in LangSmith

---

### Milestone 4 — Agent Engineer (End of Week 13)
**Can do:**
- Build single and multi-agent systems
- Design planner-executor architectures
- Implement agent memory systems
- Handle agent failures gracefully
- Build approval/review workflows
- Evaluate agent performance

**Proof project:** Multi-agent research + report generation system with checkpointing

---

### Milestone 5 — Production AI Engineer (End of Week 17)
**Can do:**
- Design production AI infrastructure
- Implement comprehensive observability
- Build evaluation pipelines
- Handle security, RBAC, PII
- Optimize cost and latency
- Design for reliability and scale

**Proof project:** Production-grade AI platform with full observability, eval pipeline, and governance

---

### Milestone 6 — Senior GenAI Systems Architect (End of Week 20)
**Can do:**
- Design any enterprise GenAI system
- Reason through architectural tradeoffs
- Answer staff-level system design interviews
- Architect scalable, reliable, observable AI platforms
- Make informed build vs buy decisions

**Proof:** Complete any system design question from Module 18

---

## FILE-BY-FILE STRUCTURE

```
genai-engineering-curriculum/
│
├── 00_learning_roadmap.md              ← YOU ARE HERE
├── 01_llm_application_engineering.md   ← LLM APIs, context, streaming, multimodal
├── 02_prompt_engineering_practical.md  ← Prompts, system prompts, chains, context eng
├── 03_structured_outputs_and_tools.md  ← JSON mode, function calling, tool use
├── 04_embeddings_and_semantic_search.md← Embeddings, similarity, vector search
├── 05_rag_fundamentals.md              ← RAG concepts, ingestion, retrieval basics
├── 06_rag_advanced_and_system_design.md← Hybrid retrieval, rerankers, graph RAG
├── 07_vector_databases.md              ← Chroma, Pinecone, Weaviate, Qdrant, FAISS
├── 08_langchain_core.md                ← Chains, runnables, retrievers, memory
├── 09_langgraph_workflows.md           ← State machines, checkpoints, human-in-loop
├── 10_langsmith_observability.md       ← Tracing, evals, datasets, prompt mgmt
├── 11_agent_engineering.md             ← Agent fundamentals, planning, tool use
├── 12_multi_agent_systems.md           ← Supervisor/worker, orchestration, comms
├── 13_production_agent_patterns.md     ← Reliability, guardrails, long-running agents
├── 14_huggingface_ecosystem.md         ← Transformers, inference APIs, fine-tuning
├── 15_open_source_llms_and_serving.md  ← Ollama, vLLM, quantization, deployment
├── 16_production_ai_engineering.md     ← Observability, evals, caching, security
├── 17_genai_system_design.md           ← Architecture components, patterns, design
├── 18_genai_system_design_interviews.md← 10 deep system design walkthroughs
└── 19_advanced_emerging_topics.md      ← MCP, voice, multimodal, graph RAG, future
```

---

## PROJECT PROGRESSION

### Project 1 — Smart Assistant (Milestone 1)
```
Features:
- Multi-turn conversation
- Tool calling (web search, calculator, code exec)
- Streaming responses
- Structured output extraction
- Semantic memory via embeddings

Stack: OpenAI API + FastAPI + ChromaDB
Files: ~500 lines of production Python
```

### Project 2 — RAG Knowledge Base (Milestone 2)
```
Features:
- PDF/web ingestion pipeline
- Hybrid retrieval (dense + sparse)
- Reranking with cross-encoder
- Citation tracking
- Eval framework (precision@k, faithfulness)
- Admin panel for document management

Stack: LangChain + Qdrant + FastAPI + Streamlit
Files: ~1,500 lines across multiple modules
```

### Project 3 — Stateful Research Agent (Milestone 3)
```
Features:
- LangGraph state machine
- Multi-step research planning
- Web + vector search tools
- Human review checkpoints
- Full LangSmith tracing
- Report generation

Stack: LangGraph + LangSmith + Tavily + OpenAI
Files: ~1,200 lines
```

### Project 4 — Multi-Agent Workflow Platform (Milestone 4)
```
Features:
- Supervisor/worker agent hierarchy
- Specialized agents (researcher, coder, writer)
- Shared memory/context
- Checkpointing and recovery
- Approval workflows
- Agent evaluation

Stack: LangGraph + Redis + PostgreSQL + FastAPI
Files: ~2,000 lines across services
```

### Project 5 — Production AI Platform (Milestone 5)
```
Features:
- Complete observability (traces, metrics, logs)
- Cost tracking per request/user
- Evaluation pipeline (automated + human)
- Multi-model routing
- Semantic caching
- RBAC and audit logging
- PII redaction
- Rate limiting

Stack: LangSmith/Langfuse + Redis + PostgreSQL + Kubernetes
Files: ~3,000+ lines across microservices
```

---

## SYSTEM DESIGN PROGRESSION

```
Week 1-3:   Understand single-model request lifecycle
Week 4-7:   Understand RAG architecture + ingestion pipelines
Week 8-10:  Understand orchestration layers and state management
Week 11-13: Understand agent architectures and multi-agent communication
Week 14-15: Understand serving infrastructure and inference optimization
Week 16-17: Understand production reliability, observability, security
Week 18-20: Full end-to-end system design for any GenAI application
```

---

## INTERVIEW PREPARATION PROGRESSION

### Level 1 — Junior GenAI Engineer Questions
- What is RAG and why is it used?
- How does function calling work?
- What is the difference between embeddings and tokens?
- How do you handle hallucinations?

### Level 2 — Mid-Level Questions
- How would you design a RAG system for a company's internal documents?
- How do you evaluate a RAG system?
- What are the tradeoffs between different chunking strategies?
- How do you implement streaming in a production API?

### Level 3 — Senior Engineer Questions
- Design an enterprise RAG system for 10M documents
- How would you architect a multi-agent research platform?
- How do you ensure reliability in a production AI system?
- Walk me through your approach to GenAI observability

### Level 4 — Staff/Principal Questions
- Design a complete AI platform serving 1M users
- How would you architect a real-time voice AI system?
- Design an AI observability platform used by 100 teams
- How would you approach building a coding assistant like Copilot?

---

## REVISION STRATEGY

### Weekly Review Cadence
```
Daily (30 min):   Review previous day's concepts + one implementation exercise
Weekly (2 hours): Full topic review + project checkpoint
Bi-weekly:        System design practice (whiteboarding)
Monthly:          Full interview simulation
```

### Spaced Repetition Topics (Review these repeatedly)
1. RAG evaluation metrics
2. LangGraph state machine patterns
3. Agent reliability patterns
4. Vector DB tradeoffs
5. Production AI observability
6. System design components

---

## CONTINUOUS LEARNING STRATEGY

### Stay Current
- Follow: Simon Willison's Weblog, Lilian Weng's blog, LangChain blog
- Papers: arxiv cs.AI + cs.CL (weekly scan)
- Repos: LangChain, LangGraph, LlamaIndex, vLLM (watch releases)
- Communities: LangChain Discord, Hugging Face forums

### Benchmark Against Reality
- Build one real project per month
- Contribute to one open-source AI project
- Participate in one AI engineering challenge (e.g., Kaggle, ARC)
- Attempt one system design question from scratch monthly

### Technology Radar (as of 2025)
```
ADOPT:     LangGraph, LangSmith, Qdrant, vLLM, LlamaIndex, Ollama
TRIAL:     CrewAI, AutoGen, DSPy, LiteLLM, Portkey
ASSESS:    MCP servers, Browser agents, Computer-use agents
HOLD:      Basic LangChain chains (superseded by LCEL + LangGraph)
```

---

## HOW TO USE THIS CURRICULUM

**If you're new to AI engineering:** Start at Module 01 and progress linearly. Do every exercise.

**If you have some LLM API experience:** Skip to Module 03, read 01-02 as reference.

**If you need RAG specifically:** Read 04-07 deeply. Reference 08 for LangChain patterns.

**If you need agents:** Read 05-07 for RAG context, then 08-13 for agents.

**If you're interview prepping:** Read 17-18 deeply, use 05-07, 11-13 as reference.

**If you're architecting a production system:** Read 16-18, reference others as needed.

---

## READING GUIDE FOR EACH MODULE

Each module follows this structure:

```
1. THE BIG PICTURE        — Why this matters, where it fits
2. CORE CONCEPTS          — What it is, mental models
3. IMPLEMENTATION         — Code, patterns, examples
4. PRODUCTION PATTERNS    — How it works in real systems
5. TRADEOFFS              — Decisions and their implications
6. DEBUGGING              — What goes wrong and how to fix it
7. SCALING                — How to handle growth
8. SECURITY               — What to watch out for
9. EXERCISES              — Build it yourself
10. INTERVIEW QUESTIONS   — Prepare for the conversation
```

---

*Next: [Module 01 — LLM Application Engineering →](01_llm_application_engineering.md)*
