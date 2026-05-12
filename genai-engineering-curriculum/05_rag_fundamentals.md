# Module 05 — RAG Fundamentals

> **Phase:** 2 — RAG Engineering  
> **Prerequisites:** Modules 01–04  
> **Leads to:** Advanced RAG, Vector Databases  
> **Estimated time:** 3–4 days

---

## 1. THE BIG PICTURE

RAG (Retrieval-Augmented Generation) is the most important pattern in production AI engineering. Nearly every enterprise AI system uses RAG in some form.

**The problem RAG solves:** LLMs have static, frozen knowledge (training cutoff). They don't know:
- Your internal documents and policies
- Recent events
- Private company data
- Real-time information
- Domain-specific knowledge not in training data

**The RAG solution:** Before generating an answer, retrieve relevant information from an external knowledge base and inject it into the prompt. Now the model can answer questions it was never trained on.

```
WITHOUT RAG:
User: "What is our data retention policy?"
LLM: "I don't have access to your specific data retention policy..." (or hallucinates one)

WITH RAG:
1. User: "What is our data retention policy?"
2. System retrieves: [Policy Doc: "All production data must be retained for 7 years..."]
3. LLM + retrieved context: "According to your data retention policy, production data must be retained for 7 years. Specifically, financial transaction data must be..."
```

**Why it matters over fine-tuning:**
| Factor | RAG | Fine-tuning |
|--------|-----|-------------|
| Update data | Minutes (re-index) | Days (retrain) |
| Cost | Low | Very high |
| Explainability | High (cite sources) | Low |
| Knowledge scope | Unlimited | Fixed to training |
| Privacy | Data stays external | Data in weights |
| Production readiness | High | Complex |

**RAG is not a silver bullet.** It adds complexity, new failure modes, and requires careful engineering. This module covers both how to build it and how to think about when not to use it.

---

## 2. RAG ARCHITECTURE OVERVIEW

### 2.1 The Two Phases

Every RAG system has two phases:

```
PHASE 1: INDEXING (offline / async)
──────────────────────────────────────────────────────
Documents → Load → Clean → Chunk → Embed → Store in Vector DB

PHASE 2: RETRIEVAL + GENERATION (online / real-time)
──────────────────────────────────────────────────────
User Query → Embed Query → Search Vector DB → Retrieved Chunks
         → Build Prompt (Query + Chunks) → LLM → Answer
```

### 2.2 Complete RAG Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         INDEXING PIPELINE                        │
│                                                                  │
│  PDF/Word/Web  ──► Document    ──► Text      ──► Semantic       │
│  Databases         Loader          Cleaner       Chunker        │
│  APIs                                                ↓           │
│                                               Embedding         │
│                                               Model             │
│                                                 ↓               │
│                                          ┌──────────────┐       │
│                                          │  Vector DB   │       │
│                                          │  (Qdrant/    │       │
│                                          │   Pinecone)  │       │
│                                          └──────────────┘       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       QUERY PIPELINE                             │
│                                                                  │
│  User Query ──► Query ──► Vector ──► Top-K    ──► Reranker      │
│               Rewrite    Search      Chunks        (optional)   │
│                                         ↓                       │
│                                    Prompt       ──► LLM ──► Answer│
│                                    Builder                      │
│                                    + Citations                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DOCUMENT LOADING

### 3.1 Loading Different Document Types

```python
# document_loaders.py
from pathlib import Path
from typing import List, Dict, Optional
import asyncio

class DocumentLoader:
    """
    Unified document loader supporting multiple formats.
    Always returns: List[{"content": str, "metadata": dict, "source": str}]
    """
    
    @staticmethod
    def load_pdf(file_path: str) -> List[Dict]:
        """Load PDF with metadata preservation."""
        try:
            import pypdf
        except ImportError:
            import subprocess
            subprocess.run(["pip", "install", "pypdf"], check=True)
            import pypdf
        
        documents = []
        reader = pypdf.PdfReader(file_path)
        
        # Extract document-level metadata
        info = reader.metadata
        doc_metadata = {
            "source": file_path,
            "title": info.get("/Title", Path(file_path).stem),
            "author": info.get("/Author", "Unknown"),
            "total_pages": len(reader.pages),
            "file_type": "pdf",
        }
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                documents.append({
                    "content": text,
                    "metadata": {
                        **doc_metadata,
                        "page_number": page_num + 1,
                        "section": f"Page {page_num + 1}",
                    },
                    "source": f"{file_path}#page={page_num + 1}",
                })
        
        return documents
    
    @staticmethod
    def load_text(file_path: str, encoding: str = "utf-8") -> List[Dict]:
        """Load plain text or markdown file."""
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()
        
        return [{
            "content": content,
            "metadata": {
                "source": file_path,
                "file_type": Path(file_path).suffix.lower(),
                "size_bytes": Path(file_path).stat().st_size,
            },
            "source": file_path,
        }]
    
    @staticmethod
    async def load_url(url: str) -> List[Dict]:
        """Load content from a URL."""
        import httpx
        from bs4 import BeautifulSoup
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=30)
            response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove navigation, ads, scripts
        for tag in soup(["nav", "header", "footer", "script", "style", "ads"]):
            tag.decompose()
        
        # Extract main content
        main = soup.find("main") or soup.find("article") or soup.find("body")
        text = main.get_text(separator="\n", strip=True) if main else soup.get_text()
        
        # Clean whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)
        
        return [{
            "content": clean_text,
            "metadata": {
                "source": url,
                "title": soup.title.string if soup.title else url,
                "file_type": "html",
            },
            "source": url,
        }]
    
    @staticmethod
    def load_docx(file_path: str) -> List[Dict]:
        """Load Word document."""
        from docx import Document
        
        doc = Document(file_path)
        paragraphs = []
        
        current_section = "Introduction"
        for para in doc.paragraphs:
            # Detect headings for metadata
            if para.style.name.startswith("Heading"):
                current_section = para.text
            elif para.text.strip():
                paragraphs.append({
                    "text": para.text,
                    "section": current_section,
                })
        
        # Group by section
        sections = {}
        for para in paragraphs:
            section = para["section"]
            if section not in sections:
                sections[section] = []
            sections[section].append(para["text"])
        
        documents = []
        for section, texts in sections.items():
            documents.append({
                "content": "\n\n".join(texts),
                "metadata": {
                    "source": file_path,
                    "section": section,
                    "file_type": "docx",
                },
                "source": f"{file_path}#{section}",
            })
        
        return documents
    
    @classmethod
    def load(cls, source: str) -> List[Dict]:
        """Auto-detect and load from any source."""
        if source.startswith("http://") or source.startswith("https://"):
            import asyncio
            return asyncio.run(cls.load_url(source))
        
        path = Path(source)
        suffix = path.suffix.lower()
        
        loaders = {
            ".pdf": cls.load_pdf,
            ".txt": cls.load_text,
            ".md": cls.load_text,
            ".docx": cls.load_docx,
            ".doc": cls.load_docx,
        }
        
        loader = loaders.get(suffix)
        if not loader:
            raise ValueError(f"Unsupported file type: {suffix}")
        
        return loader(source)
```

---

## 4. CHUNKING STRATEGIES

Chunking is one of the most impactful decisions in RAG. Poor chunking → poor retrieval → poor answers.

### 4.1 Why Chunking Matters

**Too small chunks:**
- Embeddings lack context → low retrieval accuracy
- More chunks → slower search
- Answers may be incomplete (important context split across chunks)

**Too large chunks:**
- One chunk contains multiple topics → embedding averages them
- More tokens in context → higher cost
- LLM may focus on wrong part of long chunk

**The sweet spot:** 256-1024 tokens with 10-20% overlap. Exact value depends on your content.

### 4.2 Chunking Strategies

```python
# chunking.py
from typing import List, Dict, Optional
import re

class TextChunker:
    """Multiple chunking strategies for different content types."""
    
    @staticmethod
    def fixed_size_chunker(
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        metadata: dict = None,
    ) -> List[Dict]:
        """
        Fixed-size chunking by character count.
        Simple, predictable, but ignores semantic boundaries.
        Good for: technical docs, log files, structured text
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Try to end at a sentence boundary
            if end < len(text):
                # Look for last period/newline within last 100 chars
                boundary = max(
                    chunk_text.rfind(". "),
                    chunk_text.rfind("\n"),
                    chunk_text.rfind("? "),
                    chunk_text.rfind("! "),
                )
                if boundary > chunk_size * 0.5:  # Only if not too early
                    end = start + boundary + 1
                    chunk_text = text[start:end]
            
            if chunk_text.strip():
                chunks.append({
                    "content": chunk_text.strip(),
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks),
                        "start_char": start,
                        "end_char": end,
                        "chunking_strategy": "fixed_size",
                    }
                })
            
            start = end - chunk_overlap
        
        return chunks
    
    @staticmethod
    def recursive_chunker(
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        metadata: dict = None,
    ) -> List[Dict]:
        """
        Recursive chunking: splits on \n\n, then \n, then ". ", then " ".
        Preserves semantic boundaries as much as possible.
        BEST GENERAL-PURPOSE STRATEGY.
        """
        
        def _split(text: str, separators: List[str], chunk_size: int) -> List[str]:
            if not separators:
                return [text]
            
            separator = separators[0]
            remaining_separators = separators[1:]
            
            splits = text.split(separator)
            
            chunks = []
            current_chunk = ""
            
            for split in splits:
                test_chunk = (current_chunk + separator + split).strip()
                
                if len(test_chunk) <= chunk_size:
                    current_chunk = test_chunk
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    # Recursively split long splits
                    if len(split) > chunk_size:
                        sub_chunks = _split(split, remaining_separators, chunk_size)
                        chunks.extend(sub_chunks[:-1])
                        current_chunk = sub_chunks[-1] if sub_chunks else ""
                    else:
                        current_chunk = split
            
            if current_chunk:
                chunks.append(current_chunk)
            
            return chunks
        
        separators = ["\n\n", "\n", ". ", "? ", "! ", ", ", " ", ""]
        raw_chunks = _split(text, separators, chunk_size)
        
        # Add overlap
        chunks_with_overlap = []
        for i, chunk in enumerate(raw_chunks):
            if i > 0 and chunk_overlap > 0:
                # Take last N characters of previous chunk as prefix
                prev_chunk = raw_chunks[i-1]
                overlap_text = prev_chunk[-chunk_overlap:]
                chunk = overlap_text + " " + chunk
            
            if chunk.strip():
                chunks_with_overlap.append({
                    "content": chunk.strip(),
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks_with_overlap),
                        "chunking_strategy": "recursive",
                    }
                })
        
        return chunks_with_overlap
    
    @staticmethod
    def sentence_chunker(
        text: str,
        sentences_per_chunk: int = 5,
        sentence_overlap: int = 1,
        metadata: dict = None,
    ) -> List[Dict]:
        """
        Chunk by sentences.
        Good for: Q&A documents, articles, conversational content
        """
        import nltk
        try:
            sentences = nltk.sent_tokenize(text)
        except LookupError:
            nltk.download('punkt')
            sentences = nltk.sent_tokenize(text)
        
        chunks = []
        
        for i in range(0, len(sentences), sentences_per_chunk - sentence_overlap):
            chunk_sentences = sentences[i:i + sentences_per_chunk]
            chunk_text = " ".join(chunk_sentences)
            
            if chunk_text.strip():
                chunks.append({
                    "content": chunk_text.strip(),
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks),
                        "sentence_start": i,
                        "sentence_end": i + len(chunk_sentences) - 1,
                        "chunking_strategy": "sentence",
                    }
                })
        
        return chunks
    
    @staticmethod
    def markdown_chunker(
        text: str,
        metadata: dict = None,
    ) -> List[Dict]:
        """
        Chunk markdown documents by headers.
        Best for: README files, documentation, wikis
        """
        # Split on markdown headers
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        
        sections = []
        current_section = {"level": 0, "title": "Introduction", "content": ""}
        last_end = 0
        
        for match in header_pattern.finditer(text):
            # Save previous section
            content = text[last_end:match.start()].strip()
            if content:
                current_section["content"] = content
                sections.append(current_section.copy())
            
            # Start new section
            level = len(match.group(1))
            title = match.group(2)
            current_section = {
                "level": level,
                "title": title,
                "content": "",
                "header_path": title,  # TODO: build full path
            }
            last_end = match.end()
        
        # Last section
        content = text[last_end:].strip()
        if content:
            current_section["content"] = content
            sections.append(current_section)
        
        chunks = []
        for section in sections:
            if section["content"]:
                chunks.append({
                    "content": f"# {section['title']}\n\n{section['content']}",
                    "metadata": {
                        **(metadata or {}),
                        "section_title": section["title"],
                        "header_level": section["level"],
                        "chunking_strategy": "markdown",
                        "chunk_index": len(chunks),
                    }
                })
        
        return chunks
    
    @staticmethod
    def semantic_chunker(
        text: str,
        embedder: "CachedEmbedder",
        breakpoint_threshold: float = 0.3,
        metadata: dict = None,
    ) -> List[Dict]:
        """
        Semantic chunking: split where topic changes significantly.
        Most accurate but expensive (requires embedding every sentence).
        
        Algorithm:
        1. Split into sentences
        2. Embed each sentence
        3. Compute similarity between adjacent sentences
        4. Split where similarity drops below threshold (topic change)
        """
        # This requires async — see async version below
        raise NotImplementedError("Use async_semantic_chunker instead")
    
    @staticmethod
    async def async_semantic_chunker(
        text: str,
        embedder: "CachedEmbedder",
        breakpoint_percentile: float = 95,  # Split at top 5% similarity drops
        min_chunk_size: int = 100,
        metadata: dict = None,
    ) -> List[Dict]:
        """Async semantic chunker."""
        import numpy as np
        
        # Split into sentences
        sentences = text.split(". ")
        if len(sentences) < 3:
            return [{"content": text, "metadata": metadata or {}}]
        
        # Embed all sentences
        embeddings = await embedder.embed_batch(sentences)
        emb_array = np.array(embeddings, dtype=np.float32)
        
        # Compute similarity between adjacent sentences
        norms = np.linalg.norm(emb_array, axis=1, keepdims=True)
        normalized = emb_array / norms
        
        # Cosine similarity between consecutive sentences
        similarities = [
            float(normalized[i] @ normalized[i+1])
            for i in range(len(normalized) - 1)
        ]
        
        # Find breakpoints where similarity drops significantly
        threshold = np.percentile(similarities, 100 - breakpoint_percentile)
        breakpoints = [
            i for i, sim in enumerate(similarities) 
            if sim < threshold
        ]
        
        # Build chunks
        chunks = []
        prev_break = 0
        
        for bp in breakpoints + [len(sentences)]:
            chunk_sentences = sentences[prev_break:bp + 1]
            chunk_text = ". ".join(chunk_sentences).strip()
            
            if len(chunk_text) >= min_chunk_size:
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks),
                        "sentence_start": prev_break,
                        "sentence_end": bp,
                        "chunking_strategy": "semantic",
                    }
                })
            prev_break = bp + 1
        
        return chunks
```

### 4.3 Choosing a Chunking Strategy

```
CONTENT TYPE                    RECOMMENDED STRATEGY
─────────────────────────────────────────────────────────
FAQ / Q&A documents             Sentence (5-7 sentences per chunk)
Technical documentation         Recursive (512 tokens, 50 overlap)
Legal documents                 Recursive (1024 tokens, 100 overlap)
Markdown/Wiki pages             Markdown header-based
Code documentation              Recursive + code-aware (by function)
News articles                   Recursive (256-512 tokens)
Research papers                 Section-based (abstract, intro, methods, etc.)
Chat transcripts                Fixed (10-20 messages per chunk)
Mixed/unknown                   Recursive (best default)
```

---

## 5. BUILDING A COMPLETE BASIC RAG SYSTEM

### 5.1 The Complete Pipeline

```python
# basic_rag.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, AsyncGenerator
import asyncio

@dataclass
class RAGConfig:
    """Configuration for the RAG system."""
    # Indexing
    chunk_size: int = 512
    chunk_overlap: int = 50
    embedding_model: str = "text-embedding-3-small"
    
    # Retrieval
    retrieval_top_k: int = 20  # Initial retrieval
    rerank_top_k: int = 5      # After reranking
    use_reranker: bool = True
    
    # Generation
    llm_model: str = "gpt-4o"
    max_context_tokens: int = 8000
    temperature: float = 0.0
    
    # Features
    enable_citations: bool = True
    enable_semantic_caching: bool = False


class BasicRAGSystem:
    """
    Production-grade basic RAG system.
    Handles: indexing, retrieval, reranking, generation, citations.
    """
    
    def __init__(
        self,
        vector_store,     # Vector DB (see Module 07)
        embedder: CachedEmbedder,
        llm_client: LLMClient,
        config: RAGConfig = None,
        reranker: CrossEncoderReranker = None,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.llm = llm_client
        self.config = config or RAGConfig()
        self.reranker = reranker
        self.chunker = TextChunker()
    
    # ─── INDEXING ─────────────────────────────────────────────────
    
    async def index_documents(
        self,
        sources: List[str],  # File paths or URLs
        batch_size: int = 50,
    ) -> dict:
        """
        Full indexing pipeline:
        Load → Clean → Chunk → Embed → Store
        """
        loader = DocumentLoader()
        all_chunks = []
        
        for source in sources:
            print(f"Loading: {source}")
            docs = loader.load(source)
            
            for doc in docs:
                # Chunk the document
                chunks = self.chunker.recursive_chunker(
                    text=doc["content"],
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                    metadata=doc.get("metadata", {}),
                )
                
                # Add source to each chunk
                for chunk in chunks:
                    chunk["source"] = doc["source"]
                
                all_chunks.extend(chunks)
        
        print(f"Total chunks: {len(all_chunks)}")
        
        # Embed and store in batches
        texts = [c["content"] for c in all_chunks]
        
        print(f"Embedding {len(texts)} chunks...")
        embeddings = await self.embedder.embed_batch(
            texts,
            batch_size=batch_size,
        )
        
        # Store in vector database
        await self.vector_store.upsert(
            ids=[str(i) for i in range(len(all_chunks))],
            embeddings=embeddings,
            documents=all_chunks,
        )
        
        return {
            "sources_indexed": len(sources),
            "total_chunks": len(all_chunks),
            "avg_chunk_size": sum(len(t) for t in texts) // len(texts) if texts else 0,
        }
    
    # ─── RETRIEVAL ────────────────────────────────────────────────
    
    async def retrieve(
        self,
        query: str,
        filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Retrieve relevant chunks for a query.
        
        Process:
        1. Embed query
        2. ANN search in vector DB
        3. Optional: rerank with cross-encoder
        """
        
        # Embed query
        query_embedding = await self.embedder.embed(query)
        
        # Search vector DB
        initial_results = await self.vector_store.search(
            embedding=query_embedding,
            top_k=self.config.retrieval_top_k,
            filters=filters,
        )
        
        # Rerank if enabled
        if self.reranker and self.config.use_reranker and len(initial_results) > self.config.rerank_top_k:
            final_results = self.reranker.rerank(
                query=query,
                documents=initial_results,
                top_k=self.config.rerank_top_k,
            )
        else:
            final_results = initial_results[:self.config.rerank_top_k]
        
        return final_results
    
    # ─── GENERATION ───────────────────────────────────────────────
    
    async def generate(
        self,
        query: str,
        retrieved_docs: List[Dict],
    ) -> Dict:
        """
        Generate an answer using retrieved documents.
        """
        
        # Build context from retrieved docs
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            source = doc.get("source", "Unknown")
            content = doc["content"]
            score = doc.get("rerank_score") or doc.get("similarity_score", 0)
            
            context_parts.append(
                f"[Document {i}] (Source: {source}, Relevance: {score:.2f})\n{content}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Truncate if too long
        context_tokens = estimate_tokens(context)
        if context_tokens > self.config.max_context_tokens:
            # Take proportional amount from each document
            ratio = self.config.max_context_tokens / context_tokens
            for i, doc in enumerate(retrieved_docs):
                max_chars = int(len(doc["content"]) * ratio)
                retrieved_docs[i]["content"] = doc["content"][:max_chars] + "..."
            
            # Rebuild context
            context_parts = [
                f"[Document {i}] (Source: {doc.get('source', 'Unknown')})\n{doc['content']}"
                for i, doc in enumerate(retrieved_docs, 1)
            ]
            context = "\n\n---\n\n".join(context_parts)
        
        system_prompt = """You are a helpful AI assistant that answers questions based on provided documents.

Instructions:
- Answer the question using ONLY the information in the provided documents
- Cite your sources using [Document N] format
- If the documents don't contain the answer, say "I couldn't find information about this in the provided documents"
- Do not invent or extrapolate information not in the documents
- Be precise and factual"""
        
        messages = [
            {
                "role": "user",
                "content": f"""<documents>
{context}
</documents>

<question>
{query}
</question>

Answer the question based on the documents above."""
            }
        ]
        
        response = await self.llm.complete(
            messages=messages,
            system=system_prompt,
            temperature=self.config.temperature,
        )
        
        return {
            "answer": response["content"],
            "sources": list(set(doc.get("source", "") for doc in retrieved_docs)),
            "retrieved_docs": retrieved_docs,
            "tokens": response["usage"],
        }
    
    # ─── QUERY ────────────────────────────────────────────────────
    
    async def query(
        self,
        question: str,
        filters: Optional[Dict] = None,
    ) -> Dict:
        """
        Full RAG query: retrieve + generate.
        This is the main endpoint.
        """
        
        # Step 1: Retrieve
        retrieved = await self.retrieve(question, filters=filters)
        
        if not retrieved:
            return {
                "answer": "I couldn't find any relevant documents to answer this question.",
                "sources": [],
                "retrieved_docs": [],
            }
        
        # Step 2: Generate
        result = await self.generate(question, retrieved)
        
        return result
    
    async def stream_query(
        self,
        question: str,
        filters: Optional[Dict] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming version of query for better UX."""
        
        retrieved = await self.retrieve(question, filters=filters)
        
        # Stream the generation
        context = self._build_context(retrieved)
        
        system_prompt = "You are a helpful assistant..."
        messages = [{"role": "user", "content": f"Documents:\n{context}\n\nQuestion: {question}"}]
        
        async for chunk in self.llm.stream(messages=messages, system=system_prompt):
            yield chunk
    
    def _build_context(self, docs: List[Dict]) -> str:
        return "\n\n---\n\n".join(
            f"[Doc {i}] {doc['content']}" 
            for i, doc in enumerate(docs, 1)
        )
```

### 5.2 FastAPI RAG Service

```python
# rag_api.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import asyncio

app = FastAPI(title="RAG Service API")

# Initialize RAG system (in production, use dependency injection)
rag_system: Optional[BasicRAGSystem] = None

class QueryRequest(BaseModel):
    question: str
    filters: Optional[dict] = None
    top_k: Optional[int] = 5

class IndexRequest(BaseModel):
    sources: List[str]  # file paths or URLs

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    retrieved_count: int

@app.on_event("startup")
async def startup():
    global rag_system
    # Initialize your RAG system here
    # rag_system = BasicRAGSystem(...)
    pass

@app.post("/index")
async def index_documents(request: IndexRequest, background_tasks: BackgroundTasks):
    """Index new documents (async background task)."""
    
    async def do_index():
        result = await rag_system.index_documents(request.sources)
        print(f"Indexing complete: {result}")
    
    background_tasks.add_task(do_index)
    return {"status": "indexing_started", "sources": len(request.sources)}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the RAG system."""
    
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    result = await rag_system.query(
        question=request.question,
        filters=request.filters,
    )
    
    # Compute rough confidence from retrieval scores
    scores = [d.get("rerank_score", d.get("similarity_score", 0)) 
              for d in result["retrieved_docs"]]
    confidence = sum(scores) / len(scores) if scores else 0.0
    
    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=round(confidence, 2),
        retrieved_count=len(result["retrieved_docs"]),
    )

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## 6. RAG EVALUATION

### 6.1 The RAGAS Framework

RAGAS (RAG Assessment) is the standard evaluation framework for RAG systems:

```python
# rag_evaluation.py
"""
RAGAS metrics:
1. Faithfulness: Is the answer grounded in retrieved context? (0-1)
   - High = answer sticks to what documents say
   - Low = answer contains info not in documents (hallucination)

2. Answer Relevancy: Does the answer actually address the question? (0-1)
   - High = answer directly answers the question
   - Low = answer is tangential or off-topic

3. Context Recall: Did retrieval find all relevant documents? (0-1)
   - High = all information needed to answer is in retrieved context
   - Low = important information was missed by retrieval

4. Context Precision: Are retrieved documents actually relevant? (0-1)
   - High = retrieved documents are mostly relevant
   - Low = many irrelevant documents retrieved

Overall quality = harmonic mean of all metrics
"""

class RAGEvaluator:
    """
    Evaluate RAG system quality using LLM-based assessment.
    """
    
    def __init__(self, eval_client: LLMClient):
        self.client = eval_client
    
    async def eval_faithfulness(
        self,
        answer: str,
        contexts: List[str],
    ) -> float:
        """
        Measure: Is every claim in the answer supported by the contexts?
        """
        context_text = "\n---\n".join(contexts)
        
        response = await self.client.complete(
            messages=[{
                "role": "user",
                "content": f"""Evaluate if the answer is faithful to the provided context.

Context:
{context_text}

Answer:
{answer}

For each claim in the answer, check if it's supported by the context.
Return JSON: {{"faithful_claims": N, "total_claims": N, "faithfulness_score": 0.0-1.0, "unsupported_claims": ["..."]}}"""
            }],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        
        import json
        result = json.loads(response["content"])
        return result.get("faithfulness_score", 0.0)
    
    async def eval_answer_relevancy(
        self,
        question: str,
        answer: str,
    ) -> float:
        """
        Measure: Does the answer address the question?
        Approach: Generate hypothetical questions from the answer, 
        measure similarity to original question.
        """
        response = await self.client.complete(
            messages=[{
                "role": "user",
                "content": f"""Given this answer, generate 3 questions it would best answer.

Answer: {answer}

Return JSON: {{"questions": ["q1", "q2", "q3"]}}"""
            }],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        
        import json
        hypothetical_questions = json.loads(response["content"])["questions"]
        
        # Embed original and hypothetical questions, compute similarity
        original_emb = await embed_text(question)
        hypo_embs = await batch_embed(hypothetical_questions)
        
        import numpy as np
        orig = np.array(original_emb)
        hypos = np.array(hypo_embs)
        
        # Cosine similarities
        similarities = [
            float(np.dot(orig, h) / (np.linalg.norm(orig) * np.linalg.norm(h)))
            for h in hypos
        ]
        
        return float(np.mean(similarities))
    
    async def eval_context_precision(
        self,
        question: str,
        contexts: List[str],
        answer: str,
    ) -> float:
        """
        Measure: What proportion of retrieved context is actually useful?
        """
        if not contexts:
            return 0.0
        
        useful_count = 0
        for context in contexts:
            response = await self.client.complete(
                messages=[{
                    "role": "user",
                    "content": f"""Was this context useful for answering the question?

Question: {question}
Context: {context}
Answer: {answer}

Return JSON: {{"is_useful": true/false, "reason": "..."}}"""
                }],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            
            import json
            result = json.loads(response["content"])
            if result.get("is_useful"):
                useful_count += 1
        
        return useful_count / len(contexts)
    
    async def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
    ) -> Dict:
        """Run all evaluations."""
        
        faithfulness, relevancy, precision = await asyncio.gather(
            self.eval_faithfulness(answer, contexts),
            self.eval_answer_relevancy(question, answer),
            self.eval_context_precision(question, contexts, answer),
        )
        
        return {
            "faithfulness": round(faithfulness, 3),
            "answer_relevancy": round(relevancy, 3),
            "context_precision": round(precision, 3),
            "overall_score": round(
                (faithfulness + relevancy + precision) / 3, 3
            ),
        }


# Batch evaluation on a test set
async def evaluate_rag_system(
    rag_system: BasicRAGSystem,
    evaluator: RAGEvaluator,
    test_questions: List[Dict],  # [{"question": ..., "ground_truth": ...}]
) -> dict:
    
    results = []
    
    for test_case in test_questions:
        result = await rag_system.query(test_case["question"])
        
        scores = await evaluator.evaluate(
            question=test_case["question"],
            answer=result["answer"],
            contexts=[d["content"] for d in result["retrieved_docs"]],
        )
        
        results.append({
            "question": test_case["question"],
            "answer": result["answer"][:200],
            **scores,
        })
    
    # Aggregate
    avg_scores = {
        "avg_faithfulness": sum(r["faithfulness"] for r in results) / len(results),
        "avg_relevancy": sum(r["answer_relevancy"] for r in results) / len(results),
        "avg_precision": sum(r["context_precision"] for r in results) / len(results),
        "avg_overall": sum(r["overall_score"] for r in results) / len(results),
        "total_questions": len(results),
    }
    
    return {"summary": avg_scores, "per_question": results}
```

---

## 7. RAG FAILURE MODES

Understanding where RAG fails is as important as building it.

### 7.1 Retrieval Failures

```
FAILURE: Wrong documents retrieved
CAUSE: Query semantics don't match document semantics
SYMPTOMS: Answer ignores relevant information, uses hallucinated facts
FIXES:
  - Query rewriting (expand/rephrase query before retrieval)
  - Hybrid retrieval (dense + sparse)
  - Better chunking (preserve semantic units)
  - Query decomposition (split complex questions)

FAILURE: Relevant documents not in index
CAUSE: Indexing gaps, stale index, documents not loaded
SYMPTOMS: "I couldn't find information about X" for known topics
FIXES:
  - Audit index coverage
  - Implement incremental indexing
  - Monitor failed retrievals

FAILURE: Retrieved wrong chunk from correct document
CAUSE: Chunking breaks information across chunks
SYMPTOMS: Partial answers, missing key details
FIXES:
  - Increase chunk size
  - Add chunk overlap
  - Use parent chunk retrieval (retrieve small, return large)
```

### 7.2 Generation Failures

```
FAILURE: Hallucination despite relevant context
CAUSE: Model "fills in" rather than using context, or context too long
SYMPTOMS: Fabricated details, incorrect specifics
FIXES:
  - Lower temperature
  - Stronger grounding instruction
  - Structured output with citation requirement
  - Confidence scoring

FAILURE: Answer ignores retrieved context
CAUSE: "Lost in the middle" effect, system prompt issues
SYMPTOMS: Generic answer unrelated to documents
FIXES:
  - Put most relevant docs at top/bottom of context
  - Reduce number of retrieved docs
  - Stronger instruction to use ONLY provided context

FAILURE: Contradiction between documents
CAUSE: Multiple docs with conflicting info
SYMPTOMS: Confused or hedged answers, or model picks wrong one
FIXES:
  - Include document date/version in metadata
  - Instruct model to prefer newer/authoritative sources
  - Flag conflicts explicitly in the answer
```

---

## 8. TRADEOFFS

### 8.1 Chunk Size vs Quality

```
Small chunks (128-256 tokens):
+ More precise retrieval (specific information)
+ Less noise in context
- Less contextual information per chunk
- More chunks to store and search
- Risk of breaking across sentences

Large chunks (1024-2048 tokens):
+ More context per chunk
+ Better for complex, contextual questions
- Less precise retrieval
- More tokens in LLM context (higher cost)
- Embedding less specific (multi-topic)

Sweet spot: 512 tokens, 50-100 token overlap
```

### 8.2 Number of Retrieved Documents

```
More docs (k=20):
+ Higher recall (less likely to miss relevant info)
- Higher cost (more tokens in context)
- "Lost in the middle" risk
- Slower generation

Fewer docs (k=3-5):
+ Lower cost
+ More focused answers
- Lower recall
- May miss relevant information

Best practice: Retrieve k=20, rerank to k=5
```

---

## 9. EXERCISES

### Exercise 1 — Index Your Documentation
Take any technical documentation (AWS docs, GCP docs, company docs) and:
- Load, chunk, embed, and store in ChromaDB
- Query it with 20 questions
- Measure retrieval accuracy manually (did you get relevant chunks?)

### Exercise 2 — Chunking Strategy Comparison
Take a 50-page PDF. Apply 4 different chunking strategies. For 10 test questions:
- Measure retrieval hit rate (correct chunk in top-5)
- Measure answer quality (manual 1-5 rating)
- Which strategy wins?

### Exercise 3 — RAG Evaluation Pipeline
Build an automated evaluation pipeline that:
- Tests 50 question-answer pairs
- Computes faithfulness, relevancy, and precision
- Generates a quality report
- Alerts when scores drop below threshold

### Exercise 4 — RAG API
Build a FastAPI service that:
- Accepts document URLs or file uploads
- Indexes documents asynchronously
- Supports querying with metadata filters
- Returns answers with citations
- Tracks usage metrics

---

## 10. INTERVIEW QUESTIONS

**Q: Walk me through the complete flow of a RAG query from user input to final answer.**
A: When a user submits a question: (1) Query pre-processing — optionally rewrite or expand the query for better retrieval. (2) Query embedding — convert the query text to a vector using the same embedding model used during indexing. (3) ANN search — query the vector database for the top-k most similar document chunks. (4) Optional reranking — use a cross-encoder to rerank the top-k results for higher precision. (5) Prompt construction — inject retrieved chunks into the prompt as context, with the question appended. (6) LLM generation — the model reads the question + context and generates a grounded answer. (7) Citation extraction — identify which sources were used in the answer. (8) Response formatting — format for the end user with sources, confidence scores, etc.

**Q: What is the "lost in the middle" problem and how does it affect RAG?**
A: Research shows that LLMs pay more attention to content at the beginning and end of their context window than content in the middle. For RAG, this means if you have 10 retrieved documents, the model may ignore documents in positions 3-8. Mitigation strategies: (1) Place the most relevant document first, (2) Use fewer but more relevant documents, (3) Rerank documents and place highest-scored ones at position 1 and last, (4) Use "lost in the middle" reordering to alternate between beginning and end positions, (5) Use models with better long-context handling.

**Q: How would you evaluate a RAG system in production?**
A: Multi-layer evaluation: Offline metrics — faithfulness (is answer grounded in retrieved text), context precision (are retrieved docs relevant), context recall (did we retrieve all needed info), answer relevancy (does answer address question). Online metrics — user satisfaction (thumbs up/down), answer acceptance rate, time-to-answer, retrieval latency, LLM generation latency. Test data — create a golden test set of 100+ question-answer pairs. Run the RAG system on these and compare against ground truth. For faithfulness, use an LLM judge. For retrieval, measure whether the correct document appears in top-k. Run evaluations before deployment and on a regular schedule (weekly) to catch regression.

---

*Next: [Module 06 — Advanced RAG & System Design →](06_rag_advanced_and_system_design.md)*
