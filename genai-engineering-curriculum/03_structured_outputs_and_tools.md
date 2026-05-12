# Module 03 — Structured Outputs & Tool Calling

> **Phase:** 1 — Foundations  
> **Prerequisites:** Modules 01, 02  
> **Leads to:** Agent Engineering, LangChain  
> **Estimated time:** 2–3 days

---

## 1. THE BIG PICTURE

Structured outputs and tool calling transform LLMs from a text generation API into a programmable reasoning engine. This is the fundamental mechanism that makes AI agents possible.

**Structured outputs:** Instead of getting raw text, you get machine-parseable data (JSON, XML) that conforms to a schema.

**Tool calling:** Instead of just describing what it would do, the model can actually invoke real functions — searching the web, querying databases, calling APIs.

Without these capabilities, LLMs are conversational. With them, LLMs become computational — capable of participating in multi-step workflows and integrating with existing software systems.

**This is the most practically important module for building production AI systems.**

---

## 2. STRUCTURED OUTPUTS

### 2.1 Why Structured Output is Hard Without API Support

```python
# The naive approach — fragile in production
response = await client.complete(
    messages=[{"role": "user", "content": "Extract person's name and age from: 'John Smith is 34 years old.' Return as JSON."}]
)

# Problems:
# 1. Model might wrap JSON in ```json ... ``` markdown blocks
# 2. Model might add explanation text before/after JSON
# 3. Model might use slightly different field names
# 4. Model might return invalid JSON (unclosed brackets, trailing commas)
# 5. Inconsistent behavior across model versions

# This is why we need guaranteed structured output mechanisms
```

### 2.2 JSON Mode

The simplest form — guarantees the output is valid JSON:

```python
# json_mode.py
from openai import AsyncOpenAI
import json

client = AsyncOpenAI()

async def extract_with_json_mode(text: str) -> dict:
    """
    JSON mode guarantees valid JSON output.
    IMPORTANT: You must still tell the model what JSON to produce in the prompt.
    JSON mode just ensures validity, not specific schema adherence.
    """
    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},  # Enable JSON mode
        messages=[
            {
                "role": "system",
                "content": """Extract entity information from text.
                Return a JSON object with these exact fields:
                {
                  "name": "person's full name",
                  "age": "integer or null",
                  "email": "email address or null",
                  "company": "company name or null"
                }"""
            },
            {
                "role": "user",
                "content": f"Extract from: {text}"
            }
        ]
    )
    
    # This is now guaranteed to be valid JSON
    return json.loads(response.choices[0].message.content)


# Test
result = await extract_with_json_mode(
    "Sarah Johnson (sarah.j@techcorp.com), VP Engineering at TechCorp, age 41"
)
# {"name": "Sarah Johnson", "age": 41, "email": "sarah.j@techcorp.com", "company": "TechCorp"}
```

**Limitations of JSON mode:**
- Guarantees valid JSON, but not a specific schema
- Field names, nesting, types can still vary
- No enum validation
- Use Structured Outputs (next section) for schema guarantees

### 2.3 Structured Outputs (Schema-Enforced)

OpenAI's Structured Outputs feature uses JSON Schema to guarantee the output matches your exact schema:

```python
# structured_outputs.py
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
import json

client = AsyncOpenAI()

# Define your schema with Pydantic
class ContactInfo(BaseModel):
    name: str = Field(description="Full name of the person")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    company: Optional[str] = Field(None, description="Company name")

class MeetingActionItem(BaseModel):
    owner: str = Field(description="Person responsible for this action")
    task: str = Field(description="Description of the task")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format")
    priority: Literal["high", "medium", "low"] = Field(description="Priority level")

class MeetingNotes(BaseModel):
    date: str = Field(description="Meeting date in YYYY-MM-DD format")
    participants: List[ContactInfo] = Field(description="List of meeting participants")
    summary: str = Field(description="Brief summary of the meeting")
    decisions: List[str] = Field(description="Key decisions made")
    action_items: List[MeetingActionItem] = Field(description="Action items from the meeting")
    next_meeting: Optional[str] = Field(None, description="Next meeting date if mentioned")


async def extract_meeting_notes(raw_notes: str) -> MeetingNotes:
    """
    Extract structured meeting notes using schema-enforced output.
    Guaranteed to return valid MeetingNotes object.
    """
    response = await client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",  # Structured outputs available on this model+
        messages=[
            {
                "role": "system",
                "content": "Extract structured meeting information from the provided notes."
            },
            {
                "role": "user",
                "content": f"Extract meeting information from:\n\n{raw_notes}"
            }
        ],
        response_format=MeetingNotes,  # Pass Pydantic model directly
    )
    
    # Returns a validated MeetingNotes object — type-safe!
    return response.choices[0].message.parsed


# Example usage
raw_notes = """
Met with the data engineering team on March 15, 2025.
Present: Viraaj (viraaj@wf.com, Wells Fargo), Sarah Chen, and Mike Torres (mike@vendor.com, DataCo).

We decided to migrate to Qdrant for vector storage by April 30.
Sarah will lead the migration POC - due by March 28, HIGH priority.
Mike will provide the Qdrant enterprise license - needed by March 20.
Viraaj will update the architecture docs - low priority, by April 5.

Next meeting: April 2, 2025.
"""

meeting = await extract_meeting_notes(raw_notes)
print(meeting.model_dump_json(indent=2))
```

### 2.4 Pydantic Integration Pattern

```python
# pydantic_patterns.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Literal, Union
from decimal import Decimal
import re

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "US"
    
    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: str) -> str:
        if not re.match(r'^\d{5}(-\d{4})?$', v):
            raise ValueError("Invalid ZIP code format")
        return v

class OrderLineItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(ge=1, le=1000)  # 1 to 1000
    unit_price: float = Field(ge=0)
    discount_pct: float = Field(ge=0, le=100, default=0)
    
    @property
    def line_total(self) -> float:
        return self.quantity * self.unit_price * (1 - self.discount_pct / 100)

class CustomerOrder(BaseModel):
    order_id: Optional[str] = None
    customer_name: str
    customer_email: str
    shipping_address: Address
    items: List[OrderLineItem] = Field(min_length=1)
    notes: Optional[str] = None
    priority: Literal["standard", "express", "overnight"] = "standard"
    
    @model_validator(mode="after")
    def validate_email(self) -> "CustomerOrder":
        if "@" not in self.customer_email:
            raise ValueError("Invalid email address")
        return self
    
    @property
    def total(self) -> float:
        return sum(item.line_total for item in self.items)


async def extract_order_from_email(email_text: str) -> CustomerOrder:
    """Extract structured order from customer email."""
    response = await client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "Extract order details from customer emails."},
            {"role": "user", "content": email_text}
        ],
        response_format=CustomerOrder,
    )
    return response.choices[0].message.parsed
```

### 2.5 Fallback Parsing Pattern

When structured output isn't available (older models, different providers):

```python
# robust_json_parser.py
import json
import re
from typing import TypeVar, Type
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

def robust_parse_json(content: str, model_class: Type[T]) -> T:
    """
    Robustly parse JSON from LLM output.
    Handles: markdown code blocks, leading/trailing text, single quotes.
    """
    
    # Strategy 1: Direct parse
    try:
        return model_class.model_validate_json(content)
    except (json.JSONDecodeError, ValidationError):
        pass
    
    # Strategy 2: Strip markdown code blocks
    # Handles: ```json ... ``` and ``` ... ```
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'\{.*\}',  # Extract first JSON object
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            candidate = match.group(1) if '(' in pattern and ')' in pattern else match.group(0)
            try:
                return model_class.model_validate_json(candidate)
            except (json.JSONDecodeError, ValidationError):
                continue
    
    # Strategy 3: Fix common JSON issues
    cleaned = content
    # Fix trailing commas: {"a": 1,} → {"a": 1}
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    # Fix single quotes to double quotes (simple cases)
    # Note: This is fragile for complex strings - use Strategy 4 for robustness
    
    try:
        return model_class.model_validate_json(cleaned)
    except (json.JSONDecodeError, ValidationError):
        pass
    
    # Strategy 4: Ask the model to fix its own output
    raise ValueError(f"Could not parse JSON from: {content[:200]}...")


async def parse_with_retry(
    client,
    messages: list,
    model_class: Type[T],
    max_retries: int = 2,
) -> T:
    """Parse structured output with automatic retry on parse failure."""
    
    for attempt in range(max_retries + 1):
        response = await client.complete(
            messages=messages,
            response_format={"type": "json_object"},
        )
        
        try:
            return robust_parse_json(response["content"], model_class)
        except ValueError as e:
            if attempt < max_retries:
                # Add the failed output and ask model to fix it
                messages = messages + [
                    {"role": "assistant", "content": response["content"]},
                    {"role": "user", "content": f"The JSON you provided was invalid. Error: {e}. Please provide corrected JSON."}
                ]
            else:
                raise
```

---

## 3. TOOL CALLING (FUNCTION CALLING)

### 3.1 How Tool Calling Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tool Calling Flow                             │
│                                                                  │
│  1. User asks question                                           │
│     "What's the weather in Hyderabad and what time is it there?"│
│                                ↓                                 │
│  2. You send question + tool definitions to LLM                  │
│     Tools: [get_weather(city), get_time(timezone)]               │
│                                ↓                                 │
│  3. LLM decides it needs tools, returns tool_call requests       │
│     {"tool": "get_weather", "args": {"city": "Hyderabad"}}      │
│     {"tool": "get_time", "args": {"timezone": "Asia/Kolkata"}}  │
│                                ↓                                 │
│  4. YOUR CODE executes the actual functions                      │
│     result1 = get_weather("Hyderabad")  → {"temp": 34, ...}    │
│     result2 = get_time("Asia/Kolkata")  → {"time": "15:30", ...}│
│                                ↓                                 │
│  5. You send tool results back to LLM                            │
│                                ↓                                 │
│  6. LLM generates final answer using tool results               │
│     "The weather in Hyderabad is 34°C and sunny. It is 3:30 PM."│
└─────────────────────────────────────────────────────────────────┘
```

**Key insight:** The LLM doesn't execute code. It generates structured requests to execute code. YOUR application runs the actual functions. The LLM is the orchestrator; your code is the executor.

### 3.2 Defining Tools

```python
# tool_definitions.py
from openai import AsyncOpenAI
from typing import Any
import json
import httpx
from datetime import datetime
import pytz

client = AsyncOpenAI()

# Tool definitions — these describe the tools to the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the company's internal knowledge base for information. Use this when the user asks about company policies, procedures, products, or internal documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query — be specific and descriptive"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["policy", "product", "technical", "hr", "general"],
                        "description": "Category to search within (optional)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time in a specified timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (e.g., 'Asia/Kolkata', 'America/New_York', 'UTC')"
                    }
                },
                "required": ["timezone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_jira_ticket",
            "description": "Create a new Jira ticket. Use when user explicitly asks to create a ticket or task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Ticket title/summary"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the issue or task"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High", "Critical"],
                        "description": "Ticket priority"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Username of person to assign to (optional)"
                    }
                },
                "required": ["title", "description", "priority"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql_query",
            "description": "Execute a read-only SQL query against the analytics database. Only SELECT statements are allowed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query to execute"
                    },
                    "database": {
                        "type": "string",
                        "enum": ["analytics", "reporting", "staging"],
                        "description": "Target database"
                    }
                },
                "required": ["query", "database"]
            }
        }
    }
]
```

### 3.3 Complete Tool Calling Implementation

```python
# tool_calling_engine.py
import asyncio
import json
from typing import Dict, Callable, Any, Optional
from openai.types.chat import ChatCompletionMessage

class ToolCallingEngine:
    """
    Complete implementation of the tool calling loop.
    Handles: tool definitions, execution, multi-step reasoning,
    parallel calls, error handling.
    """
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self._tool_registry: Dict[str, Callable] = {}
        self._tool_definitions = []
    
    def register_tool(self, tool_def: dict, impl: Callable):
        """Register a tool with its definition and implementation."""
        name = tool_def["function"]["name"]
        self._tool_definitions.append(tool_def)
        self._tool_registry[name] = impl
    
    async def _execute_tool(self, tool_call) -> str:
        """Execute a single tool call and return result as string."""
        function_name = tool_call.function.name
        
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid arguments JSON: {e}"})
        
        implementation = self._tool_registry.get(function_name)
        if not implementation:
            return json.dumps({"error": f"Unknown tool: {function_name}"})
        
        try:
            # Support both sync and async implementations
            if asyncio.iscoroutinefunction(implementation):
                result = await implementation(**arguments)
            else:
                result = implementation(**arguments)
            
            # Ensure result is JSON serializable
            if isinstance(result, str):
                return result
            return json.dumps(result)
            
        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
    
    async def run(
        self,
        messages: list,
        system_prompt: Optional[str] = None,
        model: str = "gpt-4o",
        max_iterations: int = 10,
        parallel_tools: bool = True,
    ) -> dict:
        """
        Run the complete tool-calling loop.
        Handles multi-step reasoning with tool use.
        
        Returns:
            {
                "content": "final response",
                "messages": [full conversation with tool calls],
                "tool_calls_made": [list of tools called],
                "iterations": number of reasoning steps,
            }
        """
        
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            full_messages = messages.copy()
        
        tool_calls_made = []
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            # Call LLM
            response = await self.client.chat.completions.create(
                model=model,
                messages=full_messages,
                tools=self._tool_definitions if self._tool_definitions else None,
                tool_choice="auto",  # Let model decide when to use tools
            )
            
            message = response.choices[0].message
            full_messages.append(message.model_dump())  # Add to conversation
            
            # Check if model wants to use tools
            if response.choices[0].finish_reason == "tool_calls":
                tool_calls = message.tool_calls
                
                if parallel_tools and len(tool_calls) > 1:
                    # Execute multiple tool calls in parallel
                    tasks = [self._execute_tool(tc) for tc in tool_calls]
                    results = await asyncio.gather(*tasks)
                else:
                    # Sequential execution
                    results = []
                    for tc in tool_calls:
                        result = await self._execute_tool(tc)
                        results.append(result)
                
                # Add tool results to conversation
                for tool_call, result in zip(tool_calls, results):
                    tool_calls_made.append({
                        "tool": tool_call.function.name,
                        "args": json.loads(tool_call.function.arguments),
                        "result_preview": result[:200],
                    })
                    
                    full_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                
                # Continue loop — LLM will process tool results
                continue
            
            # Model finished (stop reason = "stop")
            return {
                "content": message.content,
                "messages": full_messages,
                "tool_calls_made": tool_calls_made,
                "iterations": iterations,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
            }
        
        # Max iterations reached
        return {
            "content": "I reached the maximum number of steps without completing the task.",
            "messages": full_messages,
            "tool_calls_made": tool_calls_made,
            "iterations": iterations,
            "error": "max_iterations_reached",
        }
```

### 3.4 Real Tool Implementations

```python
# tool_implementations.py
import httpx
import asyncio
from datetime import datetime
import pytz
from typing import Optional, List, Dict

# Actual implementations of the tools defined above

async def search_knowledge_base(
    query: str,
    category: Optional[str] = None,
    max_results: int = 5
) -> dict:
    """Search company knowledge base using vector similarity."""
    # In production: call your vector DB (Qdrant, Pinecone, etc.)
    # This is a mock implementation
    results = [
        {
            "id": "doc_123",
            "title": "Data Retention Policy",
            "excerpt": "All production data must be retained for 7 years...",
            "score": 0.92,
            "category": "policy",
            "url": "/docs/data-retention-policy",
        }
    ]
    return {
        "results": results[:max_results],
        "total": len(results),
        "query": query,
    }


def get_current_time(timezone: str) -> dict:
    """Get current time in specified timezone."""
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return {
            "timezone": timezone,
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
        }
    except pytz.exceptions.UnknownTimeZoneError:
        return {"error": f"Unknown timezone: {timezone}. Use IANA timezone format (e.g., 'Asia/Kolkata')"}


async def create_jira_ticket(
    title: str,
    description: str,
    priority: str,
    assignee: Optional[str] = None,
) -> dict:
    """Create a Jira ticket via API."""
    # In production: actual Jira API call
    import os
    
    jira_token = os.environ.get("JIRA_API_TOKEN")
    jira_url = os.environ.get("JIRA_URL", "https://yourcompany.atlassian.net")
    
    async with httpx.AsyncClient() as client:
        payload = {
            "fields": {
                "project": {"key": "ENG"},
                "summary": title,
                "description": description,
                "issuetype": {"name": "Task"},
                "priority": {"name": priority},
            }
        }
        if assignee:
            payload["fields"]["assignee"] = {"name": assignee}
        
        # Mock response for this example
        return {
            "id": "ENG-12345",
            "url": f"{jira_url}/browse/ENG-12345",
            "title": title,
            "status": "created",
        }


async def run_sql_query(query: str, database: str) -> dict:
    """Execute a read-only SQL query."""
    import asyncpg
    import os
    
    # Security: Only allow SELECT
    if not query.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed"}
    
    # Security: Disallow dangerous patterns
    dangerous_patterns = ["DROP", "DELETE", "INSERT", "UPDATE", "CREATE", "ALTER", "--", ";"]
    query_upper = query.upper()
    for pattern in dangerous_patterns:
        if pattern in query_upper:
            return {"error": f"Query contains disallowed pattern: {pattern}"}
    
    # In production: actual DB connection
    conn_string = os.environ.get(f"DB_{database.upper()}_URL")
    
    try:
        conn = await asyncpg.connect(conn_string)
        rows = await conn.fetch(query)
        await conn.close()
        
        return {
            "columns": list(rows[0].keys()) if rows else [],
            "rows": [dict(row) for row in rows[:100]],  # Limit to 100 rows
            "total_rows": len(rows),
            "query": query,
        }
    except Exception as e:
        return {"error": str(e)}
```

### 3.5 Building a Complete Tool-Using Assistant

```python
# complete_assistant.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Initialize the engine
engine = ToolCallingEngine(client=AsyncOpenAI())

# Register tools
engine.register_tool(
    TOOLS[0],  # search_knowledge_base definition
    search_knowledge_base  # implementation
)
engine.register_tool(TOOLS[1], get_current_time)
engine.register_tool(TOOLS[2], create_jira_ticket)
engine.register_tool(TOOLS[3], run_sql_query)

SYSTEM_PROMPT = """You are an intelligent enterprise assistant.

You have access to these tools:
- search_knowledge_base: Search company documentation and policies
- get_current_time: Get current time in any timezone
- create_jira_ticket: Create Jira tickets (only when explicitly asked)
- run_sql_query: Query the analytics database (read-only)

Guidelines:
- Search the knowledge base BEFORE answering questions about company policies
- Confirm with the user before creating tickets
- Show query results in a formatted table when possible
- Always explain what tools you used and why"""


class ChatRequest(BaseModel):
    messages: list
    user_id: str


@app.post("/chat")
async def chat(request: ChatRequest):
    result = await engine.run(
        messages=request.messages,
        system_prompt=SYSTEM_PROMPT,
        model="gpt-4o",
        max_iterations=10,
    )
    
    return {
        "response": result["content"],
        "tools_used": result["tool_calls_made"],
        "iterations": result["iterations"],
    }
```

### 3.6 Tool Choice Strategies

```python
# tool_choice_strategies.py

# "auto" — model decides whether to use tools (default)
tool_choice = "auto"

# "required" — model MUST use at least one tool
tool_choice = "required"

# "none" — model must NOT use tools (force text response)
tool_choice = "none"

# Specific tool — force the model to use exactly this tool
tool_choice = {"type": "function", "function": {"name": "search_knowledge_base"}}


# Production pattern: Use specific tool for the first call when you know
# what the model needs to do, then switch to "auto" for subsequent calls.

async def retrieval_augmented_response(query: str) -> str:
    """
    Pattern: Force retrieval first, then let model decide next steps.
    """
    
    # Step 1: Force the model to search (don't let it answer from memory)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        tools=TOOLS,
        tool_choice={"type": "function", "function": {"name": "search_knowledge_base"}},
    )
    
    # Execute the forced search
    tool_call = response.choices[0].message.tool_calls[0]
    search_result = await search_knowledge_base(**json.loads(tool_call.function.arguments))
    
    # Step 2: Let model generate answer from search results (no more tools)
    final_response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
            response.choices[0].message.model_dump(),
            {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(search_result)},
        ],
        tools=TOOLS,
        tool_choice="none",  # No more tools — just answer now
    )
    
    return final_response.choices[0].message.content
```

---

## 4. ADVANCED PATTERNS

### 4.1 Tool Calling with Anthropic (Claude)

```python
# anthropic_tools.py
import anthropic

client = anthropic.AsyncAnthropic()

# Anthropic uses slightly different format
ANTHROPIC_TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": "Search the company knowledge base",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results"}
            },
            "required": ["query"]
        }
    }
]

async def claude_with_tools(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    
    while True:
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system="You are a helpful assistant...",
            tools=ANTHROPIC_TOOLS,
            messages=messages,
        )
        
        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Add Claude's response to messages
            messages.append({
                "role": "assistant",
                "content": response.content  # List of content blocks
            })
            
            # Process tool use blocks
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # Execute the tool
                    result = await search_knowledge_base(**block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            
            # Add tool results to messages
            messages.append({
                "role": "user",
                "content": tool_results
            })
            
            continue
        
        # Final response
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
```

### 4.2 Typed Tool Calling with Instructor

The `instructor` library wraps OpenAI/Anthropic clients to make structured outputs + tool calling easier:

```python
# instructor_pattern.py
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import List, Optional

# Patch the client with instructor
client = instructor.from_openai(AsyncOpenAI())

class SearchQuery(BaseModel):
    query: str
    filters: Optional[dict] = None
    top_k: int = 5

class ResearchResult(BaseModel):
    title: str
    summary: str
    confidence: float
    sources: List[str]
    follow_up_questions: List[str]

# instructor makes structured outputs trivial
async def research(topic: str) -> ResearchResult:
    return await client.chat.completions.create(
        model="gpt-4o",
        response_model=ResearchResult,  # instructor handles the rest
        messages=[
            {"role": "system", "content": "Research the given topic thoroughly."},
            {"role": "user", "content": f"Research: {topic}"}
        ]
    )

# Result is automatically validated and typed
result = await research("Apache Kafka vs Pub/Sub for streaming pipelines")
print(f"Title: {result.title}")
print(f"Confidence: {result.confidence:.0%}")
print(f"Sources: {result.sources}")
```

### 4.3 Parallel Tool Execution

```python
# parallel_tools.py
"""
OpenAI often returns multiple tool calls in one response.
Execute them in parallel for better performance.
"""

async def execute_parallel_tools(tool_calls: list, registry: dict) -> list:
    """Execute multiple tool calls concurrently."""
    
    async def execute_one(tool_call) -> dict:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        impl = registry.get(name)
        
        if not impl:
            return {
                "tool_call_id": tool_call.id,
                "content": json.dumps({"error": f"Unknown tool: {name}"}),
            }
        
        try:
            if asyncio.iscoroutinefunction(impl):
                result = await impl(**args)
            else:
                result = impl(**args)
                
            return {
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            }
        except Exception as e:
            return {
                "tool_call_id": tool_call.id,
                "content": json.dumps({"error": str(e)}),
            }
    
    # Execute all tool calls concurrently
    results = await asyncio.gather(*[execute_one(tc) for tc in tool_calls])
    
    return [
        {"role": "tool", **result}
        for result in results
    ]
```

### 4.4 Tool Calling with Memory

```python
# tool_with_memory.py
"""
Pattern: Remember tool call results across conversation turns.
Prevents re-executing expensive tools for the same query.
"""

class ConversationWithTools:
    def __init__(self, engine: ToolCallingEngine):
        self.engine = engine
        self.history = []
        self.tool_cache = {}  # Cache tool results
    
    async def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        
        result = await self.engine.run(
            messages=self.history,
            max_iterations=10,
        )
        
        # Cache expensive tool results
        for tool_call in result["tool_calls_made"]:
            cache_key = f"{tool_call['tool']}:{json.dumps(tool_call['args'], sort_keys=True)}"
            self.tool_cache[cache_key] = tool_call.get("result")
        
        # Add assistant response to history
        self.history.append({
            "role": "assistant",
            "content": result["content"]
        })
        
        # Trim history if getting long
        if len(self.history) > 20:
            # Keep system + last 18 messages
            self.history = self.history[:1] + self.history[-18:]
        
        return result["content"]
```

---

## 5. PRODUCTION PATTERNS

### 5.1 Tool Security

```python
# tool_security.py
"""
Production tool calling requires strict security controls.
Never let LLMs execute arbitrary code or unconstrained SQL.
"""

class SecureToolWrapper:
    """Wrap tools with security controls."""
    
    def __init__(self, impl: Callable, allowed_users: list = None, rate_limit: int = 100):
        self.impl = impl
        self.allowed_users = allowed_users  # None = allow all
        self.rate_limit = rate_limit  # requests per hour
        self._request_counts = {}
    
    async def __call__(self, user_id: str = None, **kwargs):
        # 1. Authorization check
        if self.allowed_users and user_id not in self.allowed_users:
            return {"error": "Unauthorized to use this tool"}
        
        # 2. Rate limiting
        if user_id:
            count = self._request_counts.get(user_id, 0)
            if count >= self.rate_limit:
                return {"error": f"Rate limit exceeded: {self.rate_limit}/hour"}
            self._request_counts[user_id] = count + 1
        
        # 3. Input validation
        # (Tool-specific validation happens in the tool itself)
        
        # 4. Execute
        return await self.impl(**kwargs)
    
    # 5. Audit log (in production: write to persistent storage)
    async def log_execution(self, user_id: str, tool: str, args: dict, result: dict):
        import logging
        logging.info(f"TOOL_EXECUTION user={user_id} tool={tool} args={args}")
```

### 5.2 Tool Result Validation

```python
# result_validation.py
from pydantic import BaseModel, ValidationError

class WeatherResult(BaseModel):
    temperature_celsius: float
    conditions: str
    humidity_pct: int
    city: str

def validate_tool_result(tool_name: str, result: dict) -> dict:
    """Validate tool results match expected schema."""
    
    schemas = {
        "get_weather": WeatherResult,
        # Add schemas for other tools
    }
    
    schema = schemas.get(tool_name)
    if not schema:
        return result  # No validation for this tool
    
    try:
        validated = schema(**result)
        return validated.model_dump()
    except ValidationError as e:
        # Log the validation error
        return {
            "error": f"Tool returned unexpected format: {e}",
            "raw_result": result,
        }
```

---

## 6. TRADEOFFS

### 6.1 Structured Outputs Comparison

| Method | Reliability | Flexibility | Model Support | Latency |
|--------|------------|-------------|---------------|---------|
| JSON Mode | High (valid JSON) | Medium | Broad | Low overhead |
| Structured Outputs (OpenAI) | Very High (schema guaranteed) | Medium | GPT-4o+ only | Low overhead |
| Instructor library | High | High | Broad | Low overhead |
| Manual parsing | Low | Very High | All | None |
| Tool calling for extraction | Very High | Medium | Broad | Slight overhead |

**Recommendation:** Use OpenAI's Structured Outputs for JSON extraction when on GPT-4o. Use `instructor` for multi-provider or complex schemas.

### 6.2 When NOT to Use Tool Calling

- Simple factual questions (no tools needed)
- Summarization tasks (tools add latency and complexity)
- Creative generation (tools interfere with output quality)
- When you need maximum token efficiency
- When debugging (tools make tracing harder)

---

## 7. DEBUGGING

### 7.1 Common Tool Calling Issues

**Problem: Model calls wrong tool**
- Diagnosis: Tool descriptions are ambiguous
- Fix: Make tool descriptions more specific and distinct
- Fix: Add negative examples in descriptions ("Don't use this for...")

**Problem: Model calls tool with wrong arguments**
- Diagnosis: Parameter descriptions are unclear
- Fix: Add explicit examples in parameter descriptions
- Fix: Add format constraints (enum, pattern, minimum/maximum)

**Problem: Model doesn't use tools when it should**
- Diagnosis: tool_choice is "auto" and model thinks it knows the answer
- Fix: Set tool_choice to "required" for retrieval-first flows
- Fix: Add system instruction: "Always search the knowledge base before answering policy questions"

**Problem: Infinite tool calling loop**
- Diagnosis: Tool result doesn't satisfy the model's need, it keeps calling tools
- Fix: Implement max_iterations limit
- Fix: Add instruction: "If tool results don't help after 2 attempts, say you cannot find the information"

---

## 8. EXERCISES

### Exercise 1 — Build a Data Extraction Pipeline
Create a pipeline that:
- Accepts raw text (emails, documents)
- Extracts structured data into Pydantic models
- Handles validation errors gracefully
- Logs extraction quality metrics

### Exercise 2 — Multi-Tool Assistant
Build an assistant with 5 tools:
- Calculator (math operations)
- Unit converter
- Time zone converter
- Temperature converter
- Currency converter

### Exercise 3 — Tool Safety Testing
Take an existing tool-calling assistant and:
- Test prompt injection via tool results
- Implement rate limiting per user
- Add audit logging for all tool calls
- Test edge cases for each tool

### Exercise 4 — Structured Output Benchmark
Compare accuracy, token usage, and latency for:
- Naive JSON extraction (no format control)
- JSON mode
- Structured Outputs API
- Tool calling as extraction mechanism

---

## 9. INTERVIEW QUESTIONS

**Q: How does function/tool calling work under the hood?**
A: The LLM doesn't execute functions. It's trained to output specially formatted JSON when it determines a function call is needed. The API layer intercepts this, returns it to your application as a `tool_calls` response rather than a text response. Your application then actually executes the function with the provided arguments, adds the result back to the conversation as a "tool" role message, and sends everything back to the model for a final response. The model sees function results as just another message in its context.

**Q: What are the security concerns with tool calling in production?**
A: Multiple layers: (1) Prompt injection — malicious content in documents could instruct the model to call destructive tools. Mitigation: input validation, tool whitelisting, principle of least privilege. (2) Argument injection — even with proper tool definitions, model may be manipulated to pass unexpected arguments (e.g., SQL injection via the SQL query tool). Mitigation: strict argument validation, allowlist SQL patterns, parameterized queries. (3) Over-permissioned tools — giving the model tools it doesn't need increases attack surface. Mitigation: scope tools narrowly, use different tool sets for different users/roles. (4) Denial of service — model could call expensive tools repeatedly. Mitigation: rate limiting, max_iterations guard, cost caps per request.

**Q: How would you implement a "human in the loop" approval for certain tool calls?**
A: Categorize tools as "auto-execute" vs "requires-approval". When the model calls a requires-approval tool, pause the execution, send an approval request (email, Slack, UI notification) to the authorized approver, and resume execution only after approval is received. Implement this as a middleware layer in your tool execution engine. For async approval flows, use a queue (Redis, SQS) to hold pending approvals and resume when the approval message arrives. LangGraph's `interrupt()` mechanism is designed exactly for this pattern.

---

*Next: [Module 04 — Embeddings & Semantic Search →](04_embeddings_and_semantic_search.md)*
