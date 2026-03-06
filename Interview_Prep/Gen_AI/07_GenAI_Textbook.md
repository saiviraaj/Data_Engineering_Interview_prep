# Generative AI — Complete Textbook for Data Engineers
### From Zero to Interview-Confident

---

## CHAPTER 1: FOUNDATIONS — What Is Generative AI?

### 1.1 What Is AI, ML, and GenAI?

**Artificial Intelligence (AI):** The broad field of making machines simulate human intelligence — reasoning, learning, problem-solving.

**Machine Learning (ML):** A subset of AI where machines learn patterns from data without being explicitly programmed. You feed data, the model finds patterns, and it makes predictions.

**Deep Learning:** A subset of ML using neural networks with many layers. These networks automatically learn hierarchical representations of data.

**Generative AI (GenAI):** A class of AI models that can *generate new content* — text, images, code, audio, video — that resembles the training data. Unlike traditional ML which classifies or predicts, GenAI *creates*.

Examples:
- ChatGPT / Claude / Gemini → generate text
- DALL-E / Midjourney → generate images
- GitHub Copilot → generate code
- Suno → generate music

---

### 1.2 Why GenAI Matters for Data Engineers

As a Data Engineer, GenAI is relevant to you in three ways:

1. **Building GenAI-powered data products** — pipelines that use LLMs to process, enrich, or summarise data
2. **Using GenAI as a productivity tool** — generating SQL, writing DAGs, debugging code
3. **Architecting the data infrastructure that GenAI needs** — vector databases, embedding pipelines, RAG systems

In interviews, they want to know:
- Do you understand what GenAI is and how it works conceptually?
- Can you integrate GenAI into data pipelines?
- Can you build and deploy RAG systems?
- Do you understand the infrastructure behind it?

---

### 1.3 The Transformer Architecture — The Engine Behind LLMs

All modern LLMs (GPT, Gemini, Claude, LLaMA) are built on the **Transformer** architecture, introduced in the 2017 paper *"Attention Is All You Need"*.

#### Key Concepts:

**Tokens:**
- Text is broken into tokens before being processed
- A token is roughly 3–4 characters or 0.75 words
- "Hello world" = 2 tokens; "Supercalifragilistic" = ~5 tokens
- Models have a **context window** — max tokens they can process at once (e.g., GPT-4: 128K, Gemini 1.5 Pro: 1M, Claude 3.5: 200K)

**Embeddings:**
- Tokens are converted to numerical vectors called embeddings
- These vectors capture *semantic meaning*
- "King" and "Queen" have similar embeddings; "King" and "Pizza" do not
- Embeddings are the foundation of semantic search and RAG

**Attention Mechanism:**
- Allows the model to weigh which tokens are most relevant to each other
- "The bank by the river was steep" — the word "bank" attends to "river" to understand context
- **Self-attention** = every token looks at every other token in the sequence
- This is why transformers understand long-range dependencies better than older models

**Multi-Head Attention:**
- Multiple attention mechanisms running in parallel
- Each "head" learns to attend to different types of relationships
- One head might track grammatical structure; another might track semantic meaning

**Feed-Forward Layers:**
- After attention, each token goes through a feed-forward neural network
- This is where most of the "knowledge" is stored

**Positional Encoding:**
- Since transformers process all tokens at once (not sequentially), they need positional encoding to know word order
- Without it, "dog bites man" and "man bites dog" would look the same

#### The Training Process:
1. Collect massive text data from the internet, books, code
2. Train the model to predict the next token (autoregressive training)
3. The model learns language, facts, reasoning from this prediction task
4. Fine-tune on curated instruction-following examples (RLHF — Reinforcement Learning from Human Feedback)

---

### 1.4 How LLMs Generate Text

LLMs are **autoregressive** — they generate one token at a time, each token conditioned on all previous tokens.

Process:
1. You send a prompt: "The capital of France is"
2. Model calculates probability distribution over all possible next tokens
3. Selects "Paris" (highest probability)
4. Appends "Paris" to context, repeats
5. Continues until a stop token or max length

**Temperature:**
- Controls randomness of token selection
- Temperature = 0 → always picks highest probability token (deterministic, repetitive)
- Temperature = 1 → picks proportionally to probabilities (balanced)
- Temperature > 1 → more random/creative
- For data tasks: use low temperature (0–0.3) for reliability

**Top-P (Nucleus Sampling):**
- Only sample from tokens that make up the top P% of probability mass
- Top-P = 0.9 means only consider tokens comprising 90% of probability

---

## CHAPTER 2: LARGE LANGUAGE MODELS (LLMs)

### 2.1 Major LLMs You Should Know

| Model | Creator | Key Strength |
|-------|---------|-------------|
| GPT-4o | OpenAI | General purpose, multimodal |
| Claude 3.5 Sonnet | Anthropic | Long context, safety, coding |
| Gemini 1.5 Pro | Google | 1M context, multimodal, GCP native |
| LLaMA 3 | Meta | Open source, self-hostable |
| Mistral | Mistral AI | Lightweight, open source |
| Gemini 1.0 Ultra | Google | Highest capability Google model |

**For GCP interviews: Know Gemini well.** Google's Vertex AI hosts Gemini models and is the enterprise platform for building GenAI on GCP.

### 2.2 Types of LLMs by Deployment

**Proprietary / API-based:**
- Access via API (OpenAI API, Vertex AI, Anthropic API)
- No model weights exposed
- Pay per token
- Best quality but data leaves your environment

**Open Source:**
- LLaMA, Mistral, Falcon
- Weights downloadable, self-hostable
- Full data control — important for banking/regulated industries
- Requires GPU infrastructure

**Fine-tuned / Domain-specific:**
- Base model fine-tuned on domain data
- Examples: Med-PaLM (medical), CodeLlama (code), FinBERT (finance)

### 2.3 Context Window — Why It Matters for Data Engineering

The context window is the maximum amount of text the model can "see" at once.

Data engineering implications:
- Want to summarise a 500-page data dictionary? Needs large context window
- Want to do RAG over a large codebase? Need to chunk carefully to fit context
- Larger context = more expensive per call
- Gemini 1.5 Pro's 1M context window can fit ~700K words — entire codebases

---

## CHAPTER 3: PROMPT ENGINEERING

### 3.1 What Is Prompt Engineering?

Prompt engineering is the art of crafting inputs to LLMs to get reliable, accurate, high-quality outputs. It's a critical skill for using GenAI in production data systems.

### 3.2 Core Prompting Techniques

#### Zero-Shot Prompting
Give the task with no examples:
```
Classify the following SQL query as SELECT, INSERT, UPDATE, or DELETE:
"SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id"
```

#### Few-Shot Prompting
Give 2–5 examples before the actual task:
```
Classify these SQL queries:
"SELECT * FROM users" → SELECT
"DELETE FROM logs WHERE date < '2023-01-01'" → DELETE
"INSERT INTO events VALUES (1, 'login')" → INSERT

Now classify: "UPDATE customers SET status='inactive' WHERE last_login < '2024-01-01'"
```

Few-shot is more reliable than zero-shot for structured tasks.

#### Chain-of-Thought (CoT) Prompting
Ask the model to reason step by step:
```
Explain step by step how to optimise this BigQuery query, then provide the optimised version.
```
This dramatically improves accuracy for complex reasoning tasks.

#### System Prompts
Set the model's persona and constraints at the start:
```
System: You are a senior data engineering expert specialising in GCP and BigQuery. 
Give concise, accurate technical answers. Never hallucinate — if unsure, say so.
```

#### Role Prompting
```
Act as a BigQuery optimisation expert and review this query for performance issues.
```

#### Structured Output Prompting
Force structured responses for downstream processing:
```
Return your answer ONLY as valid JSON in this format:
{
  "table_name": "",
  "issues": [],
  "recommendations": []
}
Do not include any text outside the JSON.
```

### 3.3 Prompt Engineering Best Practices for Production

1. **Be explicit about format** — specify JSON, markdown, plain text
2. **Set constraints** — "maximum 3 bullet points", "in under 100 words"
3. **Provide context** — the more relevant context, the better the output
4. **Use delimiters** — separate instructions from data using `###`, `---`, XML tags
5. **Iterate and version your prompts** — treat prompts like code
6. **Test edge cases** — what happens with empty input, malformed data, adversarial input?
7. **Temperature control** — use 0 for deterministic tasks like data extraction

### 3.4 Text-to-SQL — Key Use Case for Data Engineers

Text-to-SQL is one of the most valuable GenAI applications for data engineering. It allows non-technical users to query data using natural language.

**How it works:**
1. User types: "Show me top 10 customers by revenue last month"
2. LLM + schema context → generates SQL
3. SQL executed on BigQuery
4. Results returned to user

**What you need to provide in the prompt:**
- Table schemas (DDL statements)
- Sample data (optional but helps)
- Business rules and column descriptions
- Dialect (BigQuery, PostgreSQL, etc.)

**Example prompt structure:**
```
You are a BigQuery SQL expert. Given the following schema, write a valid BigQuery SQL query.

Schema:
CREATE TABLE orders (
  order_id STRING,
  customer_id STRING,
  amount FLOAT64,
  order_date DATE,
  status STRING
);

Question: Show the top 10 customers by total order amount in the last 30 days, 
only including completed orders.

Return ONLY the SQL query with no explanation.
```

**Challenges:**
- Schema changes break prompts — need schema versioning
- LLMs can hallucinate column/table names
- Complex joins require careful schema descriptions
- Need a validation layer to test generated SQL before running

---

## CHAPTER 4: RETRIEVAL-AUGMENTED GENERATION (RAG)

### 4.1 The Problem RAG Solves

LLMs have two fundamental limitations:
1. **Knowledge cutoff** — trained on data up to a certain date, don't know recent events
2. **No access to private data** — they don't know your company's internal databases, documents, policies

**Without RAG:** "What was our Q3 revenue?" → LLM has no idea, will hallucinate

**With RAG:** Retrieve relevant documents from your database → inject into prompt → LLM answers based on retrieved context

RAG = giving the LLM a "reference book" at query time

### 4.2 RAG Architecture — Complete Flow

```
User Query
    ↓
[Query Embedding] ← convert query to vector using embedding model
    ↓
[Vector Database Search] ← find semantically similar documents
    ↓
[Retrieved Chunks] ← top K most relevant text chunks
    ↓
[Prompt Assembly] ← combine query + retrieved chunks + system prompt
    ↓
[LLM] ← generate answer grounded in retrieved context
    ↓
Response
```

### 4.3 Embeddings Deep Dive

An **embedding** is a numerical vector representation of text that captures semantic meaning.

- "I love data engineering" → [0.23, -0.41, 0.87, 0.12, ...] (768 or 1536 dimensions)
- Semantically similar texts have vectors close together in vector space
- Measured using **cosine similarity**: values from -1 (opposite) to 1 (identical)

**Embedding models:**
- `text-embedding-004` (Google / Vertex AI) — best for GCP stack
- `text-embedding-ada-002` (OpenAI)
- `sentence-transformers` (open source, self-hostable)
- `textembedding-gecko` (older Google model)

**The embedding pipeline for RAG:**
1. Take your documents (PDFs, SQL files, data dictionaries, wiki pages)
2. Split into chunks (e.g., 512 tokens each with 50-token overlap)
3. Generate embedding vector for each chunk
4. Store (chunk text + embedding vector + metadata) in a vector database
5. At query time: embed the query, find top-K nearest chunks

### 4.4 Vector Databases

A vector database is purpose-built to store and efficiently query high-dimensional embedding vectors.

**Key operation: Approximate Nearest Neighbor (ANN) search**
- Given a query vector, find the K most similar vectors
- Uses indexing algorithms like HNSW (Hierarchical Navigable Small World)

**Popular vector databases:**

| Database | Type | Notes |
|----------|------|-------|
| Pinecone | Managed cloud | Easiest to start with |
| Weaviate | Open source / managed | Good metadata filtering |
| Qdrant | Open source | High performance |
| ChromaDB | Open source | Best for local dev |
| pgvector | PostgreSQL extension | If already on Postgres |
| BigQuery | Native vector search | `VECTOR_SEARCH` function — key for GCP |
| Vertex AI Vector Search | GCP managed | Enterprise scale on GCP |
| AlloyDB | GCP managed Postgres | pgvector built in |

**For GCP interviews: Know BigQuery Vector Search and Vertex AI Vector Search.**

**BigQuery Vector Search (added 2023):**
```sql
-- Find top 5 most similar documents to a query embedding
SELECT base.doc_id, base.content, distance
FROM VECTOR_SEARCH(
  TABLE my_dataset.document_embeddings,
  'embedding_column',
  (SELECT ml_generate_embedding_result FROM ML.GENERATE_EMBEDDING(
    MODEL my_dataset.embedding_model,
    (SELECT 'What is our data retention policy?' AS content)
  )),
  top_k => 5
);
```

### 4.5 Chunking Strategies

How you split documents into chunks dramatically affects RAG quality.

**Fixed-size chunking:**
- Split every N characters/tokens
- Simple but may cut sentences mid-thought
- Overlap (e.g., 10%) helps maintain context across chunks

**Sentence-based chunking:**
- Split on sentence boundaries
- Better semantic coherence
- Variable chunk sizes

**Recursive character splitting:**
- Try to split on paragraphs first, then sentences, then words
- Used in LangChain's `RecursiveCharacterTextSplitter`

**Semantic chunking:**
- Use embeddings to detect topic shifts and split there
- Best quality but more expensive

**Chunk size considerations:**
- Too small → loses context, poor retrieval
- Too large → irrelevant content, hits context window limits, expensive
- Typical: 256–1024 tokens with 10–20% overlap

### 4.6 RAG Pipeline as a Data Engineering Problem

As a Data Engineer, building RAG is fundamentally a data pipeline problem:

**Ingestion pipeline (offline):**
```
Source documents (GCS, databases, APIs)
    ↓
Document extraction (PDFs → text, tables → markdown)
    ↓
Chunking (split into pieces)
    ↓
Embedding generation (call embedding model API)
    ↓
Store in vector DB (upsert embeddings + metadata)
    ↓
Index refresh (scheduled via Cloud Composer)
```

**Query pipeline (online/real-time):**
```
User query
    ↓
Query embedding
    ↓
Vector similarity search (top-K)
    ↓
Context assembly
    ↓
LLM inference
    ↓
Response
```

**Your CDM Next angle:** You built configuration-driven data pipelines. RAG ingestion is the same pattern — configurable, source-agnostic pipelines that process and store data for downstream consumption.

### 4.7 Advanced RAG Techniques

**Hybrid Search:**
Combine semantic search (vector) with keyword search (BM25/full-text):
- Vector search finds semantically similar content
- Keyword search finds exact term matches
- Combine scores for better retrieval
- Important when domain has specific jargon (e.g., "CDM", "DAG", "slot")

**Re-ranking:**
After retrieval, use a cross-encoder model to re-rank the top-K results:
- Bi-encoder (standard RAG): fast but less precise
- Cross-encoder: takes (query, document) pair and scores relevance more accurately
- Two-stage: retrieve 20 with bi-encoder, re-rank to get top 5 with cross-encoder

**Query Rewriting:**
Use LLM to expand or rewrite the query before embedding:
- "WF data migration tool" → "Wells Fargo cloud data movement platform CDM"
- Improves recall for ambiguous queries

**Metadata Filtering:**
Filter vector search results by metadata before semantic search:
- "Only search documents from Q4 2024"
- "Only search in the 'governance' category"
- Dramatically reduces noise and cost

**Multi-vector Retrieval:**
Store multiple embeddings per document (title + body + summary separately):
- Retrieve based on any representation
- Better coverage

---

## CHAPTER 5: GEN AI ON GCP — VERTEX AI

### 5.1 Vertex AI Overview

Vertex AI is Google's unified ML platform. For GenAI, it provides:

**Model Garden:**
- Access to Gemini models (Google's flagship LLMs)
- Open source models (LLaMA, Mistral, Falcon)
- Specialised models (Imagen for images, Chirp for audio)
- Access via API or deployment to endpoints

**Vertex AI Studio:**
- UI to test prompts without writing code
- Prompt management and versioning
- Evaluate model outputs

**Vertex AI Pipelines:**
- Orchestrate ML/GenAI workflows using Kubeflow Pipelines
- Similar concept to Airflow DAGs but for ML

**Vertex AI Agent Builder (formerly Gen AI App Builder):**
- Build RAG applications with minimal code
- Connects to BigQuery, GCS, websites as data sources
- Built-in vector search and grounding

**Vertex AI Vector Search:**
- Managed ANN vector search
- Scalable to billions of vectors
- Sub-100ms latency at scale

### 5.2 Gemini API on Vertex AI

```python
import vertexai
from vertexai.generative_models import GenerativeModel

# Initialize Vertex AI
vertexai.init(project="your-project", location="us-central1")

# Load Gemini model
model = GenerativeModel("gemini-1.5-pro")

# Simple generation
response = model.generate_content("Explain BigQuery partitioning in 3 bullet points")
print(response.text)

# With system instruction
model = GenerativeModel(
    "gemini-1.5-pro",
    system_instruction="You are a BigQuery expert. Be concise and technical."
)

response = model.generate_content(
    "What is the difference between partitioning and clustering?",
    generation_config={
        "temperature": 0.1,
        "max_output_tokens": 500
    }
)
```

### 5.3 Embeddings on Vertex AI

```python
from vertexai.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained("text-embedding-004")

# Generate single embedding
embeddings = model.get_embeddings(["What is data lineage?"])
vector = embeddings[0].values  # List of 768 floats

# Batch embedding
texts = ["document 1 content", "document 2 content", "document 3 content"]
embeddings = model.get_embeddings(texts)
vectors = [e.values for e in embeddings]
```

### 5.4 BigQuery ML for GenAI

BigQuery ML allows you to call LLMs directly from SQL:

```sql
-- Create a remote model pointing to Gemini
CREATE OR REPLACE MODEL my_dataset.gemini_model
REMOTE WITH CONNECTION `us.my-connection`
OPTIONS (endpoint = 'gemini-1.5-pro');

-- Generate text from SQL
SELECT
  order_id,
  customer_comment,
  ML.GENERATE_TEXT(
    MODEL my_dataset.gemini_model,
    STRUCT(
      CONCAT('Classify this customer comment as POSITIVE, NEGATIVE, or NEUTRAL: ', customer_comment) AS prompt,
      0.1 AS temperature,
      100 AS max_output_tokens
    )
  ).predictions[0].content AS sentiment
FROM my_dataset.customer_feedback
LIMIT 100;

-- Generate embeddings in BigQuery
SELECT
  doc_id,
  content,
  ML.GENERATE_EMBEDDING(
    MODEL my_dataset.embedding_model,
    STRUCT(content AS content)
  ).predictions[0].embeddings.values AS embedding
FROM my_dataset.documents;
```

This is powerful for data engineers — no Python needed, runs at BigQuery scale.

---

## CHAPTER 6: GEN AI IN DATA ENGINEERING — PRACTICAL USE CASES

### 6.1 Automated Data Documentation

**Problem:** Data dictionaries are always out of date. Nobody documents tables.

**GenAI Solution:**
1. Extract table schemas from BigQuery information schema
2. Sample a few rows of data
3. Feed to LLM: "Generate a description for this table and each column"
4. Store generated descriptions back in BigQuery or Dataplex catalog

```python
def generate_column_descriptions(schema: dict, sample_data: list) -> dict:
    prompt = f"""
    You are a data documentation expert. Given this BigQuery table schema and sample data,
    generate clear, concise descriptions for the table and each column.
    
    Schema: {json.dumps(schema)}
    Sample rows: {json.dumps(sample_data[:3])}
    
    Return ONLY valid JSON in this format:
    {{
        "table_description": "...",
        "columns": {{
            "column_name": "description",
            ...
        }}
    }}
    """
    response = model.generate_content(prompt, generation_config={"temperature": 0})
    return json.loads(response.text)
```

### 6.2 Intelligent Data Quality Monitoring

**Problem:** Writing data quality rules manually is time-consuming and incomplete.

**GenAI Solution:**
1. Analyse historical data patterns
2. Use LLM to suggest data quality rules
3. Auto-generate SQL checks based on business descriptions
4. LLM explains anomalies in plain English for non-technical stakeholders

### 6.3 Automated Pipeline Debugging

**Problem:** Airflow DAG failures require manual log analysis.

**GenAI Solution:**
1. Capture Cloud Logging output from failed tasks
2. Feed to LLM with DAG code context
3. LLM identifies root cause and suggests fix
4. Alert engineers with plain-English explanation + suggested code fix

### 6.4 Data Lineage Summarisation

**Problem:** Data lineage graphs are complex, hard to explain to stakeholders.

**GenAI Solution:**
1. Extract lineage from Dataplex or custom audit tables
2. Feed to LLM: "Explain this data lineage in plain English for a business analyst"
3. Generate stakeholder-friendly impact analysis for schema changes

### 6.5 Natural Language Data Exploration (Text-to-SQL product)

**Architecture for production Text-to-SQL:**

```
User Question (natural language)
    ↓
[Intent Classification] → Is this a data question or something else?
    ↓
[Schema Retrieval] → RAG over data dictionary to find relevant tables/columns
    ↓
[SQL Generation] → LLM generates BigQuery SQL with schema context
    ↓
[SQL Validation] → Parse and validate SQL syntax (sqlparse library)
    ↓
[Dry Run] → BigQuery dry run to check for errors, estimate bytes scanned
    ↓
[Execution] → Run on BigQuery
    ↓
[Result Formatting] → LLM summarises results in plain English
    ↓
User Response
```

---

## CHAPTER 7: LLM FRAMEWORKS — LANGCHAIN & LLAMAINDEX

### 7.1 LangChain

LangChain is the most popular framework for building LLM applications. Think of it as the "Airflow of GenAI" — it orchestrates LLM calls, data retrieval, and tool use.

**Core components:**
- **Models** — wrappers for LLM APIs (OpenAI, Vertex AI, etc.)
- **Prompts** — PromptTemplates for reusable, parameterised prompts
- **Chains** — sequences of LLM calls and operations
- **Retrievers** — components that fetch relevant documents
- **Memory** — maintain conversation history
- **Agents** — LLMs that decide which tools to call

**Basic RAG with LangChain:**
```python
from langchain_google_vertexai import VertexAI, VertexAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 1. Load and split documents
with open("data_dictionary.txt") as f:
    text = f.read()

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_text(text)

# 2. Create embeddings and vector store
embeddings = VertexAIEmbeddings(model_name="text-embedding-004")
vectorstore = Chroma.from_texts(chunks, embeddings)

# 3. Create RAG chain
llm = VertexAI(model_name="gemini-1.5-pro", temperature=0)
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
)

# 4. Query
result = qa_chain.invoke("What columns are in the customer orders table?")
print(result["result"])
```

### 7.2 LlamaIndex

LlamaIndex (formerly GPT Index) is specifically optimised for RAG over structured and semi-structured data — making it particularly useful for data engineers.

**Strengths over LangChain:**
- Better for structured data (SQL tables, CSV, JSON)
- More sophisticated indexing strategies
- Built-in query routing (route to SQL vs vector vs keyword)

**Key concept — Query Engines:**
```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.vertex import Vertex

# Load documents and build index
documents = SimpleDirectoryReader("./docs").load_data()
index = VectorStoreIndex.from_documents(documents)

# Query
query_engine = index.as_query_engine()
response = query_engine.query("What is the data retention policy for customer tables?")
```

---

## CHAPTER 8: EVALUATING AND PRODUCTIONISING GEN AI

### 8.1 LLM Evaluation

You cannot deploy an LLM-powered application without evaluation. Key metrics:

**Retrieval metrics (for RAG):**
- **Recall@K** — of all relevant documents, what fraction did we retrieve in top K?
- **Precision@K** — of retrieved documents, what fraction were actually relevant?
- **MRR (Mean Reciprocal Rank)** — how highly ranked was the first relevant document?

**Generation metrics:**
- **RAGAS (RAG Assessment)** — open source framework specifically for evaluating RAG
  - *Faithfulness* — is the answer supported by retrieved context?
  - *Answer Relevancy* — does the answer address the question?
  - *Context Precision* — is retrieved context relevant?
  - *Context Recall* — was all relevant context retrieved?

- **Human evaluation** — still the gold standard; create evaluation datasets with expected outputs

### 8.2 Hallucination and Mitigation

**What is hallucination?**
LLMs generate confident-sounding text that is factually wrong or unsupported.

**Why it happens:**
- Model "fills in" gaps in knowledge with plausible-sounding content
- No built-in mechanism to say "I don't know"
- Worse with obscure topics or very specific facts

**Mitigation strategies:**
1. **RAG grounding** — force model to answer only from retrieved context
2. **Citation requirements** — prompt: "Only answer based on the provided documents. Cite which document supports each claim."
3. **Confidence scoring** — ask model to rate its confidence; flag low-confidence answers
4. **Constrained generation** — use structured output to limit response scope
5. **Verification layer** — secondary LLM call to fact-check the first
6. **Temperature = 0** — reduces creativity, increases consistency

### 8.3 Production Architecture for GenAI Data Products

```
                    ┌─────────────────────────────────────┐
                    │         OFFLINE PIPELINE             │
                    │  (Cloud Composer / Airflow DAG)      │
                    │                                       │
                    │  GCS → Extract → Chunk → Embed →     │
                    │  Vector DB (Vertex AI Vector Search) │
                    └─────────────────────────────────────┘
                                      ↓ (refresh daily)
                    ┌─────────────────────────────────────┐
                    │         ONLINE SERVING               │
                    │  (Cloud Run / Cloud Functions)       │
                    │                                       │
                    │  Query → Embed → Retrieve → LLM →   │
                    │  Response                             │
                    └─────────────────────────────────────┘
                    ┌─────────────────────────────────────┐
                    │         OBSERVABILITY                │
                    │                                       │
                    │  Log prompts + responses to BigQuery │
                    │  Monitor latency, cost, token usage  │
                    │  Alert on error rate spikes          │
                    └─────────────────────────────────────┘
```

### 8.4 Cost Management for LLM Applications

LLM costs are primarily token-based. As a data engineer, you must manage this:

**Cost levers:**
- **Model selection** — Gemini Flash vs Pro vs Ultra have 10-100x cost differences. Use the cheapest model that meets quality bar.
- **Caching** — Cache identical or near-identical prompt responses (Vertex AI supports prompt caching)
- **Context compression** — Summarise or compress retrieved chunks before sending to LLM
- **Batching** — Use batch prediction APIs for offline workloads (60–80% cheaper than real-time)
- **Token budgets** — Set max_output_tokens deliberately; don't leave unlimited
- **Prompt optimisation** — Shorter prompts = lower cost; remove unnecessary instructions

**Monitoring cost:**
```python
# Track token usage per call
response = model.generate_content(prompt)
input_tokens = response.usage_metadata.prompt_token_count
output_tokens = response.usage_metadata.candidates_token_count
total_cost = (input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE) / 1000
```

Log to BigQuery → build cost dashboards → set budget alerts on GCP.

### 8.5 Security and Governance for GenAI in Banking

Critical for your role at a financial institution:

**Prompt Injection:**
- Malicious users craft inputs that override system instructions
- Defence: input sanitisation, output validation, privilege separation

**Data Privacy:**
- Never send PII to external LLM APIs (violates GDPR, banking regulations)
- Use Cloud DLP to detect and mask PII before sending to LLM
- Use on-premise or VPC-hosted models for sensitive data (Vertex AI private endpoints)
- Data residency — ensure data stays in approved regions

**Model Governance:**
- Version your prompts (treat like code in Git)
- Log all LLM inputs and outputs for audit
- Implement approval workflow for prompt changes in production
- Regular evaluation/regression testing when model versions change

**Output Validation:**
- Never trust LLM output blindly — validate before acting
- Especially critical for generated SQL — dry run before execution
- Use allowlists for SQL operations (SELECT only, no DDL)

---

## CHAPTER 9: AGENTIC AI

### 9.1 What Are AI Agents?

An AI agent is an LLM that can:
1. Take a goal (not just a single question)
2. Decide which tools to use
3. Execute tools, observe results
4. Iterate until goal is achieved

**ReAct Pattern (Reasoning + Acting):**
```
Thought: I need to find the top customers. I should query BigQuery.
Action: run_sql("SELECT customer_id, SUM(amount) FROM orders GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
Observation: Returns table with 10 rows
Thought: Now I have the data. I should format it for the user.
Action: format_response(data)
Final Answer: Here are the top 10 customers by revenue...
```

### 9.2 Data Engineering Agents

**Data debugging agent:**
- Tools: read_logs, read_dag_code, query_bigquery, search_documentation
- Goal: "The CDM pipeline failed at 3am, find root cause and suggest fix"

**Data exploration agent:**
- Tools: list_tables, get_schema, run_sql, generate_visualisation
- Goal: "Analyse customer churn patterns over the last 6 months"

**Self-healing pipeline:**
- Monitor pipeline health
- On failure: agent analyses logs, identifies issue type, attempts automated fix
- Falls back to human escalation if can't resolve

---

## CHAPTER 10: QUICK REFERENCE SUMMARY

### Key Terms Cheat Sheet

| Term | Definition |
|------|-----------|
| LLM | Large Language Model — transformer-based model trained on massive text |
| Token | Unit of text (~4 chars); LLMs process and generate tokens |
| Embedding | Numerical vector representing semantic meaning of text |
| RAG | Retrieval-Augmented Generation — ground LLM in retrieved documents |
| Vector DB | Database optimised for similarity search on embeddings |
| Prompt | Input to an LLM including instructions and context |
| Fine-tuning | Further training a pre-trained LLM on domain-specific data |
| Hallucination | LLM generating confident but factually wrong output |
| Context window | Maximum tokens LLM can process at once |
| Temperature | Randomness control for LLM output (0=deterministic) |
| Grounding | Connecting LLM responses to verifiable sources |
| Agent | LLM that uses tools iteratively to achieve a goal |
| Chain | Sequence of LLM calls and operations |
| Chunking | Splitting documents into smaller pieces for embedding/retrieval |
| ANN | Approximate Nearest Neighbor search — how vector DBs find similar vectors |
| CoT | Chain-of-Thought — prompting technique for step-by-step reasoning |

### GCP GenAI Services Quick Reference

| Service | Purpose |
|---------|---------|
| Vertex AI | Unified ML/GenAI platform |
| Model Garden | Access Gemini and open-source models |
| Vertex AI Studio | UI for prompt testing and management |
| Vertex AI Vector Search | Managed vector database |
| Vertex AI Agent Builder | Build RAG apps with UI |
| BigQuery ML | Run LLMs from SQL with ML.GENERATE_TEXT |
| Cloud Run | Host LLM application APIs |
| Dataflow | Process and embed documents at scale |
| Cloud Composer | Orchestrate embedding refresh pipelines |
| Cloud DLP | Detect/mask PII before sending to LLMs |

---

*End of Generative AI Textbook*
