# Module 08 — LangChain Core

> LangChain is the most widely used framework for building LLM applications. This module covers the modern LCEL-based architecture — not the legacy chain classes.

---

## Table of Contents

1. [LangChain Architecture Overview](#1-langchain-architecture-overview)
2. [LCEL — LangChain Expression Language](#2-lcel--langchain-expression-language)
3. [Core Primitives — Runnables](#3-core-primitives--runnables)
4. [Chat Models and Prompts](#4-chat-models-and-prompts)
5. [Output Parsers](#5-output-parsers)
6. [Document Loaders](#6-document-loaders)
7. [Text Splitters](#7-text-splitters)
8. [Retrievers](#8-retrievers)
9. [Memory and History](#9-memory-and-history)
10. [Callbacks and Streaming](#10-callbacks-and-streaming)
11. [Building a Complete RAG Chain with LCEL](#11-building-a-complete-rag-chain-with-lcel)
12. [Common Patterns and Anti-Patterns](#12-common-patterns-and-anti-patterns)
13. [Interview Questions](#13-interview-questions)

---

## 1. LangChain Architecture Overview

LangChain is a framework with three tiers:

```
langchain-core        — Base abstractions: Runnables, BaseMessage, BaseLLM
langchain             — Chains, agents, memory (uses core + community)
langchain-community   — Third-party integrations (hundreds of loaders, vectorstores, LLMs)
langchain-openai      — OpenAI-specific (GPT-4o, embeddings)
langchain-anthropic   — Claude-specific
langgraph             — Stateful agent workflows (covered in Module 09)
langsmith             — Observability and evaluation (covered in Module 10)
```

### Package Installation

```bash
pip install langchain langchain-openai langchain-community
pip install langchain-anthropic  # for Claude
pip install chromadb faiss-cpu   # vector stores
pip install pypdf unstructured   # document loaders
```

### The LCEL Philosophy

LangChain Expression Language (LCEL) is the modern way to build LangChain applications. It replaces legacy classes (`LLMChain`, `RetrievalQA`, etc.) with a composable pipe-operator syntax:

```python
# Legacy (avoid)
from langchain.chains import LLMChain, RetrievalQA

# Modern LCEL
chain = prompt | llm | output_parser
rag_chain = {"context": retriever, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser()
```

---

## 2. LCEL — LangChain Expression Language

### The Pipe Operator

Every LCEL component implements `Runnable`. The `|` operator chains them: output of left becomes input of right.

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_template("Tell me a fact about {topic}.")
parser = StrOutputParser()

# LCEL chain
chain = prompt | llm | parser

# Invoke
result = chain.invoke({"topic": "black holes"})
print(result)  # "Black holes have such intense gravity that..."

# Stream
for chunk in chain.stream({"topic": "black holes"}):
    print(chunk, end="", flush=True)

# Batch (parallel)
results = chain.batch([
    {"topic": "black holes"},
    {"topic": "quantum computing"},
    {"topic": "CRISPR"},
])

# Async
import asyncio
result = asyncio.run(chain.ainvoke({"topic": "black holes"}))
```

### Every Runnable Has the Same Interface

```python
# All Runnables support:
runnable.invoke(input)           # single, sync
runnable.ainvoke(input)          # single, async
runnable.stream(input)           # streaming, sync
runnable.astream(input)          # streaming, async
runnable.batch(inputs)           # parallel, sync
runnable.abatch(inputs)          # parallel, async
runnable.get_input_schema()      # Pydantic schema for input
runnable.get_output_schema()     # Pydantic schema for output
runnable.with_config(...)        # Override config (callbacks, tags, etc.)
runnable.with_retry(...)         # Add retry logic
runnable.with_fallbacks(...)     # Add fallbacks
```

---

## 3. Core Primitives — Runnables

### RunnablePassthrough

Passes input through unchanged. Used to preserve original values in parallel branches.

```python
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda

# Simple passthrough
passthrough = RunnablePassthrough()
result = passthrough.invoke({"question": "What is RAG?"})
# Returns: {"question": "What is RAG?"}

# Passthrough with additional key
result = RunnablePassthrough.assign(
    extra_field=lambda x: x["question"].upper()
).invoke({"question": "What is RAG?"})
# Returns: {"question": "What is RAG?", "extra_field": "WHAT IS RAG?"}
```

### RunnableParallel

Runs multiple runnables in parallel, merges outputs into a dict.

```python
from langchain_core.runnables import RunnableParallel

# Run two LLM calls in parallel
parallel_chain = RunnableParallel(
    joke=prompt_joke | llm | StrOutputParser(),
    fact=prompt_fact | llm | StrOutputParser(),
)
result = parallel_chain.invoke({"topic": "penguins"})
# Returns: {"joke": "...", "fact": "..."}

# Classic RAG setup
rag_setup = RunnableParallel(
    context=retriever,
    question=RunnablePassthrough()
)
rag_chain = rag_setup | qa_prompt | llm | StrOutputParser()
```

### RunnableLambda

Wraps any Python function as a Runnable.

```python
from langchain_core.runnables import RunnableLambda

def preprocess(text: str) -> str:
    return text.strip().lower()

def postprocess(text: str) -> dict:
    return {"answer": text, "length": len(text)}

chain = (
    RunnableLambda(preprocess)
    | prompt
    | llm
    | StrOutputParser()
    | RunnableLambda(postprocess)
)

result = chain.invoke("  What is quantum computing?  ")
# {"answer": "Quantum computing uses...", "length": 450}
```

### RunnableBranch

Conditional routing based on input.

```python
from langchain_core.runnables import RunnableBranch

router = RunnableBranch(
    # (condition, runnable)
    (lambda x: "code" in x["question"].lower(), code_chain),
    (lambda x: "math" in x["question"].lower(), math_chain),
    # Default (no condition)
    general_chain
)

result = router.invoke({"question": "Can you write code for sorting?"})
# Routes to code_chain
```

### with_retry and with_fallbacks

```python
# Retry on transient failures
robust_llm = llm.with_retry(
    stop_after_attempt=3,
    wait_exponential_jitter=True,
    retry_if_exception_type=(Exception,)
)

# Fallback to cheaper model if primary fails
fallback_chain = (
    ChatOpenAI(model="gpt-4o", temperature=0)
    .with_fallbacks([ChatOpenAI(model="gpt-4o-mini", temperature=0)])
)

chain = prompt | fallback_chain | StrOutputParser()
```

---

## 4. Chat Models and Prompts

### ChatPromptTemplate

```python
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# From template strings (most common)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant specializing in {domain}."),
    MessagesPlaceholder(variable_name="history"),  # For conversation history
    ("human", "{question}"),
])

# Format and inspect
formatted = prompt.format_messages(
    domain="data engineering",
    history=[
        HumanMessage(content="Hi"),
        AIMessage(content="Hello! How can I help?")
    ],
    question="What is Apache Spark?"
)
print(formatted)

# From template with f-string-style
simple_prompt = ChatPromptTemplate.from_template(
    "Summarize the following text in {num_sentences} sentences:\n\n{text}"
)
```

### FewShotChatMessagePromptTemplate

```python
from langchain_core.prompts import FewShotChatMessagePromptTemplate

examples = [
    {"input": "2+2", "output": "4"},
    {"input": "2+3", "output": "5"},
]

example_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}"),
])

few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=examples,
)

final_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a math assistant."),
    few_shot_prompt,
    ("human", "{input}"),
])
```

### Model Configuration

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# OpenAI
gpt4o = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
    max_tokens=2000,
    timeout=30,
    max_retries=3,
    # Structured output
    # model_kwargs={"response_format": {"type": "json_object"}}
)

# Bind stop sequences
llm_with_stop = gpt4o.bind(stop=["END"])

# Bind tools
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Sunny, 25°C in {city}"

llm_with_tools = gpt4o.bind_tools([get_weather])

# Claude
claude = ChatAnthropic(
    model="claude-sonnet-4-5",
    temperature=0,
    max_tokens=2000,
)
```

---

## 5. Output Parsers

### StrOutputParser

```python
from langchain_core.output_parsers import StrOutputParser

parser = StrOutputParser()
chain = prompt | llm | parser
# Returns plain string
```

### PydanticOutputParser

```python
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class ExtractedEntity(BaseModel):
    name: str = Field(description="Entity name")
    type: str = Field(description="Entity type: PERSON, ORG, or LOCATION")
    context: str = Field(description="Brief context about the entity")

class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    summary: str

parser = PydanticOutputParser(pydantic_object=ExtractionResult)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Extract entities from the text.\n\n{format_instructions}"),
    ("human", "{text}"),
]).partial(format_instructions=parser.get_format_instructions())

chain = prompt | llm | parser
result = chain.invoke({"text": "Apple CEO Tim Cook announced..."})
# Returns ExtractionResult with structured entities
```

### JsonOutputParser

```python
from langchain_core.output_parsers import JsonOutputParser

parser = JsonOutputParser()
# Works with llm configured for JSON output
chain = prompt | llm.bind(response_format={"type": "json_object"}) | parser
```

### With Structured Output (Recommended for OpenAI)

```python
from pydantic import BaseModel

class Article(BaseModel):
    title: str
    summary: str
    key_points: list[str]
    sentiment: str

# Uses OpenAI's structured output API directly
structured_llm = ChatOpenAI(model="gpt-4o-mini").with_structured_output(Article)
chain = prompt | structured_llm
result = chain.invoke({"text": "..."})
# Returns Article instance, guaranteed
```

---

## 6. Document Loaders

Document loaders handle ingestion of various file types into LangChain's `Document` objects.

```python
from langchain_core.documents import Document

# Document has: page_content (str) + metadata (dict)
doc = Document(
    page_content="The text content here",
    metadata={"source": "wiki", "page": 1, "author": "John"}
)
```

### PDF Loader

```python
from langchain_community.document_loaders import PyPDFLoader, PDFMinerLoader

# PyPDFLoader — page-by-page
loader = PyPDFLoader("financial_report.pdf")
pages = loader.load()  # List[Document], one per page

# Lazy loading (memory efficient for large PDFs)
for page in loader.lazy_load():
    process(page)

# PDFMiner — better text extraction
loader = PDFMinerLoader("report.pdf")
docs = loader.load()
```

### Web and URL Loaders

```python
from langchain_community.document_loaders import WebBaseLoader, RecursiveUrlLoader
import bs4

# Single URL
loader = WebBaseLoader(
    web_paths=["https://example.com/page"],
    bs_kwargs={"parse_only": bs4.SoupStrainer("article")}  # CSS selector
)
docs = loader.load()

# Recursive URL (crawl entire site)
loader = RecursiveUrlLoader(
    url="https://docs.example.com",
    max_depth=3,
    extractor=lambda x: bs4.BeautifulSoup(x, "html.parser").get_text()
)
docs = loader.load()
```

### Directory Loader

```python
from langchain_community.document_loaders import DirectoryLoader, TextLoader

# Load all .txt files in directory
loader = DirectoryLoader(
    "./documents/",
    glob="**/*.txt",
    loader_cls=TextLoader,
    show_progress=True,
    use_multithreading=True,
    max_concurrency=8,
)
docs = loader.load()

# Mixed file types
from langchain_community.document_loaders import UnstructuredFileLoader

loader = DirectoryLoader(
    "./documents/",
    glob="**/*",
    loader_cls=UnstructuredFileLoader,
)
docs = loader.load()
```

### Database Loaders

```python
from langchain_community.document_loaders import BigQueryLoader, PostgresLoader

# BigQuery
loader = BigQueryLoader(
    query="SELECT content, source, created_at FROM my_dataset.documents",
    page_content_columns=["content"],
    metadata_columns=["source", "created_at"],
    project="my-gcp-project",
)
docs = loader.load()
```

### Custom Loader

```python
from langchain_core.document_loaders import BaseLoader
from typing import Iterator

class CustomAPILoader(BaseLoader):
    """Load documents from a custom API."""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
    def lazy_load(self) -> Iterator[Document]:
        import requests
        resp = requests.get(self.api_url, headers={"Authorization": f"Bearer {self.api_key}"})
        for item in resp.json()["items"]:
            yield Document(
                page_content=item["text"],
                metadata={"id": item["id"], "source": self.api_url}
            )
    
    def load(self) -> list[Document]:
        return list(self.lazy_load())
```

---

## 7. Text Splitters

### RecursiveCharacterTextSplitter (Default Choice)

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""],
    # ^ Tries each separator in order, falls back to next
)

docs = splitter.split_documents(loaded_docs)
# or
chunks = splitter.create_documents(
    texts=["Long text here..."],
    metadatas=[{"source": "my_doc"}]
)
```

### Code-Aware Splitter

```python
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

python_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON,
    chunk_size=2000,
    chunk_overlap=200,
)
# Splits on class definitions, functions, etc. — not mid-code

code_docs = python_splitter.create_documents([python_source_code])
```

### Token-Based Splitter

```python
from langchain_text_splitters import TokenTextSplitter

# Split by actual tokens (not characters)
splitter = TokenTextSplitter(
    encoding_name="cl100k_base",  # GPT-4 tokenizer
    chunk_size=512,
    chunk_overlap=50,
)
docs = splitter.split_documents(loaded_docs)
```

### Markdown-Aware Splitter

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
md_docs = splitter.split_text(markdown_content)
# Each chunk gets header hierarchy as metadata
# {"Header 1": "Architecture", "Header 2": "Components"}
```

### Semantic Splitter (High Quality, Slower)

```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

splitter = SemanticChunker(
    embeddings=embeddings,
    breakpoint_threshold_type="percentile",  # or "standard_deviation"
    breakpoint_threshold_amount=95,
)

docs = splitter.create_documents([long_document_text])
```

---

## 8. Retrievers

Retrievers in LangChain have a single interface: `get_relevant_documents(query)` → `List[Document]`.

### VectorStore Retriever

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Build vectorstore from documents
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

# Basic retriever
retriever = vectorstore.as_retriever(
    search_type="similarity",  # or "mmr" or "similarity_score_threshold"
    search_kwargs={"k": 5}
)

# MMR (Maximal Marginal Relevance) — reduces redundancy
retriever_mmr = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
)

# Score threshold — filter by minimum similarity
retriever_threshold = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.7, "k": 5}
)

# Use retriever
docs = retriever.invoke("What is HNSW indexing?")
```

### MultiQueryRetriever

Generates multiple query variants, retrieves for each, deduplicates.

```python
from langchain.retrievers.multi_query import MultiQueryRetriever

multi_query_retriever = MultiQueryRetriever.from_llm(
    retriever=base_retriever,
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
)

docs = multi_query_retriever.invoke("how to make RAG faster?")
# Internally generates: ["RAG optimization techniques", "Reducing RAG latency", ...]
# Retrieves and deduplicates
```

### ContextualCompressionRetriever

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

compressor = LLMChainExtractor.from_llm(
    llm=ChatOpenAI(model="gpt-4o-mini")
)

compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=base_retriever,
)

docs = compression_retriever.invoke("What is HNSW?")
# Returns only relevant excerpts from retrieved docs
```

### EnsembleRetriever (Hybrid)

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

bm25_retriever = BM25Retriever.from_documents(chunks)
bm25_retriever.k = 5

dense_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# Combine with weights
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, dense_retriever],
    weights=[0.4, 0.6],  # BM25 40%, Dense 60%
)

docs = ensemble_retriever.invoke("HNSW graph algorithm")
```

### SelfQueryRetriever

Translates natural language into structured metadata filters.

```python
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo

metadata_field_info = [
    AttributeInfo(
        name="category",
        description="Category of the document: technical, business, legal",
        type="string",
    ),
    AttributeInfo(
        name="year",
        description="Year the document was published",
        type="integer",
    ),
]

self_query_retriever = SelfQueryRetriever.from_llm(
    llm=ChatOpenAI(model="gpt-4o"),
    vectorstore=vectorstore,
    document_contents="Technical documentation",
    metadata_field_info=metadata_field_info,
)

# Automatically translates to filter
docs = self_query_retriever.invoke("technical documents from 2023")
# filter={"category": "technical", "year": 2023}
```

---

## 9. Memory and History

### ChatMessageHistory

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# In-memory store per session
store: dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# Build conversational chain
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | llm | StrOutputParser()

# Wrap with history management
chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

# Use with session ID
config = {"configurable": {"session_id": "user_123"}}
response1 = chain_with_history.invoke({"input": "My name is Viru"}, config=config)
response2 = chain_with_history.invoke({"input": "What's my name?"}, config=config)
# response2 will know the name is Viru
```

### Redis-Backed History (Production)

```python
from langchain_community.chat_message_histories import RedisChatMessageHistory

def get_redis_history(session_id: str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(
        session_id=session_id,
        url="redis://localhost:6379",
        ttl=3600,  # 1-hour expiry
        key_prefix="chat_history:"
    )

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_redis_history,
    input_messages_key="input",
    history_messages_key="history",
)
```

### Managing Context Window with Trimming

```python
from langchain_core.messages import trim_messages, SystemMessage

# Trim messages to fit in context window
trimmer = trim_messages(
    max_tokens=2000,
    strategy="last",       # Keep most recent
    token_counter=llm,     # Use LLM's tokenizer
    include_system=True,   # Always keep system message
    allow_partial=False,
    start_on="human",      # Always start with human message
)

# Add to chain
chain = (
    RunnablePassthrough.assign(history=lambda x: trimmer.invoke(x["history"]))
    | prompt
    | llm
    | StrOutputParser()
)
```

---

## 10. Callbacks and Streaming

### Custom Callback Handler

```python
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from typing import Any, Union

class MetricsCallbackHandler(BaseCallbackHandler):
    """Collect metrics during chain execution."""
    
    def __init__(self):
        self.llm_calls = 0
        self.total_tokens = 0
        self.errors = 0
    
    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs):
        self.llm_calls += 1
    
    def on_llm_end(self, response: LLMResult, **kwargs):
        for generation in response.generations:
            for gen in generation:
                if hasattr(gen, "generation_info") and gen.generation_info:
                    usage = gen.generation_info.get("token_usage", {})
                    self.total_tokens += usage.get("total_tokens", 0)
    
    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs):
        self.errors += 1
    
    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs):
        pass
    
    def on_chain_end(self, outputs: dict, **kwargs):
        pass
    
    def on_retriever_start(self, serialized: dict, query: str, **kwargs):
        print(f"Retrieving for: {query[:50]}")
    
    def on_retriever_end(self, documents: list, **kwargs):
        print(f"Retrieved {len(documents)} documents")

# Use callback
metrics = MetricsCallbackHandler()
chain = prompt | llm | StrOutputParser()
result = chain.invoke({"topic": "RAG"}, config={"callbacks": [metrics]})
print(f"LLM calls: {metrics.llm_calls}, Tokens: {metrics.total_tokens}")
```

### Streaming with FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig

app = FastAPI()

@app.post("/chat/stream")
async def stream_chat(request: dict):
    chain = prompt | llm | StrOutputParser()
    
    async def generate():
        async for chunk in chain.astream(
            {"question": request["question"]},
            config=RunnableConfig(tags=["streaming"])
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### astream_events (Token + Metadata Streaming)

```python
# Stream individual tokens AND metadata about chain steps
async def stream_with_events(query: str):
    async for event in chain.astream_events(
        {"question": query},
        version="v2"
    ):
        event_type = event["event"]
        
        if event_type == "on_llm_stream":
            # Individual token
            chunk = event["data"]["chunk"].content
            if chunk:
                print(chunk, end="", flush=True)
        
        elif event_type == "on_retriever_end":
            # Retrieval completed
            docs = event["data"]["output"]
            print(f"\n[Retrieved {len(docs)} docs]")
        
        elif event_type == "on_chain_end":
            # Full chain completed
            print("\n[Chain completed]")
```

---

## 11. Building a Complete RAG Chain with LCEL

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
import operator
from typing import List

# ── 1. Ingestion Pipeline ─────────────────────────────────────────────
def build_vectorstore(pdf_path: str) -> Chroma:
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200
    )
    chunks = splitter.split_documents(docs)
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma.from_documents(chunks, embeddings, persist_directory="./chroma")


# ── 2. Retrieval Chain ────────────────────────────────────────────────
def build_rag_chain(vectorstore: Chroma):
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 20}
    )
    
    # Format documents into string with source citations
    def format_docs(docs: List[Document]) -> str:
        return "\n\n".join(
            f"[Source {i+1}: {doc.metadata.get('source', 'unknown')}, "
            f"p.{doc.metadata.get('page', '?')}]\n{doc.page_content}"
            for i, doc in enumerate(docs)
        )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant. Answer questions using ONLY the provided context.
If the context doesn't contain enough information, say "I don't have enough information to answer that."
Cite specific sources using [Source N] notation."""),
        ("human", "Context:\n{context}\n\nQuestion: {question}")
    ])
    
    # Full RAG chain with LCEL
    rag_chain = (
        RunnableParallel(
            context=(retriever | RunnableLambda(format_docs)),
            question=RunnablePassthrough(),
        )
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain


# ── 3. Conversational RAG Chain ────────────────────────────────────────
def build_conversational_rag_chain(vectorstore: Chroma):
    """RAG with conversation history — condenses follow-up questions."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    # Step 1: Condense the question with history
    condense_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        ("human", "Given the conversation above, generate a standalone search query "
                  "that captures what the user is asking. Return ONLY the query.")
    ])
    
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, condense_prompt
    )
    
    # Step 2: Answer with retrieved context
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer using the context:\n\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)
    
    # Wrap with history
    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )
    
    return chain_with_history
```

---

## 12. Common Patterns and Anti-Patterns

### Patterns

```python
# Pattern 1: Add input validation
from pydantic import BaseModel, validator

class QueryInput(BaseModel):
    question: str
    max_length: int = 500
    
    @validator("question")
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()

# Pattern 2: Trace chain execution
chain_with_tags = chain.with_config({"tags": ["production", "v2"], "run_name": "MyChain"})

# Pattern 3: Per-request configuration
chain.invoke(
    {"question": "What is RAG?"},
    config={"run_name": "user_query", "tags": ["user_123"]}
)

# Pattern 4: Parallel retrieval across multiple vectorstores
multi_store_retrieval = RunnableParallel(
    internal_docs=internal_retriever,
    public_docs=public_retriever,
).with_config({"max_concurrency": 2})

# Pattern 5: Graceful degradation
safe_chain = chain.with_fallbacks(
    [fallback_chain],
    exceptions_to_handle=(Exception,)
)
```

### Anti-Patterns

```python
# ❌ ANTI-PATTERN: Legacy chain classes
from langchain.chains import LLMChain  # Avoid in new code
chain = LLMChain(llm=llm, prompt=prompt)  # Use LCEL instead

# ❌ ANTI-PATTERN: Blocking async LLM calls in sync context
result = asyncio.run(chain.ainvoke(input))  # Fine in scripts
# In FastAPI: use await, don't use asyncio.run()

# ❌ ANTI-PATTERN: Storing secrets in prompts
prompt = ChatPromptTemplate.from_template(
    f"API key is {os.environ['API_KEY']}..."  # Never!
)

# ❌ ANTI-PATTERN: Not handling retrieval failures
docs = retriever.invoke(query)  # What if vectorstore is down?
# ✅ Wrap with try/except and return empty list with error message

# ❌ ANTI-PATTERN: No token budget management
chain = retriever | (lambda docs: "\n".join([d.page_content for d in docs])) | llm
# If 50 docs retrieved, context explodes. Use k=5 and max_chars limit.
```

---

## 13. Interview Questions

**Q1: What is LCEL and why is it preferred over legacy LangChain chains?**

LCEL is LangChain Expression Language — a declarative, composable way to build chains using the pipe operator. It's preferred because: (1) every component implements the same Runnable interface — consistent invoke/stream/batch/async API; (2) streaming works automatically through any chain composition; (3) parallelism is first-class via RunnableParallel; (4) retry/fallback logic is composable; (5) LangSmith observability integrates automatically. Legacy chains like LLMChain are still functional but LCEL is significantly more flexible.

**Q2: How does RunnableParallel work and when would you use it?**

RunnableParallel runs multiple runnables concurrently and merges their outputs into a dict. Use cases: (1) Classic RAG — run retriever and passthrough simultaneously; (2) Multi-aspect analysis — call LLM twice for different perspectives in parallel; (3) Multi-vectorstore retrieval — query multiple stores simultaneously. Under the hood, RunnableParallel uses threading for sync execution and asyncio.gather for async.

**Q3: What's the difference between EnsembleRetriever and MultiQueryRetriever?**

EnsembleRetriever combines results from multiple different retrieval methods (e.g., BM25 + dense) — it solves the query-method diversity problem. MultiQueryRetriever uses a single retrieval method but generates multiple query phrasings — it solves the query-formulation problem. They're complementary: you can use MultiQueryRetriever where each variant calls an EnsembleRetriever underneath.

**Q4: How would you implement a production-ready conversational RAG with LangChain?**

Three components: (1) history-aware retriever — condenses conversation history + current question into standalone search query using LLM; (2) QA chain — answers using retrieved context + history via stuff_documents pattern; (3) RunnableWithMessageHistory — manages session storage per user, supports Redis/Postgres backends. Critical production details: trim history at context limit, invalidate cache on new messages, track token usage per session.

---

*Next: Module 09 — LangGraph Stateful Workflows*
