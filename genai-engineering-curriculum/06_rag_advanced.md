# Module 06 — Advanced RAG Engineering

> **Prerequisite:** Module 05 (RAG Fundamentals). You know basic retrieval. Now we make it production-grade.

---

## Table of Contents

1. [Why Basic RAG Fails in Production](#1-why-basic-rag-fails-in-production)
2. [Hybrid Retrieval — BM25 + Dense](#2-hybrid-retrieval--bm25--dense)
3. [Query Rewriting and Expansion](#3-query-rewriting-and-expansion)
4. [HyDE — Hypothetical Document Embeddings](#4-hyde--hypothetical-document-embeddings)
5. [Parent-Child Chunking](#5-parent-child-chunking)
6. [Contextual Compression](#6-contextual-compression)
7. [Rerankers](#7-rerankers)
8. [Graph RAG](#8-graph-rag)
9. [Multi-Tenant RAG](#9-multi-tenant-rag)
10. [Semantic Caching](#10-semantic-caching)
11. [RAG Evaluation Deep-Dive](#11-rag-evaluation-deep-dive)
12. [Production RAG Architecture](#12-production-rag-architecture)
13. [Debugging RAG Systems](#13-debugging-rag-systems)
14. [Interview Questions](#14-interview-questions)

---

## 1. Why Basic RAG Fails in Production

Basic RAG (embed → store → retrieve top-k → generate) works in demos. It breaks in production for predictable reasons:

| Failure Mode | Root Cause | Fix |
|---|---|---|
| Retrieved docs are irrelevant | Query-doc lexical mismatch | Hybrid retrieval |
| Query is vague/ambiguous | Single query embedding misses intent | Query rewriting/expansion |
| Answer uses only part of context | Chunks too small, lack context | Parent-child chunks |
| Wrong docs retrieved for complex Q | Pure semantic search misses specifics | BM25 + reranker |
| Latency too high | Large top-k, no caching | Semantic cache + smaller k with reranker |
| Different tenants leak data | No namespace isolation | Multi-tenant design |
| Hallucination despite retrieval | LLM ignores retrieved context | Grounding + structured output |

Each of these is solved by a specific advanced pattern covered in this module.

---

## 2. Hybrid Retrieval — BM25 + Dense

### What It Is

Hybrid retrieval combines two complementary signals:
- **BM25** (sparse): keyword-based, exact match, works well for named entities, codes, IDs
- **Dense** (semantic): embedding-based, captures meaning, works for paraphrases

Neither alone is sufficient. A query for "HIPAA section 164.312" needs BM25. A query for "what rules govern PHI access" needs dense. Production RAG needs both.

### Architecture

```
Query
  ├── BM25 Retriever → sparse_scores[]
  └── Dense Retriever → dense_scores[]
        ↓
  Reciprocal Rank Fusion (RRF)
        ↓
  Merged & Ranked Results
        ↓
  (Optional) Reranker
        ↓
  Top-K Docs → LLM
```

### Reciprocal Rank Fusion (RRF)

RRF is the standard approach to merge results from multiple retrieval systems without requiring score normalization:

```
RRF_score(doc) = Σ  1 / (k + rank_i(doc))
```

Where `k=60` is a smoothing constant and `rank_i` is the rank of the document in retriever `i`.

### Implementation

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np
from rank_bm25 import BM25Okapi
import chromadb
from openai import OpenAI
import re

@dataclass
class Document:
    id: str
    content: str
    metadata: Dict = field(default_factory=dict)

@dataclass
class RetrievalResult:
    document: Document
    score: float
    retriever: str

class BM25Retriever:
    """Sparse keyword-based retriever using BM25Okapi."""
    
    def __init__(self, documents: List[Document]):
        self.documents = documents
        tokenized = [self._tokenize(doc.content) for doc in documents]
        self.bm25 = BM25Okapi(tokenized)
    
    def _tokenize(self, text: str) -> List[str]:
        # Basic tokenization — improve with NLTK in production
        return re.sub(r'[^a-z0-9\s]', '', text.lower()).split()
    
    def retrieve(self, query: str, top_k: int = 20) -> List[RetrievalResult]:
        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        return [
            RetrievalResult(
                document=self.documents[i],
                score=float(scores[i]),
                retriever="bm25"
            )
            for i in top_indices
            if scores[i] > 0
        ]

class DenseRetriever:
    """Semantic dense retriever using embeddings + ChromaDB."""
    
    def __init__(self, collection_name: str = "documents"):
        self.client_oai = OpenAI()
        self.chroma = chromadb.Client()
        self.collection = self.chroma.get_or_create_collection(collection_name)
    
    def embed(self, text: str) -> List[float]:
        resp = self.client_oai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return resp.data[0].embedding
    
    def add_documents(self, documents: List[Document]):
        for doc in documents:
            self.collection.add(
                ids=[doc.id],
                documents=[doc.content],
                embeddings=[self.embed(doc.content)],
                metadatas=[doc.metadata]
            )
    
    def retrieve(self, query: str, top_k: int = 20) -> List[RetrievalResult]:
        q_emb = self.embed(query)
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k
        )
        
        docs, distances, metadatas, ids = (
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0],
            results["ids"][0],
        )
        
        return [
            RetrievalResult(
                document=Document(id=ids[i], content=docs[i], metadata=metadatas[i]),
                score=1.0 - distances[i],  # cosine → similarity
                retriever="dense"
            )
            for i in range(len(docs))
        ]

class HybridRetriever:
    """Combines BM25 + Dense with Reciprocal Rank Fusion."""
    
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        dense_retriever: DenseRetriever,
        rrf_k: int = 60,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
    ):
        self.bm25 = bm25_retriever
        self.dense = dense_retriever
        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
    
    def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        # Retrieve from both — get more candidates than needed
        bm25_results = self.bm25.retrieve(query, top_k=top_k * 3)
        dense_results = self.dense.retrieve(query, top_k=top_k * 3)
        
        # RRF scoring
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}
        
        for rank, result in enumerate(bm25_results):
            doc_id = result.document.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + \
                self.bm25_weight * (1.0 / (self.rrf_k + rank + 1))
            doc_map[doc_id] = result.document
        
        for rank, result in enumerate(dense_results):
            doc_id = result.document.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + \
                self.dense_weight * (1.0 / (self.rrf_k + rank + 1))
            doc_map[doc_id] = result.document
        
        # Sort by RRF score
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [
            RetrievalResult(
                document=doc_map[doc_id],
                score=score,
                retriever="hybrid"
            )
            for doc_id, score in sorted_docs[:top_k]
        ]
```

### When to Use Hybrid vs Pure Dense

| Scenario | Use |
|---|---|
| Technical docs with product names, codes, IDs | Hybrid (BM25 essential) |
| General Q&A over narrative text | Dense often sufficient |
| Legal/compliance docs | Hybrid |
| Customer support over conversation history | Dense |
| Mixed document types | Hybrid always |

**Production default: always start with hybrid.** The overhead is small. The accuracy gain is significant.

---

## 3. Query Rewriting and Expansion

### The Problem

Users write queries the way humans speak, not the way documents are written:
- User: "how do I fix the memory issue"
- Document: "Resolving OutOfMemoryError in Java heap allocation"

The embedding of the user query may be far from the embedding of the relevant passage.

### Query Rewriting with LLM

```python
from openai import OpenAI
from typing import List

client = OpenAI()

QUERY_REWRITE_PROMPT = """You are an expert at reformulating search queries to improve document retrieval.

Given the original query, generate {n} alternative phrasings that:
1. Preserve the original intent
2. Use different terminology that might appear in documents
3. Are more specific or use domain vocabulary
4. Cover different angles of the question

Return ONLY a JSON array of strings. No explanation.

Original query: {query}"""

def rewrite_query(query: str, n: int = 3) -> List[str]:
    """Generate n alternative query phrasings."""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": QUERY_REWRITE_PROMPT.format(query=query, n=n)
        }],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    import json
    result = json.loads(resp.choices[0].message.content)
    # Handle both {"queries": [...]} and direct array
    if isinstance(result, list):
        return result
    return result.get("queries", result.get("alternatives", []))

def retrieve_with_query_expansion(
    query: str,
    retriever: HybridRetriever,
    top_k: int = 10,
    n_rewrites: int = 3
) -> List[RetrievalResult]:
    """Retrieve using original + rewritten queries, merge with RRF."""
    
    queries = [query] + rewrite_query(query, n=n_rewrites)
    
    all_results: Dict[str, List[Tuple[int, float]]] = {}  # doc_id → [(query_rank, score)]
    doc_map: Dict[str, Document] = {}
    
    for q_idx, q in enumerate(queries):
        results = retriever.retrieve(q, top_k=top_k * 2)
        for rank, result in enumerate(results):
            doc_id = result.document.id
            if doc_id not in all_results:
                all_results[doc_id] = []
            all_results[doc_id].append((rank, result.score))
            doc_map[doc_id] = result.document
    
    # Merge: average RRF score across queries that found this doc
    rrf_k = 60
    merged_scores: Dict[str, float] = {}
    for doc_id, appearances in all_results.items():
        merged_scores[doc_id] = sum(1.0 / (rrf_k + rank + 1) for rank, _ in appearances)
    
    sorted_docs = sorted(merged_scores.items(), key=lambda x: x[1], reverse=True)
    
    return [
        RetrievalResult(document=doc_map[doc_id], score=score, retriever="query_expansion")
        for doc_id, score in sorted_docs[:top_k]
    ]
```

### Step-Back Prompting

A related technique: ask LLM to generate a more abstract version of the query before retrieval.

```python
STEP_BACK_PROMPT = """You are helping improve a search query by stepping back to a higher-level question.

Original question: {query}

Generate a broader, more general question that would help find background knowledge to answer the original question.
Return only the broader question, nothing else."""

def step_back_query(query: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": STEP_BACK_PROMPT.format(query=query)}],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()
```

---

## 4. HyDE — Hypothetical Document Embeddings

### Concept

HyDE (Gao et al., 2022) addresses the query-document asymmetry problem:

- Queries are short, sparse, question-like
- Documents are long, dense, answer-like
- Their embeddings live in different regions of the embedding space

**HyDE's insight:** Ask the LLM to generate a *hypothetical* document that would answer the query. Then embed that hypothetical document and search with it instead.

```
Query: "How does Redis handle cache eviction?"
         ↓
LLM generates hypothetical answer document (~100-200 words)
         ↓
Embed the hypothetical document
         ↓
Search vector DB with hypothetical embedding
         ↓
Find REAL documents similar to the hypothetical
```

### Why It Works

The hypothetical document has:
- Similar length to real documents
- Similar vocabulary and phrasing
- Similar structure

Its embedding lands in the same region of the embedding space as real relevant documents.

### Implementation

```python
HYDE_PROMPT = """Write a short passage (100-150 words) that would directly answer the following question.
Write as if you are an authoritative source on this topic. Be specific and factual.
Do NOT say "This passage answers..." — just write the passage directly.

Question: {query}"""

def hyde_retrieve(
    query: str,
    retriever: HybridRetriever,
    top_k: int = 10,
    use_both: bool = True
) -> List[RetrievalResult]:
    """
    Retrieve using HyDE. If use_both=True, merge results from
    original query + hypothetical document.
    """
    # Generate hypothetical document
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": HYDE_PROMPT.format(query=query)}],
        temperature=0.7,
        max_tokens=200
    )
    hypothetical_doc = resp.choices[0].message.content.strip()
    
    if use_both:
        # Retrieve with both original query and hypothetical
        orig_results = retriever.retrieve(query, top_k=top_k * 2)
        hyde_results = retriever.dense.retrieve(hypothetical_doc, top_k=top_k * 2)
        
        # Merge with RRF
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}
        rrf_k = 60
        
        for rank, r in enumerate(orig_results):
            rrf_scores[r.document.id] = rrf_scores.get(r.document.id, 0) + \
                1.0 / (rrf_k + rank + 1)
            doc_map[r.document.id] = r.document
        
        for rank, r in enumerate(hyde_results):
            rrf_scores[r.document.id] = rrf_scores.get(r.document.id, 0) + \
                1.0 / (rrf_k + rank + 1)
            doc_map[r.document.id] = r.document
        
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            RetrievalResult(document=doc_map[did], score=s, retriever="hyde")
            for did, s in sorted_ids[:top_k]
        ]
    else:
        # Pure HyDE — search only with hypothetical
        return retriever.dense.retrieve(hypothetical_doc, top_k=top_k)
```

### Tradeoffs

| Aspect | HyDE | Standard |
|---|---|---|
| Query quality | Better for vague queries | Better for precise keyword queries |
| Latency | +1 LLM call | None |
| Cost | +LLM tokens | None |
| Hallucination risk | Can generate misleading hypothetical | None |
| Best for | Open-domain Q&A | Keyword search, known terminology |

**Production recommendation:** Use HyDE as part of a query ensemble (not as sole strategy). Test with/without on your dataset.

---

## 5. Parent-Child Chunking

### The Problem

Basic chunking creates a fundamental tension:

- **Small chunks** → precise retrieval, poor context for LLM
- **Large chunks** → context-rich for LLM, poor retrieval precision

Example: A 512-token financial report chunk is retrieved correctly, but it only contains half the relevant information. The LLM is stuck.

### Solution: Parent-Child (Small-to-Big) Retrieval

Store two representations of each document section:

- **Child chunks** (small, ~128 tokens): used for retrieval
- **Parent chunks** (large, ~512-1024 tokens): passed to LLM

The index is built on child chunks. When a child is retrieved, its parent is returned to the LLM.

```
Document
├── Parent Chunk 1 (512 tokens)
│   ├── Child 1.1 (128 tokens) ← indexed in vector DB
│   ├── Child 1.2 (128 tokens) ← indexed in vector DB
│   └── Child 1.3 (128 tokens) ← indexed in vector DB
└── Parent Chunk 2 (512 tokens)
    ├── Child 2.1 (128 tokens) ← indexed in vector DB
    └── Child 2.2 (128 tokens) ← indexed in vector DB
```

Query → finds Child 1.2 → returns Parent 1 to LLM.

### Implementation

```python
from typing import Optional
import uuid

@dataclass
class ChunkNode:
    id: str
    content: str
    parent_id: Optional[str]
    doc_id: str
    chunk_type: str  # "parent" or "child"
    metadata: Dict = field(default_factory=dict)

class ParentChildChunker:
    """Creates parent-child chunk hierarchy."""
    
    def __init__(
        self,
        parent_chunk_size: int = 512,
        child_chunk_size: int = 128,
        parent_overlap: int = 50,
        child_overlap: int = 20,
    ):
        self.parent_size = parent_chunk_size
        self.child_size = child_chunk_size
        self.parent_overlap = parent_overlap
        self.child_overlap = child_overlap
    
    def _split_tokens(self, text: str, size: int, overlap: int) -> List[str]:
        """Simple word-based splitting as proxy for token splitting."""
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + size, len(words))
            chunks.append(" ".join(words[start:end]))
            start += size - overlap
        return chunks
    
    def chunk(self, document: Document) -> Tuple[List[ChunkNode], List[ChunkNode]]:
        """Returns (parent_chunks, child_chunks)."""
        parents = []
        children = []
        
        parent_texts = self._split_tokens(
            document.content, self.parent_size, self.parent_overlap
        )
        
        for p_idx, p_text in enumerate(parent_texts):
            parent_id = f"{document.id}_p{p_idx}"
            parent_node = ChunkNode(
                id=parent_id,
                content=p_text,
                parent_id=None,
                doc_id=document.id,
                chunk_type="parent",
                metadata={**document.metadata, "chunk_index": p_idx}
            )
            parents.append(parent_node)
            
            # Create children for this parent
            child_texts = self._split_tokens(
                p_text, self.child_size, self.child_overlap
            )
            for c_idx, c_text in enumerate(child_texts):
                child_node = ChunkNode(
                    id=f"{parent_id}_c{c_idx}",
                    content=c_text,
                    parent_id=parent_id,
                    doc_id=document.id,
                    chunk_type="child",
                    metadata={**document.metadata, "parent_id": parent_id}
                )
                children.append(child_node)
        
        return parents, children

class ParentChildRAG:
    """RAG system using parent-child chunking strategy."""
    
    def __init__(self):
        self.chunker = ParentChildChunker()
        self.oai = OpenAI()
        self.chroma = chromadb.Client()
        # Separate collections for children (indexed) and parents (storage)
        self.child_collection = self.chroma.get_or_create_collection("children")
        self.parent_store: Dict[str, str] = {}  # parent_id → content
    
    def ingest(self, documents: List[Document]):
        for doc in documents:
            parents, children = self.chunker.chunk(doc)
            
            # Store parents in-memory (use Redis/DB in production)
            for p in parents:
                self.parent_store[p.id] = p.content
            
            # Index children in vector DB
            embeddings = self._embed_batch([c.content for c in children])
            self.child_collection.add(
                ids=[c.id for c in children],
                documents=[c.content for c in children],
                embeddings=embeddings,
                metadatas=[c.metadata for c in children]
            )
    
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        resp = self.oai.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [r.embedding for r in resp.data]
    
    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieve parent chunks via child-level search."""
        q_emb = self._embed_batch([query])[0]
        
        # Search children
        results = self.child_collection.query(
            query_embeddings=[q_emb],
            n_results=top_k * 3  # More children → better parent coverage
        )
        
        # Deduplicate: get unique parent IDs
        seen_parents = set()
        parent_contents = []
        
        for metadata in results["metadatas"][0]:
            parent_id = metadata.get("parent_id")
            if parent_id and parent_id not in seen_parents:
                seen_parents.add(parent_id)
                if parent_id in self.parent_store:
                    parent_contents.append(self.parent_store[parent_id])
                if len(parent_contents) >= top_k:
                    break
        
        return parent_contents
```

---

## 6. Contextual Compression

### What It Is

Contextual compression reduces retrieved chunks by extracting only the relevant portion before passing to the LLM. This combats the "noisy context" problem: a chunk is retrieved correctly but contains mostly irrelevant text.

```
Original chunk (500 tokens):
"The company was founded in 1985. Revenue grew by 15% in Q3.
The CEO stated that the new product line... [300 tokens of unrelated content]...
Operating margin expanded to 22% due to cost controls."

Query: "What was the operating margin?"

After compression (50 tokens):
"Operating margin expanded to 22% due to cost controls."
```

### Implementation

```python
COMPRESSION_PROMPT = """Given the following context and question, extract ONLY the portions of the context that are directly relevant to answering the question.

If no portion is relevant, respond with exactly: "NOT_RELEVANT"

Do not add explanations. Return only the extracted relevant text.

Question: {query}

Context:
{context}

Relevant extract:"""

class ContextualCompressor:
    """Compresses retrieved chunks to extract only query-relevant content."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model
    
    def compress(self, query: str, chunks: List[str]) -> List[str]:
        """Compress a list of chunks, discarding irrelevant ones."""
        compressed = []
        
        for chunk in chunks:
            # Skip very short chunks
            if len(chunk.split()) < 20:
                compressed.append(chunk)
                continue
            
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": COMPRESSION_PROMPT.format(query=query, context=chunk)
                }],
                temperature=0,
                max_tokens=500
            )
            result = resp.choices[0].message.content.strip()
            
            if result != "NOT_RELEVANT" and len(result) > 10:
                compressed.append(result)
        
        return compressed
    
    async def compress_async(self, query: str, chunks: List[str]) -> List[str]:
        """Async version for parallel compression."""
        import asyncio
        from openai import AsyncOpenAI
        
        async_client = AsyncOpenAI()
        
        async def compress_one(chunk: str) -> Optional[str]:
            resp = await async_client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": COMPRESSION_PROMPT.format(query=query, context=chunk)
                }],
                temperature=0,
                max_tokens=500
            )
            result = resp.choices[0].message.content.strip()
            return result if result != "NOT_RELEVANT" else None
        
        results = await asyncio.gather(*[compress_one(c) for c in chunks])
        return [r for r in results if r is not None]
```

### When to Use Contextual Compression

- Documents have heterogeneous content (tables, mixed topics)
- Chunks are large (>300 tokens)
- LLM context window is limited
- You notice LLM ignoring relevant info in noisy contexts

**Tradeoff:** Each chunk requires an LLM call → latency and cost increase. Use async compression in parallel.

---

## 7. Rerankers

### Why Retrieval Ranking Isn't Enough

Vector similarity is a proxy for relevance. It measures geometric distance between embeddings, not semantic suitability for answering a specific question. A cross-encoder reranker directly models the query-document relevance.

```
Stage 1 — Fast retrieval (ANN search)
Retrieves top-50 by approximate vector similarity
Cost: ~1ms, ~$0.00001

Stage 2 — Precise reranking (cross-encoder)
Scores each of the 50 docs against the query
Cost: ~100ms, moderate compute

Return top-5 to LLM
```

### Cross-Encoder vs Bi-Encoder

| | Bi-Encoder (Embeddings) | Cross-Encoder (Reranker) |
|---|---|---|
| Input | Encodes query and doc separately | Encodes query+doc together |
| Speed | Very fast (precomputed) | Slow (runs at query time) |
| Quality | Good | Better (sees interaction) |
| Scalable to | Millions of docs | ~100 docs per query |
| Use for | First-stage retrieval | Second-stage reranking |

### Implementation with Cohere Reranker

```python
import cohere

class CohereReranker:
    """Production-grade reranker using Cohere's cross-encoder."""
    
    def __init__(self, model: str = "rerank-english-v3.0"):
        self.client = cohere.Client()  # Uses COHERE_API_KEY env var
        self.model = model
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float, str]]:
        """
        Returns list of (original_index, relevance_score, document_text)
        sorted by relevance descending.
        """
        if not documents:
            return []
        
        response = self.client.rerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=top_k,
            return_documents=True,
        )
        
        return [
            (result.index, result.relevance_score, result.document.text)
            for result in response.results
        ]

class SentenceTransformerReranker:
    """Local reranker using sentence-transformers cross-encoder (no API cost)."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name)
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float, str]]:
        pairs = [(query, doc) for doc in documents]
        scores = self.model.predict(pairs)
        
        ranked = sorted(
            enumerate(zip(scores, documents)),
            key=lambda x: x[1][0],
            reverse=True
        )
        
        return [
            (orig_idx, float(score), doc)
            for orig_idx, (score, doc) in ranked[:top_k]
        ]

class RerankedRetriever:
    """Full pipeline: hybrid retrieval → reranking → context delivery."""
    
    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: SentenceTransformerReranker,
        initial_k: int = 20,
        final_k: int = 5
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.initial_k = initial_k
        self.final_k = final_k
    
    def retrieve_and_rerank(self, query: str) -> List[str]:
        # Stage 1: broad retrieval
        candidates = self.retriever.retrieve(query, top_k=self.initial_k)
        candidate_texts = [r.document.content for r in candidates]
        
        # Stage 2: precise reranking
        reranked = self.reranker.rerank(query, candidate_texts, top_k=self.final_k)
        
        return [doc for _, _, doc in reranked]
```

---

## 8. Graph RAG

### What Is Graph RAG?

Standard RAG treats documents as independent chunks. Graph RAG builds a knowledge graph from documents, enabling retrieval that follows relationships between entities.

```
Standard RAG:
Query → [Chunk A, Chunk B, Chunk C] → LLM

Graph RAG:
Query → Entity Extraction → Graph Traversal → [Entity A] → [Related B, C, D] → LLM
```

### When Graph RAG Is Valuable

- Documents have rich entity relationships (people, orgs, events, products)
- Queries require multi-hop reasoning ("what companies does the CEO of X have ties to?")
- Knowledge accumulates over time (news, research, legal docs)
- Standard RAG gives disconnected, incomplete answers

### Architecture

```
INGESTION PIPELINE
Documents
    ↓ LLM Entity Extraction
Entities + Relationships
    ↓ Graph Construction
Knowledge Graph (Neo4j / NetworkX)
    ↓ Community Detection
Community Summaries
    ↓ Embed Communities
Vector Index of Summaries

QUERY PIPELINE
Query
    ├── Entity Recognition → Graph Lookup → Subgraph Extraction
    └── Semantic Search → Community Summaries
          ↓
    Merged Context
          ↓
    LLM Generation
```

### Simplified Implementation

```python
import networkx as nx
from collections import defaultdict
import json

ENTITY_EXTRACTION_PROMPT = """Extract all named entities and their relationships from the following text.

Return JSON with this structure:
{
  "entities": [{"name": "...", "type": "PERSON|ORG|LOCATION|PRODUCT|CONCEPT", "description": "..."}],
  "relationships": [{"source": "...", "target": "...", "relation": "...", "description": "..."}]
}

Text:
{text}"""

class GraphRAG:
    """Simplified Graph RAG implementation."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entity_descriptions: Dict[str, str] = {}
        self.oai = OpenAI()
    
    def extract_graph(self, document: Document) -> Dict:
        """Extract entities and relationships using LLM."""
        resp = self.oai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": ENTITY_EXTRACTION_PROMPT.format(text=document.content[:3000])
            }],
            response_format={"type": "json_object"},
            temperature=0
        )
        return json.loads(resp.choices[0].message.content)
    
    def ingest(self, documents: List[Document]):
        for doc in documents:
            extracted = self.extract_graph(doc)
            
            # Add entities as nodes
            for entity in extracted.get("entities", []):
                name = entity["name"]
                self.graph.add_node(name, **entity)
                self.entity_descriptions[name] = entity.get("description", "")
            
            # Add relationships as edges
            for rel in extracted.get("relationships", []):
                self.graph.add_edge(
                    rel["source"],
                    rel["target"],
                    relation=rel["relation"],
                    description=rel.get("description", ""),
                    source_doc=doc.id
                )
    
    def query_subgraph(self, entity: str, depth: int = 2) -> str:
        """Get subgraph context around an entity."""
        if entity not in self.graph:
            return ""
        
        # BFS to depth
        nodes = {entity}
        frontier = {entity}
        
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                neighbors = set(self.graph.predecessors(node)) | \
                           set(self.graph.successors(node))
                next_frontier |= neighbors - nodes
            nodes |= next_frontier
            frontier = next_frontier
        
        # Build context string
        context_parts = []
        for node in nodes:
            desc = self.entity_descriptions.get(node, "")
            if desc:
                context_parts.append(f"- {node}: {desc}")
        
        for src, tgt, data in self.graph.edges(data=True):
            if src in nodes and tgt in nodes:
                context_parts.append(
                    f"- {src} {data.get('relation', 'relates to')} {tgt}: {data.get('description', '')}"
                )
        
        return "\n".join(context_parts)
    
    def retrieve(self, query: str) -> str:
        """Extract entities from query, traverse graph, return context."""
        # Extract query entities
        resp = self.oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Extract entity names from: {query}\nReturn JSON array of strings only."
            }],
            response_format={"type": "json_object"},
            temperature=0
        )
        import json
        try:
            entities = json.loads(resp.choices[0].message.content)
            if isinstance(entities, dict):
                entities = next(iter(entities.values()))
        except Exception:
            entities = []
        
        # Get subgraphs for each entity
        context_parts = []
        for entity in entities:
            subgraph_context = self.query_subgraph(entity)
            if subgraph_context:
                context_parts.append(f"## Knowledge about {entity}:\n{subgraph_context}")
        
        return "\n\n".join(context_parts)
```

**Production Graph RAG:** Use Microsoft's GraphRAG library or Neo4j for large-scale graph storage. Community detection (Leiden algorithm) generates hierarchical summaries that enable global+local retrieval.

---

## 9. Multi-Tenant RAG

### The Problem

Enterprise RAG systems serve multiple customers/departments on shared infrastructure. Isolation is critical:
- Customer A must never see Customer B's documents
- Access control must be enforced at retrieval time, not just at the application layer
- Shared infrastructure (embedding model, vector DB) must support efficient tenancy

### Isolation Strategies

#### Strategy 1: Namespace/Collection per Tenant

```python
class MultiTenantRAG:
    """RAG with strict per-tenant collection isolation."""
    
    def __init__(self):
        self.chroma = chromadb.Client()
        self.oai = OpenAI()
        self._collections: Dict[str, Any] = {}
    
    def _get_collection(self, tenant_id: str):
        """Lazy-create collection per tenant."""
        if tenant_id not in self._collections:
            # Each tenant gets its own collection — full isolation
            self._collections[tenant_id] = self.chroma.get_or_create_collection(
                name=f"tenant_{tenant_id}",
                metadata={"tenant_id": tenant_id}
            )
        return self._collections[tenant_id]
    
    def ingest(self, tenant_id: str, documents: List[Document]):
        collection = self._get_collection(tenant_id)
        
        embeddings = self._embed_batch([d.content for d in documents])
        collection.add(
            ids=[f"{tenant_id}_{d.id}" for d in documents],
            documents=[d.content for d in documents],
            embeddings=embeddings,
            metadatas=[{**d.metadata, "tenant_id": tenant_id} for d in documents]
        )
    
    def retrieve(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None
    ) -> List[str]:
        """Retrieve strictly within tenant's collection."""
        collection = self._get_collection(tenant_id)
        q_emb = self._embed_batch([query])[0]
        
        # Optional sub-tenant filtering (e.g., department, project)
        where = {}
        if metadata_filter:
            where.update(metadata_filter)
        
        results = collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where=where if where else None
        )
        return results["documents"][0]
    
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        resp = self.oai.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [r.embedding for r in resp.data]
```

#### Strategy 2: Metadata Filter on Shared Collection (High Scale)

For very large deployments with thousands of tenants, maintaining separate collections becomes operationally complex. Use a single collection with strict metadata filtering:

```python
class SharedCollectionMultiTenantRAG:
    """Single collection with metadata-based tenant isolation."""
    
    def __init__(self):
        self.chroma = chromadb.Client()
        self.collection = self.chroma.get_or_create_collection("shared_docs")
        self.oai = OpenAI()
    
    def ingest(self, tenant_id: str, documents: List[Document]):
        embeddings = self._embed_batch([d.content for d in documents])
        self.collection.add(
            ids=[f"{tenant_id}_{d.id}" for d in documents],
            documents=[d.content for d in documents],
            embeddings=embeddings,
            metadatas=[{**d.metadata, "tenant_id": tenant_id} for d in documents]
        )
    
    def retrieve(self, tenant_id: str, query: str, top_k: int = 5) -> List[str]:
        q_emb = self._embed_batch([query])[0]
        
        # CRITICAL: Always filter by tenant_id
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where={"tenant_id": {"$eq": tenant_id}}  # Strict isolation
        )
        return results["documents"][0]
    
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        resp = self.oai.embeddings.create(model="text-embedding-3-small", input=texts)
        return [r.embedding for r in resp.data]
```

### Multi-Tenant Security Checklist

- [ ] Tenant ID comes from authentication token, never from user input
- [ ] Every retrieval call includes tenant filter — verified in code review
- [ ] Tenant ID is immutable after ingestion
- [ ] Audit log records every retrieval with tenant ID
- [ ] Row-level security in relational metadata store
- [ ] Rate limiting per tenant

---

## 10. Semantic Caching

### What Is Semantic Caching?

Standard caching: cache exact query string → response.
Semantic caching: cache by *meaning* — a cached response for "what is the capital of France?" also serves "what's France's capital city?"

```
Query: "what is the capital of France?"
         ↓
Embed query → [0.12, -0.45, ...]
         ↓
Search cache by vector similarity
         ↓
Cache hit if similarity > 0.95: return "Paris"
Cache miss: run full RAG pipeline, store in cache
```

### Implementation

```python
import time
import hashlib

@dataclass
class CacheEntry:
    query: str
    response: str
    embedding: List[float]
    created_at: float
    ttl: float  # seconds
    hit_count: int = 0

class SemanticCache:
    """
    In-memory semantic cache for RAG responses.
    Production: replace with Redis + vector index.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.92,
        max_size: int = 1000,
        default_ttl: float = 3600.0
    ):
        self.threshold = similarity_threshold
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: List[CacheEntry] = []
        self.oai = OpenAI()
    
    def _embed(self, text: str) -> List[float]:
        resp = self.oai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return resp.data[0].embedding
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
    
    def _evict_expired(self):
        now = time.time()
        self.cache = [e for e in self.cache if now - e.created_at < e.ttl]
    
    def _evict_lru(self):
        """Evict least recently used entries if over max_size."""
        if len(self.cache) > self.max_size:
            # Sort by hit_count (ascending) as proxy for LRU
            self.cache.sort(key=lambda e: e.hit_count)
            self.cache = self.cache[len(self.cache) - self.max_size:]
    
    def get(self, query: str) -> Optional[str]:
        """Return cached response if similar query exists."""
        self._evict_expired()
        
        q_emb = self._embed(query)
        best_score = 0.0
        best_entry = None
        
        for entry in self.cache:
            score = self._cosine_similarity(q_emb, entry.embedding)
            if score > best_score:
                best_score = score
                best_entry = entry
        
        if best_score >= self.threshold and best_entry:
            best_entry.hit_count += 1
            return best_entry.response
        
        return None
    
    def set(self, query: str, response: str, ttl: Optional[float] = None):
        """Cache a query-response pair."""
        q_emb = self._embed(query)
        entry = CacheEntry(
            query=query,
            response=response,
            embedding=q_emb,
            created_at=time.time(),
            ttl=ttl or self.default_ttl
        )
        self.cache.append(entry)
        self._evict_lru()
    
    @property
    def stats(self) -> Dict:
        total = len(self.cache)
        total_hits = sum(e.hit_count for e in self.cache)
        return {"size": total, "total_hits": total_hits}
```

### Production Semantic Cache with Redis + Pinecone

```python
# Production pattern: Redis for fast lookup, Pinecone for semantic search
import redis
import pinecone

class ProductionSemanticCache:
    """Production semantic cache using Redis + Pinecone."""
    
    def __init__(
        self,
        redis_url: str,
        pinecone_index: str,
        similarity_threshold: float = 0.92,
        ttl: int = 3600
    ):
        self.redis = redis.from_url(redis_url)
        pinecone.init()  # Uses PINECONE_API_KEY env
        self.index = pinecone.Index(pinecone_index)
        self.threshold = similarity_threshold
        self.ttl = ttl
        self.oai = OpenAI()
    
    def _cache_key(self, vector_id: str) -> str:
        return f"semantic_cache:{vector_id}"
    
    def get(self, query: str) -> Optional[str]:
        q_emb = self.oai.embeddings.create(
            model="text-embedding-3-small", input=query
        ).data[0].embedding
        
        # Search Pinecone for similar cached queries
        results = self.index.query(vector=q_emb, top_k=1, include_metadata=True)
        
        if not results.matches:
            return None
        
        best = results.matches[0]
        if best.score < self.threshold:
            return None
        
        # Retrieve response from Redis
        cache_key = self._cache_key(best.id)
        cached = self.redis.get(cache_key)
        return cached.decode() if cached else None
    
    def set(self, query: str, response: str):
        q_emb = self.oai.embeddings.create(
            model="text-embedding-3-small", input=query
        ).data[0].embedding
        
        vector_id = hashlib.md5(query.encode()).hexdigest()
        
        # Store in Pinecone (vector index)
        self.index.upsert([(vector_id, q_emb, {"query": query[:500]})])
        
        # Store response in Redis with TTL
        self.redis.setex(self._cache_key(vector_id), self.ttl, response)
```

---

## 11. RAG Evaluation Deep-Dive

### The Evaluation Problem

RAG has three components to evaluate:
1. **Retrieval quality**: Are the right docs retrieved?
2. **Generation quality**: Is the answer faithful to retrieved docs?
3. **End-to-end quality**: Does the answer correctly address the user?

### RAGAS Metrics

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness,
)
from datasets import Dataset

def evaluate_rag_pipeline(
    questions: List[str],
    answers: List[str],
    contexts: List[List[str]],
    ground_truths: List[str],
) -> Dict:
    """Evaluate RAG using RAGAS framework."""
    
    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(data)
    
    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,        # Is answer grounded in context?
            answer_relevancy,    # Is answer relevant to question?
            context_precision,   # Are retrieved docs relevant?
            context_recall,      # Were all needed docs retrieved?
            answer_correctness,  # Is answer factually correct vs ground truth?
        ]
    )
    
    return result.to_pandas().to_dict()

# Custom evaluation without RAGAS
class RAGEvaluator:
    """Manual RAG evaluation using LLM-as-judge."""
    
    def __init__(self):
        self.client = OpenAI()
    
    def evaluate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """Score: is the answer grounded in the provided contexts?"""
        context_text = "\n---\n".join(contexts)
        
        resp = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"""Rate how faithfully this answer is grounded in the provided context.
Score 0-10 where 10 = completely grounded, 0 = complete hallucination.

Context:
{context_text}

Answer:
{answer}

Respond with JSON: {{"score": <0-10>, "reasoning": "<brief explanation>"}}"""
            }],
            response_format={"type": "json_object"},
            temperature=0
        )
        import json
        result = json.loads(resp.choices[0].message.content)
        return result["score"] / 10.0
    
    def evaluate_retrieval_quality(
        self,
        query: str,
        retrieved_docs: List[str],
        relevant_doc_ids: List[str],
        all_doc_ids: List[str]
    ) -> Dict[str, float]:
        """Compute precision@k, recall@k for retrieval."""
        retrieved_set = set(range(len(retrieved_docs)))
        relevant_set = set(relevant_doc_ids)
        
        # Precision@k: of retrieved, how many are relevant?
        hits = sum(1 for i, doc in enumerate(retrieved_docs) if str(i) in relevant_set)
        precision = hits / len(retrieved_docs) if retrieved_docs else 0
        
        # Recall@k: of all relevant, how many were retrieved?
        recall = hits / len(relevant_set) if relevant_set else 0
        
        # MRR: Mean Reciprocal Rank
        mrr = 0.0
        for rank, doc in enumerate(retrieved_docs, 1):
            if str(rank-1) in relevant_set:
                mrr = 1.0 / rank
                break
        
        return {"precision_at_k": precision, "recall_at_k": recall, "mrr": mrr}
```

---

## 12. Production RAG Architecture

### Full Production Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE                              │
│                                                                     │
│  Raw Docs → Loader → Preprocessor → Chunker → Embedder → VectorDB  │
│     ↑           ↓                                          ↓        │
│  S3/GCS    Doc Parser                                   Metadata    │
│            (PDF,DOCX,                                     Store     │
│             HTML,...)                                   (Postgres)  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     QUERY PIPELINE                                  │
│                                                                     │
│  User Query                                                         │
│      ↓                                                              │
│  [Auth / Tenant Resolution]                                         │
│      ↓                                                              │
│  [Semantic Cache] ──hit──→ Return Cached Response                   │
│      ↓ miss                                                         │
│  [Query Analysis] → classify: RAG / direct / web search            │
│      ↓                                                              │
│  [Query Rewriting] → 3 alternative queries                          │
│      ↓                                                              │
│  [Hybrid Retrieval] → BM25 + Dense, merged with RRF                │
│      ↓                                                              │
│  [Reranker] → cross-encoder, top-5                                  │
│      ↓                                                              │
│  [Contextual Compression] → extract relevant portions               │
│      ↓                                                              │
│  [Context Assembly] → format with citations                         │
│      ↓                                                              │
│  [LLM Generation] → with grounding instructions                     │
│      ↓                                                              │
│  [Response Validation] → hallucination check                        │
│      ↓                                                              │
│  [Cache Store] → write to semantic cache                            │
│      ↓                                                              │
│  Response with Citations                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Complete Production RAG System

```python
import asyncio
from dataclasses import dataclass
from typing import Optional

@dataclass
class RAGResponse:
    answer: str
    citations: List[Dict]
    retrieval_scores: List[float]
    cache_hit: bool
    latency_ms: float

class ProductionRAGPipeline:
    """Production-grade RAG pipeline with all advanced features."""
    
    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: SentenceTransformerReranker,
        cache: SemanticCache,
        compressor: Optional[ContextualCompressor] = None,
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.cache = cache
        self.compressor = compressor
        self.client = OpenAI()
    
    async def query(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        use_cache: bool = True,
        rewrite_query: bool = True,
    ) -> RAGResponse:
        import time
        start = time.time()
        
        # 1. Check semantic cache
        if use_cache:
            cached = self.cache.get(query)
            if cached:
                return RAGResponse(
                    answer=cached,
                    citations=[],
                    retrieval_scores=[],
                    cache_hit=True,
                    latency_ms=(time.time() - start) * 1000
                )
        
        # 2. Retrieve with optional query expansion
        if rewrite_query:
            docs = retrieve_with_query_expansion(query, self.retriever, top_k=top_k * 3)
            candidate_texts = [r.document.content for r in docs]
        else:
            results = self.retriever.retrieve(query, top_k=top_k * 3)
            candidate_texts = [r.document.content for r in results]
        
        # 3. Rerank
        reranked = self.reranker.rerank(query, candidate_texts, top_k=top_k)
        final_docs = [doc for _, _, doc in reranked]
        scores = [score for _, score, _ in reranked]
        
        # 4. Optional contextual compression
        if self.compressor:
            final_docs = await self.compressor.compress_async(query, final_docs)
        
        # 5. Assemble context with citation markers
        context_parts = []
        citations = []
        for i, doc in enumerate(final_docs):
            context_parts.append(f"[{i+1}] {doc}")
            citations.append({"id": i+1, "excerpt": doc[:200]})
        context = "\n\n".join(context_parts)
        
        # 6. Generate with grounding instructions
        answer = await self._generate(query, context)
        
        # 7. Cache the result
        if use_cache:
            self.cache.set(query, answer)
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            retrieval_scores=scores,
            cache_hit=False,
            latency_ms=(time.time() - start) * 1000
        )
    
    async def _generate(self, query: str, context: str) -> str:
        from openai import AsyncOpenAI
        async_client = AsyncOpenAI()
        
        resp = await async_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful assistant. Answer questions using ONLY the provided context.
If the context doesn't contain enough information, say so explicitly.
Always cite sources using [1], [2], etc. notation when referencing specific information."""
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {query}"
                }
            ],
            temperature=0.1
        )
        return resp.choices[0].message.content
```

---

## 13. Debugging RAG Systems

### Debugging Checklist

```
SYMPTOM: Answer is wrong / hallucinated
├── Check: Is the correct document in the index?
│     → grep/search index for expected content
├── Check: Is the correct document being retrieved?
│     → Log all retrieved chunks, check if correct one is in top-k
├── Check: Is the retrieved content reaching the LLM?
│     → Log the full prompt sent to LLM
└── Check: Is the LLM ignoring the context?
      → Strengthen system prompt grounding instructions
      → Try GPT-4o (stronger instruction following)

SYMPTOM: Relevant docs not retrieved
├── Check: Chunk size too small?
│     → Key information may be split across chunks
├── Check: Query-doc vocabulary mismatch?
│     → Add BM25 to hybrid retrieval
├── Check: Embedding model appropriate?
│     → Try domain-specific embedding model
└── Check: Top-k too small?
      → Increase initial retrieval k, use reranker

SYMPTOM: Too much irrelevant context
├── Check: Reranker filtering properly?
│     → Lower reranker top-k
├── Check: Similarity threshold?
│     → Add minimum score filter
└── Check: Add contextual compression
```

### RAG Debugging Toolkit

```python
class RAGDebugger:
    """Tools for debugging RAG pipeline issues."""
    
    def __init__(self, pipeline: ProductionRAGPipeline):
        self.pipeline = pipeline
    
    def trace_retrieval(self, query: str, top_k: int = 10) -> Dict:
        """Full retrieval trace with scores."""
        bm25_results = self.pipeline.retriever.bm25.retrieve(query, top_k)
        dense_results = self.pipeline.retriever.dense.retrieve(query, top_k)
        hybrid_results = self.pipeline.retriever.retrieve(query, top_k)
        
        candidate_texts = [r.document.content for r in hybrid_results]
        reranked = self.pipeline.reranker.rerank(query, candidate_texts, top_k)
        
        return {
            "query": query,
            "bm25_top3": [
                {"content": r.document.content[:100], "score": r.score}
                for r in bm25_results[:3]
            ],
            "dense_top3": [
                {"content": r.document.content[:100], "score": r.score}
                for r in dense_results[:3]
            ],
            "hybrid_top5": [
                {"content": r.document.content[:100], "score": r.score}
                for r in hybrid_results[:5]
            ],
            "reranked_top3": [
                {"content": doc[:100], "rerank_score": score}
                for _, score, doc in reranked[:3]
            ]
        }
    
    def check_document_in_index(self, text_fragment: str, collection) -> bool:
        """Check if a text fragment is present in any chunk."""
        # Search collection for the fragment
        results = collection.query(
            query_texts=[text_fragment],
            n_results=5
        )
        for doc in results["documents"][0]:
            if text_fragment.lower() in doc.lower():
                return True
        return False
```

---

## 14. Interview Questions

**Q1: What's wrong with basic top-k cosine similarity retrieval in production?**

Answer: Basic cosine retrieval fails because: (1) it's purely semantic — it misses exact keyword matches critical for names/codes/IDs; (2) single query embedding may miss user intent for ambiguous queries; (3) small chunks lose context when sent to LLM; (4) similarity score is a poor proxy for actual answer-relevance. Production systems need hybrid retrieval (BM25+dense), query expansion, parent-child chunking, and cross-encoder reranking.

**Q2: When would you use HyDE vs query rewriting vs both?**

Answer: HyDE works best for open-domain Q&A where the query is abstract ("explain quantum entanglement") — the hypothetical document bridges the lexical gap. Query rewriting works best for ambiguous or domain-specific queries where alternative phrasings help. Use both in an ensemble for complex production systems: rewrite + HyDE + original query, merge with RRF.

**Q3: How does a cross-encoder reranker differ from bi-encoder retrieval?**

Answer: Bi-encoder embeds query and document independently — fast, parallelizable, but loses query-document interaction. Cross-encoder processes query+document jointly (as a pair) — captures fine-grained interaction but requires running the model for every candidate. This is why you use bi-encoders for first-stage retrieval (millions of docs) and cross-encoders for second-stage reranking (top 20-50 candidates).

**Q4: Design multi-tenant RAG for a SaaS company serving 10,000 enterprise clients.**

Answer: At that scale, per-tenant collections are unmanageable. Use: (1) Shared collection with mandatory `tenant_id` metadata filter; (2) Tenant ID derived from auth token (never user input); (3) Pinecone/Weaviate for vector storage with namespace support; (4) Semantic cache with tenant-scoped keys; (5) Audit logging of all retrievals with tenant+user identity; (6) Rate limiting per tenant; (7) Separate vector index shards per tier (enterprise/standard) for performance isolation.

**Q5: How do you evaluate whether adding HyDE improved your RAG system?**

Answer: Run offline evaluation: (1) Build evaluation set with query + expected answer + relevant doc IDs; (2) Measure Recall@k (did we retrieve all relevant docs?) and MRR before/after; (3) Measure answer faithfulness and correctness using RAGAS/LLM-as-judge; (4) Compare latency and cost overhead (HyDE adds 1 LLM call per query); (5) A/B test in production with 10% traffic, measure user satisfaction or task completion rate.

---

*Next: Module 07 — Vector Databases Deep Dive*
