# Low-Level Design (LLD): Designing Components Well
## How to Design Classes, Methods, and Interactions

**Target**: Data engineers designing system components  
**Level**: Beginner to intermediate  
**Time**: 6-8 hours reading + 4-5 hours practice  
**Goal**: Design individual components that are clean, testable, maintainable

---

## Table of Contents

1. [What is Low-Level Design?](#what-is-low-level-design)
2. [Design Process](#design-process)
3. [Class Design](#class-design)
4. [Method Design](#method-design)
5. [Handling Errors](#handling-errors)
6. [Design Trade-offs](#design-trade-offs)
7. [Testing Considerations](#testing-considerations)
8. [LLD Examples](#lld-examples)

---

## What is Low-Level Design?

### Definition

**Low-Level Design** = Designing individual components, classes, and methods

```
System Design:
├─ What databases do we use?
├─ How do services communicate?
└─ How do we scale?

Low-Level Design:
├─ How does this class work?
├─ What methods should it have?
├─ How do classes interact?
└─ How do we test it?

You're designing at COMPONENT level, not SYSTEM level.
```

### When You Use LLD

```
System Design Interview:
├─ "Design a ride-sharing app"
├─ Decide: Use PostgreSQL, Kafka, Redis
├─ Decide: Services talk via REST
└─ This is HIGH-level

LLD Interview:
├─ "Design the Ride class"
├─ What attributes? (rider_id, driver_id, start_location, etc.)
├─ What methods? (start_ride(), end_ride(), calculate_fare())
├─ What error cases? (invalid location, driver not found, etc.)
└─ This is LOW-level

In real job:
├─ Morning: Architect system (high-level)
└─ Rest of day: Design components (low-level)
```

### LLD vs High-Level Design

```
High-Level Design:
├─ Big picture (system architecture)
├─ Which components? (databases, services, queues)
├─ How do they talk? (REST, message queue, gRPC)
└─ Scalability, reliability at system level

Low-Level Design:
├─ Individual component (single service/class)
├─ How does it work internally?
├─ What classes/methods?
├─ Scalability, reliability at component level

Analogy:
├─ High-level: Designing a car factory
├─ Low-level: Designing the engine

Both important! You need both skills.
```

---

## Design Process

### Step 1: Understand Requirements

**Ask Questions**:
```
What should this component do?
├─ Extract data from source X
├─ Transform it with business logic
├─ Load to destination Y
└─ Be testable, maintainable, performant

What are constraints?
├─ Must process 1M records/second
├─ Must handle failures gracefully
├─ Must support new sources
└─ Must be deployable in containers

What about error cases?
├─ Source connection fails
├─ Invalid data
├─ Destination full
└─ Timeout
```

### Step 2: Identify Classes/Components

```
Example: Data Pipeline Extractor

Components needed:
├─ ConnectionManager (manage database connections)
├─ QueryBuilder (build queries dynamically)
├─ DataExtractor (extract data)
├─ ErrorHandler (handle errors)
└─ Logger (log operations)

Why split?
├─ Single Responsibility (each does one thing)
├─ Testability (can test each independently)
├─ Reusability (can use in other places)
└─ Maintainability (changes isolated)
```

### Step 3: Design Class Interfaces

```
Each class needs:
├─ Public methods (what users call)
├─ Private methods (internal only)
├─ Attributes (what it stores)
└─ Dependencies (what it needs)

Example: DataExtractor

Public methods:
├─ extract(config) → List[Dict]
├─ extract_with_filter(config, filter) → List[Dict]
└─ get_row_count(config) → int

Private methods:
├─ _validate_config(config)
├─ _execute_query(query)
└─ _handle_error(error)

Attributes:
├─ connection: DatabaseConnection
├─ logger: Logger
└─ config: Dict

Dependencies:
├─ DatabaseConnection (injected)
├─ Logger (injected)
└─ QueryBuilder (created internally)
```

### Step 4: Define Data Models

```
What data flows through?

Input: config dict
├─ host: str
├─ port: int
├─ database: str
├─ query: str
└─ timeout: int

Output: List[Dict]
├─ [{id: 1, name: 'John', amount: 100}, ...]
└─ Empty list if no records

Error: Exception
├─ ConnectionError
├─ QueryError
├─ TimeoutError
└─ Custom exceptions
```

### Step 5: Handle Edge Cases

```
What can go wrong?

Empty results:
├─ Return empty list (not None!)
└─ Log as warning (might be normal)

Connection failure:
├─ Raise exception
├─ Don't return None (confusing)
└─ Let caller handle

Invalid config:
├─ Validate in constructor
├─ Raise ValueError immediately
└─ Don't allow bad state

Timeout:
├─ Set timeout on database operation
├─ Raise TimeoutError if exceeded
└─ Caller decides what to do
```

---

## Class Design

### What Should Be a Class?

```
Good candidates for classes:

Entity: Something that exists
├─ Trade (has id, trader, amount)
├─ User (has id, name, email)
├─ DatabaseConnection (has host, port)
└─ These are NOUNS

Behavior: Something that does work
├─ DataExtractor (extracts data)
├─ TradeValidator (validates trades)
├─ ConnectionPool (manages connections)
└─ These are VERBS (sometimes)

Manager: Coordinates multiple things
├─ Pipeline (orchestrates extraction, transformation, loading)
├─ ConnectionManager (manages multiple connections)
├─ ErrorHandler (coordinates error handling)
└─ These coordinate

BAD candidates:

Utility class with only static methods:
├─ Utils.reverse_string()
├─ Utils.format_date()
├─ Utils.calculate_sum()
└─ Should be functions, not classes!
```

### Class Attributes

```
Should be:
├─ Used by multiple methods
├─ Represent state of object
├─ Initialized in constructor
└─ Example: connection (used by extract, query, close)

Should NOT be:
├─ Only used by one method (make it local variable)
├─ Temporary calculations (make it local variable)
├─ Configuration that doesn't change (make it constant)
└─ Example: temp_list = [] (should be local in method)
```

### Constructor Design

```
Constructor should:
├─ Initialize all attributes
├─ Validate inputs
├─ Inject dependencies (not create them!)
└─ Leave object in valid state

Example - GOOD:
class DataExtractor:
    def __init__(self, connection: DatabaseConnection, logger: Logger):
        self.connection = connection  # Injected
        self.logger = logger  # Injected
        # Valid state: ready to use

Example - BAD:
class DataExtractor:
    def __init__(self):
        self.connection = DatabaseConnection()  # Creates own!
        self.logger = None  # Might be None later
        # Not ready to use! Missing logger.

Why dependency injection?
├─ Testable (can pass mock objects)
├─ Flexible (can swap implementations)
├─ Loose coupling (doesn't know about creation)
└─ Follows Dependency Inversion Principle
```

### Method Design

```
Good methods:
├─ Single responsibility (do one thing)
├─ Small (fit on one screen, 10-20 lines)
├─ Clear name (explains what it does)
├─ Few parameters (1-3 is ideal)
└─ Clear return value (what does it return?)

Example - GOOD:
def extract_trades(self, config: Dict) -> List[Dict]:
    """Extract trades from database"""
    self._validate_config(config)
    connection = self._create_connection(config)
    try:
        rows = connection.fetch_all(config['query'])
        return self._format_rows(rows)
    finally:
        connection.close()

Example - BAD:
def process_everything(self, config, logger, cache, alert_manager, db):
    """Does everything: extract, transform, validate, load, alert, cache, log"""
    # 100 lines of code
    # Many responsibilities
    # Impossible to test
    # Impossible to understand
```

---

## Method Design

### Parameters

```
Good practices:
├─ Few parameters (1-3 ideal)
├─ Meaningful names
├─ Type hints (Python 3.5+)
└─ Validation

Example - GOOD:
def extract(self, config: Dict) -> List[Dict]:
    """Extract data from source"""

Example - BAD:
def extract(self, c, v, t, f):
    """No type hints, unclear params"""

If many parameters:
├─ Create configuration object
└─ Pass that instead

Example:
def extract(self, config: ExtractorConfig) -> List[Dict]:
    # config.host, config.port, config.database, etc.
```

### Return Values

```
Always return explicit values:
├─ Return result (not None)
└─ Return empty list (not None!)

Example - GOOD:
def get_trades(self) -> List[Dict]:
    if no_trades:
        return []  # Empty list, not None!
    return trades

Example - BAD:
def get_trades(self) -> List[Dict]:
    if no_trades:
        return None  # Confusing! Caller expects list
    return trades

If nothing to return:
├─ Use None explicitly (with type hint Optional)
└─ Or raise exception

Example:
def get_first_trade(self) -> Optional[Dict]:
    if no_trades:
        return None  # Explicit that it can be None
    return trades[0]

If error occurred:
├─ Raise exception (don't return error code)
└─ Let caller handle

Example:
def extract(self):
    try:
        # ... extraction ...
    except ConnectionError:
        raise  # Re-raise, don't return error code
```

---

## Handling Errors

### Error Strategy

```
Goal: Make errors explicit and handleable

Don't hide errors:
├─ DON'T: Return None (caller doesn't know if error)
├─ DON'T: Return -1 (magic numbers are confusing)
├─ DON'T: Log and continue (pretend it didn't happen)
└─ DO: Raise exception (explicit error)

Example - BAD:
def extract(self):
    try:
        connection = self._create_connection()
    except ConnectionError:
        logger.error("Connection failed")
        return None  # Hidden error!

# Caller doesn't know if None means error or no data!
result = extractor.extract()
if result is None:
    # Is this an error? Or no data?
    # Can't tell!

Example - GOOD:
def extract(self):
    connection = self._create_connection()  # Raises if fails
    return connection.fetch_all()  # Raises if fails

# Caller knows exactly what happened:
try:
    result = extractor.extract()
    # Success! result is data
except ConnectionError:
    # Known error, handle it
except QueryError:
    # Different error, handle differently
```

### Custom Exceptions

```
Use exceptions for error cases:

Good custom exceptions:
├─ InvalidConfigError (config missing/wrong)
├─ ConnectionError (can't connect to database)
├─ QueryError (query syntax wrong or times out)
├─ ValidationError (data doesn't meet requirements)
└─ TimeoutError (operation took too long)

Example:
class InvalidConfigError(Exception):
    """Raised when configuration is invalid"""
    pass

class DataExtractor:
    def __init__(self, config: Dict):
        if 'host' not in config:
            raise InvalidConfigError("Missing 'host' in config")
        if 'port' not in config:
            raise InvalidConfigError("Missing 'port' in config")
        self.config = config

# Clear, explicit error!
try:
    extractor = DataExtractor({})
except InvalidConfigError as e:
    print(f"Invalid config: {e}")
```

---

## Design Trade-offs

### Simplicity vs Flexibility

```
Simple design:
├─ Easy to understand
├─ Easy to test
├─ Hard to extend
└─ Good for: Well-defined, stable requirements

Flexible design:
├─ Easy to extend
├─ Harder to understand
├─ More code
└─ Good for: Changing requirements, multiple variations

Start simple!
├─ If requirements change, refactor
├─ Don't anticipate changes that might not happen
└─ "YAGNI" = You Aren't Gonna Need It
```

### Caching vs Correctness

```
With caching:
├─ Faster (serve from cache)
└─ Might be stale (old data)

Without caching:
├─ Slower (always fresh)
└─ Always correct

Trade-off:
├─ Cache frequently accessed data
├─ Use TTL (time-to-live)
└─ Invalidate when data changes

Example:
def get_user(self, user_id):
    # Check cache first
    if user_id in self._cache:
        cached_user, timestamp = self._cache[user_id]
        if (now - timestamp) < 300:  # 5 min TTL
            return cached_user
    
    # Cache miss, fetch from DB
    user = self.db.fetch(user_id)
    self._cache[user_id] = (user, now)
    return user
```

### Validation Where?

```
Constructor:
├─ Validate immutable attributes
├─ Fail early (invalid state impossible)
└─ Example: config must have host and port

Method:
├─ Validate input parameters
├─ Fail if invalid
└─ Example: user_id must be > 0

Both:
├─ Constructor: Validate state once
├─ Method: Validate each call's parameters
└─ Defense in depth (belt and suspenders)
```

---

## Testing Considerations

### Design for Testability

```
Testable design:
├─ Dependencies injected (can pass mocks)
├─ No hardcoded values (parameterized)
├─ Single responsibility (can test one thing)
└─ Clear inputs/outputs (deterministic)

Example - HARD to test:
class UserProcessor:
    def __init__(self):
        self.db = PostgresqlDatabase()  # Can't mock!
        self.cache = RedisCache()  # Can't mock!
    
    def process(self):
        user = self.db.fetch_user(123)  # Hardcoded ID!
        self.cache.set(user)
        return user

# Can't test without real DB and Redis!
# Can't test with different data!

Example - EASY to test:
class UserProcessor:
    def __init__(self, db: Database, cache: Cache):
        self.db = db  # Injected, can be mock!
        self.cache = cache  # Injected, can be mock!
    
    def process(self, user_id: int):
        user = self.db.fetch_user(user_id)  # Parameterized!
        self.cache.set(user)
        return user

# Test with mock objects:
mock_db = MockDatabase()
mock_cache = MockCache()
processor = UserProcessor(mock_db, mock_cache)

mock_db.add_user(123, user_data)
result = processor.process(123)
assert result == user_data
# Fast, isolated test!
```

---

## LLD Examples

### Example 1: Simple Data Validator

```python
class TradeValidator:
    """Validates trades meet business requirements"""
    
    MIN_AMOUNT = 0
    MAX_AMOUNT = 1_000_000_000
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def validate(self, trade: Dict) -> bool:
        """
        Validate trade. 
        
        Args:
            trade: Trade dict with required fields
        
        Returns:
            True if valid, raises exception if invalid
        
        Raises:
            ValueError: If trade is invalid
        """
        self._validate_required_fields(trade)
        self._validate_amount(trade['amount'])
        self._validate_symbol(trade['symbol'])
        
        self.logger.info(f"Trade {trade['id']} validated successfully")
        return True
    
    def _validate_required_fields(self, trade: Dict) -> None:
        required = ['id', 'trader_id', 'symbol', 'amount', 'timestamp']
        missing = [f for f in required if f not in trade]
        if missing:
            raise ValueError(f"Missing fields: {missing}")
    
    def _validate_amount(self, amount: float) -> None:
        if amount < self.MIN_AMOUNT or amount > self.MAX_AMOUNT:
            raise ValueError(f"Amount {amount} out of range")
    
    def _validate_symbol(self, symbol: str) -> None:
        if not symbol or len(symbol) > 10:
            raise ValueError(f"Invalid symbol: {symbol}")

# Usage:
validator = TradeValidator(logger)
try:
    validator.validate(trade)
    # Trade is valid
except ValueError as e:
    # Trade is invalid
    logger.error(f"Invalid trade: {e}")
```

### Example 2: Data Extractor with Dependency Injection

```python
class DataExtractor:
    """Extracts data from database"""
    
    def __init__(self, 
                 connection: DatabaseConnection,
                 logger: Logger,
                 error_handler: ErrorHandler):
        self.connection = connection  # Injected
        self.logger = logger  # Injected
        self.error_handler = error_handler  # Injected
    
    def extract(self, config: ExtractConfig) -> List[Dict]:
        """
        Extract data from source.
        
        Args:
            config: Configuration with query, filters, etc.
        
        Returns:
            List of records
        
        Raises:
            ConnectionError: If can't connect
            QueryError: If query fails
        """
        self._validate_config(config)
        
        self.logger.info(f"Starting extraction: {config.source}")
        
        try:
            self.connection.connect(config.host, config.port)
            records = self.connection.fetch(config.query)
            self.logger.info(f"Extracted {len(records)} records")
            return records
        
        except ConnectionError as e:
            self.error_handler.handle_connection_error(e)
            raise
        
        except QueryError as e:
            self.error_handler.handle_query_error(e)
            raise
        
        finally:
            self.connection.close()
    
    def _validate_config(self, config: ExtractConfig) -> None:
        if not config.host:
            raise ValueError("Missing host")
        if not config.port:
            raise ValueError("Missing port")
        if not config.query:
            raise ValueError("Missing query")

# Testing:
mock_connection = MockConnection()
mock_logger = MockLogger()
mock_error_handler = MockErrorHandler()

extractor = DataExtractor(mock_connection, mock_logger, mock_error_handler)

# Configure mock
mock_connection.add_result([{'id': 1, 'name': 'John'}])

# Test
config = ExtractConfig(host='localhost', port=5432, query='SELECT *')
result = extractor.extract(config)

assert result == [{'id': 1, 'name': 'John'}]
```

---

## LLD Checklist

Before you design a component, ask:

```
□ What is this component's single responsibility?
□ What are its inputs and outputs?
□ What dependencies does it have?
□ How will it be tested?
□ What error cases exist?
□ How do I handle errors?
□ Is the interface clear?
□ Are dependencies injected?
□ Are there any magic numbers/strings?
□ Is it maintainable?

If you answer all YES:
└─ You have good low-level design!
```

---

**You now understand Low-Level Design.**

**Next: High-Level Design shows how to design entire systems!**
