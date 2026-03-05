# APIs Part 5: Authentication & Security

## API Keys

### How API Keys Work

```
1. You sign up for service
2. Service generates unique key for you
3. You include key in every request
4. Service validates key
5. Service applies your rate limits/permissions
6. Service tracks your usage
```

### Using API Keys

```python
import requests
import os

# Load from environment variable (SECURE!)
API_KEY = os.environ.get("OPENWEATHER_API_KEY")

# Include in request
response = requests.get(
    "https://api.openweathermap.org/data/2.5/weather",
    params={
        "q": "London",
        "appid": API_KEY
    }
)
```

### Storing API Keys Securely

```
❌ NEVER hardcode:
API_KEY = "abc123def456"

✅ ALWAYS use environment variables:
API_KEY = os.environ.get("API_KEY")

✅ Or use .env file:
# .env
OPENWEATHER_API_KEY=abc123def456
GITHUB_TOKEN=ghp_xyz789

# .gitignore (IMPORTANT!)
.env

# Python code
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENWEATHER_API_KEY")
```

### API Key Rotation

```python
# Periodically regenerate keys
# 1. Generate new key
# 2. Update environment variables
# 3. Delete old key
# 4. Monitor for errors

# Never keep old keys lying around!
```

---

## Bearer Tokens (OAuth 2.0)

### What is OAuth 2.0?

```
Flow: User logs in with their account

1. User clicks "Login with Google"
   ↓
2. Browser redirects to Google login
   ↓
3. User enters credentials
   ↓
4. Google asks "Allow this app to access your data?"
   ↓
5. User clicks "Allow"
   ↓
6. Google redirects back with authorization code
   ↓
7. App exchanges code for access token
   ↓
8. App uses token to access user's data
   ↓
9. User is logged in!

Benefits:
- User doesn't give password to your app
- User controls what data app can access
- User can revoke access anytime
- Google handles security
```

### Using Bearer Tokens

```python
import requests

# You received this token from OAuth login flow
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Accept": "application/json"
}

# Make request with token
response = requests.get(
    "https://api.example.com/user",
    headers=headers
)

if response.status_code == 401:
    print("Token expired, need to refresh")
elif response.status_code == 200:
    user = response.json()
    print(f"Logged in as {user['name']}")
```

---

## JWT (JSON Web Token)

### JWT Structure

```
JWT consists of 3 parts separated by dots:

header.payload.signature

Example:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

Part 1: Header (encrypted)
{
  "alg": "HS256",
  "typ": "JWT"
}

Part 2: Payload (encrypted)
{
  "sub": "1234567890",
  "name": "John Doe",
  "iat": 1516239022
}

Part 3: Signature (validates token wasn't tampered)
```

### Creating JWT Tokens

```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your_secret_key_keep_safe"

# Create token (server creates when user logs in)
payload = {
    "user_id": 123,
    "username": "john",
    "email": "john@example.com",
    "exp": datetime.utcnow() + timedelta(hours=24),  # Expires in 24 hours
    "iat": datetime.utcnow()  # Issued at
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(token)
# eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjogMTIzLCAidXNlcm5hbWU...
```

### Verifying JWT Tokens

```python
import jwt

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

try:
    # Verify and decode token
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    
    print(f"User ID: {payload['user_id']}")
    print(f"Username: {payload['username']}")
    
except jwt.ExpiredSignatureError:
    print("Token has expired")
except jwt.InvalidTokenError:
    print("Invalid token")
```

### Using JWT in API

```python
from flask import Flask, request, jsonify
import jwt
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

def token_required(f):
    """Decorator to require JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Format: "Bearer token"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid token format"}), 401
        
        if not token:
            return jsonify({"error": "Token required"}), 401
        
        try:
            # Verify and decode token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        
        return f(*args, **kwargs)
    
    return decorated

# Login endpoint - returns token
@app.route('/login', methods=['POST'])
def login():
    """Login and get JWT token"""
    data = request.get_json()
    
    # Verify credentials (simplified)
    if data['username'] == 'john' and data['password'] == 'password123':
        token = jwt.encode({
            'user_id': 1,
            'username': 'john',
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({'token': token}), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

# Protected endpoint - requires token
@app.route('/protected', methods=['GET'])
@token_required
def protected_route():
    """Only accessible with valid token"""
    return jsonify({
        'message': f'Hello user {request.user_id}'
    }), 200
```

### Token Refresh

```python
@app.route('/refresh', methods=['POST'])
@token_required
def refresh_token():
    """Get new token"""
    # Create new token with new expiration
    token = jwt.encode({
        'user_id': request.user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({'token': token}), 200
```

---

## HTTPS/TLS Encryption

### Why HTTPS?

```
HTTP (No encryption):
Client: "My API key is abc123"
        ↓ (visible on network)
Server

Anyone on network can see: API key, passwords, personal data!

HTTPS (Encrypted):
Client: "My API key is ***encrypted***"
        ↓ (encrypted, only server can decrypt)
Server

Only client and server can see data!
```

### Using HTTPS in Python

```python
import requests

# ✅ ALWAYS use HTTPS for APIs
response = requests.get("https://api.example.com/data")

# ❌ NEVER use HTTP for sensitive data
response = requests.get("http://api.example.com/data")  # WRONG!
```

### Certificate Verification

```python
import requests

# ✅ Verify certificate (default, recommended)
response = requests.get("https://api.example.com/data")

# ❌ NEVER disable verification (security risk!)
response = requests.get(
    "https://api.example.com/data",
    verify=False  # WRONG! Don't do this
)

# Use custom CA certificate if needed
response = requests.get(
    "https://api.example.com/data",
    verify='/path/to/ca-bundle.crt'
)
```

---

## API Security Best Practices

### 1. Input Validation

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    # Validate required fields
    if not data or 'email' not in data:
        return jsonify({"error": "Email required"}), 400
    
    # Validate email format
    if '@' not in data['email']:
        return jsonify({"error": "Invalid email"}), 400
    
    # Validate length
    if len(data['email']) > 255:
        return jsonify({"error": "Email too long"}), 400
    
    # Validate type
    if not isinstance(data['email'], str):
        return jsonify({"error": "Email must be string"}), 400
    
    return jsonify({"id": 1, "email": data['email']}), 201
```

### 2. Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/users')
@limiter.limit("10 per minute")
def get_users():
    return jsonify([])

# Client exceeding limit gets:
# HTTP 429 Too Many Requests
# Retry-After: 60
```

### 3. CORS (Cross-Origin Resource Sharing)

```python
from flask_cors import CORS

app = Flask(__name__)

# Restrict to specific origins
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://example.com", "https://app.example.com"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }
})
```

### 4. SQL Injection Prevention

```python
❌ NEVER do this:
query = f"SELECT * FROM users WHERE id = {user_id}"
db.execute(query)

✅ ALWAYS use parameterized queries:
query = "SELECT * FROM users WHERE id = ?"
db.execute(query, (user_id,))
```

### 5. Secrets Management

```python
# ✅ Use environment variables
import os
db_password = os.environ.get("DATABASE_PASSWORD")

# ✅ Use .env files (add to .gitignore!)
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("API_KEY")

# ✅ Use secret management services
# AWS Secrets Manager
# Google Cloud Secret Manager
# HashiCorp Vault
# Azure Key Vault
```

### 6. Logging and Monitoring

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    try:
        # Fetch user
        user = db.get_user(user_id)
        logger.info(f"User {user_id} accessed")
        return jsonify(user)
    except Exception as e:
        logger.error(f"Error accessing user {user_id}: {e}")
        return jsonify({"error": "Internal error"}), 500
```

### 7. Error Messages

```python
# ❌ TOO MUCH INFO (Security risk!)
try:
    user = db.query(f"SELECT * FROM users WHERE id = {id}")
except Exception as e:
    return jsonify({"error": str(e)}), 500
    # Attacker sees: "ERROR: relation 'users' does not exist"

# ✅ GENERIC MESSAGE (Secure)
try:
    user = get_user(id)
except Exception as e:
    logger.error(f"Database error: {e}")
    return jsonify({"error": "Internal server error"}), 500
    # Attacker only sees: "Internal server error"
```

---

## Security Checklist

```
☐ Use HTTPS for all API calls
☐ Store secrets in environment variables
☐ Validate all inputs
☐ Don't expose internal error messages
☐ Implement rate limiting
☐ Use authentication (API key, OAuth, JWT)
☐ Log all access/errors
☐ Keep dependencies updated
☐ Use parameterized queries (no SQL injection)
☐ Implement CORS correctly
☐ Set secure headers
☐ Monitor for suspicious activity
☐ Regular security audits
☐ Educate team on security
```

---

## Common Security Mistakes

```
❌ Storing passwords in plaintext
✅ Use hashing (bcrypt, argon2)

❌ Logging sensitive data
✅ Mask passwords, tokens in logs

❌ Using weak API keys
✅ Generate strong random keys

❌ No expiration on tokens
✅ Set reasonable expiration times

❌ Same key for all environments
✅ Different key for dev, staging, prod

❌ Committing secrets to Git
✅ Use .gitignore, environment variables

❌ Trusting user input
✅ Always validate and sanitize
```

---

## Next Steps

You now understand:
- ✅ How APIs work
- ✅ HTTP methods and status codes
- ✅ Creating APIs
- ✅ Using public APIs
- ✅ Authentication and security

Practice by:
1. Using public APIs (GitHub, Weather, etc.)
2. Create simple APIs (Flask, FastAPI)
3. Add authentication (API keys, JWT)
4. Deploy to cloud (Heroku, AWS, Google Cloud)
5. Monitor and secure

Happy API coding! 🚀

