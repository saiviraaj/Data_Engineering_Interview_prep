# Module 10 — LangSmith Observability

> You cannot improve what you cannot measure. LangSmith is the observability and evaluation platform built for LangChain applications.

---

## Table of Contents

1. [Why LangSmith?](#1-why-langsmith)
2. [Setup and Configuration](#2-setup-and-configuration)
3. [Tracing — Understanding Your Chain](#3-tracing)
4. [Datasets — Test Sets for Evaluation](#4-datasets)
5. [Evaluators — Automated Quality Scoring](#5-evaluators)
6. [Human Feedback and Annotation](#6-human-feedback-and-annotation)
7. [Prompt Hub](#7-prompt-hub)
8. [LangSmith SDK — Programmatic Access](#8-langsmith-sdk)
9. [Production Monitoring](#9-production-monitoring)
10. [CI/CD Integration](#10-cicd-integration)
11. [Interview Questions](#11-interview-questions)

---

## 1. Why LangSmith?

LLM applications fail in non-deterministic ways:
- The same prompt produces different answers on different days
- Retrieval quality degrades as your document corpus grows
- Subtle prompt changes break edge cases
- You can't tell if v2 is actually better than v1

LangSmith solves these by providing:

| Feature | What It Does |
|---|---|
| Tracing | Record every LLM call, chain step, retrieval with full context |
| Datasets | Curate golden test sets from production traces |
| Evaluators | Automatically score runs on quality metrics |
| Feedback | Collect human ratings and corrections |
| Prompt Hub | Version and share prompts across projects |
| Monitoring | Dashboards for latency, cost, quality over time |

---

## 2. Setup and Configuration

```bash
pip install langsmith langchain-openai
```

```python
import os

# Required: LangSmith API key
os.environ["LANGCHAIN_API_KEY"] = "ls__your_key_here"

# Enable tracing globally (all LangChain calls auto-traced)
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Project name (organizes traces in LangSmith UI)
os.environ["LANGCHAIN_PROJECT"] = "my-rag-app-production"

# Optional: endpoint (default is api.smith.langchain.com)
# os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
```

Once these env vars are set, **every LangChain/LangGraph call is automatically traced** — no code changes needed.

---

## 3. Tracing

### Automatic Tracing

With env vars set, all LangChain primitives trace automatically:

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o-mini")
chain = ChatPromptTemplate.from_template("Explain {topic}") | llm | StrOutputParser()

# This call is automatically traced to LangSmith
result = chain.invoke({"topic": "HNSW indexing"})
```

In LangSmith UI you see: input, output, latency, token count, cost, model name, all intermediate steps.

### Manual Tracing with @traceable

```python
from langsmith import traceable
from langsmith.run_trees import RunTree

@traceable(
    run_type="chain",
    name="MyRAGPipeline",
    tags=["production", "v2"],
    metadata={"component": "rag", "version": "2.1"}
)
def rag_query(query: str, tenant_id: str) -> dict:
    # Your RAG logic here
    docs = retrieve(query, tenant_id)
    answer = generate(query, docs)
    return {"answer": answer, "sources": len(docs)}

# Use normally — automatically traced
result = rag_query("What is HNSW?", "tenant_abc")
```

### Tracing Non-LangChain Code

```python
from langsmith import Client
from langsmith.run_trees import RunTree
import time

client = Client()

def trace_custom_step(
    name: str,
    run_type: str,
    inputs: dict,
    outputs: dict,
    error: str = None,
    parent_run_id: str = None
):
    """Manually log a trace step to LangSmith."""
    run = client.create_run(
        name=name,
        run_type=run_type,
        inputs=inputs,
        project_name=os.environ["LANGCHAIN_PROJECT"],
        parent_run_id=parent_run_id,
        start_time=time.time(),
    )
    
    client.update_run(
        run.id,
        outputs=outputs,
        error=error,
        end_time=time.time(),
    )
    return run.id

# Example: trace a custom embedding call
run_id = trace_custom_step(
    name="CustomEmbedding",
    run_type="embedding",
    inputs={"texts": ["query text"], "model": "text-embedding-3-small"},
    outputs={"embeddings_shape": [1, 1536], "latency_ms": 45},
)
```

### Adding Run Metadata

```python
from langchain_core.runnables import RunnableConfig

# Add metadata, tags, and run names at invocation time
result = chain.invoke(
    {"question": "What is RAG?"},
    config=RunnableConfig(
        run_name="production_query",
        tags=["user_query", "v2", "tenant_abc"],
        metadata={
            "user_id": "user_123",
            "session_id": "sess_abc",
            "tenant": "acme_corp",
            "query_type": "technical"
        }
    )
)
```

---

## 4. Datasets

Datasets are curated collections of (input, expected_output) pairs used for evaluation.

### Creating a Dataset

```python
from langsmith import Client

client = Client()

# Create dataset
dataset = client.create_dataset(
    dataset_name="RAG Quality v1",
    description="Golden test set for RAG pipeline quality evaluation",
)

# Add examples manually
examples = [
    {
        "inputs": {"question": "What is HNSW indexing?"},
        "outputs": {"answer": "HNSW (Hierarchical Navigable Small World) is a graph-based ANN algorithm..."}
    },
    {
        "inputs": {"question": "How does BM25 work?"},
        "outputs": {"answer": "BM25 is a probabilistic ranking function that scores documents..."}
    },
    {
        "inputs": {"question": "What is the difference between dense and sparse retrieval?"},
        "outputs": {"answer": "Dense retrieval uses neural embeddings, sparse uses keyword-based..."}
    },
]

client.create_examples(
    inputs=[e["inputs"] for e in examples],
    outputs=[e["outputs"] for e in examples],
    dataset_id=dataset.id,
)

print(f"Dataset created: {dataset.id}")
```

### Creating Dataset from Production Traces

```python
# Select high-quality traces from production and add to dataset
runs = client.list_runs(
    project_name="my-rag-app-production",
    run_type="chain",
    filter='and(gt(total_tokens, 100), lt(latency, 5))',  # Fast, substantive runs
    limit=100,
)

# Add selected runs to dataset
for run in runs:
    if run.outputs:
        client.create_examples(
            inputs=[run.inputs],
            outputs=[run.outputs],
            dataset_id=dataset.id,
        )
```

### Dataset Management

```python
# List all datasets
for ds in client.list_datasets():
    print(f"{ds.name}: {ds.example_count} examples")

# Add more examples later
client.create_examples(
    inputs=[{"question": "New test question"}],
    outputs=[{"answer": "Expected answer"}],
    dataset_id=dataset.id,
)

# Get dataset examples
examples = list(client.list_examples(dataset_id=dataset.id))
for ex in examples[:3]:
    print(f"Input: {ex.inputs}, Expected: {ex.outputs}")
```

---

## 5. Evaluators

### Built-in Evaluators

```python
from langchain.evaluation import (
    load_evaluator,
    EvaluatorType,
)
from langchain_openai import ChatOpenAI

# LLM-as-judge evaluators
evaluator_map = {
    "correctness": load_evaluator(
        EvaluatorType.LABELED_SCORE_STRING,
        llm=ChatOpenAI(model="gpt-4o"),
        criteria="correctness",
    ),
    "faithfulness": load_evaluator(
        EvaluatorType.SCORE_STRING,
        llm=ChatOpenAI(model="gpt-4o"),
        criteria="Is the answer faithful to the retrieved context?",
    ),
    "conciseness": load_evaluator(
        EvaluatorType.SCORE_STRING,
        llm=ChatOpenAI(model="gpt-4o"),
        criteria="conciseness",
    ),
}
```

### Running Evaluations with LangSmith

```python
from langsmith.evaluation import evaluate, LangChainStringEvaluator

def predict_fn(inputs: dict) -> dict:
    """Run your chain on an example input."""
    result = rag_chain.invoke({"question": inputs["question"]})
    return {"answer": result}

# Run evaluation on full dataset
eval_results = evaluate(
    predict_fn,
    data="RAG Quality v1",           # Dataset name
    evaluators=[
        LangChainStringEvaluator("correctness", config={"llm": ChatOpenAI(model="gpt-4o")}),
        LangChainStringEvaluator("conciseness", config={"llm": ChatOpenAI(model="gpt-4o-mini")}),
    ],
    experiment_prefix="rag_v2_evaluation",
    metadata={"version": "2.0", "retriever": "hybrid"},
    num_repetitions=1,
    max_concurrency=5,
)

print(f"Experiment URL: {eval_results.experiment_url}")
```

### Custom Evaluators

```python
from langsmith.evaluation import run_evaluator, EvaluationResult

@run_evaluator
def answer_length_evaluator(run, example) -> EvaluationResult:
    """Simple heuristic: penalize very short or very long answers."""
    answer = run.outputs.get("answer", "")
    length = len(answer.split())
    
    if length < 10:
        score = 0.2
        comment = "Too short"
    elif length > 500:
        score = 0.6
        comment = "Too verbose"
    else:
        score = 1.0
        comment = "Good length"
    
    return EvaluationResult(
        key="answer_length",
        score=score,
        comment=comment
    )

@run_evaluator
def citation_present_evaluator(run, example) -> EvaluationResult:
    """Check if the answer contains citations."""
    answer = run.outputs.get("answer", "")
    has_citations = "[" in answer and "]" in answer
    
    return EvaluationResult(
        key="has_citations",
        score=1.0 if has_citations else 0.0,
    )

@run_evaluator
def relevance_evaluator(run, example) -> EvaluationResult:
    """LLM-as-judge for relevance."""
    question = run.inputs.get("question", "")
    answer = run.outputs.get("answer", "")
    
    judge_prompt = f"""Does this answer relevantly address the question?
    
Question: {question}
Answer: {answer}

Score 1-10 where 10 = perfectly relevant. Respond with JSON: {{"score": N, "reasoning": "..."}}"""
    
    import json
    response = ChatOpenAI(model="gpt-4o-mini").invoke([
        HumanMessage(content=judge_prompt)
    ])
    result = json.loads(response.content)
    
    return EvaluationResult(
        key="relevance",
        score=result["score"] / 10.0,
        comment=result["reasoning"]
    )

# Use custom evaluators
eval_results = evaluate(
    predict_fn,
    data="RAG Quality v1",
    evaluators=[answer_length_evaluator, citation_present_evaluator, relevance_evaluator],
    experiment_prefix="rag_custom_eval",
)
```

### Comparing Experiments

```python
# Run same evaluation on two versions
results_v1 = evaluate(
    predict_fn_v1,
    data="RAG Quality v1",
    evaluators=[...],
    experiment_prefix="rag_v1",
)

results_v2 = evaluate(
    predict_fn_v2,
    data="RAG Quality v1",
    evaluators=[...],
    experiment_prefix="rag_v2",
)

# LangSmith UI shows side-by-side comparison
# Programmatically:
import pandas as pd

df_v1 = pd.DataFrame(results_v1.to_pandas())
df_v2 = pd.DataFrame(results_v2.to_pandas())
print(df_v1.groupby("feedback.key")["feedback.score"].mean())
print(df_v2.groupby("feedback.key")["feedback.score"].mean())
```

---

## 6. Human Feedback and Annotation

### Collecting Feedback via SDK

```python
from langsmith import Client
import uuid

client = Client()

# Log feedback for a specific run
def log_user_feedback(run_id: str, was_helpful: bool, correction: str = None):
    """Log thumbs up/down and optional correction from users."""
    client.create_feedback(
        run_id=run_id,
        key="user_satisfaction",
        score=1.0 if was_helpful else 0.0,
        comment=correction,
        feedback_source_type="api",
    )

# In your FastAPI app:
from fastapi import FastAPI
app = FastAPI()

@app.post("/feedback")
async def collect_feedback(payload: dict):
    log_user_feedback(
        run_id=payload["run_id"],
        was_helpful=payload["helpful"],
        correction=payload.get("correction")
    )
    return {"status": "recorded"}
```

### Annotation Queues

Annotation queues let you route traces to human reviewers for labeling.

```python
# Create annotation queue
queue = client.create_annotation_queue(
    name="RAG Answer Review",
    description="Human review of RAG answers that scored below 0.7",
)

# Add runs to queue (e.g., those with low evaluation scores)
low_quality_runs = client.list_runs(
    project_name="my-rag-app-production",
    filter='lt(feedback_stats.answer_quality.avg, 0.7)',
    limit=50,
)

for run in low_quality_runs:
    client.add_runs_to_annotation_queue(
        queue_id=queue.id,
        run_ids=[str(run.id)]
    )
```

---

## 7. Prompt Hub

### Pushing Prompts to Hub

```python
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate

# Create prompt
rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant answering questions based on context.
Always cite sources. If context is insufficient, say so explicitly."""),
    ("human", "Context:\n{context}\n\nQuestion: {question}")
])

# Push to your LangSmith hub
hub.push("my-org/rag-qa-v2", rag_prompt, new_repo_is_public=False)
```

### Pulling Prompts from Hub

```python
from langchain import hub

# Pull specific version
prompt = hub.pull("my-org/rag-qa-v2:abc12345")

# Pull latest
prompt = hub.pull("my-org/rag-qa-v2")

# Use in chain
chain = prompt | llm | StrOutputParser()
```

### Versioning Workflow

```python
# Development: iterate on prompts
draft_prompt = hub.pull("my-org/rag-qa-v2")
# ... test and modify ...
hub.push("my-org/rag-qa-v2", updated_prompt)

# Production: pin to specific commit hash
PROD_PROMPT_COMMIT = "abc12345"
prod_prompt = hub.pull(f"my-org/rag-qa-v2:{PROD_PROMPT_COMMIT}")
```

---

## 8. LangSmith SDK

### Querying Runs Programmatically

```python
from langsmith import Client
from datetime import datetime, timedelta

client = Client()

# List recent runs with filters
runs = list(client.list_runs(
    project_name="my-rag-app-production",
    start_time=datetime.now() - timedelta(days=7),
    run_type="chain",
    error=False,  # Successful only
    filter='gt(total_tokens, 500)',
    limit=200,
))

# Analyze latency
latencies = [r.end_time - r.start_time for r in runs if r.end_time and r.start_time]
p50 = sorted(latencies)[len(latencies)//2].total_seconds()
p99 = sorted(latencies)[int(len(latencies)*0.99)].total_seconds()
print(f"P50: {p50:.2f}s, P99: {p99:.2f}s")

# Analyze errors
error_runs = list(client.list_runs(
    project_name="my-rag-app-production",
    error=True,
    start_time=datetime.now() - timedelta(hours=24),
))
print(f"Errors in last 24h: {len(error_runs)}")
for run in error_runs[:5]:
    print(f"  Error: {run.error[:100]}")
```

### Bulk Data Export

```python
import pandas as pd
import json

def export_runs_to_dataframe(project_name: str, days: int = 7) -> pd.DataFrame:
    """Export recent runs to a pandas DataFrame for analysis."""
    runs = list(client.list_runs(
        project_name=project_name,
        start_time=datetime.now() - timedelta(days=days),
        run_type="chain",
    ))
    
    records = []
    for run in runs:
        records.append({
            "run_id": str(run.id),
            "name": run.name,
            "start_time": run.start_time,
            "latency_s": (run.end_time - run.start_time).total_seconds() if run.end_time else None,
            "total_tokens": run.total_tokens,
            "prompt_tokens": run.prompt_tokens,
            "completion_tokens": run.completion_tokens,
            "input_question": run.inputs.get("question", ""),
            "output_answer": run.outputs.get("answer", "")[:200] if run.outputs else "",
            "error": run.error,
        })
    
    return pd.DataFrame(records)

df = export_runs_to_dataframe("my-rag-app-production")
print(df.describe())
```

---

## 9. Production Monitoring

### Key Metrics Dashboard

Track these metrics in LangSmith and set up alerts:

```python
from langsmith import Client
from datetime import datetime, timedelta
import statistics

class LangSmithMonitor:
    """Production monitoring using LangSmith SDK."""
    
    def __init__(self, project_name: str):
        self.client = Client()
        self.project = project_name
    
    def daily_report(self) -> dict:
        """Generate daily health report."""
        yesterday = datetime.now() - timedelta(days=1)
        
        all_runs = list(self.client.list_runs(
            project_name=self.project,
            start_time=yesterday,
            run_type="chain",
        ))
        
        successful = [r for r in all_runs if not r.error]
        failed = [r for r in all_runs if r.error]
        
        latencies = [
            (r.end_time - r.start_time).total_seconds()
            for r in successful
            if r.end_time and r.start_time
        ]
        
        tokens = [r.total_tokens for r in successful if r.total_tokens]
        
        return {
            "total_requests": len(all_runs),
            "success_rate": len(successful) / len(all_runs) if all_runs else 0,
            "error_rate": len(failed) / len(all_runs) if all_runs else 0,
            "latency_p50": statistics.median(latencies) if latencies else 0,
            "latency_p99": sorted(latencies)[int(len(latencies)*0.99)] if latencies else 0,
            "avg_tokens": statistics.mean(tokens) if tokens else 0,
            "estimated_cost_usd": sum(tokens) * 0.000002 if tokens else 0,  # Rough estimate
            "top_errors": [
                r.error[:100] for r in failed[:5] if r.error
            ]
        }
```

### Alerting Integration

```python
def check_and_alert(monitor: LangSmithMonitor, alert_thresholds: dict):
    """Check metrics and send alerts if thresholds exceeded."""
    report = monitor.daily_report()
    alerts = []
    
    if report["error_rate"] > alert_thresholds.get("max_error_rate", 0.05):
        alerts.append(f"ERROR RATE: {report['error_rate']:.1%} > threshold {alert_thresholds['max_error_rate']:.1%}")
    
    if report["latency_p99"] > alert_thresholds.get("max_p99_latency", 10.0):
        alerts.append(f"P99 LATENCY: {report['latency_p99']:.1f}s > {alert_thresholds['max_p99_latency']}s")
    
    if report["estimated_cost_usd"] > alert_thresholds.get("max_daily_cost", 100.0):
        alerts.append(f"DAILY COST: ${report['estimated_cost_usd']:.2f} > ${alert_thresholds['max_daily_cost']}")
    
    for alert in alerts:
        send_slack_alert(alert)  # Your alerting function
    
    return alerts
```

---

## 10. CI/CD Integration

```python
# tests/test_rag_quality.py
import pytest
from langsmith.evaluation import evaluate
from langchain_openai import ChatOpenAI
from langsmith.evaluation import LangChainStringEvaluator
import os

MINIMUM_SCORES = {
    "correctness": 0.75,
    "relevance": 0.80,
}

@pytest.mark.integration
def test_rag_quality_regression():
    """Fail CI if RAG quality drops below thresholds."""
    
    from my_app.rag import build_rag_chain
    rag_chain = build_rag_chain()
    
    def predict(inputs: dict) -> dict:
        result = rag_chain.invoke({"question": inputs["question"]})
        return {"answer": result}
    
    results = evaluate(
        predict,
        data="RAG Quality v1",
        evaluators=[
            LangChainStringEvaluator("correctness", config={"llm": ChatOpenAI(model="gpt-4o")}),
        ],
        experiment_prefix=f"ci_test_{os.environ.get('CI_COMMIT_SHA', 'local')[:8]}",
    )
    
    df = results.to_pandas()
    
    for metric, min_score in MINIMUM_SCORES.items():
        metric_col = f"feedback.{metric}"
        if metric_col in df.columns:
            avg_score = df[metric_col].mean()
            assert avg_score >= min_score, (
                f"REGRESSION: {metric} score {avg_score:.3f} < minimum {min_score}. "
                f"See results: {results.experiment_url}"
            )
```

```yaml
# .github/workflows/rag-quality.yml
name: RAG Quality Gates
on:
  pull_request:
    paths:
      - 'src/rag/**'
      - 'prompts/**'

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: pip install langsmith langchain-openai pytest
      - name: Run quality tests
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          LANGCHAIN_PROJECT: "ci-quality-checks"
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: pytest tests/test_rag_quality.py -v -m integration
```

---

## 11. Interview Questions

**Q1: What is the difference between tracing and evaluation in LangSmith?**

Tracing is passive observation — it records every LLM call, retrieval step, and chain execution with inputs, outputs, latency, and token counts. Evaluation is active measurement — it runs your chain against a curated dataset and scores outputs using automated evaluators (LLM-as-judge, heuristics, or custom functions). Tracing gives you debugging visibility; evaluation gives you quality metrics for comparison and regression detection.

**Q2: How would you build a regression testing pipeline for a production RAG system using LangSmith?**

Four steps: (1) Build a golden dataset by manually curating high-quality input/expected-output pairs, plus converting production runs with positive feedback into test cases; (2) Write evaluators — at minimum: correctness (LLM-as-judge vs ground truth), faithfulness (answer grounded in context), and latency check; (3) Integrate into CI — on every PR touching RAG code or prompts, run `evaluate()` against the dataset and fail the build if average scores drop below thresholds; (4) Weekly automated full evaluation and dashboard alert if scores trend down.

**Q3: What is LangSmith's Prompt Hub and why does prompt versioning matter?**

Prompt Hub is a version-controlled repository for prompts, similar to GitHub for code. It matters because: prompts are part of your application's behavior — changing a prompt is a code change that affects output quality; you need to reproduce past runs by knowing exactly which prompt was active; A/B testing different prompt variants requires tracking which was used for which session; rolling back a broken prompt requires knowing the previous version's commit hash.

**Q4: How would you use LangSmith to diagnose a sudden drop in RAG answer quality?**

Six steps: (1) Check error rate in runs — are there retrieval failures or LLM errors?; (2) Filter recent failing runs, examine traces step-by-step — is retrieval returning wrong docs?; (3) Compare current run scores vs baseline — run the evaluation dataset against current prod to get a score; (4) Check if corpus recently changed — new document ingestion may have diluted retrieval quality; (5) Sample 20 recent low-quality answers, add to annotation queue for human review; (6) If caused by prompt drift (someone changed the prompt), roll back via Prompt Hub to the last known-good commit.

---

*Next: Module 11 — Agent Engineering*
