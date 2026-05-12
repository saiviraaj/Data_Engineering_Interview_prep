# Module 04 — Embeddings & Semantic Search

> **Phase:** 1 — Foundations  
> **Prerequisites:** Modules 01–03  
> **Leads to:** RAG Engineering (Modules 05–07)  
> **Estimated time:** 2–3 days

---

## 1. THE BIG PICTURE

Embeddings are the foundation of how LLMs "understand" semantic meaning in text, and they're the core primitive powering every RAG system, semantic search engine, and recommendation system in modern AI.

**The core idea:** Convert any piece of text (word, sentence, paragraph, document) into a vector of floating-point numbers that captures its semantic meaning. Text with similar meanings gets similar vectors — measurable by mathematical distance.

Without embeddings, you're limited to keyword search (find documents containing the word "pipeline"). With embeddings, you can find documents that discuss the concept even if they don't use the same words ("data flow", "ETL process", "ingestion workflow" all cluster together semantically).

**This module is the prerequisite for everything RAG.**

---

## 2. CORE CONCEPTS

### 2.1 What Are Embeddings?

An embedding is a dense vector representation of text. The model learned during training that texts with similar meanings should be close together in this high-dimensional space.

```
"What is machine learning?" 
    → [0.023, -0.156, 0.891, -0.034, ..., 0.223]  # 1536 dimensions for text-embedding-3-small
    
"Explain ML concepts"
    → [0.019, -0.148, 0.887, -0.041, ..., 0.231]  # Very similar vector!
    
"How do I make pasta?"
    → [-0.432, 0.821, -0.234, 0.567, ..., -0.189]  # Very different vector
```

**Key properties:**
- Fixed dimensionality (e.g., 1536d, 3072d, 768d)
- Semantic similarity = geometric closeness
- Language agnostic (sentence in Hindi and English about same topic → similar vectors)
- Order-sensitive (sentence embeddings capture word order context)

### 2.2 The Vector Space Mental Model

```
                    High-dimensional embedding space
                    
    ◆ "Apache Kafka streaming"
         ◆ "real-time data processing"
              ◆ "event streaming platform"    ← Cluster: streaming tech
         
    
    ◆ "BigQuery SQL optimization"
         ◆ "database query performance"
              ◆ "index optimization"          ← Cluster: databases
    
    
    ◆ "deep learning neural networks"
         ◆ "backpropagation gradient descent"
              ◆ "model training"              ← Cluster: ML
```

When you query "kafka performance", your query vector lands close to the streaming cluster and far from the ML cluster — that's semantic search.

### 2.3 Similarity Metrics

**Cosine Similarity** (most common for text)
- Measures angle between vectors
- Range: -1 to 1 (1 = identical direction, 0 = orthogonal, -1 = opposite)
- Invariant to vector magnitude — good for text embeddings
- Use when: comparing text semantics

```python
import numpy as np

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# For normalized vectors (unit vectors), this simplifies to:
def cosine_sim_normalized(v1: np.ndarray, v2: np.ndarray) -> float:
    return np.dot(v1, v2)  # Just the dot product when vectors are normalized
```

**Dot Product Similarity**
- Not normalized — magnitude matters
- Used when you want to scale by "importance" or length
- Some embedding models optimize for dot product (OpenAI's newer models)

**Euclidean Distance (L2)**
- Geometric distance in the space
- Use when: you want absolute distance, not just direction
- Less common for text but used in some clustering algorithms

**When to use which:**
- Default choice: Cosine similarity
- OpenAI text-embedding-3-*: Works well with cosine or dot product (vectors are normalized)
- Specialized domain embeddings: Check the model card

### 2.4 Embedding Models Compared

| Model | Dimensions | Context | Strength | Use Case |
|-------|-----------|---------|----------|----------|
| text-embedding-3-small | 1536 | 8191 tokens | Balance cost/quality | General RAG, semantic search |
| text-embedding-3-large | 3072 | 8191 tokens | Best quality | High-accuracy applications |
| text-embedding-ada-002 | 1536 | 8191 tokens | Legacy | Avoid for new systems |
| cohere-embed-v3 | 1024 | 512 tokens | Multilingual | Multi-language RAG |
| bge-large-en-v1.5 | 1024 | 512 tokens | Open source | Self-hosted systems |
| e5-large-v2 | 1024 | 512 tokens | Open source | Self-hosted, good at tasks |
| jina-embeddings-v2 | 768 | 8192 tokens | Long doc | Long document processing |
| nomic-embed-text | 768 | 8192 tokens | Open source | Local/private deployment |

**Practical guidance:**
- OpenAI text-embedding-3-small is the default for most production systems (cost/quality)
- Use text-embedding-3-large when accuracy is critical and cost allows
- Use an open-source model (bge, e5) when data can't leave your infrastructure
- Consider cohere for multilingual applications

---

## 3. IMPLEMENTATION

### 3.1 Getting Embeddings from the API

```python
# embeddings_client.py
from openai import AsyncOpenAI
from typing import List, Optional, Union
import asyncio
import numpy as np

client = AsyncOpenAI()

async def embed_text(
    text: Union[str, List[str]],
    model: str = "text-embedding-3-small",
    dimensions: Optional[int] = None,  # Can reduce dimensions (Matryoshka)
) -> Union[List[float], List[List[float]]]:
    """
    Get embeddings for text(s).
    
    text: single string or list of strings
    model: embedding model to use
    dimensions: optional dimension reduction (for text-embedding-3-*)
    
    Returns: single embedding or list of embeddings
    """
    single = isinstance(text, str)
    texts = [text] if single else text
    
    # Clean text (embeddings are sensitive to formatting)
    texts = [t.replace("\n", " ").strip() for t in texts]
    
    kwargs = {"model": model, "input": texts}
    if dimensions:
        kwargs["dimensions"] = dimensions
    
    response = await client.embeddings.create(**kwargs)
    
    # Sort by index in case API returns out of order
    sorted_data = sorted(response.data, key=lambda x: x.index)
    embeddings = [item.embedding for item in sorted_data]
    
    return embeddings[0] if single else embeddings


async def batch_embed(
    texts: List[str],
    model: str = "text-embedding-3-small",
    batch_size: int = 100,  # OpenAI allows up to 2048 inputs per request
) -> List[List[float]]:
    """
    Embed a large list of texts in batches.
    Essential for ingestion pipelines with thousands of documents.
    """
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = await embed_text(batch, model=model)
        all_embeddings.extend(batch_embeddings)
        
        # Rate limiting pause between batches
        if i + batch_size < len(texts):
            await asyncio.sleep(0.1)
    
    return all_embeddings


async def batch_embed_parallel(
    texts: List[str],
    model: str = "text-embedding-3-small",
    batch_size: int = 100,
    max_concurrent: int = 5,
) -> List[List[float]]:
    """
    Parallel batch embedding for maximum throughput.
    Use when you have 1000+ texts to embed.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def embed_batch(batch: List[str]) -> List[List[float]]:
        async with semaphore:
            return await embed_text(batch, model=model)
    
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
    
    tasks = [embed_batch(batch) for batch in batches]
    batch_results = await asyncio.gather(*tasks)
    
    # Flatten results
    return [emb for batch in batch_results for emb in batch]
```

### 3.2 Basic Semantic Search

```python
# semantic_search.py
import numpy as np
from typing import List, Dict, Tuple
import json

class InMemorySemanticSearch:
    """
    Simple in-memory semantic search using embeddings.
    Good for small corpora (<10K documents) or prototyping.
    For production with large corpora: use a vector database.
    """
    
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.documents: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
    
    async def add_documents(
        self,
        documents: List[Dict],
        text_key: str = "content",
    ) -> None:
        """
        Index documents for search.
        documents: list of dicts, each with at least text_key
        """
        texts = [doc[text_key] for doc in documents]
        
        print(f"Embedding {len(texts)} documents...")
        embeddings = await batch_embed_parallel(texts, model=self.model)
        
        # Convert to numpy array for efficient operations
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Normalize for cosine similarity via dot product
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        normalized = embeddings_array / norms
        
        if self.embeddings is None:
            self.embeddings = normalized
        else:
            self.embeddings = np.vstack([self.embeddings, normalized])
        
        self.documents.extend(documents)
        print(f"Indexed {len(documents)} documents. Total: {len(self.documents)}")
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,  # Minimum similarity score
    ) -> List[Dict]:
        """
        Search for documents most similar to query.
        Returns ranked list of documents with similarity scores.
        """
        if not self.documents:
            return []
        
        # Embed the query
        query_embedding = await embed_text(query, model=self.model)
        query_vector = np.array(query_embedding, dtype=np.float32)
        
        # Normalize query vector
        query_vector = query_vector / np.linalg.norm(query_vector)
        
        # Compute similarities via dot product (works because normalized)
        similarities = self.embeddings @ query_vector
        
        # Get top-k indices
        top_k_indices = np.argsort(-similarities)[:top_k]
        
        results = []
        for idx in top_k_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append({
                    **self.documents[idx],
                    "similarity_score": score,
                    "rank": len(results) + 1,
                })
        
        return results
    
    def save(self, path: str) -> None:
        """Persist index to disk."""
        import pickle
        with open(path, "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "embeddings": self.embeddings,
                "model": self.model,
            }, f)
    
    @classmethod
    def load(cls, path: str) -> "InMemorySemanticSearch":
        import pickle
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        instance = cls(model=data["model"])
        instance.documents = data["documents"]
        instance.embeddings = data["embeddings"]
        return instance
```

### 3.3 Embedding with FAISS

For medium-scale search (10K-1M documents), FAISS is highly efficient:

```python
# faiss_search.py
import faiss
import numpy as np
from typing import List, Dict

class FAISSSearch:
    """
    High-performance semantic search using Facebook's FAISS library.
    Handles millions of vectors efficiently.
    """
    
    def __init__(
        self,
        dimension: int = 1536,  # text-embedding-3-small dimension
        index_type: str = "IVF",  # IVF for large scale, Flat for exact
    ):
        self.dimension = dimension
        self.documents: List[Dict] = []
        
        if index_type == "Flat":
            # Exact search — slower but perfect recall
            self.index = faiss.IndexFlatIP(dimension)  # IP = Inner Product (dot product)
        elif index_type == "IVF":
            # Approximate search — much faster for large datasets
            # nlist = number of clusters (sqrt of dataset size is a good starting point)
            nlist = 100
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_INNER_PRODUCT)
        elif index_type == "HNSW":
            # Hierarchical NSW — fast and accurate, good for most cases
            self.index = faiss.IndexHNSWFlat(dimension, 32)  # 32 = neighbors per node
    
    def add_documents(
        self,
        documents: List[Dict],
        embeddings: List[List[float]],
    ) -> None:
        """Add pre-computed embeddings to the index."""
        
        embedding_array = np.array(embeddings, dtype=np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embedding_array)
        
        # Train IVF index if needed
        if hasattr(self.index, 'is_trained') and not self.index.is_trained:
            print("Training FAISS index...")
            self.index.train(embedding_array)
        
        self.index.add(embedding_array)
        self.documents.extend(documents)
        
        print(f"FAISS index: {self.index.ntotal} vectors")
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Dict]:
        """Search for nearest neighbors."""
        
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)
        
        # Search
        distances, indices = self.index.search(query_array, top_k)
        
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= 0:  # -1 means no result
                results.append({
                    **self.documents[idx],
                    "similarity_score": float(dist),
                    "rank": i + 1,
                })
        
        return results
    
    def save(self, index_path: str, docs_path: str) -> None:
        faiss.write_index(self.index, index_path)
        import json
        with open(docs_path, "w") as f:
            json.dump(self.documents, f)
    
    @classmethod
    def load(cls, index_path: str, docs_path: str) -> "FAISSSearch":
        import json
        instance = cls.__new__(cls)
        instance.index = faiss.read_index(index_path)
        instance.dimension = instance.index.d
        with open(docs_path) as f:
            instance.documents = json.load(f)
        return instance
```

### 3.4 Embedding Caching

Embeddings are expensive to compute. Cache aggressively:

```python
# embedding_cache.py
import hashlib
import json
import asyncio
from typing import Optional, List

class EmbeddingCache:
    """
    Cache embeddings to avoid recomputing.
    Two levels: memory (L1) and Redis (L2).
    """
    
    def __init__(self, redis_client=None, model: str = "text-embedding-3-small"):
        self.model = model
        self.redis = redis_client
        self._memory_cache = {}  # L1 cache
        self.ttl = 86400 * 7  # 7 days in Redis
    
    def _cache_key(self, text: str) -> str:
        text_hash = hashlib.sha256(f"{self.model}:{text}".encode()).hexdigest()
        return f"emb:{text_hash}"
    
    async def get(self, text: str) -> Optional[List[float]]:
        key = self._cache_key(text)
        
        # L1: Memory cache
        if key in self._memory_cache:
            return self._memory_cache[key]
        
        # L2: Redis cache
        if self.redis:
            cached = await self.redis.get(key)
            if cached:
                embedding = json.loads(cached)
                self._memory_cache[key] = embedding  # Promote to L1
                return embedding
        
        return None
    
    async def set(self, text: str, embedding: List[float]) -> None:
        key = self._cache_key(text)
        self._memory_cache[key] = embedding
        
        if self.redis:
            await self.redis.setex(key, self.ttl, json.dumps(embedding))
    
    async def get_or_compute(
        self,
        text: str,
        compute_fn,  # Async function that computes the embedding
    ) -> List[float]:
        """Get from cache or compute and cache."""
        cached = await self.get(text)
        if cached:
            return cached
        
        embedding = await compute_fn(text)
        await self.set(text, embedding)
        return embedding


class CachedEmbedder:
    """Embedder with automatic caching."""
    
    def __init__(self, openai_client, model: str = "text-embedding-3-small", cache=None):
        self.client = openai_client
        self.model = model
        self.cache = cache or EmbeddingCache(model=model)
    
    async def embed(self, text: str) -> List[float]:
        return await self.cache.get_or_compute(
            text,
            compute_fn=lambda t: embed_text(t, model=self.model)
        )
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embed with cache checking."""
        
        # Check cache for each text
        results = [None] * len(texts)
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cached = await self.cache.get(text)
            if cached:
                results[i] = cached
            else:
                uncached_indices.append(i)
        
        if uncached_indices:
            # Compute uncached in batch
            uncached_texts = [texts[i] for i in uncached_indices]
            new_embeddings = await batch_embed(uncached_texts, model=self.model)
            
            # Store results and update cache
            for idx, embedding in zip(uncached_indices, new_embeddings):
                results[idx] = embedding
                await self.cache.set(texts[idx], embedding)
        
        return results
```

### 3.5 Cross-Encoder Reranking

Bi-encoders (standard embeddings) are fast but approximate. Cross-encoders provide higher accuracy for final reranking:

```python
# reranking.py
"""
Two-stage retrieval:
Stage 1: Bi-encoder (fast) — retrieve top 100 candidates
Stage 2: Cross-encoder (slow but accurate) — rerank to top 10

This pattern is used in all production RAG systems.
"""

from sentence_transformers import CrossEncoder
from typing import List, Tuple

class CrossEncoderReranker:
    """
    Rerank retrieved documents using a cross-encoder model.
    Cross-encoders process (query, document) pairs together,
    enabling much more accurate relevance scoring.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)
    
    def rerank(
        self,
        query: str,
        documents: List[Dict],
        text_key: str = "content",
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Rerank documents using cross-encoder scores.
        Much more accurate than bi-encoder similarity alone.
        """
        
        # Create (query, document) pairs for the cross-encoder
        pairs = [(query, doc[text_key]) for doc in documents]
        
        # Get cross-encoder scores
        scores = self.model.predict(pairs)
        
        # Combine scores with documents
        scored_docs = [
            {**doc, "rerank_score": float(score), "original_rank": i + 1}
            for i, (doc, score) in enumerate(zip(documents, scores))
        ]
        
        # Sort by cross-encoder score
        reranked = sorted(scored_docs, key=lambda x: x["rerank_score"], reverse=True)
        
        # Add final rank
        for i, doc in enumerate(reranked):
            doc["final_rank"] = i + 1
        
        return reranked[:top_k]


# Usage in RAG pipeline:
async def rag_with_reranking(
    query: str,
    search_index: InMemorySemanticSearch,
    reranker: CrossEncoderReranker,
    initial_top_k: int = 20,
    final_top_k: int = 5,
) -> List[Dict]:
    
    # Stage 1: Fast bi-encoder retrieval (get many candidates)
    candidates = await search_index.search(query, top_k=initial_top_k)
    
    # Stage 2: Accurate cross-encoder reranking (narrow to best ones)
    reranked = reranker.rerank(query, candidates, top_k=final_top_k)
    
    return reranked
```

### 3.6 Embedding-Based Classification

```python
# embedding_classification.py
"""
Lightweight classification using embeddings.
Much cheaper than calling GPT-4o for simple classification tasks.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import pickle

class EmbeddingClassifier:
    """
    Train a classifier on top of embeddings.
    
    Advantages over LLM classification:
    - 100x cheaper (embed once, classify instantly)
    - Deterministic
    - Fast (microseconds vs seconds)
    
    Disadvantages:
    - Needs labeled training data
    - Less flexible (fixed categories)
    - Lower accuracy for edge cases
    """
    
    def __init__(self, embedder: CachedEmbedder):
        self.embedder = embedder
        self.classifier = LogisticRegression(max_iter=1000)
        self.label_map = {}
        self.trained = False
    
    async def fit(
        self,
        texts: List[str],
        labels: List[str],
    ) -> dict:
        """Train the classifier on labeled examples."""
        
        print(f"Embedding {len(texts)} training examples...")
        embeddings = await self.embedder.embed_batch(texts)
        X = np.array(embeddings)
        
        # Encode labels
        unique_labels = sorted(set(labels))
        self.label_map = {label: i for i, label in enumerate(unique_labels)}
        self.reverse_label_map = {i: label for label, i in self.label_map.items()}
        y = [self.label_map[label] for label in labels]
        
        # Train
        self.classifier.fit(X, y)
        self.trained = True
        
        # Evaluate on training set
        predictions = self.classifier.predict(X)
        pred_labels = [self.reverse_label_map[p] for p in predictions]
        report = classification_report(labels, pred_labels, output_dict=True)
        
        return {"training_accuracy": report["accuracy"], "classes": unique_labels}
    
    async def predict(self, text: str) -> dict:
        """Classify a single text."""
        if not self.trained:
            raise ValueError("Classifier not trained. Call fit() first.")
        
        embedding = await self.embedder.embed(text)
        X = np.array([embedding])
        
        pred_idx = self.classifier.predict(X)[0]
        probas = self.classifier.predict_proba(X)[0]
        
        return {
            "label": self.reverse_label_map[pred_idx],
            "confidence": float(probas[pred_idx]),
            "all_scores": {
                self.reverse_label_map[i]: float(p)
                for i, p in enumerate(probas)
            }
        }
```

### 3.7 Semantic Deduplication

```python
# semantic_dedup.py
"""
Remove semantically duplicate documents before indexing.
Prevents polluting your search index with near-duplicates.
"""
import numpy as np

async def semantic_dedup(
    documents: List[Dict],
    embedder: CachedEmbedder,
    text_key: str = "content",
    similarity_threshold: float = 0.95,
) -> List[Dict]:
    """
    Remove documents that are semantically too similar.
    Returns deduplicated document list.
    """
    texts = [doc[text_key] for doc in documents]
    embeddings = await embedder.embed_batch(texts)
    
    # Normalize
    emb_array = np.array(embeddings, dtype=np.float32)
    norms = np.linalg.norm(emb_array, axis=1, keepdims=True)
    emb_array = emb_array / norms
    
    # Compute all-pairs similarity (expensive for large sets — use batching)
    similarity_matrix = emb_array @ emb_array.T
    
    # Greedy deduplication
    keep = []
    removed = set()
    
    for i in range(len(documents)):
        if i in removed:
            continue
        
        keep.append(i)
        
        # Mark all future documents too similar to this one as removed
        for j in range(i + 1, len(documents)):
            if similarity_matrix[i, j] >= similarity_threshold:
                removed.add(j)
    
    print(f"Deduplication: {len(documents)} → {len(keep)} documents "
          f"({len(documents) - len(keep)} duplicates removed)")
    
    return [documents[i] for i in keep]
```

---

## 4. EMBEDDING APPLICATIONS

### 4.1 Recommendation System

```python
# recommendation.py

class ContentRecommender:
    """
    Simple content-based recommender using embeddings.
    "More like this" functionality.
    """
    
    def __init__(self, search_index: InMemorySemanticSearch):
        self.index = search_index
    
    async def recommend_similar(
        self,
        item_id: str,
        top_k: int = 5,
        exclude_self: bool = True,
    ) -> List[Dict]:
        """Find items similar to the given item."""
        
        # Find the item
        item = next(
            (doc for doc in self.index.documents if doc.get("id") == item_id),
            None
        )
        if not item:
            return []
        
        # Use the item's content as the query
        results = await self.index.search(item["content"], top_k=top_k + 1)
        
        if exclude_self:
            results = [r for r in results if r.get("id") != item_id]
        
        return results[:top_k]
    
    async def find_by_concept(
        self,
        concept: str,
        top_k: int = 10,
    ) -> List[Dict]:
        """Find items matching a concept description."""
        return await self.index.search(concept, top_k=top_k)
```

### 4.2 Anomaly Detection with Embeddings

```python
# anomaly_detection.py
"""
Use embeddings to detect anomalous text (e.g., prompt injection attempts,
off-topic requests, policy violations).
"""

class TextAnomalyDetector:
    """
    Detect anomalous text by measuring distance from "normal" text cluster.
    Train on examples of normal text; flag outliers.
    """
    
    def __init__(self, embedder: CachedEmbedder, threshold_percentile: float = 95):
        self.embedder = embedder
        self.threshold_percentile = threshold_percentile
        self.normal_embeddings: Optional[np.ndarray] = None
        self.normal_centroid: Optional[np.ndarray] = None
        self.threshold: Optional[float] = None
    
    async def fit(self, normal_texts: List[str]) -> None:
        """Train on examples of normal text."""
        embeddings = await self.embedder.embed_batch(normal_texts)
        self.normal_embeddings = np.array(embeddings, dtype=np.float32)
        
        # Compute centroid of normal examples
        self.normal_centroid = self.normal_embeddings.mean(axis=0)
        
        # Compute distances from centroid for all normal examples
        distances = np.linalg.norm(
            self.normal_embeddings - self.normal_centroid, axis=1
        )
        
        # Set threshold at the Nth percentile
        self.threshold = np.percentile(distances, self.threshold_percentile)
        print(f"Anomaly threshold (distance): {self.threshold:.4f}")
    
    async def is_anomalous(self, text: str) -> dict:
        """Check if text is anomalous."""
        embedding = await self.embedder.embed(text)
        emb_array = np.array(embedding, dtype=np.float32)
        
        distance = np.linalg.norm(emb_array - self.normal_centroid)
        is_anomaly = distance > self.threshold
        
        return {
            "is_anomalous": bool(is_anomaly),
            "distance": float(distance),
            "threshold": float(self.threshold),
            "anomaly_score": float(distance / self.threshold),  # >1 = anomaly
        }
```

---

## 5. VECTOR SIMILARITY AT SCALE — QUICK REFERENCE

```
SCALE         SOLUTION                 QUERY TIME    SETUP COMPLEXITY
----------------------------------------------------------------------
< 10K docs    NumPy (in-memory)        <1ms          Trivial
10K-1M docs   FAISS (in-memory/disk)   1-10ms        Low
1M-100M docs  FAISS + IVF/HNSW        5-50ms        Medium
100M+ docs    Pinecone/Qdrant/Weaviate  10-100ms      Managed service
Enterprise    Elasticsearch kNN        10-100ms      High (infra)
```

---

## 6. TRADEOFFS

### 6.1 Embedding Dimensionality

Higher dimensions = more information but:
- More storage (1536d float32 = 6KB per embedding)
- Slower similarity computation
- More memory for indexes

OpenAI's "Matryoshka" embeddings (text-embedding-3-*) allow dimension reduction:
```python
# Reduce to 256 dimensions for storage efficiency
embedding = await embed_text(text, model="text-embedding-3-small", dimensions=256)
# ~85% quality of full 1536d with 6x less storage
```

### 6.2 Embedding Freshness

Embeddings don't auto-update when documents change. You need a re-indexing strategy:
- **Event-driven:** Re-embed when document is updated
- **Scheduled:** Re-embed all documents nightly
- **Version-based:** Track embedding model version, re-embed when upgrading

### 6.3 Chunking Effects on Embeddings

The chunking strategy profoundly affects embedding quality (covered in depth in RAG module):
- Too small chunks → embeddings lack context (embedding of single sentence has less semantic content than paragraph)
- Too large chunks → embeddings lose specificity (embedding of page mixes many topics)
- **Sweet spot:** 256-512 tokens per chunk for most use cases

---

## 7. DEBUGGING

**Problem: Semantic search returns irrelevant results**
- Check: Is the text properly cleaned before embedding?
- Check: Are you using the same model for indexing and querying?
- Check: Is your similarity threshold too low?
- Test: Compute similarity between known-similar docs and verify high score

**Problem: Similar-looking text gets very different embeddings**
- Cause: Text formatting differences (HTML tags, special characters)
- Fix: Normalize text before embedding
- Check: Leading/trailing whitespace, newlines, markdown formatting

**Problem: Embeddings for the same text differ across calls**
- This shouldn't happen — embeddings are deterministic
- If different: you're using different model versions or caching is broken

**Problem: High memory usage**
- 1M documents × 1536d × 4 bytes (float32) = 6GB RAM
- Fix: Use FAISS with on-disk indexing
- Fix: Reduce dimensions (Matryoshka embeddings)
- Fix: Use a vector database with efficient storage

---

## 8. EXERCISES

### Exercise 1 — Build Semantic FAQ Search
Create a semantic search system for 500 FAQ entries. Compare keyword search accuracy vs semantic search. Measure hit rate @1, @3, @5.

### Exercise 2 — Document Clustering
Embed 200 documents and cluster them using k-means. Visualize with UMAP/t-SNE. Identify natural topic clusters.

### Exercise 3 — Cross-Language Search  
Create an English knowledge base. Query in Hindi/Spanish/French. Demonstrate that multilingual embeddings find relevant results across languages.

### Exercise 4 — Embedding Model Comparison
Compare text-embedding-3-small vs bge-large-en-v1.5 on:
- Accuracy (MTEB benchmarks or custom test set)
- Cost (API vs self-hosted)
- Latency (API call vs local inference)
- Storage requirements

### Exercise 5 — Build a Recommendation Engine
Ingest 1000 tech articles. Build "similar articles" feature. Implement concept search. Measure relevance of top-5 recommendations.

---

## 9. INTERVIEW QUESTIONS

**Q: What's the difference between sparse and dense embeddings?**
A: Dense embeddings (what we've covered) are continuous vectors where every dimension carries semantic meaning — typically 768-3072 dimensional, compact, and learned by neural networks. Every position has a value. Sparse embeddings (like TF-IDF or BM25) are extremely high-dimensional vectors (vocabulary size, ~50K+) where most values are zero — only the dimensions corresponding to words present in the text are non-zero. Dense is better for semantic search (finds conceptually similar content); sparse is better for keyword matching (finds exact terms). Hybrid search combines both for best results (covered in RAG module).

**Q: Why do we normalize embeddings before computing cosine similarity?**
A: Cosine similarity measures the angle between vectors, ignoring their magnitude. Normalizing (making unit vectors) means we can compute cosine similarity with just a dot product: cos_sim(a,b) = a·b when |a|=|b|=1. This is dramatically faster than computing the full cosine formula, especially for batch operations in FAISS. Without normalization, longer documents would naturally have higher magnitude vectors and score higher regardless of actual relevance.

**Q: How would you handle embedding drift when you need to upgrade your embedding model?**
A: Embedding spaces are model-specific — vectors from different models are not comparable. When upgrading models: (1) Re-embed ALL documents with the new model. (2) Build a new index in parallel with the old one. (3) Run both indexes simultaneously for a transition period. (4) A/B test retrieval quality with both models. (5) Migrate traffic to the new model once quality is validated. (6) Deprecate the old model and index. This is a classic "dual-write" migration pattern. For large document collections, this can be expensive — plan for significant compute costs and schedule it as a batch job, not a live migration.

---

*Next: [Module 05 — RAG Fundamentals →](05_rag_fundamentals.md)*
