# APIs Part 2: HTTP Methods & Status Codes (Complete Guide)

## HTTP Methods (Verbs)

HTTP defines methods for performing actions on resources.

---

## GET - Retrieve Data

**Purpose:** Fetch data from server without modifying anything

**Key Properties:**
- **Safe:** Doesn't change server state
- **Idempotent:** Same result no matter how many times called
- **Cacheable:** Can be cached
- **No Body:** GET requests don't have request body

### Examples

```
Example 1: Get all users
GET /api/users HTTP/1.1
Host: api.example.com

Response (200 OK):
[
  {"id": 1, "name": "Alice"},
  {"id": 2, "name": "Bob"},
  {"id": 3, "name": "Charlie"}
]
```

```
Example 2: Get specific user
GET /api/users/1 HTTP/1.1
Host: api.example.com

Response (200 OK):
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com",
  "created_at": "2024-01-15"
}
```

```
Example 3: Get with query parameters (filtering)
GET /api/users?role=admin&active=true HTTP/1.1
Host: api.example.com

Query params:
  role=admin   → Only admin users
  active=true  → Only active users

Response (200 OK):
[
  {"id": 1, "name": "Alice", "role": "admin", "active": true}
]
```

```
Example 4: Get with pagination
GET /api/users?page=2&limit=10 HTTP/1.1
Host: api.example.com

Query params:
  page=2   → Get page 2
  limit=10 → 10 results per page

Response (200 OK):
{
  "data": [...10 users...],
  "pagination": {
    "page": 2,
    "limit": 10,
    "total": 150,
    "pages": 15
  }
}
```

### When to use GET
- ✅ Retrieve data
- ✅ Search/filter data
- ✅ Pagination
- ✅ Fetch list of resources
- ✅ Fetch single resource details

### When NOT to use GET
- ❌ Creating data (use POST)
- ❌ Updating data (use PUT/PATCH)
- ❌ Deleting data (use DELETE)
- ❌ Sensitive data in query params (use POST instead)

---

## POST - Create Data

**Purpose:** Create new resource

**Key Properties:**
- **Not Safe:** Creates/modifies data on server
- **Not Idempotent:** Calling twice creates 2 resources
- **Cacheable:** Only with specific headers
- **Has Body:** POST includes request body with data

### Examples

```
Example 1: Create new user
POST /api/users HTTP/1.1
Host: api.example.com
Content-Type: application/json
Content-Length: 65

{
  "name": "David",
  "email": "david@example.com",
  "role": "user"
}

Response (201 Created):
{
  "id": 4,
  "name": "David",
  "email": "david@example.com",
  "role": "user",
  "created_at": "2024-03-04T10:30:00Z"
}

Note: Server returns 201 (Created) and includes created resource
Location header: /api/users/4
```

```
Example 2: Create nested resource
POST /api/users/1/posts HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "title": "My First Post",
  "content": "This is great!",
  "tags": ["python", "api"]
}

Response (201 Created):
{
  "id": 1,
  "user_id": 1,
  "title": "My First Post",
  "content": "This is great!",
  "tags": ["python", "api"],
  "created_at": "2024-03-04T10:30:00Z"
}
```

```
Example 3: Create with minimal data
POST /api/posts HTTP/1.1
Content-Type: application/json

{
  "title": "Post Title"
}

Response (201 Created):
{
  "id": 5,
  "title": "Post Title",
  "content": "",
  "published": false,
  "created_at": "2024-03-04T10:30:00Z"
}

Note: Server can use defaults for missing fields
```

### When to use POST
- ✅ Create new resource
- ✅ Send data that shouldn't be in URL
- ✅ Large data in body
- ✅ File uploads
- ✅ Complex operations

### Common Response Codes for POST
- **201 Created:** Resource created successfully
- **400 Bad Request:** Invalid data
- **401 Unauthorized:** Not authenticated
- **403 Forbidden:** Not authorized
- **409 Conflict:** Resource already exists

---

## PUT - Replace Entire Resource

**Purpose:** Replace entire resource (all fields)

**Key Properties:**
- **Not Safe:** Modifies data
- **Idempotent:** Calling twice has same effect
- **Has Body:** Includes complete resource
- **Must be Complete:** Send all fields (those not sent are deleted)

### Examples

```
Example 1: Replace entire user
PUT /api/users/1 HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "name": "Alice Updated",
  "email": "alice.new@example.com",
  "role": "admin"
}

Response (200 OK):
{
  "id": 1,
  "name": "Alice Updated",
  "email": "alice.new@example.com",
  "role": "admin"
}

Important: If you don't send a field, it might be deleted or set to default
```

```
Example 2: Complete replacement (all fields required)
Current user:
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com",
  "phone": "555-1234",
  "role": "user",
  "active": true
}

PUT /api/users/1 HTTP/1.1
{
  "name": "Alice Updated",
  "email": "alice.new@example.com",
  "role": "admin"
}

Result: Missing fields (phone, active) might be:
- Deleted
- Set to null
- Set to default

To avoid issues, send ALL fields:
{
  "name": "Alice Updated",
  "email": "alice.new@example.com",
  "phone": "555-1234",
  "role": "admin",
  "active": true
}
```

### When to use PUT
- ✅ Replace entire resource
- ✅ When you want to overwrite everything
- ✅ Full data updates

### When NOT to use PUT
- ❌ Partial updates (use PATCH)
- ❌ When you don't have all fields
- ❌ Creating new resources (use POST)

---

## PATCH - Partial Update

**Purpose:** Update only specified fields (partial update)

**Key Properties:**
- **Not Safe:** Modifies data
- **Should be Idempotent:** Calling twice has same effect
- **Has Body:** Only includes fields to update
- **Partial:** Send only what's changing

### Examples

```
Example 1: Update only email
PATCH /api/users/1 HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "email": "alice.new@example.com"
}

Response (200 OK):
{
  "id": 1,
  "name": "Alice",
  "email": "alice.new@example.com",
  "phone": "555-1234",
  "role": "user",
  "active": true
}

Note: Only email changed, other fields untouched
```

```
Example 2: Update multiple fields
PATCH /api/users/1 HTTP/1.1
Content-Type: application/json

{
  "email": "alice.new@example.com",
  "role": "admin",
  "phone": "555-9999"
}

Response (200 OK):
{
  "id": 1,
  "name": "Alice",
  "email": "alice.new@example.com",
  "phone": "555-9999",
  "role": "admin",
  "active": true
}

Note: Only specified fields updated
```

```
Example 3: Update nested/array fields
Current:
{
  "id": 1,
  "name": "Alice",
  "tags": ["python", "java"]
}

PATCH /api/users/1 HTTP/1.1
{
  "tags": ["python", "javascript"]
}

Response:
{
  "id": 1,
  "name": "Alice",
  "tags": ["python", "javascript"]
}
```

### When to use PATCH
- ✅ Partial updates
- ✅ Update single or few fields
- ✅ When you don't have complete data
- ✅ More efficient than PUT

### PATCH vs PUT

```
Original:
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com",
  "role": "user"
}

PUT /api/users/1 with {"name": "Alice2"}
Result: Only name changed, others become NULL/default

PATCH /api/users/1 with {"name": "Alice2"}
Result: Only name changed, others preserved
```

---

## DELETE - Remove Resource

**Purpose:** Delete resource

**Key Properties:**
- **Not Safe:** Deletes data
- **Idempotent:** Deleting twice is same as once
- **May Have Body:** Usually no body (or minimal metadata)

### Examples

```
Example 1: Simple delete
DELETE /api/users/1 HTTP/1.1
Host: api.example.com

Response (204 No Content):
(no body)

Or with body:

Response (200 OK):
{
  "message": "User deleted successfully",
  "deleted_id": 1
}
```

```
Example 2: Delete with confirmation
DELETE /api/users/1 HTTP/1.1
Content-Type: application/json

{
  "reason": "User requested deletion",
  "confirm_password": "hashed_password"
}

Response (200 OK):
{
  "message": "User deleted",
  "deleted_at": "2024-03-04T10:30:00Z"
}
```

```
Example 3: Delete not found
DELETE /api/users/9999 HTTP/1.1

Response (404 Not Found):
{
  "error": "User not found"
}
```

### When to use DELETE
- ✅ Delete resource
- ✅ Delete collection (all items)
- ✅ Remove data

### Common Response Codes for DELETE
- **204 No Content:** Deleted successfully, no response body
- **200 OK:** Deleted successfully, response body with details
- **404 Not Found:** Resource doesn't exist
- **403 Forbidden:** Not authorized to delete

---

## Other HTTP Methods

### HEAD - Like GET but no body

```
HEAD /api/users/1 HTTP/1.1
Host: api.example.com

Response (200 OK):
Content-Type: application/json
Content-Length: 234
Cache-Control: max-age=3600

(no body)

Use: Check if resource exists, get headers without data
```

### OPTIONS - Describe communication options

```
OPTIONS /api/users HTTP/1.1
Host: api.example.com

Response (200 OK):
Allow: GET, POST, PUT, PATCH, DELETE, OPTIONS

Use: CORS preflight, discover available methods
```

---

## HTTP Status Codes

### 2xx - Success

```
200 OK - Request succeeded
  ├─ GET returns data
  ├─ POST with created response
  ├─ PUT with updated data
  └─ DELETE with metadata response

201 Created - Resource created
  ├─ POST created new resource
  ├─ Response includes created resource
  └─ Location header: /api/users/123

202 Accepted - Request accepted, processing
  ├─ Long-running operation
  ├─ Return job ID
  └─ Client can check status later

204 No Content - Success, no response body
  ├─ DELETE successful
  ├─ PATCH/PUT with no data to return
  └─ Used when response body not needed

206 Partial Content - Partial response
  ├─ Resumable download
  ├─ Range request
  └─ Content-Range header included
```

### 3xx - Redirection

```
301 Moved Permanently - Resource moved
  ├─ Update bookmarks
  ├─ /users → /api/v2/users
  └─ Redirect permanently

302 Found - Temporary redirect
  ├─ Resource temporarily elsewhere
  ├─ Try original URL next time
  └─ Example: Redirect to login

304 Not Modified - Cached version is current
  ├─ Client has current version
  ├─ ETag matches
  ├─ Saves bandwidth
  └─ No response body

307 Temporary Redirect - Preserve method
  ├─ Like 302 but preserve HTTP method
  ├─ POST stays POST (302 might change to GET)
  └─ Used for temporary moves
```

### 4xx - Client Error

```
400 Bad Request - Malformed request
  ├─ Invalid JSON
  ├─ Missing required fields
  ├─ Invalid data format
  └─ Client should fix and retry

401 Unauthorized - Authentication required
  ├─ No authentication provided
  ├─ Invalid credentials
  ├─ Missing token
  └─ Client should authenticate first

403 Forbidden - Authenticated but not authorized
  ├─ User doesn't have permission
  ├─ Example: Regular user deleting admin
  ├─ Client can't fix this
  └─ Contact admin for access

404 Not Found - Resource doesn't exist
  ├─ Wrong URL
  ├─ Resource deleted
  ├─ ID doesn't exist
  └─ Client should check URL or ID

409 Conflict - Request conflicts with existing state
  ├─ Duplicate email on create
  ├─ Version conflict
  ├─ Creating with existing ID
  └─ Client must resolve conflict

429 Too Many Requests - Rate limited
  ├─ Exceeded API limits
  ├─ X-RateLimit-Reset header
  ├─ Client should wait and retry
  └─ Check X-RateLimit-* headers
```

### 5xx - Server Error

```
500 Internal Server Error - Server error
  ├─ Unexpected error
  ├─ Developer should check logs
  ├─ Client should retry
  └─ Could be temporary

502 Bad Gateway - Invalid upstream response
  ├─ Server received bad response
  ├─ Temporary issue
  └─ Retry should work

503 Service Unavailable - Server down
  ├─ Maintenance
  ├─ Overloaded
  └─ Retry after delay

504 Gateway Timeout - Upstream not responding
  ├─ Upstream server too slow
  ├─ Request timeout
  └─ Client can retry
```

---

## Summary: Which Method to Use?

```
GET     → Retrieve data (read only)
POST    → Create new resource
PUT     → Replace entire resource
PATCH   → Update partial resource
DELETE  → Delete resource
HEAD    → Get headers only
OPTIONS → Get allowed methods

Safe Methods (don't modify): GET, HEAD, OPTIONS
Idempotent (can call multiple times): GET, PUT, DELETE
Not Idempotent (different each time): POST, PATCH
```

---

## Real-World Examples

### Create, Read, Update, Delete (CRUD) Full Example

```
1. CREATE - POST /api/users
   Request: {name: "John", email: "john@example.com"}
   Response: 201 Created {id: 1, name: "John", ...}

2. READ - GET /api/users/1
   Response: 200 OK {id: 1, name: "John", ...}

3. UPDATE - PATCH /api/users/1
   Request: {email: "john.new@example.com"}
   Response: 200 OK {id: 1, name: "John", email: "john.new@example.com"}

4. DELETE - DELETE /api/users/1
   Response: 204 No Content
```

### Collection Operations

```
GET /api/users
  → Get all users (200 OK)

POST /api/users
  → Create new user (201 Created)

GET /api/users?role=admin
  → Get filtered users (200 OK)

DELETE /api/users?role=inactive
  → Delete all inactive users (204 No Content)
```

Continue to Part 3: Creating and Using APIs!

