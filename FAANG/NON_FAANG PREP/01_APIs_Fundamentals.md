# APIs: Comprehensive Complete Guide Part 1 - Fundamentals

## Table of Contents
1. [What is an API](#what-is-an-api)
2. [Why APIs Matter](#why-apis-matter)
3. [Types of APIs](#types-of-apis)
4. [API Architecture](#api-architecture)
5. [REST Fundamentals](#rest-fundamentals)

---

## What is an API?

**API = Application Programming Interface**

An API is a set of rules and protocols that allow different software applications to communicate and exchange data.

### Real-World Analogy

```
Restaurant Without API:
1. You walk into kitchen
2. Tell chef "I want pasta"
3. Chef asks what type, how much
4. Chef cooks
5. You take it yourself
6. Problem: Chef is interrupted, inefficient

Restaurant With API (Waiter):
1. You sit at table
2. Order through waiter (API)
3. Waiter knows the protocol:
   - "I need pasta, medium portion, olive oil"
4. Waiter takes to kitchen
5. Kitchen follows standard procedure
6. Waiter brings food back
7. Benefits: Chef never interrupted, consistent, scalable
```

### What API Does

```
Application A (Your Website)
         ↓ (Make Request)
       API (Rules & Protocol)
         ↓ (Translate Request)
Application B (Google Maps Service)
         ↓ (Process)
       Database (Store Location Data)
         ↓ (Return Data)
Application B (Return Location)
         ↓ (Translate Response)
       API (Rules & Protocol)
         ↓ (Return Response)
Application A (Show Map to User)
```

---

## Why APIs Matter

### 1. Modularity (Separation of Concerns)

```
Without API (Monolithic):
Single System
├─ Frontend (HTML, CSS, JS)
├─ Backend (Business logic)
├─ Database (Store data)
└─ All tightly coupled
Problem: Change database → break frontend

With API (Modular):
Frontend ← API → Backend ← API → Database
         ← API →

Benefits:
- Change frontend without affecting backend
- Change database without affecting frontend
- Each can scale independently
- Each can be developed separately
```

### 2. Reusability

```
One API, Multiple Clients:

API Server
    ↙    ↓    ↘
  Web    Mobile  Desktop
  App    App     App

Same API, different user interfaces
Example: Twitter
- Web version (twitter.com)
- Mobile app (iOS)
- Mobile app (Android)
All use same Twitter API
```

### 3. Integration

```
Your Application
    ↙  ↓  ↓  ↘
  Payment  Email  SMS  Analytics
  Gateway  Service Service Platform

Each service has its own API
Your app integrates all of them
Example: E-commerce site
- Stripe API for payment
- SendGrid API for emails
- Twilio API for SMS
- Google Analytics API for tracking
```

### 4. Scalability

```
Without API:
User 1 → App Instance 1
User 2 → App Instance 2
User 3 → App Instance 3
Problem: Each instance needs database connection
Database gets overloaded

With API:
User 1 → Load Balancer → App Instance 1
User 2 → Load Balancer → App Instance 2
User 3 → Load Balancer → App Instance 3
All → Cached API Layer → Database

Benefits: Database protected, can add more instances
```

### 5. Security

```
Without API:
Direct Database Access
- Exposed: Schema, data structure
- Risk: SQL injection, full data loss

With API:
Database ← API ← Application
- Hidden: Schema, internal structure
- Validation: All inputs checked
- Authorization: Only authorized data returned
- Audit: Track who accessed what
```

---

## Types of APIs

### 1. REST APIs (Representational State Transfer)

**Most popular, uses HTTP methods**

```
Core Principles:
1. Client-Server: Separated concerns
2. Stateless: Server doesn't store client state
3. Cacheable: Responses can be cached
4. Uniform Interface: Consistent design
5. Layered: Can have intermediaries
```

**Example:**
```
GET /api/users           → Get all users
GET /api/users/123       → Get user 123
POST /api/users          → Create new user
PUT /api/users/123       → Update user 123
DELETE /api/users/123    → Delete user 123
PATCH /api/users/123     → Partial update
```

**Advantages:**
- ✅ Simple, HTTP-based
- ✅ Easy to test (works in browser)
- ✅ Stateless (scales well)
- ✅ Standard HTTP tools work
- ✅ Most popular (huge ecosystem)

**Disadvantages:**
- ❌ Over-fetching (get data you don't need)
- ❌ Under-fetching (need multiple requests)
- ❌ No real-time by default
- ❌ Fixed response format

---

### 2. GraphQL APIs

**Query language: Request exactly what you need**

```graphql
# Request (exactly what you want)
query {
  user(id: 123) {
    name
    email
    posts {
      title
    }
  }
}

# Response (matches request structure)
{
  "data": {
    "user": {
      "name": "John",
      "email": "john@example.com",
      "posts": [
        {"title": "First Post"}
      ]
    }
  }
}
```

**Advantages:**
- ✅ No over-fetching (get only what you request)
- ✅ No under-fetching (single request for related data)
- ✅ Strong typing
- ✅ Real-time subscriptions
- ✅ Mobile-friendly (bandwidth efficient)

**Disadvantages:**
- ❌ Complex to implement
- ❌ Harder to cache
- ❌ Learning curve
- ❌ File uploads complex
- ❌ Less mature than REST

**When to use:**
- ✅ Mobile apps (bandwidth matters)
- ✅ Complex data relationships
- ✅ Flexible frontend needs
- ✅ Multiple client types

---

### 3. SOAP APIs (Simple Object Access Protocol)

**XML-based, very formal (legacy)**

```xml
<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetUser xmlns="http://example.com">
      <userId>123</userId>
    </GetUser>
  </soap:Body>
</soap:Envelope>
```

**Advantages:**
- ✅ Strict standards
- ✅ Enterprise support
- ✅ Built-in security

**Disadvantages:**
- ❌ Verbose (large XML)
- ❌ Complex
- ❌ Slow
- ❌ Old (rarely used now)

**When used:**
- Legacy systems
- Banking (very strict standards)
- Healthcare (HIPAA compliance)
- Government systems

---

### 4. RPC APIs (Remote Procedure Call)

**Make function calls across network**

```json
POST /rpc

Request:
{
  "jsonrpc": "2.0",
  "method": "getUserById",
  "params": [123],
  "id": 1
}

Response:
{
  "jsonrpc": "2.0",
  "result": {
    "id": 123,
    "name": "John"
  },
  "id": 1
}
```

**Use cases:**
- ✅ Cryptocurrency (Bitcoin, Ethereum JSON-RPC)
- ✅ Blockchain interactions
- ✅ Simple function calls
- ✅ Notifications

**Advantages:**
- ✅ Simple (function call semantics)
- ✅ Good for blockchain

**Disadvantages:**
- ❌ Not HTTP semantic
- ❌ Less standard
- ❌ Harder to cache

---

### 5. Webhook APIs

**Server pushes data to you (instead of polling)**

```
Traditional (Polling - You ask repeatedly):
Your App → "Any messages?" → Server
Your App → "Any messages?" → Server (waste!)
Your App → "Any messages?" → Server (waste!)
Your App → "Any messages?" → Server (finally!)
         →  "Yes, you have new message"

Webhook (Pushing - Server tells you):
Your App (listening...)
                     ← Server: "You have new message!"

Benefits: Real-time, efficient, no polling
```

**Example: GitHub Webhook**
```
When code is pushed to repository:
GitHub → POST to your webhook URL

{
  "action": "pushed",
  "ref": "refs/heads/main",
  "commits": [...],
  "pusher": {"name": "john", "email": "john@example.com"}
}
```

**Use cases:**
- ✅ Real-time notifications
- ✅ Event-driven systems
- ✅ Integrations (Slack, Discord)
- ✅ CI/CD pipelines

---

## API Architecture

### Request-Response Cycle

```
1. Client Prepares Request
   ├─ URL: https://api.example.com/api/users/123
   ├─ Method: GET
   ├─ Headers: {"Authorization": "Bearer token"}
   └─ Body: (empty for GET)

2. Request Travels Over Network
   └─ HTTPS (secure)

3. Server Receives Request
   ├─ Parse URL
   ├─ Extract method
   ├─ Read headers
   └─ Read body

4. Server Processes
   ├─ Validate input
   ├─ Check authentication
   ├─ Check authorization
   ├─ Execute business logic
   ├─ Query database
   └─ Generate response

5. Server Prepares Response
   ├─ Status Code: 200
   ├─ Headers: {"Content-Type": "application/json"}
   └─ Body: {"id": 123, "name": "John"}

6. Response Travels Over Network
   └─ HTTPS (secure)

7. Client Receives Response
   ├─ Check status code
   ├─ Parse headers
   ├─ Parse body
   └─ Update UI
```

### API Endpoint Structure

```
https://api.example.com/v1/users/123/posts

├─ https://        → Protocol (secure)
├─ api              → API subdomain (optional)
├─ example.com      → Domain
├─ /v1              → API version
├─ /users           → Resource
├─ /123             → Resource ID
└─ /posts           → Sub-resource

Full endpoint identifies:
- Server: example.com
- Version: v1
- Resource: users
- Instance: 123
- Sub-resource: posts (user 123's posts)
```

### Request Headers

```
Common Request Headers:

Content-Type: application/json
  → Body is JSON format

Authorization: Bearer eyJhbGc...
  → Authentication token (JWT, OAuth, etc.)

Accept: application/json
  → Want response in JSON format

User-Agent: MyApp/1.0
  → Identify your client

X-Request-ID: abc-123-def
  → Unique ID to track request

X-Idempotency-Key: unique-id
  → Ensure request isn't duplicated if retried

Cache-Control: no-cache
  → Don't use cached version

If-None-Match: "abc123"
  → Only send if different from this ETag
```

### Response Headers

```
Common Response Headers:

Content-Type: application/json; charset=utf-8
  → Response format is JSON

Content-Length: 1234
  → Size of response body (bytes)

Cache-Control: max-age=3600
  → Browser can cache for 1 hour

ETag: "abc123def456"
  → Unique version ID for this response

X-RateLimit-Limit: 1000
  → API allows 1000 requests per period

X-RateLimit-Remaining: 999
  → 999 requests left in this period

X-RateLimit-Reset: 1709529600
  → Unix timestamp when limit resets

Set-Cookie: session=xyz789; Path=/
  → Store cookie in browser

Access-Control-Allow-Origin: *
  → CORS: Allow requests from any origin

Location: /api/users/456
  → Where new resource created (POST response)
```

---

## REST Fundamentals

### REST Constraints

```
1. Client-Server Constraint
   ├─ Client (makes requests)
   └─ Server (handles requests)
   Benefit: Can evolve independently

2. Statelessness Constraint
   ├─ Server doesn't store client context
   ├─ Each request has all info needed
   └─ Example: Include auth token in every request
   Benefit: Scales horizontally (any server can handle request)

3. Cacheability Constraint
   ├─ Responses explicitly marked cacheable/not-cacheable
   ├─ HTTP includes caching rules
   └─ Example: Cache-Control header
   Benefit: Reduce server load, improve performance

4. Uniform Interface Constraint
   ├─ Consistent design across API
   ├─ Resources identified by URL
   ├─ Manipulated via standard methods (GET, POST, etc.)
   └─ Self-descriptive messages
   Benefit: Easy to understand and use

5. Layered System Constraint
   ├─ Can have proxy, gateway, cache layers
   ├─ Client doesn't know if connected directly
   └─ Each layer does specific job
   Benefit: Scalability, security

6. Code on Demand Constraint (Optional)
   ├─ Server can send executable code
   ├─ Example: JavaScript for browser
   └─ Optional in REST
   Benefit: Extends client functionality
```

### Resource-Oriented Design

```
Everything is a Resource

Resources:
- Users
- Posts
- Comments
- Products
- Orders
- etc.

Each resource has:
1. Identity (ID)
   Example: User 123

2. Representation (Format)
   Example: JSON

3. Operations (Methods)
   GET (read)
   POST (create)
   PUT (update all)
   PATCH (update some)
   DELETE (delete)

Example:

Resource: User
Identity: 123
Operations:
  GET /api/users/123      → Read user 123
  PUT /api/users/123      → Replace user 123
  PATCH /api/users/123    → Update user 123
  DELETE /api/users/123   → Delete user 123
```

### RESTful Endpoint Naming Conventions

```
✅ GOOD (Resource-focused):

GET /api/users
  → Get list of users

GET /api/users/123
  → Get specific user

POST /api/users
  → Create new user

PUT /api/users/123
  → Replace user 123

PATCH /api/users/123
  → Update user 123

DELETE /api/users/123
  → Delete user 123

---

❌ BAD (Action-focused):

GET /api/getUsers
  → Resource name (users) should be in URL

POST /api/createUser
  → Method name (create) should be implied by POST

GET /api/getUserById?id=123
  → ID should be in path (/123), not query

PUT /api/updateUser
  → Resource name should be in URL

---

Rules for RESTful naming:
1. Use nouns, not verbs (/users not /getUsers)
2. Use plural names (/users not /user)
3. Use IDs for specific resources (/users/123)
4. Use HTTP methods for operations (POST, PUT, etc.)
5. Use query params for filtering, not actions
6. Use hyphens for multi-word (/user-profiles not /userProfiles)
```

---

## API Request Formats

### JSON Format (Most Common)

```json
POST /api/users HTTP/1.1
Host: api.example.com
Content-Type: application/json
Content-Length: 65

{
  "name": "John Doe",
  "email": "john@example.com",
  "age": 30
}
```

### XML Format (Legacy)

```xml
POST /api/users HTTP/1.1
Host: api.example.com
Content-Type: application/xml

<?xml version="1.0" encoding="UTF-8"?>
<User>
  <Name>John Doe</Name>
  <Email>john@example.com</Email>
  <Age>30</Age>
</User>
```

### Form Data (HTML Forms)

```
POST /api/users HTTP/1.1
Host: api.example.com
Content-Type: application/x-www-form-urlencoded

name=John+Doe&email=john@example.com&age=30
```

### Query Parameters (Filtering, Pagination)

```
GET /api/users?page=1&limit=10&sort=name&filter=active

Query string:
  page=1        → Which page
  limit=10      → Results per page
  sort=name     → Sort by name
  filter=active → Only active users
```

---

## Next Steps

This is Part 1: Fundamentals. In Part 2 we'll cover:
- ✅ HTTP Methods in detail
- ✅ HTTP Status Codes
- ✅ Creating APIs
- ✅ Using Public APIs
- ✅ Authentication
- ✅ Error Handling

Continue to the next file!

