# APIs Part 3: Creating Your Own REST APIs

## Framework Comparison

### Python Frameworks for APIs

```
Framework      Complexity   Speed    Learning   Best For
Flask          Low          Medium   Easy       Simple APIs, Learning
FastAPI        Medium       Fast     Medium     Modern APIs, Auto-docs
Django REST    High         Slow     Hard       Large projects
Bottle         Very Low     Medium   Easy       Micro APIs
Pyramid        High         Slow     Hard       Complex large apps
```

We'll focus on **Flask** (easiest) and **FastAPI** (most modern).

---

## Creating API with Flask

### Installation

```bash
pip install flask
```

### Simple Flask API (Complete Example)

```python
# app.py

from flask import Flask, request, jsonify
from datetime import datetime
import uuid

app = Flask(__name__)

# In-memory database (for demo, use real DB in production)
users = {
    1: {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "created_at": "2024-01-01T10:00:00Z"
    },
    2: {
        "id": 2,
        "name": "Bob",
        "email": "bob@example.com",
        "created_at": "2024-01-02T10:00:00Z"
    }
}

next_id = 3

# ============== GET Endpoints ==============

@app.route('/api/users', methods=['GET'])
def get_all_users():
    """Get all users with optional pagination"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    # Validate pagination
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 10
    
    # Calculate offset
    all_users = list(users.values())
    offset = (page - 1) * limit
    
    return jsonify({
        "data": all_users[offset:offset + limit],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": len(all_users)
        }
    }), 200

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get specific user by ID"""
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify(users[user_id]), 200

# ============== POST Endpoint ==============

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create new user"""
    global next_id
    
    # Get JSON data
    data = request.get_json()
    
    # Validate required fields
    if not data:
        return jsonify({"error": "Request body required"}), 400
    
    if 'name' not in data or 'email' not in data:
        return jsonify({"error": "name and email required"}), 400
    
    # Validate email format
    if '@' not in data['email']:
        return jsonify({"error": "Invalid email format"}), 400
    
    # Check for duplicate email
    for user in users.values():
        if user['email'] == data['email']:
            return jsonify({"error": "Email already exists"}), 409
    
    # Create new user
    new_user = {
        "id": next_id,
        "name": data['name'],
        "email": data['email'],
        "created_at": datetime.now().isoformat() + 'Z'
    }
    
    users[next_id] = new_user
    next_id += 1
    
    return jsonify(new_user), 201

# ============== PUT Endpoint ==============

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update entire user (PUT)"""
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json()
    
    # Validate required fields (PUT requires all)
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({"error": "name and email required"}), 400
    
    # Update user
    users[user_id] = {
        "id": user_id,
        "name": data['name'],
        "email": data['email'],
        "created_at": users[user_id]['created_at'],
        "updated_at": datetime.now().isoformat() + 'Z'
    }
    
    return jsonify(users[user_id]), 200

# ============== PATCH Endpoint ==============

@app.route('/api/users/<int:user_id>', methods=['PATCH'])
def partial_update_user(user_id):
    """Partially update user (PATCH)"""
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Update only provided fields
    if 'name' in data:
        users[user_id]['name'] = data['name']
    if 'email' in data:
        users[user_id]['email'] = data['email']
    
    users[user_id]['updated_at'] = datetime.now().isoformat() + 'Z'
    
    return jsonify(users[user_id]), 200

# ============== DELETE Endpoint ==============

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user"""
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    deleted_user = users.pop(user_id)
    
    return jsonify({
        "message": "User deleted successfully",
        "deleted": deleted_user
    }), 200

# ============== Error Handlers ==============

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ============== Info Endpoint ==============

@app.route('/api/info', methods=['GET'])
def api_info():
    """API info endpoint"""
    return jsonify({
        "name": "User API",
        "version": "1.0.0",
        "endpoints": {
            "users": "/api/users",
            "user": "/api/users/{id}"
        }
    }), 200

# ============== Run Server ==============

if __name__ == '__main__':
    # debug=True: auto-reload on code change, better error messages
    # port=5000: Run on port 5000
    app.run(debug=True, port=5000)
```

### Using the Flask API

```bash
# Start server
python app.py
# Output: Running on http://127.0.0.1:5000

# In another terminal, test the API:

# 1. GET all users
curl http://localhost:5000/api/users
# Response:
# {
#   "data": [
#     {"id": 1, "name": "Alice", "email": "alice@example.com", ...},
#     {"id": 2, "name": "Bob", "email": "bob@example.com", ...}
#   ],
#   "pagination": {"page": 1, "limit": 10, "total": 2}
# }

# 2. GET specific user
curl http://localhost:5000/api/users/1
# Response: {"id": 1, "name": "Alice", "email": "alice@example.com", ...}

# 3. GET with pagination
curl "http://localhost:5000/api/users?page=1&limit=1"
# Response: Only 1 user per page

# 4. CREATE new user
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Charlie", "email": "charlie@example.com"}'
# Response (201): {"id": 3, "name": "Charlie", "email": "charlie@example.com", ...}

# 5. UPDATE entire user (PUT)
curl -X PUT http://localhost:5000/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Updated", "email": "alice.new@example.com"}'
# Response (200): {"id": 1, "name": "Alice Updated", ...}

# 6. PARTIAL UPDATE user (PATCH)
curl -X PATCH http://localhost:5000/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"email": "alice.final@example.com"}'
# Response (200): Only email changed

# 7. DELETE user
curl -X DELETE http://localhost:5000/api/users/1
# Response (200): {"message": "User deleted successfully", ...}

# 8. Get API info
curl http://localhost:5000/api/info
# Response: API metadata
```

---

## Creating API with FastAPI (Modern)

### Installation

```bash
pip install fastapi uvicorn
```

### Complete FastAPI Example

```python
# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Initialize app
app = FastAPI(
    title="User API",
    description="API for managing users",
    version="1.0.0"
)

# ============== Data Models ==============

class UserRole(str, Enum):
    """User roles"""
    admin = "admin"
    user = "user"
    guest = "guest"

class UserBase(BaseModel):
    """User base model"""
    name: str
    email: str
    role: UserRole = UserRole.user

class UserCreate(UserBase):
    """User creation model"""
    pass

class UserUpdate(BaseModel):
    """User update model (partial)"""
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None

class User(UserBase):
    """User response model"""
    id: int
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "role": "user",
                "created_at": "2024-03-04T10:00:00"
            }
        }

# ============== Database ==============

users_db = {
    1: {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "role": "admin",
        "created_at": datetime.now()
    },
    2: {
        "id": 2,
        "name": "Bob",
        "email": "bob@example.com",
        "role": "user",
        "created_at": datetime.now()
    }
}

next_id = 3

# ============== GET Endpoints ==============

@app.get("/api/users", response_model=List[User])
def get_all_users(
    skip: int = 0,
    limit: int = 10
):
    """
    Get all users
    
    Query parameters:
    - skip: Number of users to skip (pagination)
    - limit: Number of users to return
    """
    users_list = list(users_db.values())
    return users_list[skip:skip + limit]

@app.get("/api/users/{user_id}", response_model=User)
def get_user(user_id: int):
    """Get specific user by ID"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    return users_db[user_id]

# ============== POST Endpoint ==============

@app.post("/api/users", response_model=User, status_code=201)
def create_user(user: UserCreate):
    """Create new user"""
    global next_id
    
    # Check for duplicate email
    for existing_user in users_db.values():
        if existing_user['email'] == user.email:
            raise HTTPException(
                status_code=409,
                detail="Email already exists"
            )
    
    # Create new user
    new_user = {
        "id": next_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": datetime.now()
    }
    
    users_db[next_id] = new_user
    next_id += 1
    
    return new_user

# ============== PUT Endpoint ==============

@app.put("/api/users/{user_id}", response_model=User)
def update_user(user_id: int, user: UserCreate):
    """Update entire user"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    
    updated_user = {
        "id": user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": users_db[user_id]['created_at']
    }
    
    users_db[user_id] = updated_user
    return updated_user

# ============== PATCH Endpoint ==============

@app.patch("/api/users/{user_id}", response_model=User)
def partial_update_user(user_id: int, user: UserUpdate):
    """Partially update user"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    
    existing_user = users_db[user_id]
    
    # Update only provided fields
    update_data = user.dict(exclude_unset=True)
    updated_user = {**existing_user, **update_data}
    
    users_db[user_id] = updated_user
    return updated_user

# ============== DELETE Endpoint ==============

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    """Delete user"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    
    deleted = users_db.pop(user_id)
    return {
        "message": "User deleted successfully",
        "deleted": deleted
    }

# ============== Root Endpoint ==============

@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "Welcome to User API",
        "docs": "/docs",
        "redocs": "/redocs"
    }

# Run: uvicorn main.py --reload
# Access docs: http://localhost:8000/docs
# Access redoc: http://localhost:8000/redoc
```

### Running FastAPI

```bash
# Install uvicorn (ASGI server)
pip install uvicorn

# Run server with auto-reload
uvicorn main.py --reload
# Output: Uvicorn running on http://127.0.0.1:8000

# Access interactive documentation
# Browser: http://localhost:8000/docs
# (Swagger UI - try out endpoints visually!)

# Alternative documentation
# Browser: http://localhost:8000/redoc
# (ReDoc - better for reading)
```

### Testing FastAPI with Python

```python
# test_api.py

import requests

BASE_URL = "http://localhost:8000/api"

# 1. GET all users
response = requests.get(f"{BASE_URL}/users")
print(response.json())

# 2. CREATE user
response = requests.post(
    f"{BASE_URL}/users",
    json={"name": "Charlie", "email": "charlie@example.com", "role": "user"}
)
print(response.status_code)  # 201
print(response.json())

# 3. GET specific user
response = requests.get(f"{BASE_URL}/users/1")
print(response.json())

# 4. PATCH user
response = requests.patch(
    f"{BASE_URL}/users/1",
    json={"email": "alice.new@example.com"}
)
print(response.json())

# 5. DELETE user
response = requests.delete(f"{BASE_URL}/users/1")
print(response.status_code)  # 200
```

---

## Best Practices for API Creation

### 1. Validation

```python
from pydantic import BaseModel, EmailStr, Field

class User(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr  # Validates email format
    age: int = Field(..., ge=0, le=150)  # Between 0-150
    role: str = Field(..., pattern="^(admin|user|guest)$")
```

### 2. Error Handling

```python
from fastapi import HTTPException

try:
    # Do something
    pass
except ValueError as e:
    raise HTTPException(
        status_code=400,
        detail=str(e)
    )
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

### 3. Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

@app.get("/api/protected")
def protected_endpoint(credentials: HTTPAuthCredentials = Depends(security)):
    token = credentials.credentials
    # Validate token
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"message": "Access granted"}
```

### 4. CORS (Cross-Origin Resource Sharing)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com", "https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 5. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/users")
@limiter.limit("10/minute")
def get_users(request: Request):
    return []
```

---

## Next: Using Public APIs

Continue to Part 4 for using existing public APIs!

