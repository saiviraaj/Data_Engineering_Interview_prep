# Module 07 — Vector Databases

> Everything you need to build, operate, and scale vector search infrastructure.

---

## Table of Contents

1. [Why Vector Databases?](#1-why-vector-databases)
2. [ANN Index Types — HNSW, IVF, PQ, ScaNN](#2-ann-index-types)
3. [FAISS — Deep Dive](#3-faiss--deep-dive)
4. [ChromaDB — Developer-Friendly Local to Cloud](#4-chromadb)
5. [Pinecone — Managed Vector Search at Scale](#5-pinecone)
6. [Qdrant — High-Performance with Rich Filtering](#6-qdrant)
7. [Weaviate — Graph-Vector Hybrid](#7-weaviate)
8. [pgvector — Vector Search in PostgreSQL](#8-pgvector)
9. [Metadata Filtering — Patterns and Pitfalls](#9-metadata-filtering)
10. [Multi-Tenancy Patterns](#10-multi-tenancy-patterns)
11. [Choosing the Right Vector DB](#11-choosing-the-right-vector-db)
12. [Scaling Vector Search](#12-scaling-vector-search)
13. [Production Operations](#13-production-operations)
14. [Interview Questions](#14-interview-questions)

---

## 1. Why Vector Databases?

Vector databases are optimized for one specific operation: **approximate nearest neighbor (ANN) search** over high-dimensional float vectors.

### Why Not Just Use PostgreSQL?

```sql
-- Exact nearest neighbor in PostgreSQL (no pgvector)
SELECT id, 1 - (embedding <-> query_embedding) AS similarity
FROM documents
ORDER BY similarity DESC
LIMIT 10;
-- Full table scan: O(n*d) — 1M docs × 1536 dims = 1.5B operations
-- 100ms+ at small scale, completely unusable at 10M+ docs
```

Vector DBs solve this with ANN indexes that trade small accuracy loss for massive speed gains:
- 1M vectors → sub-10ms
- 100M vectors → <100ms
- With filtering, streaming, updates, and tenant isolation

### The Vector DB Landscape

| Database | Type | Best For |
|---|---|---|
| FAISS | Library (not a DB) | Research, offline batch search |
| ChromaDB | Embedded / server | Development, small-medium scale |
| Pinecone | Managed cloud | Production, zero-ops teams |
| Qdrant | Self-hosted / cloud | Production, rich filtering, high perf |
| Weaviate | Self-hosted / cloud | Graph+vector, multi-modal |
| pgvector | PostgreSQL extension | Existing Postgres users, <5M vectors |
| Milvus | Self-hosted / cloud | Very large scale (100M+) |
| Redis VSS | Redis extension | Low-latency, existing Redis infra |

---

## 2. ANN Index Types

Understanding index types is essential for choosing the right database and configuration.

### HNSW — Hierarchical Navigable Small World

The most widely used ANN algorithm. Used by Qdrant, Weaviate, pgvector, FAISS.

**How it works:**
- Builds a multi-layer graph
- Upper layers are sparse (long-range connections)
- Lower layers are dense (local connections)
- Search starts at top layer, greedily navigates down

```
Layer 2:  A ────────────── E
Layer 1:  A ──── C ──── E ──── H
Layer 0:  A ─ B ─ C ─ D ─ E ─ F ─ G ─ H
                   ↑
               Start here, navigate to query
```

**Key parameters:**

| Parameter | Effect | Trade-off |
|---|---|---|
| `M` (connections per node) | Higher M → better recall, more memory | Typical: 16-64 |
| `ef_construction` | Higher → better index quality, slower build | Typical: 100-400 |
| `ef_search` | Higher → better recall, slower search | Typical: 50-200 |

**When to use:** General purpose. Best recall/speed balance. Default choice.

### IVF — Inverted File Index

Clusters vectors into Voronoi cells. Search only examines nearby cluster centroids.

```
All vectors → k-means → k clusters
Query → find nearest nprobe clusters → search only those
```

**Key parameters:**
- `nlist`: number of clusters (typical: sqrt(n_vectors))
- `nprobe`: clusters to search (higher = better recall, slower)

**When to use:** Very large datasets (>10M vectors). Requires training phase. Best combined with PQ compression.

### PQ — Product Quantization

Compression technique that reduces memory footprint. Divides high-dimensional vectors into subvectors, quantizes each.

```
1536-dim float32 vector = 6144 bytes
With PQ (m=96 subvectors, 8-bit codes) = 96 bytes
96x memory reduction, ~5% recall loss
```

**Production pattern:** IVF + PQ for very large scale. HNSW for performance-critical applications.

### ScaNN (Google)

Google's ANN library, exceptional performance at scale. Used internally at Google. Available via `scann` Python package.

---

## 3. FAISS — Deep Dive

FAISS (Facebook AI Similarity Search) is a library, not a database. It provides state-of-the-art ANN implementations but requires you to manage persistence, metadata, and serving.

### Core FAISS Usage

```python
import faiss
import numpy as np
import pickle
import os
from typing import List, Dict, Tuple, Optional
from openai import OpenAI

class FAISSVectorStore:
    """
    Production-ready FAISS vector store with metadata support.
    Supports HNSW and IVF indexes.
    """
    
    def __init__(
        self,
        dimension: int = 1536,
        index_type: str = "hnsw",  # "hnsw" or "ivf"
        # HNSW params
        m: int = 32,
        ef_construction: int = 200,
        ef_search: int = 100,
        # IVF params
        n_lists: int = 100,
        n_probe: int = 10,
        use_gpu: bool = False,
    ):
        self.dimension = dimension
        self.index_type = index_type
        self.ef_search = ef_search
        self.n_probe = n_probe
        
        # Build index
        if index_type == "hnsw":
            self.index = faiss.IndexHNSWFlat(dimension, m)
            self.index.hnsw.efConstruction = ef_construction
            self.index.hnsw.efSearch = ef_search
        elif index_type == "ivf":
            # IVF requires training — use with add_documents()
            quantizer = faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, n_lists)
            self.index.nprobe = n_probe
        else:
            # Flat exact search (small datasets only)
            self.index = faiss.IndexFlatIP(dimension)  # Inner product = cosine (if normalized)
        
        if use_gpu and faiss.get_num_gpus() > 0:
            self.index = faiss.index_cpu_to_all_gpus(self.index)
        
        # Metadata store (in production: use PostgreSQL)
        self.id_to_metadata: Dict[int, Dict] = {}
        self.id_to_content: Dict[int, str] = {}
        self.next_id: int = 0
        self._trained = index_type not in ("ivf",)  # HNSW/Flat don't need training
    
    def train(self, vectors: np.ndarray):
        """Required for IVF indexes."""
        if not self._trained:
            self.index.train(vectors)
            self._trained = True
    
    def add(self, vectors: np.ndarray, contents: List[str], metadatas: List[Dict]) -> List[int]:
        """Add vectors with associated content and metadata."""
        assert self._trained, "Call train() first for IVF indexes"
        assert len(vectors) == len(contents) == len(metadatas)
        
        # Normalize for cosine similarity (if using IndexFlatIP or HNSW)
        if self.index_type in ("hnsw", "flat"):
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / (norms + 1e-10)
        
        vectors = vectors.astype(np.float32)
        
        start_id = self.next_id
        ids = list(range(start_id, start_id + len(vectors)))
        
        # FAISS HNSW/Flat don't support custom IDs natively
        # We manage our own ID mapping
        self.index.add(vectors)
        
        for i, (content, metadata) in enumerate(zip(contents, metadatas)):
            internal_id = start_id + i
            self.id_to_content[internal_id] = content
            self.id_to_metadata[internal_id] = metadata
        
        self.next_id += len(vectors)
        return ids
    
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search with optional post-search metadata filtering.
        Note: FAISS doesn't support pre-search filtering — it's applied post-search.
        For large-scale filtered search, use Qdrant or Weaviate.
        """
        query_vector = query_vector.astype(np.float32).reshape(1, -1)
        
        # Normalize for cosine
        if self.index_type in ("hnsw", "flat"):
            query_vector = query_vector / (np.linalg.norm(query_vector) + 1e-10)
        
        # Search more candidates if filtering
        search_k = top_k * 10 if metadata_filter else top_k
        search_k = min(search_k, self.next_id)
        
        distances, indices = self.index.search(query_vector, search_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            metadata = self.id_to_metadata.get(idx, {})
            
            # Apply metadata filter post-search
            if metadata_filter:
                if not all(metadata.get(k) == v for k, v in metadata_filter.items()):
                    continue
            
            results.append({
                "id": idx,
                "score": float(dist),
                "content": self.id_to_content.get(idx, ""),
                "metadata": metadata
            })
            
            if len(results) >= top_k:
                break
        
        return results
    
    def save(self, directory: str):
        """Persist index and metadata to disk."""
        os.makedirs(directory, exist_ok=True)
        faiss.write_index(self.index, os.path.join(directory, "index.faiss"))
        with open(os.path.join(directory, "metadata.pkl"), "wb") as f:
            pickle.dump({
                "id_to_metadata": self.id_to_metadata,
                "id_to_content": self.id_to_content,
                "next_id": self.next_id,
                "config": {
                    "dimension": self.dimension,
                    "index_type": self.index_type
                }
            }, f)
    
    @classmethod
    def load(cls, directory: str) -> "FAISSVectorStore":
        """Load persisted index from disk."""
        with open(os.path.join(directory, "metadata.pkl"), "rb") as f:
            saved = pickle.load(f)
        
        config = saved["config"]
        store = cls(
            dimension=config["dimension"],
            index_type=config["index_type"]
        )
        store.index = faiss.read_index(os.path.join(directory, "index.faiss"))
        store.id_to_metadata = saved["id_to_metadata"]
        store.id_to_content = saved["id_to_content"]
        store.next_id = saved["next_id"]
        store._trained = True
        return store
    
    @property
    def size(self) -> int:
        return self.index.ntotal
```

### FAISS Index Selection Guide

```python
def recommend_faiss_index(n_vectors: int, dimension: int, target_recall: float) -> str:
    """Recommend FAISS index type based on scale and requirements."""
    
    if n_vectors < 100_000:
        return "IndexFlatIP (exact search — small enough)"
    
    elif n_vectors < 1_000_000:
        if target_recall > 0.95:
            return f"IndexHNSWFlat(M=32, ef_construction=200)"
        else:
            return f"IndexIVFFlat(nlist={int(n_vectors**0.5)}, nprobe=10)"
    
    elif n_vectors < 10_000_000:
        return f"IndexIVFFlat(nlist={int(n_vectors**0.5)}, nprobe=20) with PQ compression"
    
    else:
        return (
            f"IndexIVFPQ(nlist=4096, M={dimension//4}, nbits=8, nprobe=20)\n"
            "Consider switching to Milvus or Qdrant for operational simplicity"
        )
```

---

## 4. ChromaDB

ChromaDB is the easiest vector database to get started with. It runs embedded (in-process) or as a server, with a consistent API.

### Core Operations

```python
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from chromadb.config import Settings

# Embedded mode (development)
client_embedded = chromadb.Client()

# Persistent embedded mode
client_persistent = chromadb.PersistentClient(path="./chroma_data")

# Server mode (production)
client_server = chromadb.HttpClient(
    host="localhost",
    port=8000,
    settings=Settings(
        chroma_client_auth_provider="chromadb.auth.token.TokenAuthClientProvider",
        chroma_client_auth_credentials="your-token"
    )
)

# Embedding function
openai_ef = OpenAIEmbeddingFunction(
    api_key="your-key",
    model_name="text-embedding-3-small"
)

# Create collection with embedding function
collection = client_persistent.get_or_create_collection(
    name="documents",
    embedding_function=openai_ef,
    metadata={"hnsw:space": "cosine"}  # distance metric
)

# Add documents (auto-embeds with embedding_function)
collection.add(
    ids=["doc_1", "doc_2", "doc_3"],
    documents=[
        "The quick brown fox jumps over the lazy dog.",
        "Vector databases enable semantic search at scale.",
        "RAG combines retrieval with language model generation.",
    ],
    metadatas=[
        {"source": "test", "category": "example"},
        {"source": "wiki", "category": "technical"},
        {"source": "blog", "category": "technical"},
    ]
)

# Query
results = collection.query(
    query_texts=["how does semantic search work?"],
    n_results=3,
    where={"category": "technical"},  # metadata filter
    include=["documents", "metadatas", "distances", "embeddings"]
)

# Update metadata
collection.update(
    ids=["doc_1"],
    metadatas=[{"source": "test", "category": "example", "reviewed": True}]
)

# Delete
collection.delete(ids=["doc_1"])
# Or delete by filter
collection.delete(where={"category": "example"})

# Count
print(f"Collection size: {collection.count()}")
```

### ChromaDB Multi-Modal Query

```python
# Query with pre-computed embedding (bypass auto-embedding)
import numpy as np

custom_embedding = np.random.randn(1536).tolist()

results = collection.query(
    query_embeddings=[custom_embedding],
    n_results=5,
    where={"$and": [
        {"category": {"$eq": "technical"}},
        {"source": {"$ne": "test"}}
    ]}
)
```

### ChromaDB Limitations

- No built-in distributed/sharding support
- Single server — not horizontally scalable
- No real-time indexing at scale
- Maximum practical: ~10M vectors on a single server

**Use ChromaDB for:** Development, prototypes, internal tools with <1M documents.

---

## 5. Pinecone

Pinecone is the dominant managed vector database. Zero infrastructure management, scales automatically, global multi-region.

### Core Operations

```python
from pinecone import Pinecone, ServerlessSpec, PodSpec
import os

# Initialize
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

# Create serverless index (recommended for most use cases)
if "my-rag-index" not in pc.list_indexes().names():
    pc.create_index(
        name="my-rag-index",
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

# Get index reference
index = pc.Index("my-rag-index")

# Upsert vectors (idempotent — updates existing, inserts new)
index.upsert(
    vectors=[
        {
            "id": "doc_1",
            "values": [0.1, 0.2, ...],  # 1536-dim embedding
            "metadata": {
                "text": "The document content...",
                "source": "wiki",
                "category": "technical",
                "tenant_id": "tenant_abc",
                "created_at": "2024-01-15"
            }
        },
        # ...
    ],
    namespace="tenant_abc"  # namespace = tenant isolation
)

# Query
results = index.query(
    vector=[0.1, 0.2, ...],
    top_k=10,
    namespace="tenant_abc",  # tenant isolation
    filter={
        "category": {"$eq": "technical"},
        "created_at": {"$gte": "2024-01-01"}
    },
    include_values=False,
    include_metadata=True
)

for match in results.matches:
    print(f"ID: {match.id}, Score: {match.score:.4f}")
    print(f"Text: {match.metadata.get('text', '')[:100]}")

# Batch upsert helper
def upsert_batch(index, vectors: list, namespace: str, batch_size: int = 100):
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch, namespace=namespace)

# Delete
index.delete(ids=["doc_1", "doc_2"], namespace="tenant_abc")
index.delete(delete_all=True, namespace="tenant_abc")  # Clear namespace

# Index stats
stats = index.describe_index_stats()
print(f"Total vectors: {stats.total_vector_count}")
print(f"Per namespace: {stats.namespaces}")
```

### Pinecone Best Practices

```python
# Efficient batch embedding + upsert pipeline
from openai import OpenAI
import time

class PineconeIngestionPipeline:
    """Efficient ingestion: embed in batches, upsert in batches."""
    
    def __init__(self, index, namespace: str = "default"):
        self.index = index
        self.namespace = namespace
        self.oai = OpenAI()
    
    def ingest_documents(self, documents: List[Dict], batch_size: int = 50):
        """documents: [{"id": str, "text": str, "metadata": dict}]"""
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            
            # Batch embed
            texts = [d["text"] for d in batch]
            resp = self.oai.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            embeddings = [r.embedding for r in resp.data]
            
            # Prepare for Pinecone
            vectors = [
                {
                    "id": doc["id"],
                    "values": emb,
                    "metadata": {**doc.get("metadata", {}), "text": doc["text"][:1000]}
                }
                for doc, emb in zip(batch, embeddings)
            ]
            
            # Upsert with retry
            for attempt in range(3):
                try:
                    self.index.upsert(vectors=vectors, namespace=self.namespace)
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
            
            print(f"Ingested {min(i+batch_size, len(documents))}/{len(documents)}")
```

### Pinecone Pricing Considerations

| Plan | Storage | Throughput | Cost |
|---|---|---|---|
| Serverless | Pay-per-use | Auto-scale | $0.10/million reads |
| Standard Pod (p1) | 5M vectors/pod | ~200 QPS/pod | ~$0.09/hour |
| Performance Pod (p2) | 5M vectors/pod | ~2000 QPS/pod | ~$0.36/hour |

**Rule of thumb:** Serverless for variable workloads. Pods for steady high-throughput.

---

## 6. Qdrant

Qdrant is the highest-performance self-hosted vector database. Rich filtering, native payload indexing, Rust-based.

### Why Qdrant Stands Out

- **Payload indexing**: Create indexes on metadata fields → O(log n) filtering
- **HNSW with filterable payload**: Filtered ANN (not just post-search filtering)
- **Sparse+dense hybrid**: Native hybrid retrieval support
- **Snapshots**: Built-in backup/restore
- **Collections with multiple vectors**: Store multiple embeddings per document

### Core Operations

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue, Range,
    PayloadSchemaType, TextIndexParams, TokenizerType,
    HnswConfigDiff, SearchParams,
)

# Connect
client = QdrantClient(
    host="localhost",
    port=6333,
    # Or: url="https://your-instance.qdrant.tech", api_key="..."
)

# Create collection with custom HNSW config
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE,
        hnsw_config=HnswConfigDiff(
            m=16,
            ef_construct=200,
            full_scan_threshold=10000,
            on_disk=False  # Set True for large collections
        )
    ),
    # Optional: on-disk payload for large metadata
    on_disk_payload=False
)

# Create payload index for fast metadata filtering
client.create_payload_index(
    collection_name="documents",
    field_name="tenant_id",
    field_schema=PayloadSchemaType.KEYWORD
)
client.create_payload_index(
    collection_name="documents",
    field_name="category",
    field_schema=PayloadSchemaType.KEYWORD
)
client.create_payload_index(
    collection_name="documents",
    field_name="created_at",
    field_schema=PayloadSchemaType.FLOAT
)
# Full-text index for BM25 sparse search
client.create_payload_index(
    collection_name="documents",
    field_name="content",
    field_schema=TextIndexParams(
        type="text",
        tokenizer=TokenizerType.WORD,
        min_token_len=2,
        lowercase=True,
    )
)

# Upsert points
from uuid import uuid4

client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=str(uuid4()),  # UUID or int
            vector=[0.1, 0.2, ...],  # 1536-dim
            payload={
                "content": "The document text...",
                "tenant_id": "tenant_abc",
                "category": "technical",
                "source": "wiki",
                "created_at": 1705276800.0,  # Unix timestamp
            }
        ),
    ]
)

# Filtered search with Qdrant
results = client.search(
    collection_name="documents",
    query_vector=[0.1, 0.2, ...],
    limit=10,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value="tenant_abc")
            ),
            FieldCondition(
                key="category",
                match=MatchValue(value="technical")
            )
        ],
        must_not=[
            FieldCondition(
                key="source",
                match=MatchValue(value="deprecated")
            )
        ]
    ),
    search_params=SearchParams(hnsw_ef=128, exact=False),
    with_payload=True,
)

for result in results:
    print(f"ID: {result.id}, Score: {result.score:.4f}")
    print(f"Content: {result.payload.get('content', '')[:100]}")
```

### Qdrant Hybrid Search (Sparse + Dense)

```python
from qdrant_client.models import SparseVector, NamedSparseVector, NamedVector

# Create collection with both dense and sparse vectors
client.create_collection(
    collection_name="hybrid_docs",
    vectors_config={
        "dense": VectorParams(size=1536, distance=Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams()
    }
)

# For sparse vector generation, use BM42 or SPLADE
from fastembed import SparseTextEmbedding

sparse_model = SparseTextEmbedding(model_name="Qdrant/bm42-all-minilm-l6-v2-attentions")

def get_sparse_vector(text: str) -> Tuple[List[int], List[float]]:
    """Returns (indices, values) for sparse vector."""
    embeddings = list(sparse_model.embed([text]))
    return embeddings[0].indices.tolist(), embeddings[0].values.tolist()

# Upsert with both dense and sparse
indices, values = get_sparse_vector("the document text")

client.upsert(
    collection_name="hybrid_docs",
    points=[
        PointStruct(
            id="doc_1",
            vector={
                "dense": [0.1, 0.2, ...],
                "sparse": SparseVector(indices=indices, values=values)
            },
            payload={"content": "the document text", "category": "technical"}
        )
    ]
)

# Hybrid search with RRF
from qdrant_client.models import Prefetch, FusionQuery

q_indices, q_values = get_sparse_vector("my search query")

results = client.query_points(
    collection_name="hybrid_docs",
    prefetch=[
        Prefetch(
            query=SparseVector(indices=q_indices, values=q_values),
            using="sparse",
            limit=20,
        ),
        Prefetch(
            query=[0.1, 0.2, ...],  # dense query embedding
            using="dense",
            limit=20,
        )
    ],
    query=FusionQuery(fusion=Fusion.RRF),  # Merge with RRF
    limit=10,
    with_payload=True,
)
```

### Qdrant Snapshots and Backup

```python
# Create snapshot
snapshot_info = client.create_snapshot(collection_name="documents")
print(f"Snapshot: {snapshot_info.name}")

# List snapshots
snapshots = client.list_snapshots(collection_name="documents")

# Restore from snapshot
client.recover_snapshot(
    collection_name="documents",
    location=f"http://localhost:6333/collections/documents/snapshots/{snapshot_info.name}"
)
```

---

## 7. Weaviate

Weaviate's unique strengths: native GraphQL API, multi-modal support, semantic class schema, and integrated object graph.

```python
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery, Filter

# Connect
client = weaviate.connect_to_local()
# Or: weaviate.connect_to_weaviate_cloud(cluster_url="...", auth_credentials=Auth.api_key("..."))

# Create schema (class)
if not client.collections.exists("Document"):
    documents = client.collections.create(
        name="Document",
        vectorizer_config=Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-small"
        ),
        properties=[
            Property(name="content", data_type=DataType.TEXT),
            Property(name="tenant_id", data_type=DataType.TEXT),
            Property(name="category", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
        ]
    )

# Get collection reference
documents = client.collections.get("Document")

# Insert objects (auto-vectorizes with configured vectorizer)
with documents.batch.dynamic() as batch:
    for i, doc in enumerate(my_documents):
        batch.add_object(
            properties={
                "content": doc["text"],
                "tenant_id": doc["tenant_id"],
                "category": doc["category"],
                "source": doc["source"],
            },
            uuid=doc["id"]
        )

# Semantic search
results = documents.query.near_text(
    query="vector databases for RAG systems",
    limit=5,
    filters=Filter.by_property("category").equal("technical"),
    return_metadata=MetadataQuery(score=True, distance=True)
)

for obj in results.objects:
    print(f"Score: {obj.metadata.score:.4f}")
    print(f"Content: {obj.properties['content'][:100]}")

# Hybrid search
results = documents.query.hybrid(
    query="semantic search for RAG",
    alpha=0.75,  # 1.0 = pure dense, 0.0 = pure BM25
    limit=10,
)

client.close()
```

---

## 8. pgvector

pgvector adds vector search to PostgreSQL. Ideal if you already use Postgres and need vector search as a feature, not as a primary use case.

```sql
-- Install extension
CREATE EXTENSION vector;

-- Create table with vector column
CREATE TABLE documents (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    embedding   vector(1536),  -- 1536-dim OpenAI embedding
    tenant_id   VARCHAR(100) NOT NULL,
    category    VARCHAR(100),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    metadata    JSONB
);

-- Create HNSW index for fast ANN search
CREATE INDEX ON documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Or IVFFlat (less memory, needs VACUUM after bulk load)
-- CREATE INDEX ON documents
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- Semantic search
SELECT
    id,
    content,
    1 - (embedding <=> $1::vector) AS similarity,
    metadata
FROM documents
WHERE tenant_id = $2
  AND category = $3
ORDER BY embedding <=> $1::vector
LIMIT 10;

-- Hybrid search: combine cosine similarity + full-text search
SELECT
    id,
    content,
    0.7 * (1 - (embedding <=> $1::vector)) +
    0.3 * ts_rank(to_tsvector('english', content), query) AS hybrid_score
FROM documents,
     plainto_tsquery('english', $2) AS query
WHERE tenant_id = $3
ORDER BY hybrid_score DESC
LIMIT 10;
```

```python
# pgvector with psycopg2
import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect("postgresql://user:pass@localhost/mydb")
register_vector(conn)

cur = conn.cursor()

# Insert
embedding = np.array([0.1, 0.2, ...])  # 1536-dim
cur.execute(
    "INSERT INTO documents (content, embedding, tenant_id) VALUES (%s, %s, %s)",
    ("Document text here", embedding, "tenant_abc")
)
conn.commit()

# Search
query_embedding = np.array([0.1, 0.2, ...])
cur.execute(
    """
    SELECT id, content, 1 - (embedding <=> %s) AS similarity
    FROM documents
    WHERE tenant_id = %s
    ORDER BY embedding <=> %s
    LIMIT 10
    """,
    (query_embedding, "tenant_abc", query_embedding)
)
results = cur.fetchall()
```

### pgvector vs Dedicated Vector DB

| Dimension | pgvector | Pinecone/Qdrant |
|---|---|---|
| Scalability | Good to ~5M vectors | Excellent (100M+) |
| Ops simplicity | Same infra as Postgres | Separate service |
| Filtering | Full SQL | Purpose-built |
| ACID transactions | Yes | No |
| Cost | Postgres cost | Additional cost |
| ANN performance | Good | Excellent |

**Use pgvector when:** You already have Postgres, your vector dataset is <5M, you need ACID transactions joining vectors with relational data.

---

## 9. Metadata Filtering — Patterns and Pitfalls

### Filter Types

```python
# Equality filter
where={"tenant_id": {"$eq": "tenant_abc"}}

# Range filter
where={"created_at": {"$gte": 1704067200, "$lte": 1706745600}}

# List membership
where={"category": {"$in": ["technical", "api"]}}

# Exclusion
where={"source": {"$ne": "deprecated"}}

# Composite AND
where={"$and": [
    {"tenant_id": {"$eq": "tenant_abc"}},
    {"category": {"$eq": "technical"}}
]}

# Composite OR
where={"$or": [
    {"category": {"$eq": "technical"}},
    {"category": {"$eq": "api"}}
]}
```

### Critical Pitfall: Pre-Search vs Post-Search Filtering

| Database | Filtering Strategy |
|---|---|
| FAISS | Post-search (retrieve then filter) — problematic |
| ChromaDB | Post-search metadata filter |
| Qdrant | Pre-search (index on payload fields) — correct |
| Pinecone | Pre-search with metadata filter index |
| Weaviate | Pre-search with schema indexing |

**The problem with post-search filtering:**

```
You need: top-10 results for tenant_abc
FAISS does: retrieve top-100 globally → filter to tenant_abc → might get 2 results
Qdrant does: traverse HNSW graph guided by tenant_abc filter → gets top-10
```

**Solution:** For production multi-tenant systems, use Qdrant or Pinecone with proper metadata indexing.

### Combining Vector and Metadata Efficiently

```python
# WRONG pattern: retrieve many, filter in Python
all_results = retriever.retrieve(query, top_k=500)
filtered = [r for r in all_results if r.metadata.get("tenant_id") == tenant_id][:10]
# Problem: wastes 490 retrievals, slow, misses relevant docs

# RIGHT pattern: pass filter to vector DB
results = qdrant_client.search(
    collection_name="documents",
    query_vector=query_embedding,
    limit=10,
    query_filter=Filter(
        must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
    )
)
# Qdrant's HNSW traversal is guided by the filter → correct and efficient
```

---

## 10. Multi-Tenancy Patterns

### Pattern 1: Namespace-per-Tenant (Pinecone)

```python
# Each tenant gets a namespace
index.upsert(vectors=[...], namespace=f"tenant_{tenant_id}")
results = index.query(vector=[...], namespace=f"tenant_{tenant_id}", top_k=10)

# Pros: True isolation, easy to delete all tenant data
# Cons: Namespace limit (Pinecone allows thousands of namespaces)
```

### Pattern 2: Collection-per-Tenant (Qdrant, ChromaDB)

```python
# Each tenant gets a collection
client.create_collection(name=f"tenant_{tenant_id}", ...)
results = client.search(collection_name=f"tenant_{tenant_id}", ...)

# Pros: True isolation, independent index tuning
# Cons: Resource overhead per collection, complex to manage at scale (1000+ tenants)
```

### Pattern 3: Shared Collection + Metadata Filter (all DBs)

```python
# Single collection, filter by tenant_id at search time
# CRITICAL: tenant_id must be indexed
results = qdrant_client.search(
    collection_name="all_documents",
    query_vector=query_embedding,
    limit=10,
    query_filter=Filter(
        must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
    )
)

# Pros: Simple ops, scales to 10K+ tenants
# Cons: Tenant data co-located, filter must be enforced in code
```

### Tenant Isolation Decision Matrix

| Tenants | Data Sensitivity | Recommended |
|---|---|---|
| <100 | High (healthcare, finance) | Collection/namespace per tenant |
| 100-1000 | Medium | Namespace per tenant |
| >1000 | Standard | Shared collection + metadata filter |
| >10000 | Any | Shared collection + shard by tenant tier |

---

## 11. Choosing the Right Vector DB

### Decision Flowchart

```
Start
  ↓
Do you need managed, zero-ops?
  → YES: Is budget flexible?
      → YES: Pinecone (best performance, simplest ops)
      → NO: Zilliz Cloud (managed Milvus)
  → NO: Can you run infrastructure?
      → Want richest filtering + Rust performance: Qdrant
      → Want graph+vector + multi-modal: Weaviate
      → Already using PostgreSQL (<5M vectors): pgvector
      → Development/prototyping only: ChromaDB
      → Research, offline batch: FAISS
```

### Comprehensive Comparison

| Feature | FAISS | ChromaDB | Pinecone | Qdrant | Weaviate | pgvector |
|---|---|---|---|---|---|---|
| Hosting | Library | Embedded/Server | Managed | Self/Cloud | Self/Cloud | Self |
| Max scale | 100M+ (batch) | ~10M | Unlimited | 100M+ | 100M+ | ~5M |
| Filtering | Post-search | Post-search | Pre-search | Pre-search | Pre-search | SQL |
| Hybrid search | No | No | No (manual) | Yes (native) | Yes (native) | Manual |
| Multi-tenancy | Manual | Manual | Namespaces | Payloads/Collections | Multi-tenancy | Row security |
| Updates | Difficult | Easy | Easy | Easy | Easy | Easy |
| Snapshots | No | No | No | Yes | Yes | pg backup |
| Cost | Free | Free | $$$+ | Free/$ | Free/$ | Postgres cost |

---

## 12. Scaling Vector Search

### Horizontal Scaling Strategies

#### Qdrant Cluster Setup

```yaml
# docker-compose for Qdrant cluster
version: '3.8'
services:
  qdrant-node-1:
    image: qdrant/qdrant:latest
    environment:
      QDRANT__CLUSTER__ENABLED: "true"
      QDRANT__CLUSTER__P2P__PORT: "6335"
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_data_1:/qdrant/storage

  qdrant-node-2:
    image: qdrant/qdrant:latest
    environment:
      QDRANT__CLUSTER__ENABLED: "true"
      QDRANT__CLUSTER__P2P__PORT: "6335"
      QDRANT__CLUSTER__CONSENSUS__BOOTSTRAP_PEERS: "qdrant-node-1:6335"
    ports:
      - "6334:6333"
    volumes:
      - ./qdrant_data_2:/qdrant/storage
```

```python
# Create distributed collection with sharding
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    shard_number=4,           # 4 shards across cluster
    replication_factor=2,     # 2 replicas per shard
    write_consistency_factor=1
)
```

### Caching for Scale

```python
# Three-tier caching strategy
class TieredVectorSearchCache:
    """
    L1: In-process LRU cache (microseconds)
    L2: Redis semantic cache (milliseconds)
    L3: Vector DB (10-100ms)
    """
    
    def __init__(self, redis_client, vector_db, l1_size=100):
        from functools import lru_cache
        self.redis = redis_client
        self.vector_db = vector_db
        self._l1_cache = {}  # Simplified — use functools.lru_cache in practice
        self._l1_size = l1_size
    
    def search(self, query: str, query_embedding: List[float], **kwargs) -> List[Dict]:
        # L1: exact query match
        if query in self._l1_cache:
            return self._l1_cache[query]
        
        # L2: semantic match in Redis
        # (integrate with SemanticCache from Module 06)
        
        # L3: vector DB
        results = self.vector_db.search(query_embedding, **kwargs)
        
        # Populate caches
        self._l1_cache[query] = results
        if len(self._l1_cache) > self._l1_size:
            oldest = next(iter(self._l1_cache))
            del self._l1_cache[oldest]
        
        return results
```

### Read Replicas

For read-heavy RAG workloads, scale reads independently from writes:

```python
import random

class ReadReplicaVectorStore:
    """Route reads to replicas, writes to primary."""
    
    def __init__(self, primary_url: str, replica_urls: List[str]):
        self.primary = QdrantClient(url=primary_url)
        self.replicas = [QdrantClient(url=url) for url in replica_urls]
    
    def write(self, collection: str, points: list):
        """All writes go to primary."""
        return self.primary.upsert(collection_name=collection, points=points)
    
    def read(self, collection: str, query_vector: List[float], **kwargs):
        """Reads distributed across replicas."""
        replica = random.choice(self.replicas) if self.replicas else self.primary
        try:
            return replica.search(collection_name=collection, query_vector=query_vector, **kwargs)
        except Exception:
            # Fallback to primary on replica failure
            return self.primary.search(collection_name=collection, query_vector=query_vector, **kwargs)
```

---

## 13. Production Operations

### Monitoring Vector DB Health

```python
class VectorDBMonitor:
    """Monitor key vector DB metrics."""
    
    def collect_metrics(self, client: QdrantClient, collection: str) -> Dict:
        info = client.get_collection(collection)
        
        return {
            "vector_count": info.vectors_count,
            "indexed_vectors": info.indexed_vectors_count,
            "status": info.status.value,
            "optimizer_status": info.optimizer_status.status.value,
            "disk_usage_bytes": info.payload_schema,
        }
    
    def health_check(self, client: QdrantClient) -> bool:
        try:
            client.get_collections()
            return True
        except Exception:
            return False
```

### Index Maintenance

```python
# Qdrant: Force re-indexing after bulk loads
client.update_collection(
    collection_name="documents",
    optimizer_config=OptimizersConfigDiff(
        indexing_threshold=10000,  # Trigger indexing after 10K unindexed vectors
    )
)

# FAISS: Rebuild index periodically (doesn't support incremental updates well)
def rebuild_faiss_index(store: FAISSVectorStore, all_vectors: np.ndarray):
    """Full rebuild for FAISS — run during off-peak hours."""
    store.index.reset()
    store.index.add(all_vectors.astype(np.float32))
```

### Common Production Issues

| Issue | Cause | Fix |
|---|---|---|
| High p99 latency | HNSW ef_search too high | Reduce ef_search, test recall impact |
| Low recall | ef_search too low | Increase ef_search |
| Memory OOM | Too many vectors in memory | Enable on-disk storage, use PQ |
| Slow filtered search | No payload index | Create index on filter fields |
| Wrong results after update | Stale cached queries | Invalidate semantic cache on updates |
| Slow bulk ingestion | Sequential upserts | Batch upserts (100-500 per request) |

---

## 14. Interview Questions

**Q1: What is the difference between HNSW and IVF, and when would you choose each?**

HNSW builds a hierarchical graph and navigates it at search time — excellent recall at low latency, works well incrementally. IVF clusters vectors into Voronoi cells and only searches nearby clusters — more memory-efficient but requires a training phase and handles updates poorly. Choose HNSW for production RAG systems where latency and recall matter. Choose IVF+PQ when memory is the constraint (100M+ vectors) or for offline batch search.

**Q2: How does post-search filtering differ from pre-search filtering, and why does it matter?**

Post-search filtering retrieves a large candidate set and filters afterward — if your filter is selective (1% of data matches), you need to over-retrieve 100x to get enough results. Pre-search filtering (Qdrant, Pinecone) integrates the filter into the ANN graph traversal itself — only traverses nodes matching the filter condition. For multi-tenant RAG where each tenant has a small fraction of all documents, pre-search filtering is essential.

**Q3: Design a vector DB architecture for a RAG system with 10,000 enterprise tenants, each with up to 100,000 documents.**

At 10,000 tenants × 100,000 docs = 1 billion vectors total, collection-per-tenant is unmanageable. Use: (1) Pinecone or Qdrant with namespace/payload-based isolation; (2) Shard vectors by tenant tier (enterprise/standard/free) for performance isolation; (3) Payload index on `tenant_id` for efficient filtering; (4) Tenant-scoped semantic cache in Redis; (5) Background job to delete/archive inactive tenant collections; (6) Per-tenant rate limiting to prevent noisy neighbor issues.

**Q4: What embedding model would you choose and why does the choice matter?**

Embedding model choice determines: (1) semantic quality — does "fix the bug" have a similar embedding to "resolve the defect"?; (2) dimension — higher dim (3072 for text-embedding-3-large) is better but costs more storage; (3) domain fit — general models (OpenAI, Cohere) vs domain-specific (legal, medical). For production: text-embedding-3-small is best price/performance for general domains. For high accuracy: text-embedding-3-large. For privacy/on-prem: nomic-embed-text via Ollama.

**Q5: How would you handle vector DB migrations (moving from Chroma to Qdrant) with zero downtime?**

Dual-write strategy: (1) Start writing to both old (Chroma) and new (Qdrant) on new data; (2) Backfill old documents from Chroma → Qdrant in background batches; (3) Verify parity with random sample queries; (4) Shadow-read: send queries to both, compare results; (5) Canary: shift 5% of reads to Qdrant, monitor; (6) Full cutover when confidence is high; (7) Disable Chroma writes, keep as backup for 1 week.

---

*Next: Module 08 — LangChain Core*
