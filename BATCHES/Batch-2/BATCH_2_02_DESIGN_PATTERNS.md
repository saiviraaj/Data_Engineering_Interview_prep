# Design Patterns: Proven Solutions to Common Problems
## Complete Guide to 20+ Patterns for Data Engineers

**Target**: Beginner to intermediate  
**Time**: 8-10 hours reading + 5-6 hours practice  
**Goal**: Recognize and apply design patterns to solve problems

---

## Table of Contents

1. [What Are Design Patterns?](#what-are-design-patterns)
2. [Creational Patterns](#creational-patterns) (Create objects wisely)
3. [Structural Patterns](#structural-patterns) (Organize relationships)
4. [Behavioral Patterns](#behavioral-patterns) (Define interactions)
5. [Pattern Selection Guide](#pattern-selection-guide)

---

## What Are Design Patterns?

### Definition

**Design Patterns** = Proven, reusable solutions to common design problems

```
Think of design patterns like recipes in cooking:

Recipe: "To make chocolate cake"
├─ Ingredients (what you need)
├─ Steps (how to combine)
└─ Result (delicious cake)

Design Pattern: "To handle optional data"
├─ Structure (how to organize code)
├─ Pros/Cons (when to use)
└─ Result (clean, maintainable solution)
```

### Why Design Patterns Matter

```
Common problem: Creating database connection
├─ New connection for each query? (Slow, wastes resources)
├─ Keep one global connection? (Thread-safety issues)
└─ Solution: Singleton pattern (one instance, shared safely)

Without pattern knowledge:
├─ Try different approaches (time-wasting)
├─ Make same mistakes others made
└─ Code is messy and unpredictable

With pattern knowledge:
├─ Recognize problem: "This is a connection management problem"
├─ Apply pattern: "Use Singleton pattern"
├─ Know it works: "Proven solution, used everywhere"
└─ Code is clean, predictable, maintainable
```

### Pattern Categories

```
Creational Patterns (Creating Objects)
├─ Singleton: One instance of a class
├─ Factory: Create objects without knowing exact types
├─ Builder: Construct complex objects step-by-step
└─ Prototype: Clone existing objects

Structural Patterns (Organizing Relationships)
├─ Adapter: Make incompatible interfaces compatible
├─ Bridge: Separate abstraction from implementation
├─ Composite: Treat individual objects and compositions the same
├─ Decorator: Add behavior to objects dynamically
├─ Facade: Provide simple interface to complex subsystem
└─ Proxy: Control access to another object

Behavioral Patterns (Defining Interactions)
├─ Observer: Notify multiple objects of state changes
├─ Strategy: Select algorithm at runtime
├─ Command: Encapsulate requests as objects
├─ State: Change behavior based on internal state
├─ Template Method: Define algorithm skeleton, let subclasses fill in
├─ Chain of Responsibility: Pass request along chain
├─ Interpreter: Define language or grammar
├─ Iterator: Access elements of collection sequentially
├─ Mediator: Reduce coupling between objects
└─ Memento: Capture and restore object state
```

---

## Creational Patterns

### Pattern 1: Singleton

**Problem**: Need exactly one instance of a class (e.g., database connection)

**Solution**: Ensure only one instance exists, provide global access

```python
# BAD: Multiple connections
class DatabaseConnection:
    def __init__(self):
        self.connection = self._connect()
    
    def _connect(self):
        # Expensive operation (connecting to database)
        pass

# Every time you create instance, new connection!
db1 = DatabaseConnection()  # New connection
db2 = DatabaseConnection()  # Another connection
db3 = DatabaseConnection()  # Third connection!
# Wasteful! Three connections for same database

# GOOD: Singleton pattern
class DatabaseConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance
    
    def _connect(self):
        # Only happens once
        print("Connecting to database...")

# All get same instance
db1 = DatabaseConnection()  # Connects once
db2 = DatabaseConnection()  # Returns same instance
db3 = DatabaseConnection()  # Returns same instance

# Verify they're the same:
assert db1 is db2 is db3  # All point to same object!

# Usage
db1.query("SELECT * FROM trades")  # Works
db2.query("SELECT * FROM users")  # Same connection
```

**When to Use**:
```
✓ Database connections (one connection pool)
✓ Configuration objects (load config once)
✓ Logging (one logger instance)
✓ Cache managers (one cache for entire app)
```

**Pros/Cons**:
```
Pros:
├─ Only one instance (no waste)
├─ Global access (easy to use)
└─ Lazy initialization (create only when needed)

Cons:
├─ Hard to test (global state)
├─ Hidden dependencies (where is instance coming from?)
└─ Thread-safety issues (must handle carefully)
```

---

### Pattern 2: Factory

**Problem**: Create objects of different types without knowing exact type

**Solution**: Factory creates appropriate object based on input

```python
# BAD: Client knows about all types
class DataExtractor:
    pass

class TeradataExtractor(DataExtractor):
    pass

class OracleExtractor(DataExtractor):
    pass

class KafkaExtractor(DataExtractor):
    pass

# Client must know all types!
def process_data(source_type):
    if source_type == "teradata":
        extractor = TeradataExtractor()
    elif source_type == "oracle":
        extractor = OracleExtractor()
    elif source_type == "kafka":
        extractor = KafkaExtractor()
    else:
        raise ValueError(f"Unknown source: {source_type}")
    
    data = extractor.extract()
    return data

# Problem: Add new source (Redis)?
# Must modify this function! (Violates OCP)

# GOOD: Factory pattern
class ExtractorFactory:
    @staticmethod
    def create_extractor(source_type):
        """Factory creates appropriate extractor"""
        extractors = {
            "teradata": TeradataExtractor,
            "oracle": OracleExtractor,
            "kafka": KafkaExtractor,
        }
        
        extractor_class = extractors.get(source_type)
        if extractor_class is None:
            raise ValueError(f"Unknown source: {source_type}")
        
        return extractor_class()

# Client doesn't know about types!
def process_data(source_type):
    extractor = ExtractorFactory.create_extractor(source_type)
    data = extractor.extract()
    return data

# Add new source (Redis)?
# Just update factory:
class RedisExtractor(DataExtractor):
    pass

# Modify factory's dict:
extractors["redis"] = RedisExtractor

# process_data("redis") works! No other changes needed.
```

**When to Use**:
```
✓ Different implementations based on type
✓ Don't want client to know about types
✓ Want to add new types without modifying client
✓ Complex object creation logic
```

---

### Pattern 3: Builder

**Problem**: Complex object with many optional parameters

**Solution**: Build object step-by-step

```python
# BAD: Many constructor parameters
class Query:
    def __init__(self, select=None, from_table=None, where=None, 
                 order_by=None, limit=None, join=None, group_by=None, ...):
        # Many parameters, most optional
        # Easy to pass wrong order
        pass

# Usage (confusing):
query = Query("*", "trades", "amount > 1000", "date DESC", 100, ...)

# GOOD: Builder pattern
class QueryBuilder:
    def __init__(self):
        self.select = None
        self.from_table = None
        self.where = None
        self.order_by = None
        self.limit = None
    
    def select(self, columns):
        self.select = columns
        return self  # Return self for chaining
    
    def from_table(self, table):
        self.from_table = table
        return self
    
    def where(self, condition):
        self.where = condition
        return self
    
    def order_by(self, columns):
        self.order_by = columns
        return self
    
    def limit(self, count):
        self.limit = count
        return self
    
    def build(self):
        # Build and return Query object
        return Query(
            select=self.select,
            from_table=self.from_table,
            where=self.where,
            order_by=self.order_by,
            limit=self.limit
        )

# Usage (clear and flexible):
query = (QueryBuilder()
    .select("*")
    .from_table("trades")
    .where("amount > 1000")
    .order_by("date DESC")
    .limit(100)
    .build())

# Can skip optional parts:
simple_query = (QueryBuilder()
    .select("id, amount")
    .from_table("trades")
    .build())

# Much clearer! Self-documenting!
```

**When to Use**:
```
✓ Complex objects with many parameters
✓ Many optional parameters
✓ Want clear, readable construction
✓ Configuration objects
```

---

## Structural Patterns

### Pattern 4: Adapter

**Problem**: Incompatible interfaces need to work together

**Solution**: Adapter bridges the gap between interfaces

```python
# System 1: Old code expects this interface
class OldDatabase:
    def get_data(self, table):
        # Returns tuple of tuples
        return ((1, 'John'), (2, 'Jane'))

# System 2: New code expects this interface
class NewDataSource:
    def query(self, sql):
        # Returns list of dicts
        return [{'id': 1, 'name': 'John'}, {'id': 2, 'name': 'Jane'}]

# Incompatible interfaces!
# Old code uses: db.get_data('users')
# New code uses: source.query('SELECT * FROM users')

# GOOD: Adapter pattern
class DatabaseAdapter:
    """Adapts NewDataSource to look like OldDatabase"""
    
    def __init__(self, new_source: NewDataSource):
        self.source = new_source
    
    def get_data(self, table):
        # Translate old interface to new interface
        sql = f"SELECT * FROM {table}"
        result = self.source.query(sql)
        
        # Convert list of dicts to tuple of tuples
        return tuple((row['id'], row['name']) for row in result)

# Now old code can use new data source!
new_source = NewDataSource()
adapter = DatabaseAdapter(new_source)

# Old code works unchanged:
data = adapter.get_data('users')
# Returns compatible format

# Benefits:
# 1. Old code doesn't know about NewDataSource
# 2. Can use new implementation with old code
# 3. Clean separation of concerns
```

**When to Use**:
```
✓ Integrating libraries with different interfaces
✓ Working with legacy code
✓ Connecting incompatible systems
```

---

### Pattern 5: Decorator

**Problem**: Need to add behavior to objects dynamically

**Solution**: Wrap object with decorator that adds behavior

```python
# BASE: Data processor
class DataProcessor:
    def process(self, data):
        # Basic processing
        return [process_record(r) for r in data]

# NEED TO ADD: Logging, caching, error handling
# But don't want to modify DataProcessor!

# BAD: Add all behavior to DataProcessor
class DataProcessor:
    def process(self, data):
        # Log start
        logger.info("Starting processing")
        
        # Process
        result = [process_record(r) for r in data]
        
        # Cache result
        self._cache[hash(data)] = result
        
        # Log end
        logger.info("Processing complete")
        
        return result
    
    def _handle_errors(self, data):
        try:
            # ... error handling ...
        except:
            # ... handle error ...
```

This violates SRP! Too many responsibilities.

```python
# GOOD: Decorator pattern
class DataProcessor:
    def process(self, data):
        return [process_record(r) for r in data]

# Decorators add behavior
class LoggingProcessor:
    def __init__(self, processor):
        self.processor = processor
    
    def process(self, data):
        logger.info("Starting processing")
        result = self.processor.process(data)
        logger.info("Processing complete")
        return result

class CachingProcessor:
    def __init__(self, processor):
        self.processor = processor
        self.cache = {}
    
    def process(self, data):
        key = hash(tuple(data))
        if key in self.cache:
            return self.cache[key]
        
        result = self.processor.process(data)
        self.cache[key] = result
        return result

class ErrorHandlingProcessor:
    def __init__(self, processor):
        self.processor = processor
    
    def process(self, data):
        try:
            return self.processor.process(data)
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return []

# Compose decorators!
processor = DataProcessor()
processor = LoggingProcessor(processor)  # Add logging
processor = CachingProcessor(processor)  # Add caching
processor = ErrorHandlingProcessor(processor)  # Add error handling

# All behavior added without modifying DataProcessor!
result = processor.process(data)
# Will: log → check cache → process → handle errors
```

**When to Use**:
```
✓ Add behavior without modifying original class
✓ Dynamically compose multiple behaviors
✓ Keep classes focused (SRP)
```

---

## Behavioral Patterns

### Pattern 6: Observer

**Problem**: Need to notify multiple objects when something changes

**Solution**: Objects observe and react to state changes

```python
# Problem: When trade is executed, need to:
# ├─ Update portfolio
# ├─ Send alert
# ├─ Log metrics
# ├─ Update dashboard
# └─ All tight coupling!

# GOOD: Observer pattern
class Trade:
    def __init__(self):
        self._observers = []
    
    def attach(self, observer):
        """Add observer"""
        self._observers.append(observer)
    
    def detach(self, observer):
        """Remove observer"""
        self._observers.remove(observer)
    
    def notify_observers(self, event):
        """Notify all observers"""
        for observer in self._observers:
            observer.update(event)
    
    def execute_trade(self, trader_id, amount):
        # Execute trade
        print(f"Trade executed: {trader_id} - {amount}")
        
        # Notify all observers
        event = {
            'trader_id': trader_id,
            'amount': amount,
            'timestamp': datetime.now()
        }
        self.notify_observers(event)

# Observers
class PortfolioUpdater:
    def update(self, event):
        print(f"Updating portfolio: {event}")

class AlertManager:
    def update(self, event):
        print(f"Sending alert: {event}")

class MetricsLogger:
    def update(self, event):
        print(f"Logging metrics: {event}")

class DashboardUpdater:
    def update(self, event):
        print(f"Updating dashboard: {event}")

# Setup
trade = Trade()
trade.attach(PortfolioUpdater())
trade.attach(AlertManager())
trade.attach(MetricsLogger())
trade.attach(DashboardUpdater())

# Execute trade
trade.execute_trade("T001", 100000)

# Output:
# Trade executed: T001 - 100000
# Updating portfolio: {...}
# Sending alert: {...}
# Logging metrics: {...}
# Updating dashboard: {...}

# Benefits:
# 1. Loose coupling (Trade doesn't know about observers)
# 2. Easy to add new observers (just attach)
# 3. Easy to remove observers (just detach)
# 4. All observers notified consistently
```

**When to Use**:
```
✓ One-to-many relationships (one change, many reactions)
✓ Event-driven systems
✓ MVC (Model notifies Views)
✓ Pub/Sub systems
```

---

### Pattern 7: Strategy

**Problem**: Need to select algorithm at runtime

**Solution**: Encapsulate algorithms, let client choose

```python
# Problem: Different filtering strategies
# ├─ Filter by amount
# ├─ Filter by date
# ├─ Filter by trader
# └─ Combinations of above

# BAD: Multiple if-else statements
def filter_trades(trades, filter_type, filter_value):
    if filter_type == "amount":
        return [t for t in trades if t['amount'] > filter_value]
    elif filter_type == "date":
        return [t for t in trades if t['date'] >= filter_value]
    elif filter_type == "trader":
        return [t for t in trades if t['trader_id'] == filter_value]
    else:
        raise ValueError(f"Unknown filter: {filter_type}")

# GOOD: Strategy pattern
class FilterStrategy:
    def filter(self, trades, value):
        raise NotImplementedError

class AmountFilter(FilterStrategy):
    def filter(self, trades, value):
        return [t for t in trades if t['amount'] > value]

class DateFilter(FilterStrategy):
    def filter(self, trades, value):
        return [t for t in trades if t['date'] >= value]

class TraderFilter(FilterStrategy):
    def filter(self, trades, value):
        return [t for t in trades if t['trader_id'] == value]

class TradeFilter:
    def __init__(self, strategy: FilterStrategy):
        self.strategy = strategy
    
    def filter(self, trades, value):
        return self.strategy.filter(trades, value)

# Usage:
trades = [...]

# Filter by amount
filter_obj = TradeFilter(AmountFilter())
large_trades = filter_obj.filter(trades, 100000)

# Filter by date (change strategy!)
filter_obj = TradeFilter(DateFilter())
recent_trades = filter_obj.filter(trades, "2024-01-01")

# Add new filter? Create new strategy class!
class SymbolFilter(FilterStrategy):
    def filter(self, trades, value):
        return [t for t in trades if t['symbol'] == value]

filter_obj = TradeFilter(SymbolFilter())
aapl_trades = filter_obj.filter(trades, "AAPL")

# Benefits:
# 1. Easy to add new strategies (new classes)
# 2. No if-else statements
# 3. Strategies are reusable
# 4. Client doesn't know about implementations
```

**When to Use**:
```
✓ Multiple algorithms for same task
✓ Want to avoid long if-else chains
✓ Algorithms might change at runtime
✓ Different contexts need different behaviors
```

---

### Pattern 8: State

**Problem**: Behavior changes based on internal state

**Solution**: Create state objects, delegate behavior to them

```python
# Problem: Trade has different behavior based on status
# ├─ PENDING: Can cancel, can confirm
# ├─ CONFIRMED: Can execute, can cancel
# ├─ EXECUTED: Can settle, read-only
# └─ SETTLED: Read-only

# BAD: Many if-else statements
class Trade:
    def __init__(self):
        self.status = "PENDING"
    
    def confirm(self):
        if self.status == "PENDING":
            self.status = "CONFIRMED"
        else:
            raise ValueError(f"Can't confirm from {self.status}")
    
    def execute(self):
        if self.status == "CONFIRMED":
            self.status = "EXECUTED"
        else:
            raise ValueError(f"Can't execute from {self.status}")
    
    def settle(self):
        if self.status == "EXECUTED":
            self.status = "SETTLED"
        else:
            raise ValueError(f"Can't settle from {self.status}")
    
    def cancel(self):
        if self.status in ["PENDING", "CONFIRMED"]:
            self.status = "CANCELLED"
        else:
            raise ValueError(f"Can't cancel from {self.status}")

# Lots of if-else! Hard to maintain.

# GOOD: State pattern
class TradeState:
    def confirm(self, trade):
        raise NotImplementedError
    
    def execute(self, trade):
        raise NotImplementedError
    
    def cancel(self, trade):
        raise NotImplementedError

class PendingState(TradeState):
    def confirm(self, trade):
        trade.state = ConfirmedState()
    
    def cancel(self, trade):
        trade.state = CancelledState()

class ConfirmedState(TradeState):
    def execute(self, trade):
        trade.state = ExecutedState()
    
    def cancel(self, trade):
        trade.state = CancelledState()

class ExecutedState(TradeState):
    def settle(self, trade):
        trade.state = SettledState()

class SettledState(TradeState):
    pass  # No transitions from settled

class CancelledState(TradeState):
    pass  # No transitions from cancelled

class Trade:
    def __init__(self):
        self.state = PendingState()
    
    def confirm(self):
        self.state.confirm(self)
    
    def execute(self):
        self.state.execute(self)
    
    def settle(self):
        self.state.settle(self)
    
    def cancel(self):
        self.state.cancel(self)

# Usage:
trade = Trade()  # Starts in PendingState
trade.confirm()  # Moves to ConfirmedState
trade.execute()  # Moves to ExecutedState
trade.settle()   # Moves to SettledState

# Benefits:
# 1. State transitions are explicit
# 2. Each state knows what transitions are valid
# 3. No long if-else chains
# 4. Easy to add new states
```

**When to Use**:
```
✓ Object has multiple states with different behavior
✓ State transitions are well-defined
✓ Many if-else statements checking state
✓ Behavior changes based on internal state
```

---

## Pattern Selection Guide

### Quick Reference

```
Need to create ONE instance?
└─ Singleton

Need to create objects of different types?
└─ Factory

Building complex objects step-by-step?
└─ Builder

Making incompatible interfaces work together?
└─ Adapter

Adding behavior without modifying original class?
└─ Decorator

Notify multiple objects of state changes?
└─ Observer

Select algorithm at runtime?
└─ Strategy

Behavior changes based on internal state?
└─ State

Many more...
```

### For Your Data Pipeline

```
Extractors (multiple types):
├─ Use: Factory pattern
└─ Create extractors without client knowing type

Processing pipeline (add behaviors):
├─ Use: Decorator pattern
└─ Add caching, logging, error handling without modifying core

Events (trades, alerts):
├─ Use: Observer pattern
└─ Notify multiple components when trade happens

Configuration (many optional parameters):
├─ Use: Builder pattern
└─ Configure pipeline step-by-step

Schema conversions (incompatible formats):
├─ Use: Adapter pattern
└─ Convert between formats transparently
```

---

**Design patterns are PROVEN SOLUTIONS.** Master them, recognize them, apply them confidently.

**Next: Low-Level Design shows how to design individual components well!**
