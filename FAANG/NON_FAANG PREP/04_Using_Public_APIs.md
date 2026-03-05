# APIs Part 4: Using Public APIs (Requests Library)

## HTTP Requests Library

**requests** is the most popular Python library for making HTTP requests.

### Installation

```bash
pip install requests
```

### Basic Request

```python
import requests

# GET request
response = requests.get('https://api.github.com/users/octocat')

# Check status
print(response.status_code)  # 200
print(response.ok)  # True

# Get response data
print(response.json())  # Parse JSON
print(response.text)   # Raw text
print(response.content)  # Raw bytes
```

---

## Popular Public APIs

### 1. OpenWeatherMap - Weather Data

#### Sign Up

```
1. Go to openweathermap.org
2. Click "Sign Up"
3. Create account
4. Go to API keys
5. Copy default key
6. Use in requests
```

#### Get Current Weather

```python
import requests

API_KEY = "your_api_key_here"

# Request current weather
response = requests.get(
    "https://api.openweathermap.org/data/2.5/weather",
    params={
        "q": "London",
        "appid": API_KEY,
        "units": "metric"  # Celsius
    }
)

# Check response
if response.status_code == 200:
    data = response.json()
    
    print(f"City: {data['name']}")
    print(f"Temperature: {data['main']['temp']}°C")
    print(f"Feels like: {data['main']['feels_like']}°C")
    print(f"Humidity: {data['main']['humidity']}%")
    print(f"Weather: {data['weather'][0]['description']}")
    print(f"Wind: {data['wind']['speed']} m/s")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

#### Get Weather Forecast

```python
response = requests.get(
    "https://api.openweathermap.org/data/2.5/forecast",
    params={
        "q": "London",
        "appid": API_KEY,
        "units": "metric"
    }
)

data = response.json()

# 5-day forecast (40 3-hour periods)
for item in data['list'][:8]:  # First 2 days
    timestamp = item['dt_txt']
    temp = item['main']['temp']
    desc = item['weather'][0]['description']
    print(f"{timestamp}: {temp}°C - {desc}")
```

---

### 2. GitHub API - Repository Data

#### No Authentication Needed (Public Data)

```python
import requests

# Get user profile
response = requests.get("https://api.github.com/users/torvalds")
user = response.json()

print(f"Name: {user['name']}")
print(f"Location: {user['location']}")
print(f"Company: {user['company']}")
print(f"Public repos: {user['public_repos']}")
print(f"Followers: {user['followers']}")
print(f"Following: {user['following']}")

# Get user's repositories
response = requests.get(
    "https://api.github.com/users/torvalds/repos",
    params={
        "sort": "stars",
        "order": "desc",
        "per_page": 10
    }
)

repos = response.json()

for repo in repos:
    print(f"\n{repo['name']}")
    print(f"  Stars: {repo['stargazers_count']}")
    print(f"  Language: {repo['language']}")
    print(f"  Description: {repo['description'][:100]}")

# Get repo details
response = requests.get("https://api.github.com/repos/torvalds/linux")
repo = response.json()

print(f"\nLinux Kernel Info:")
print(f"Stars: {repo['stargazers_count']}")
print(f"Forks: {repo['forks_count']}")
print(f"Open issues: {repo['open_issues_count']}")
print(f"Last push: {repo['pushed_at']}")
```

#### With Authentication (Private Data)

```python
import requests

# Create personal access token on GitHub
# Settings → Developer settings → Personal access tokens
TOKEN = "ghp_your_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Get your profile
response = requests.get("https://api.github.com/user", headers=headers)
user = response.json()

print(f"GitHub User: {user['login']}")
print(f"Private repos: {user['total_private_repos']}")
print(f"Email: {user['email']}")

# Get your private repositories
response = requests.get(
    "https://api.github.com/user/repos",
    headers=headers,
    params={"visibility": "private"}
)

repos = response.json()
print(f"\nPrivate repositories: {len(repos)}")
for repo in repos[:5]:
    print(f"  - {repo['name']}")

# Create a new repository
create_response = requests.post(
    "https://api.github.com/user/repos",
    headers=headers,
    json={
        "name": "my-new-repo",
        "description": "A test repository",
        "private": False,
        "auto_init": True  # Initialize with README
    }
)

if create_response.status_code == 201:
    new_repo = create_response.json()
    print(f"\nRepository created: {new_repo['name']}")
    print(f"URL: {new_repo['html_url']}")
else:
    print(f"Error: {create_response.status_code}")
    print(create_response.json())
```

---

### 3. JSONPlaceholder - Fake API for Testing

```python
import requests

# Get fake posts
response = requests.get("https://jsonplaceholder.typicode.com/posts")
posts = response.json()

print(f"Total posts: {len(posts)}")
print(f"\nFirst post:")
print(f"Title: {posts[0]['title']}")
print(f"Body: {posts[0]['body']}")

# Get comments for specific post
response = requests.get("https://jsonplaceholder.typicode.com/posts/1/comments")
comments = response.json()

print(f"\nComments on post 1: {len(comments)}")
for comment in comments[:3]:
    print(f"  {comment['email']}: {comment['body'][:50]}...")

# Create fake post
response = requests.post(
    "https://jsonplaceholder.typicode.com/posts",
    json={
        "title": "My new post",
        "body": "This is a test post",
        "userId": 1
    }
)

print(f"\nCreated post: {response.json()}")

# Update fake post
response = requests.patch(
    "https://jsonplaceholder.typicode.com/posts/1",
    json={
        "title": "Updated title"
    }
)

print(f"Updated post: {response.json()}")

# Delete fake post
response = requests.delete("https://jsonplaceholder.typicode.com/posts/1")
print(f"Deleted post, status: {response.status_code}")
```

---

## Advanced Request Handling

### Query Parameters

```python
import requests

# Method 1: In URL
response = requests.get(
    "https://api.github.com/repos/facebook/react/issues?state=open&per_page=10"
)

# Method 2: In params (cleaner)
response = requests.get(
    "https://api.github.com/repos/facebook/react/issues",
    params={
        "state": "open",
        "per_page": 10,
        "sort": "updated"
    }
)

print(response.url)  # See actual URL constructed
```

### Request Headers

```python
import requests

headers = {
    "User-Agent": "My Python App/1.0",
    "Accept": "application/json",
    "Authorization": "Bearer token123",
    "X-Custom-Header": "custom-value"
}

response = requests.get(
    "https://api.example.com/data",
    headers=headers
)
```

### Request Body (POST/PUT)

```python
import requests
import json

# Method 1: Using json parameter (automatically sets Content-Type)
response = requests.post(
    "https://api.example.com/users",
    json={
        "name": "John",
        "email": "john@example.com"
    }
)

# Method 2: Using data parameter (raw string)
response = requests.post(
    "https://api.example.com/users",
    data=json.dumps({"name": "John"}),
    headers={"Content-Type": "application/json"}
)

# Method 3: Form data
response = requests.post(
    "https://api.example.com/form",
    data={
        "username": "john",
        "password": "secret"
    }
)

# Method 4: File upload
files = {
    'file': open('document.pdf', 'rb'),
    'description': (None, 'My document')
}
response = requests.post(
    "https://api.example.com/upload",
    files=files
)
```

### Error Handling

```python
import requests
from requests.exceptions import (
    ConnectionError,
    Timeout,
    HTTPError,
    RequestException
)

try:
    response = requests.get(
        "https://api.example.com/data",
        timeout=5  # 5 second timeout
    )
    
    # Raise exception for bad status codes
    response.raise_for_status()
    
    data = response.json()
    
except ConnectionError:
    print("Failed to connect to API")
except Timeout:
    print("Request timed out")
except HTTPError as e:
    print(f"HTTP Error: {e.response.status_code}")
    if e.response.status_code == 401:
        print("Authentication failed")
    elif e.response.status_code == 404:
        print("Resource not found")
    elif e.response.status_code == 429:
        print("Rate limited")
    print(e.response.json())
except RequestException as e:
    print(f"Request error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Session and Connection Pooling

```python
import requests

# Create session (reuses connection)
session = requests.Session()

# Set default headers
session.headers.update({
    "User-Agent": "My App/1.0"
})

# Make multiple requests (reuses connection)
for i in range(5):
    response = session.get(f"https://api.example.com/user/{i}")
    print(response.json())

# Close session when done
session.close()

# Or use context manager (auto-closes)
with requests.Session() as session:
    for i in range(5):
        response = session.get(f"https://api.example.com/user/{i}")
```

### Retrying Failed Requests

```python
import requests
import time

def make_request_with_retry(url, max_retries=3, timeout=5):
    """Make request with automatic retry"""
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                # Wait before retrying (exponential backoff)
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("Max retries exceeded")
                raise

# Usage
try:
    response = make_request_with_retry("https://api.example.com/data")
    print(response.json())
except Exception as e:
    print(f"Failed to fetch: {e}")
```

---

## Real-World Example: Weather Dashboard

```python
import requests
from datetime import datetime

class WeatherDashboard:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    def get_current_weather(self, city):
        """Get current weather"""
        response = requests.get(
            f"{self.base_url}/weather",
            params={
                "q": city,
                "appid": self.api_key,
                "units": "metric"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code}")
        
        data = response.json()
        return {
            "city": data['name'],
            "temp": data['main']['temp'],
            "feels_like": data['main']['feels_like'],
            "humidity": data['main']['humidity'],
            "description": data['weather'][0]['description'],
            "wind_speed": data['wind']['speed']
        }
    
    def get_forecast(self, city, days=5):
        """Get 5-day forecast"""
        response = requests.get(
            f"{self.base_url}/forecast",
            params={
                "q": city,
                "appid": self.api_key,
                "units": "metric"
            }
        )
        
        data = response.json()
        forecast = []
        
        for item in data['list'][::3]:  # Every 3rd item (daily forecast)
            forecast.append({
                "date": item['dt_txt'],
                "temp": item['main']['temp'],
                "description": item['weather'][0]['description']
            })
        
        return forecast[:days]
    
    def display_dashboard(self, city):
        """Display weather dashboard"""
        try:
            # Current weather
            current = self.get_current_weather(city)
            
            print(f"\n{'='*50}")
            print(f"Weather Dashboard - {current['city']}")
            print(f"{'='*50}")
            print(f"Temperature: {current['temp']}°C (feels like {current['feels_like']}°C)")
            print(f"Weather: {current['description']}")
            print(f"Humidity: {current['humidity']}%")
            print(f"Wind: {current['wind_speed']} m/s")
            
            # Forecast
            print(f"\n{'='*50}")
            print("5-Day Forecast")
            print(f"{'='*50}")
            
            forecast = self.get_forecast(city)
            for item in forecast:
                print(f"{item['date']}: {item['temp']}°C - {item['description']}")
        
        except Exception as e:
            print(f"Error: {e}")

# Usage
dashboard = WeatherDashboard("your_api_key_here")
dashboard.display_dashboard("London")
```

---

## Summary: Using Public APIs

```
1. Find API documentation
2. Sign up and get API key
3. Understand endpoints and parameters
4. Make requests using requests library
5. Parse response JSON
6. Handle errors gracefully
7. Implement retry logic if needed
8. Cache results when appropriate
```

Common status codes when using APIs:
- **200 OK**: Success
- **400 Bad Request**: Bad parameters
- **401 Unauthorized**: Need authentication
- **403 Forbidden**: Not authorized
- **404 Not Found**: Resource doesn't exist
- **429 Too Many Requests**: Rate limited (wait and retry)
- **500 Server Error**: API server error

Next: Part 5 - Authentication & Security!

