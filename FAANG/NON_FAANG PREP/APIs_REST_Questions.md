# API Design & REST Interview Questions

Complete API and REST architecture interview prep.

---

## API Design Fundamentals (1-15)

### Q1: RESTful Design Principles

```
Principle 1: Client-Server Architecture
- Separation of concerns
- Independent evolution
- Example: Frontend, Backend, Mobile all talk to same API

Principle 2: Statelessness
- Server doesn't store client context
- Each request has all needed info
- Enables horizontal scaling
- Example: JWT token instead of session

Principle 3: Resource-Oriented
- Everything is a resource (users, posts, comments)
- Identified by URI
- Manipulated via standard methods
- Example: /api/users/123

Principle 4: Standard Methods
GET    - Retrieve (safe, idempotent)
POST   - Create (not idempotent)
PUT    - Replace (idempotent)
PATCH  - Partial update (idempotent)
DELETE - Remove (idempotent)

Principle 5: Representation
- Client receives resource representation
- JSON, XML, HTML formats
- Can have multiple versions
```

### Q2: API Versioning Strategies

```
Strategy 1: URL Path Versioning
/api/v1/users
/api/v2/users
Pro: Clear, easy to debug
Con: Multiple code paths

Strategy 2: Header Versioning
GET /api/users
Accept-Version: 2
Pro: Clean URLs
Con: Harder to test

Strategy 3: Query Parameter
/api/users?version=2
Pro: Works everywhere
Con: Less RESTful

Recommendation: URL path for public APIs
```

### Q3: Error Handling Standards

```python
# Good error response
HTTP 400 Bad Request
{
    "error": {
        "code": "INVALID_INPUT",
        "message": "Email is required",
        "details": {
            "field": "email",
            "reason": "missing"
        }
    }
}

# Bad error response
HTTP 400
{
    "error": "Invalid input"
}
```

### Q4: Authentication Methods

```
1. API Key
- Simple but limited
- No expiration by default
- Good for service-to-service

2. OAuth 2.0
- Industry standard
- Delegation without sharing password
- Token-based with refresh
- Best for user-facing APIs

3. JWT (JSON Web Token)
- Stateless authentication
- Self-contained claims
- Can verify without DB hit
- Good for internal services

4. Session-based
- Traditional approach
- Server stores session
- Not suitable for APIs
```

### Q5: Rate Limiting Implementation

```python
# Token Bucket Algorithm
class RateLimiter:
    def __init__(self, rate=100, per=60):  # 100 req per 60 sec
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
    
    def is_allowed(self, user_id):
        current = time.time()
        time_passed = current - self.last_check
        
        # Refill tokens
        self.allowance += time_passed * (self.rate / self.per)
        if self.allowance > self.rate:
            self.allowance = self.rate
        
        self.last_check = current
        
        # Check if request allowed
        if self.allowance >= 1:
            self.allowance -= 1
            return True
        return False

# Response headers
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 50
X-RateLimit-Reset: 1234567890
```

### Q6: Pagination Patterns

```
Offset-based:
/api/users?page=2&limit=10
Pro: Simple
Con: Inefficient for large offsets

Cursor-based:
/api/users?cursor=eyJpZCI6IDEyMzQ1fQ&limit=10
Pro: Efficient, handles data changes
Con: More complex

Keyset:
/api/users?start_id=1000&limit=10
Pro: Efficient for large datasets
Con: Can't skip pages

Recommendation: Cursor-based for scalability
```

### Q7: Caching Strategies

```
HTTP Caching Headers:
Cache-Control: max-age=3600      (Cache 1 hour)
Cache-Control: public             (Any cache can store)
Cache-Control: private            (Only browser cache)
ETag: "abc123def456"              (Resource version)
Last-Modified: Wed, 21 Oct 2024   (Last change time)

Client-side caching:
- Store responses in memory
- Invalidate on mutation
- Check freshness before use

Server-side caching:
- Redis for hot data
- CDN for static content
- Database query cache

Cache invalidation patterns:
1. TTL (Time To Live)
2. Event-based (when data changes)
3. Manual invalidation
```

### Q8-15: Additional Topics
**8. CORS (Cross-Origin Resource Sharing)**
**9. API Documentation (OpenAPI/Swagger)**
**10. Versioning & Backward Compatibility**
**11. Batch Operations**
**12. Webhooks vs Polling**
**13. API Gateway Architecture**
**14. GraphQL vs REST**
**15. Security Headers**

---

## Advanced API Design (16-20)

### Q16: API Gateway Pattern

```
Benefits:
- Single entry point
- Route to services
- Rate limiting
- Authentication
- Load balancing

Implementation:
Client → API Gateway → Service 1
                    → Service 2
                    → Service 3

Popular: Kong, AWS API Gateway, Nginx
```

### Q17: Idempotency in APIs

```python
# Make POST idempotent with Idempotency-Key header
POST /api/payments
Idempotency-Key: unique-transaction-id-123
{
    "amount": 100,
    "recipient": "user456"
}

# Server response (first call)
{
    "transaction_id": "txn_789",
    "status": "completed"
}

# Same request (retry)
# Server returns cached response without re-processing
```

### Q18: Webhook Architecture

```python
# Register webhook
POST /api/webhooks
{
    "event": "order.created",
    "url": "https://example.com/webhook/order"
}

# Server calls webhook when event occurs
POST https://example.com/webhook/order
{
    "event_type": "order.created",
    "timestamp": "2024-03-04T10:30:00Z",
    "data": {
        "order_id": "order_123",
        "amount": 99.99
    }
}

# Client should:
1. Verify signature
2. Return 200 quickly
3. Process async
4. Implement retry logic
```

### Q19: API Monitoring & Observability

```
Key Metrics:
- Requests per second
- Error rate
- Latency (p50, p95, p99)
- Status code distribution
- Dependency health

Tools:
- Prometheus (metrics)
- ELK Stack (logs)
- Jaeger (tracing)
- DataDog (monitoring)

Alerting:
- 5xx errors > 1% → Alert
- P99 latency > 1s → Alert
- Rate limit exceeded → Alert
```

### Q20: GraphQL for Data Engineers

```
When to use REST:
- Simple CRUD operations
- Standard HTTP semantics matter
- Caching important
- Fewer data relationships

When to use GraphQL:
- Complex data relationships
- Mobile clients (bandwidth)
- Multiple client types
- Evolving data needs

GraphQL Query:
{
  user(id: 123) {
    name
    posts {
      title
      comments {
        text
      }
    }
  }
}
```

---

## Interview Tips

✅ **When designing API:**
1. Clarify requirements
2. Choose appropriate style (REST vs GraphQL)
3. Design resource structure
4. Plan authentication
5. Consider rate limiting
6. Error handling
7. Versioning strategy
8. Documentation approach

✅ **Common mistakes:**
- No error handling discussion
- Ignoring authentication
- No rate limiting plan
- Poor version management
- Inadequate documentation

---

