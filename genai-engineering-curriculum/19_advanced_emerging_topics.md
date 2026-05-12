# Module 19 — Advanced and Emerging Topics

> The frontier of AI engineering. This module covers protocols and patterns that are production-ready today and will dominate the field in the next 2-3 years.

---

## Table of Contents

1. [Model Context Protocol (MCP)](#1-model-context-protocol-mcp)
2. [Browser and Computer-Use Agents](#2-browser-and-computer-use-agents)
3. [Graph RAG — Deep Dive](#3-graph-rag)
4. [Multimodal AI Engineering](#4-multimodal-ai-engineering)
5. [AI Gateway Patterns](#5-ai-gateway-patterns)
6. [Long Context Engineering](#6-long-context-engineering)
7. [Reasoning Models](#7-reasoning-models)
8. [Mixture of Experts (MoE)](#8-mixture-of-experts)
9. [On-Device AI (Edge Inference)](#9-on-device-ai)
10. [Future Trends and Architecture Evolution](#10-future-trends)
11. [Interview Questions](#11-interview-questions)

---

## 1. Model Context Protocol (MCP)

MCP is an open standard by Anthropic that allows LLMs to connect to external data sources and tools through a standardized protocol — analogous to USB for AI tools.

### Core Concepts

```
MCP Architecture:
  
  Host (Claude, ChatGPT)     Server (your service)
  ┌─────────────────────┐    ┌─────────────────────┐
  │                     │    │                     │
  │  MCP Client         │◄──►│  MCP Server         │
  │  (built into host)  │    │  - Resources (data) │
  │                     │    │  - Tools (actions)  │
  └─────────────────────┘    │  - Prompts          │
                             └─────────────────────┘

Key entities:
- Resources: Read-only data (files, DB rows, API data)
- Tools: Functions the LLM can call (create, update, delete)
- Prompts: Reusable prompt templates
```

### Building an MCP Server

```python
from mcp import Server, types
from mcp.server.stdio import stdio_server
import asyncio

app = Server("my-data-server")

# Expose resources (read-only data)
@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="data://products/all",
            name="Product Catalog",
            description="Full product catalog with pricing",
            mimeType="application/json",
        ),
        types.Resource(
            uri="data://orders/{order_id}",
            name="Order Details",
            description="Details for a specific order",
        ),
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "data://products/all":
        products = await db.fetch_all("SELECT * FROM products")
        return json.dumps([dict(p) for p in products])
    
    if uri.startswith("data://orders/"):
        order_id = uri.split("/")[-1]
        order = await db.fetch_one("SELECT * FROM orders WHERE id = $1", order_id)
        return json.dumps(dict(order)) if order else "Order not found"
    
    raise ValueError(f"Unknown resource: {uri}")

# Expose tools (actions the LLM can take)
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_order",
            description="Create a new customer order",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer UUID"},
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "quantity": {"type": "integer", "minimum": 1},
                },
                "required": ["customer_id", "product_id", "quantity"],
            },
        ),
        types.Tool(
            name="update_inventory",
            description="Update product inventory count",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "delta": {"type": "integer", "description": "Change in inventory (positive = add, negative = remove)"},
                },
                "required": ["product_id", "delta"],
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "create_order":
        order_id = await db.execute(
            "INSERT INTO orders (customer_id, product_id, quantity) VALUES ($1, $2, $3) RETURNING id",
            arguments["customer_id"], arguments["product_id"], arguments["quantity"]
        )
        return [types.TextContent(type="text", text=f"Order created: {order_id}")]
    
    if name == "update_inventory":
        await db.execute(
            "UPDATE products SET inventory = inventory + $2 WHERE id = $1",
            arguments["product_id"], arguments["delta"]
        )
        return [types.TextContent(type="text", text="Inventory updated")]
    
    raise ValueError(f"Unknown tool: {name}")

# Run server
async def main():
    async with stdio_server() as streams:
        await app.run(*streams, app.create_initialization_options())

asyncio.run(main())
```

### MCP Client Integration

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_mcp_server():
    """Connect to an MCP server and use its tools."""
    server_params = StdioServerParameters(
        command="python",
        args=["my_mcp_server.py"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools_response = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools_response.tools]}")
            
            # Call a tool
            result = await session.call_tool(
                "create_order",
                arguments={"customer_id": "cust_123", "product_id": "prod_456", "quantity": 2}
            )
            print(f"Tool result: {result.content[0].text}")
            
            # Read a resource
            resource = await session.read_resource("data://products/all")
            print(f"Products: {resource.contents[0].text[:200]}")
```

### MCP in Production Patterns

```python
# Using MCP tools with Claude via Anthropic API
import anthropic
import json

client = anthropic.Anthropic()

# Define MCP-sourced tools in API format
tools = [
    {
        "name": "get_customer_orders",
        "description": "Get all orders for a customer",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"]
        }
    }
]

messages = [{"role": "user", "content": "What are the recent orders for customer C-123?"}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )
    
    if response.stop_reason == "tool_use":
        # Execute tool call via MCP
        tool_use = next(b for b in response.content if b.type == "tool_use")
        result = await execute_mcp_tool(tool_use.name, tool_use.input)
        
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": result}]
        })
    else:
        print(response.content[0].text)
        break
```

---

## 2. Browser and Computer-Use Agents

### Computer Use API (Anthropic)

```python
import anthropic
import base64
from PIL import ImageGrab

client = anthropic.Anthropic()

def take_screenshot() -> str:
    """Capture screen and return as base64."""
    screenshot = ImageGrab.grab()
    import io
    buffer = io.BytesIO()
    screenshot.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

async def computer_use_agent(task: str):
    """Agent that can see and interact with the computer."""
    
    tools = [
        {
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": 1920,
            "display_height_px": 1080,
        },
        {
            "type": "bash_20241022",
            "name": "bash",
        },
        {
            "type": "text_editor_20241022",
            "name": "str_replace_editor",
        }
    ]
    
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": take_screenshot()}
            },
            {"type": "text", "text": task}
        ]
    }]
    
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            tools=tools,
            messages=messages,
            betas=["computer-use-2024-10-22"],
        )
        
        if response.stop_reason == "end_turn":
            break
        
        # Execute computer actions
        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "computer":
                action = block.input["action"]
                result = await execute_computer_action(action, block.input)
                
                # Take new screenshot after action
                new_screenshot = take_screenshot()
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": new_screenshot}}
                    ]
                })
        
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
```

### Browser Agent with Playwright

```python
from playwright.async_api import async_playwright
import base64

class BrowserAgent:
    """Agent that controls a real browser via Playwright."""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def start(self, headless: bool = True):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
    
    async def screenshot_b64(self) -> str:
        img_bytes = await self.page.screenshot(type="png")
        return base64.b64encode(img_bytes).decode()
    
    async def navigate(self, url: str):
        await self.page.goto(url, wait_until="networkidle")
    
    async def click(self, x: int, y: int):
        await self.page.mouse.click(x, y)
    
    async def type_text(self, text: str):
        await self.page.keyboard.type(text)
    
    async def get_page_text(self) -> str:
        return await self.page.evaluate("document.body.innerText")
    
    async def run_task(self, task: str) -> str:
        """Run a browser automation task using LLM for decision making."""
        messages = [{"role": "user", "content": task}]
        
        for step in range(20):  # Max 20 steps
            screenshot = await self.screenshot_b64()
            page_text = await self.get_page_text()
            
            response = await llm.ainvoke([
                SystemMessage(content="""You are a browser automation agent.
Decide the next action:
- navigate(url): Go to URL
- click(x, y): Click coordinates
- type(text): Type text
- extract: Extract the needed information (final step)
Return JSON: {"action": "...", "params": {...}}"""),
                HumanMessage(content=[
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot}"}},
                    {"type": "text", "text": f"Task: {task}\nPage text preview:\n{page_text[:1000]}"}
                ])
            ])
            
            import json
            decision = json.loads(response.content)
            
            if decision["action"] == "navigate":
                await self.navigate(decision["params"]["url"])
            elif decision["action"] == "click":
                await self.click(decision["params"]["x"], decision["params"]["y"])
            elif decision["action"] == "type":
                await self.type_text(decision["params"]["text"])
            elif decision["action"] == "extract":
                return decision["params"].get("result", page_text[:2000])
        
        return "Task incomplete after maximum steps"
```

---

## 3. Graph RAG

Graph RAG enriches retrieval by building a knowledge graph from documents and using it to answer questions that require multi-hop reasoning.

### When Graph RAG Beats Standard RAG

```
Standard RAG fails at:
- Multi-hop questions: "Who is the CEO of the company that acquired Slack?"
- Relationship queries: "Which engineers worked on both Project X and Project Y?"
- Aggregation across entities: "What are all the products in the Cloud category?"
- Temporal reasoning: "How did the company's strategy change after 2020?"

Graph RAG excels at all of the above.
```

### Graph Construction

```python
from langchain_community.graphs import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

# Initialize Neo4j graph
graph = Neo4jGraph(
    url="bolt://localhost:7687",
    username="neo4j",
    password="password",
)

# Convert documents to graph entities
llm = ChatOpenAI(model="gpt-4o", temperature=0)
transformer = LLMGraphTransformer(
    llm=llm,
    allowed_nodes=["Person", "Organization", "Product", "Technology", "Location"],
    allowed_relationships=["WORKS_AT", "ACQUIRED", "USES", "LOCATED_IN", "DEVELOPED_BY"],
    node_properties=["name", "description", "date_founded"],
    relationship_properties=["since", "role"],
)

# Transform documents into graph
documents = [
    Document(page_content="Anthropic was founded by Dario Amodei and Daniela Amodei in 2021. It developed Claude."),
    Document(page_content="Claude is an AI assistant developed by Anthropic. It uses Constitutional AI."),
]

graph_documents = await transformer.aconvert_to_graph_documents(documents)

# Add to Neo4j
graph.add_graph_documents(
    graph_documents,
    baseEntityLabel=True,
    include_source=True
)

# Inspect graph schema
print(graph.get_schema)
```

### Graph-Augmented RAG Pipeline

```python
from langchain.chains import GraphCypherQAChain
from langchain_community.vectorstores import Neo4jVector

# Vector + Graph hybrid retrieval
class GraphRAG:
    def __init__(self, graph: Neo4jGraph, llm):
        self.graph = graph
        self.llm = llm
        
        # Vector index on graph nodes
        self.vector_index = Neo4jVector.from_existing_graph(
            embedding=OpenAIEmbeddings(),
            graph=graph,
            node_label="Document",
            text_node_properties=["text"],
            embedding_node_property="embedding",
        )
        
        # Cypher generation chain
        self.cypher_chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            return_intermediate_steps=True,
        )
    
    async def query(self, question: str) -> dict:
        """Hybrid retrieval: vector search + graph traversal."""
        
        # 1. Vector search for relevant entities
        vector_docs = await self.vector_index.asimilarity_search(question, k=5)
        
        # 2. Graph traversal for relationship queries
        cypher_result = self.cypher_chain.invoke({"query": question})
        graph_context = cypher_result.get("result", "")
        graph_cypher = cypher_result.get("intermediate_steps", [{}])[0].get("query", "")
        
        # 3. Combine and generate
        combined_context = f"""
Vector retrieval results:
{chr(10).join([d.page_content for d in vector_docs])}

Graph query ({graph_cypher}):
{graph_context}"""
        
        response = await self.llm.ainvoke([
            SystemMessage(content="Answer based on both the document excerpts and graph relationships."),
            HumanMessage(content=f"Context:\n{combined_context}\n\nQuestion: {question}")
        ])
        
        return {
            "answer": response.content,
            "vector_sources": len(vector_docs),
            "graph_context": graph_context[:200],
        }

# Manual Cypher for complex queries
def run_graph_query(graph: Neo4jGraph, question: str) -> str:
    """Translate natural language to Cypher and execute."""
    
    schema = graph.get_schema
    cypher_response = llm.invoke([HumanMessage(
        content=f"""Generate a Cypher query for Neo4j to answer this question.
Schema: {schema}
Question: {question}
Return ONLY the Cypher query."""
    )])
    
    cypher = cypher_response.content.strip()
    result = graph.query(cypher)
    return json.dumps(result)

# Example queries
examples = {
    "Who founded Anthropic?": 
        "MATCH (p:Person)-[:FOUNDED]->(o:Organization {{name: 'Anthropic'}}) RETURN p.name",
    
    "What products use Constitutional AI?":
        "MATCH (p:Product)-[:USES]->(t:Technology {{name: 'Constitutional AI'}}) RETURN p.name",
    
    "Who has worked at both OpenAI and Anthropic?":
        """MATCH (p:Person)-[:WORKS_AT|WORKED_AT]->(o1:Organization {{name: 'OpenAI'}})
           MATCH (p)-[:WORKS_AT|WORKED_AT]->(o2:Organization {{name: 'Anthropic'}})
           RETURN p.name""",
}
```

### Graph RAG Architecture (Microsoft's Approach)

```python
# Community detection for global queries
# Based on Microsoft's GraphRAG paper

from sklearn.cluster import KMeans
import numpy as np

class CommunityGraphRAG:
    """
    Two-level approach:
    - Local: vector search on entities
    - Global: community summaries for broad questions
    """
    
    async def build_communities(self, entities: list[dict], n_communities: int = 20):
        """Cluster entities into communities."""
        embeddings = await embed_entities(entities)
        
        kmeans = KMeans(n_clusters=n_communities, random_state=42)
        labels = kmeans.fit_predict(np.array(embeddings))
        
        communities = {}
        for entity, label in zip(entities, labels):
            if label not in communities:
                communities[label] = []
            communities[label].append(entity)
        
        # Generate community summaries
        community_summaries = {}
        for community_id, members in communities.items():
            summary = await self.llm.ainvoke([HumanMessage(
                content=f"Summarize the key entities and relationships in this community:\n"
                        f"{json.dumps(members[:20], indent=2)}"
            )])
            community_summaries[community_id] = summary.content
        
        return community_summaries
    
    async def global_query(self, question: str, community_summaries: dict) -> str:
        """Answer broad questions using community summaries."""
        
        # Score each community's relevance
        relevances = []
        for cid, summary in community_summaries.items():
            score_response = await self.llm.ainvoke([HumanMessage(
                content=f"Score 0-10 relevance of this summary to: '{question}'\n{summary[:300]}\nReturn only a number."
            )])
            try:
                score = float(score_response.content.strip())
                relevances.append((cid, score, summary))
            except Exception:
                pass
        
        # Use top communities
        top_communities = sorted(relevances, key=lambda x: x[1], reverse=True)[:5]
        context = "\n\n".join(s for _, _, s in top_communities)
        
        final = await self.llm.ainvoke([HumanMessage(
            content=f"Based on these community summaries, answer: {question}\n\n{context}"
        )])
        return final.content
```

---

## 4. Multimodal AI Engineering

### Vision + RAG

```python
from langchain_openai import ChatOpenAI
import base64
from PIL import Image
import io

def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

class MultimodalRAG:
    """RAG system that handles both text and images."""
    
    def __init__(self):
        self.vision_llm = ChatOpenAI(model="gpt-4o")
        self.text_llm = ChatOpenAI(model="gpt-4o-mini")
        self.embeddings = OpenAIEmbeddings()
    
    async def index_image(self, image_path: str, metadata: dict) -> str:
        """Generate text description of image for indexing."""
        img_b64 = image_to_base64(image_path)
        
        # Use vision model to describe the image
        description = await self.vision_llm.ainvoke([
            HumanMessage(content=[
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": "Describe this image in detail for search indexing. Include all text, charts, diagrams, and visual elements."}
            ])
        ])
        
        return description.content
    
    async def query_with_image(self, question: str, context_image: bytes = None) -> str:
        """Answer questions using both text context and optional image input."""
        
        # Retrieve text context
        text_docs = await self.retriever.ainvoke(question)
        context = "\n".join([d.page_content for d in text_docs])
        
        # Build multimodal message
        content = [{"type": "text", "text": f"Context:\n{context}\n\nQuestion: {question}"}]
        
        if context_image:
            img_b64 = base64.b64encode(context_image).decode()
            content.insert(0, {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })
        
        response = await self.vision_llm.ainvoke([HumanMessage(content=content)])
        return response.content
```

### Audio Processing

```python
import openai

async def transcribe_audio(audio_file_path: str) -> str:
    """Transcribe audio to text using Whisper."""
    client = openai.AsyncOpenAI()
    
    with open(audio_file_path, "rb") as audio_file:
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
            language="en",  # Speed up with explicit language
        )
    
    return transcript

async def audio_rag_pipeline(audio_input: bytes, question: str) -> str:
    """Full pipeline: audio → transcript → RAG → answer."""
    
    # 1. Transcribe
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        f.write(audio_input)
        transcript = await transcribe_audio(f.name)
    
    # 2. Combine with question
    full_query = f"Audio transcript: {transcript}\n\nQuestion: {question}"
    
    # 3. RAG
    docs = await retriever.ainvoke(full_query)
    context = "\n".join([d.page_content for d in docs])
    
    response = await llm.ainvoke([
        SystemMessage(content="Answer based on the context."),
        HumanMessage(content=f"Context:\n{context}\n\n{full_query}")
    ])
    
    return response.content
```

---

## 5. AI Gateway Patterns

```python
class AIGateway:
    """
    Central gateway for all LLM calls.
    Provides: routing, caching, auth, rate limiting, observability.
    """
    
    def __init__(self):
        self.router = LiteLLMRouter(model_list=[...])
        self.cache = TieredLLMCache(...)
        self.pii_redactor = PIIRedactor()
        self.cost_tracker = CostTracker(daily_budget_usd=1000)
        self.rate_limiter = RateLimiter(max_rpm=1000)
    
    async def complete(
        self,
        messages: list,
        model: str = "auto",
        user_id: str = "",
        feature: str = "",
        bypass_cache: bool = False,
    ) -> dict:
        # 1. Auth check
        if not await self.auth.verify(user_id):
            raise PermissionError("Unauthorized")
        
        # 2. Rate limit
        if not await self.rate_limiter.allow(user_id):
            raise Exception("Rate limit exceeded")
        
        # 3. Budget check
        budget_ok, reason = self.cost_tracker.check_budget(user_id)
        if not budget_ok:
            raise Exception(reason)
        
        # 4. PII redaction
        clean_messages = self.pii_redactor.redact_messages(messages)
        
        # 5. Cache check
        if not bypass_cache:
            cached, cache_status = await self.cache.get_or_generate(
                clean_messages, model, temperature=0, llm=None
            )
            if cache_status != "miss":
                return {"content": cached, "cached": True, "source": cache_status}
        
        # 6. Model selection
        selected_model = model if model != "auto" else self.select_model(messages)
        
        # 7. Route and generate
        response = await self.router.acompletion(
            model=selected_model,
            messages=clean_messages,
        )
        
        # 8. Track cost
        self.cost_tracker.record(
            user_id, feature, selected_model,
            response.usage.prompt_tokens, response.usage.completion_tokens
        )
        
        # 9. Cache store
        content = response.choices[0].message.content
        await self.cache.set(clean_messages, selected_model, 0, content)
        
        return {"content": content, "cached": False, "model": selected_model}
```

---

## 6. Long Context Engineering

Models like Gemini 1.5 Pro (2M tokens) and Claude 3.5 Sonnet (200K) enable new patterns:

```python
class LongContextStrategy:
    """Strategies for working with long context models."""
    
    @staticmethod
    def full_document_qa(document: str, questions: list[str], llm) -> list[str]:
        """Put entire document in context — no chunking needed."""
        # For < 200K token documents
        response = llm.invoke([
            SystemMessage(content="Answer all questions based on the document."),
            HumanMessage(content=f"Document:\n{document}\n\nQuestions:\n" + 
                        "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions)))
        ])
        return response.content
    
    @staticmethod
    async def parallel_chunk_analysis(document: str, task: str, llm) -> str:
        """For documents > context limit: parallel chunk analysis + synthesis."""
        
        chunks = split_into_context_sized_chunks(document, chunk_tokens=100000)
        
        # Analyze each chunk in parallel
        analyses = await asyncio.gather(*[
            llm.ainvoke([HumanMessage(content=f"Analyze this portion for: {task}\n\n{chunk}")])
            for chunk in chunks
        ])
        
        # Synthesize
        all_analyses = "\n\n".join(a.content for a in analyses)
        final = await llm.ainvoke([
            SystemMessage(content=f"Synthesize these partial analyses into a final answer for: {task}"),
            HumanMessage(content=all_analyses)
        ])
        return final.content
    
    @staticmethod
    def map_reduce_summarization(document: str, llm) -> str:
        """Classic map-reduce for very long documents."""
        
        # Split into manageable chunks
        chunks = text_splitter.split_text(document)
        
        # Map: summarize each chunk
        summaries = [
            llm.invoke([HumanMessage(content=f"Summarize concisely:\n{chunk}")]).content
            for chunk in chunks
        ]
        
        # Reduce: combine summaries
        if len(summaries) > 10:
            # Two-pass for very many chunks
            mid_summaries = [
                llm.invoke([HumanMessage(content=f"Combine these summaries:\n{chr(10).join(summaries[i:i+10])}")]).content
                for i in range(0, len(summaries), 10)
            ]
            summaries = mid_summaries
        
        final = llm.invoke([HumanMessage(
            content=f"Combine into a coherent final summary:\n{chr(10).join(summaries)}"
        )])
        return final.content
```

---

## 7. Reasoning Models

Models like OpenAI o1/o3 and DeepSeek-R1 perform chain-of-thought internally before answering:

```python
# Using o1 for complex reasoning
from openai import OpenAI

client = OpenAI()

def reason_and_answer(problem: str, effort: str = "medium") -> str:
    """Use o1 for problems requiring deep reasoning."""
    response = client.chat.completions.create(
        model="o1",  # or "o3-mini" for cost savings
        reasoning_effort=effort,  # "low", "medium", "high"
        messages=[{"role": "user", "content": problem}]
    )
    return response.choices[0].message.content

# When to use reasoning models vs standard LLMs:
ROUTING_GUIDE = {
    "use_reasoning_model": [
        "Mathematical proofs",
        "Complex code debugging with many interdependencies",
        "Multi-step logical reasoning",
        "Scientific problem solving",
        "Competitive programming",
    ],
    "use_standard_model": [
        "Simple Q&A",
        "Document summarization",
        "Translation",
        "Creative writing",
        "Simple code generation",
        "Conversational chat",
    ],
    "cost_note": "o1 costs 5-15x more than gpt-4o — use selectively"
}

async def smart_model_router(query: str) -> str:
    """Route to reasoning or standard model based on complexity."""
    
    complexity_check = await ChatOpenAI(model="gpt-4o-mini").ainvoke([
        HumanMessage(content=f"""Rate this query 1-10 for reasoning complexity.
10=requires multi-step logical reasoning, math, or code debugging.
1=simple factual or conversational.
Return ONLY a number.

Query: {query}""")
    ])
    
    score = float(complexity_check.content.strip())
    
    if score >= 7:
        return await AsyncOpenAI().chat.completions.create(
            model="o1-mini", messages=[{"role": "user", "content": query}]
        )
    else:
        return await ChatOpenAI(model="gpt-4o-mini").ainvoke([HumanMessage(content=query)])
```

---

## 8. Mixture of Experts (MoE)

```
MoE Architecture:
  Input Token
     ↓
  Router Network (trainable)
     ↓ selects top-K experts
  ┌───┬───┬───┬───┐
  │E1 │E2 │E3 │...│  Each expert = small FFN
  └───┴───┴───┴───┘  Only K/N experts activate per token
     ↓ weighted sum
  Output

Key metrics for Mixtral 8x7B:
- Total parameters: 46.7B (8 experts × 7B FFN each + shared attention)
- Active parameters per token: 12.9B (2 of 8 experts active)
- Cost: similar to 13B dense model but quality of 46.7B
```

```python
# Practical implications for engineers

MoE_CONSIDERATIONS = {
    "memory": "Load all experts (full 46.7B) but only compute 12.9B — needs 90GB+ VRAM",
    "serving": "vLLM handles MoE natively — use same API as dense models",
    "quantization": "GPTQ/AWQ work on MoE; 4-bit Mixtral fits in 24GB VRAM",
    "routing": "Expert routing is implicit — you can't control which expert handles what",
    "best_use_case": "When you need 70B quality but can't afford 70B compute costs",
    "when_to_prefer_dense": "When VRAM is the bottleneck (MoE needs more memory than equivalent dense)",
}
```

---

## 9. On-Device AI (Edge Inference)

```python
# Running LLMs on Apple Silicon / Android / Edge
from mlx_lm import load, generate  # Apple MLX (M1/M2/M3)

model, tokenizer = load("mlx-community/Llama-3.2-3B-Instruct-4bit")

response = generate(
    model,
    tokenizer,
    prompt="What is RAG?",
    max_tokens=200,
    temp=0.1,
    verbose=False,
)
print(response)

# Performance on M2 MacBook Pro:
# - Llama 3.2 3B (4-bit): ~80 tokens/sec
# - Llama 3.1 8B (4-bit): ~35 tokens/sec
# - Mistral 7B (4-bit): ~38 tokens/sec

EDGE_USE_CASES = {
    "privacy_first": "Medical apps, legal tools, personal data",
    "offline_capable": "Field apps, areas with poor connectivity",
    "low_latency": "Real-time audio/video analysis",
    "cost_zero": "No API costs, good for consumers apps at scale",
    "limitations": ["Context length limited (4-8K)", "Quality below GPT-4", "No fine-tuning on device"],
}
```

---

## 10. Future Trends

### Agent Memory Networks (2025+)

```
Current: Agents have context window + vector DB
Future: Specialized memory architectures
  ├── Short-term: Working memory in context (seconds)
  ├── Medium-term: Episodic buffer in Redis (hours/days)
  ├── Long-term: Consolidated semantic memory in graph DB (permanent)
  └── Procedural: Tool usage patterns, fine-tuned behaviors
```

### Self-Improving Systems

```python
# The emerging "agent flywheel" pattern

class SelfImprovingAgent:
    """Agent that improves itself through experience."""
    
    async def run_and_learn(self, task: str) -> str:
        # Run task
        result = await self.run(task)
        
        # Evaluate quality
        quality_score = await self.evaluate(task, result)
        
        if quality_score < 0.7:
            # Learn from failure
            improvement = await self.reflect(task, result, quality_score)
            
            # Update prompt/memory
            await self.memory.store(
                f"Poor performance on '{task[:50]}': {improvement}"
            )
        else:
            # Learn from success
            await self.memory.store(
                f"Successful pattern for '{task[:50]}': key steps taken"
            )
        
        return result
```

### Key Trends to Watch

```
1. Multimodal-first applications
   - Video understanding becomes mainstream (Gemini Pro Video)
   - Real-time audio conversations (GPT-4o Realtime)
   - Document understanding (images + text together)

2. Agentic infrastructure
   - Long-running persistent agents (days/weeks)
   - Agent-to-agent communication standards
   - MCP adoption as industry standard

3. Specialization vs generalization
   - Domain-specific fine-tuned models winning on benchmarks
   - Routing between specialized models (healthcare, legal, code)
   - LoRA adapters swapped per query type

4. Cost collapse
   - Quality of GPT-4 (2023) available at GPT-3.5 prices
   - Local 7-8B models matching GPT-3.5 on most tasks
   - Prediction: GPT-4o quality for < $0.001/1K tokens by 2026

5. Test-time compute (reasoning)
   - "Think longer" = better answers (o1/o3)
   - Adaptive reasoning budget based on query complexity
   - Verification models checking reasoning chains

6. Memory-augmented generation
   - Persistent memory across conversations becomes standard
   - Personal AI that truly knows your history and preferences
   - Privacy-preserving on-device memory sync
```

---

## 11. Interview Questions

**Q1: What is the Model Context Protocol (MCP) and why is it significant?**

MCP is an open standard from Anthropic that defines how LLMs connect to external tools and data sources. Before MCP, every application had to build custom integrations between LLMs and their tools — creating fragmented, non-interoperable implementations. MCP standardizes the interface: any MCP server exposes Resources (data), Tools (actions), and Prompts to any MCP-compatible host. This is significant because: (1) Tools built once work with Claude, ChatGPT, or any future model; (2) It enables a marketplace of AI integrations; (3) It separates tool development from model development — product teams can build MCP servers without knowing which LLM will call them.

**Q2: When would you use Graph RAG over standard RAG?**

Standard vector RAG fails at multi-hop reasoning (who founded the company that made Product X?), entity relationship queries, and broad aggregation across a corpus (what's the overall strategy?). Graph RAG builds a knowledge graph from documents, enabling Cypher queries that traverse entity relationships. Use Graph RAG when: queries frequently involve "who works with whom," "what connects A to B," or "find all X related to Y" patterns; your documents have structured entities (people, organizations, products); you need explainable retrieval paths. Standard RAG is still better for semantic similarity search and simpler Q&A.

**Q3: How do reasoning models (o1/o3/DeepSeek-R1) differ architecturally from standard LLMs?**

Standard LLMs generate tokens left-to-right in a single forward pass — they don't "think" before answering. Reasoning models are trained with reinforcement learning to generate extended chain-of-thought reasoning (hundreds to thousands of tokens) internally before producing the final answer. This reasoning scratchpad is invisible to the user but consumes tokens. The key difference is the training signal: standard SFT matches outputs, reasoning models are rewarded for reaching correct answers through any valid reasoning path. Practically: reasoning models are 5-15x more expensive per query, much slower, but significantly better on math, logic, and complex code tasks.

**Q4: Describe the architecture of a production multi-tenant AI platform that must comply with data isolation requirements.**

Three isolation strategies depending on security requirements: (1) Namespace isolation (Pinecone namespaces, Qdrant collections) — same cluster, tenant_id in metadata, cost-efficient, suitable for most enterprises; (2) Database-per-tenant (separate pgvector schema per tenant) — stronger isolation, tenant data never co-resides in same table; (3) Cluster-per-tenant — dedicated infrastructure, required for regulated industries (healthcare HIPAA, finance SOC2+). Cross-cutting controls: tenant_id enforced at API gateway level, never trusted from request body; row-level security (PostgreSQL RLS) as second defense; audit logging of every LLM call with hashed content for compliance; tenant-specific rate limits, token budgets, and model access tiers.

---

*End of GenAI Engineering Curriculum — 19 Modules Complete*
