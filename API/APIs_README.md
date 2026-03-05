# APIs & HTTP Requests: Complete Comprehensive Guide

## Overview

This comprehensive guide covers everything you need to know about APIs and HTTP requests:

### 📚 Files in This Guide

1. **01_APIs_Fundamentals.md** (Foundational)
   - What is an API?
   - Why APIs matter
   - Types of APIs (REST, GraphQL, SOAP, RPC, Webhooks)
   - API architecture
   - REST fundamentals
   - **Read time: 20-30 minutes**

2. **02_HTTP_Methods_StatusCodes.md** (Essential)
   - HTTP Methods (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
   - Detailed examples for each method
   - HTTP Status Codes (2xx, 3xx, 4xx, 5xx)
   - When to use each method
   - **Read time: 20-30 minutes**

3. **03_Creating_APIs.md** (Practical)
   - Flask framework (simple, lightweight)
   - FastAPI framework (modern, auto-docs)
   - Complete working examples
   - Testing APIs
   - Best practices
   - **Read time: 30-40 minutes**

4. **04_Using_Public_APIs.md** (Hands-On)
   - Requests library tutorial
   - Popular public APIs (OpenWeatherMap, GitHub, JSONPlaceholder)
   - Query parameters
   - Headers and body
   - Error handling
   - Real-world examples
   - **Read time: 25-35 minutes**

5. **05_Authentication_Security.md** (Important)
   - API Keys
   - Bearer Tokens (OAuth 2.0)
   - JWT (JSON Web Tokens)
   - HTTPS/TLS encryption
   - Security best practices
   - Common mistakes
   - **Read time: 25-35 minutes**

---

## Quick Start (5-Minute Overview)

### What is an API?

An API is a set of rules that allows different applications to communicate. Think of it as a waiter in a restaurant:
- You (client) make an order (request)
- Waiter (API) takes the order to kitchen
- Kitchen (server) prepares food
- Waiter brings food back to you (response)

### Common API Types

**REST API** (Most popular)
```
GET /api/users           → Get users
POST /api/users          → Create user
PUT /api/users/1         → Update user
DELETE /api/users/1      → Delete user
```

**HTTP Status Codes**
```
200 OK              → Success
201 Created         → Resource created
400 Bad Request     → Invalid input
401 Unauthorized    → Need authentication
404 Not Found       → Resource doesn't exist
429 Too Many Requests → Rate limited
500 Server Error    → Server error
```

---

## Recommended Learning Path

### For Complete Beginners
1. Start with **01_APIs_Fundamentals.md**
2. Read **02_HTTP_Methods_StatusCodes.md**
3. Try examples in **04_Using_Public_APIs.md**
4. Then learn **03_Creating_APIs.md**
5. Finally read **05_Authentication_Security.md**

### For Experienced Developers
1. Skim **01_APIs_Fundamentals.md**
2. Quick review of **02_HTTP_Methods_StatusCodes.md**
3. Jump to **03_Creating_APIs.md**
4. Reference **04_Using_Public_APIs.md** as needed
5. Deep dive **05_Authentication_Security.md**

### For Quick Reference
Use **02_HTTP_Methods_StatusCodes.md** as a quick reference for:
- What HTTP method to use
- What status code to return
- Examples for each

---

## Key Concepts

### REST API Principles

```
1. Client-Server: Separated concerns
2. Stateless: No client context stored
3. Cacheable: Can cache responses
4. Uniform Interface: Consistent design
5. Layered: Can have proxy/gateway layers
```

### HTTP Methods

| Method | Purpose | Body | Idempotent | Safe |
|--------|---------|------|------------|------|
| GET | Retrieve | No | ✅ | ✅ |
| POST | Create | Yes | ❌ | ❌ |
| PUT | Replace | Yes | ✅ | ❌ |
| PATCH | Update | Yes | ✅ | ❌ |
| DELETE | Delete | No | ✅ | ❌ |

### HTTP Status Code Ranges

| Range | Meaning | Examples |
|-------|---------|----------|
| 2xx | Success | 200, 201, 204 |
| 3xx | Redirect | 301, 302, 304 |
| 4xx | Client Error | 400, 401, 404, 429 |
| 5xx | Server Error | 500, 502, 503 |

---

## Hands-On Exercises

### Exercise 1: Use a Public API (30 minutes)

```python
import requests

# 1. Get GitHub user info
response = requests.get("https://api.github.com/users/octocat")
print(response.json())

# 2. Get GitHub repositories
response = requests.get("https://api.github.com/users/octocat/repos")
print(response.json())

# 3. Try OpenWeatherMap API (after getting free API key)
API_KEY = "your_key_here"
response = requests.get(
    "https://api.openweathermap.org/data/2.5/weather",
    params={"q": "London", "appid": API_KEY}
)
print(response.json())
```

### Exercise 2: Create Simple API (1 hour)

Using Flask:
```python
from flask import Flask, request, jsonify

app = Flask(__name__)
users = {1: {"id": 1, "name": "Alice"}}

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(list(users.values()))

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    return jsonify(users.get(user_id, {"error": "Not found"}))

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    new_id = max(users.keys()) + 1
    users[new_id] = {"id": new_id, **data}
    return jsonify(users[new_id]), 201

if __name__ == '__main__':
    app.run(debug=True)
```

### Exercise 3: Add Authentication (1 hour)

```python
import jwt
from datetime import datetime, timedelta

@app.route('/login', methods=['POST'])
def login():
    token = jwt.encode({
        'user_id': 1,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, 'secret', algorithm='HS256')
    return {'token': token}

@app.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get('Authorization').split()[1]
    try:
        jwt.decode(token, 'secret', algorithms=['HS256'])
        return {'message': 'Access granted'}
    except:
        return {'error': 'Invalid token'}, 401
```

---

## Real-World API Examples

### Weather App

```python
import requests

def get_weather(city):
    response = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={
            "q": city,
            "appid": "YOUR_KEY",
            "units": "metric"
        }
    )
    data = response.json()
    return {
        "city": data['name'],
        "temp": data['main']['temp'],
        "description": data['weather'][0]['description']
    }

print(get_weather("London"))
```

### GitHub Analysis

```python
import requests

def analyze_repo(owner, repo):
    response = requests.get(f"https://api.github.com/repos/{owner}/{repo}")
    data = response.json()
    return {
        "name": data['name'],
        "stars": data['stargazers_count'],
        "forks": data['forks_count'],
        "language": data['language']
    }

print(analyze_repo("facebook", "react"))
```

---

## Common Pitfalls to Avoid

```
❌ Hardcoding API keys
✅ Use environment variables

❌ Ignoring error responses
✅ Check status_code before parsing JSON

❌ No timeout on requests
✅ Set timeout=5 on all requests

❌ Logging sensitive data
✅ Mask passwords, tokens in logs

❌ No rate limiting in own API
✅ Implement rate limiting

❌ Trusting all user input
✅ Always validate input

❌ Weak authentication
✅ Use secure tokens (JWT, OAuth)

❌ HTTP for sensitive data
✅ Always use HTTPS
```

---

## Tools for API Development

### API Testing Tools
- **Postman**: Visual API testing
- **curl**: Command-line HTTP client
- **httpie**: User-friendly curl alternative
- **Insomnia**: Modern API client

### Python Libraries
- **requests**: Make HTTP requests
- **flask**: Create APIs (lightweight)
- **fastapi**: Create APIs (modern)
- **jwt**: JWT token handling
- **python-dotenv**: Load .env files

### Browser Tools
- **REST Client** extension: Make requests from browser
- **Thunder Client**: VS Code extension
- **Hoppscotch**: Web-based API testing

---

## Interview Questions

### Beginner

1. **What is an API?**
   API is a set of rules that allows applications to communicate.

2. **What is REST?**
   REST is an architectural style using HTTP methods (GET, POST, etc.) to manipulate resources.

3. **What is the difference between GET and POST?**
   GET retrieves data (safe, idempotent). POST creates data (not idempotent).

4. **What HTTP status code means "success"?**
   2xx range: 200 OK, 201 Created, 204 No Content

5. **What is API authentication?**
   Verification that the requester is who they claim to be.

### Intermediate

6. **What is the difference between PUT and PATCH?**
   PUT replaces entire resource. PATCH updates only specified fields.

7. **What is a JWT token?**
   Encrypted token containing user info, used for stateless authentication.

8. **What is CORS?**
   Cross-Origin Resource Sharing: Allow requests from different domains.

9. **How do you handle API errors?**
   Check status codes, parse error response, implement retry logic.

10. **What is rate limiting?**
    Limit requests per user/IP to prevent abuse.

### Advanced

11. **How would you design a secure API?**
    - HTTPS only
    - Input validation
    - Rate limiting
    - Authentication/Authorization
    - Error handling
    - Logging/monitoring

12. **How do you handle API versioning?**
    - URL path: /api/v1/, /api/v2/
    - Header: Accept-Version
    - Query param: ?version=2

13. **What is idempotency?**
    Calling endpoint multiple times has same effect as calling once.

14. **How do you test an API?**
    - Unit tests for handlers
    - Integration tests for endpoints
    - Load tests for performance
    - Security tests

15. **What is caching and why is it important?**
    Store frequently accessed data in cache to reduce server load.

---

## Next Steps

1. **Master the Basics**: Read all 5 files in order
2. **Practice with Public APIs**: Use GitHub, Weather APIs
3. **Create Your Own API**: Build Flask/FastAPI project
4. **Add Authentication**: Implement JWT or OAuth
5. **Deploy**: Host on Heroku, AWS, Google Cloud
6. **Monitor**: Add logging and error tracking
7. **Optimize**: Add caching, rate limiting
8. **Secure**: Implement all security best practices

---

## Resources

### Official Documentation
- Flask: https://flask.palletsprojects.com/
- FastAPI: https://fastapi.tiangolo.com/
- Requests: https://docs.python-requests.org/
- JWT: https://pyjwt.readthedocs.io/

### Learning Resources
- RESTful API Design: https://restfulapi.net/
- API Design Best Practices: https://github.com/microsoft/api-guidelines
- OpenAPI Specification: https://spec.openapis.org/

### Tools
- Postman: https://www.postman.com/
- httpie: https://httpie.io/
- Hoppscotch: https://hoppscotch.io/

---

## Final Checklist

Before submitting API for production:

```
☐ HTTPS enabled
☐ Input validation implemented
☐ Error handling working
☐ Rate limiting active
☐ Authentication implemented
☐ Authorization checks in place
☐ Logging configured
☐ Tests passing (unit, integration, load)
☐ Documentation complete
☐ Security audit passed
☐ Performance acceptable
☐ Monitoring/alerting set up
☐ Deployment process tested
```

---

## Summary

You now have comprehensive knowledge of:
- ✅ What APIs are and why they matter
- ✅ All HTTP methods and status codes
- ✅ How to create APIs
- ✅ How to use public APIs
- ✅ How to secure APIs

This is industry-standard knowledge used in every software company. Master these concepts and you'll be valuable to any team!

**Happy API coding! 🚀**

