# SOLID Principles: Writing Good Code at Scale
## Complete Guide for Non-CS Background Engineers

**Target Audience**: Data engineers, non-CS background  
**Level**: Beginner to intermediate  
**Time to Complete**: 6-8 hours reading + 4-6 hours practice  
**Goal**: Write maintainable, scalable code that's easy to modify

---

## Table of Contents

1. [Introduction to SOLID](#introduction-to-solid)
2. [S - Single Responsibility Principle](#s---single-responsibility-principle)
3. [O - Open/Closed Principle](#o---openclosed-principle)
4. [L - Liskov Substitution Principle](#l---liskov-substitution-principle)
5. [I - Interface Segregation Principle](#i---interface-segregation-principle)
6. [D - Dependency Inversion Principle](#d---dependency-inversion-principle)
7. [SOLID in Practice](#solid-in-practice)
8. [Common SOLID Violations](#common-solid-violations)

---

## Introduction to SOLID

### What are SOLID Principles?

**SOLID** = 5 design principles for writing better code

```
S = Single Responsibility Principle
O = Open/Closed Principle
L = Liskov Substitution Principle
I = Interface Segregation Principle
D = Dependency Inversion Principle
```

**Why They Matter**:
```
Good code (following SOLID):
├─ Easy to understand (new developers get it quickly)
├─ Easy to modify (change one thing, nothing breaks)
├─ Easy to test (can test components in isolation)
├─ Easy to reuse (components work in different contexts)
└─ Easy to maintain (bugs are rare and isolated)

Bad code (violating SOLID):
├─ Hard to understand (what does this do?)
├─ Hard to modify (change one thing, everything breaks)
├─ Hard to test (can't test in isolation)
├─ Hard to reuse (tightly coupled to specific use case)
└─ Hard to maintain (bugs cascade, nightmare to fix)
```

**Real Cost Example**:
```
You wrote code 6 months ago.
Now need to change one feature.

With SOLID:
├─ Find the component responsible
├─ Modify that component only
├─ Run tests, everything passes
└─ Time: 1 hour

Without SOLID:
├─ One feature touches 10 components
├─ Change one, breaks 5 others
├─ Hunt through code finding failures
├─ Fix one, breaks another
└─ Time: 1 week of debugging

Difference: 7 days vs 1 hour!
SOLID principles save you time and sanity.
```

**Your Data Engineering Context**:
```
You build data pipelines:
├─ Extract data from sources
├─ Transform it
├─ Load to warehouse
└─ Monitor and alert

SOLID helps:
├─ Easily swap databases (PostgreSQL → BigQuery)
├─ Easily add new data sources
├─ Easily change transformation logic
├─ Easily test each component
└─ Easily reuse components across pipelines
```

---

## S - Single Responsibility Principle

### Definition

**"A class should have only one reason to change"**

Meaning: Each component should do ONE thing, and do it well.

### The Problem (Without SRP)

```python
# BAD: One class doing too many things
class TradeProcessor:
    def extract_trades_from_kafka(self):
        # Read from Kafka
        pass
    
    def transform_trades(self):
        # Apply business logic
        pass
    
    def validate_trades(self):
        # Check for errors
        pass
    
    def load_to_bigquery(self):
        # Write to BigQuery
        pass
    
    def send_alerts(self):
        # Send notifications
        pass
    
    def log_metrics(self):
        # Log to monitoring system
        pass

# Problems:
# 1. Class has 6 responsibilities (reasons to change)
# 2. If Kafka API changes → modify TradeProcessor
# 3. If BigQuery API changes → modify TradeProcessor
# 4. If alert system changes → modify TradeProcessor
# 5. Can't test transformation without Kafka
# 6. Can't reuse transformation in another pipeline
# 7. One failure cascades to entire system
```

### The Solution (With SRP)

```python
# GOOD: Each class has ONE responsibility

class KafkaTradeExtractor:
    """Only responsible for reading from Kafka"""
    def extract(self):
        # Read from Kafka
        pass

class TradeTransformer:
    """Only responsible for applying business logic"""
    def transform(self, trades):
        # Transform trades
        return transformed_trades

class TradeValidator:
    """Only responsible for validation"""
    def validate(self, trades):
        # Check trades are valid
        return valid_trades

class BigQueryTradeLoader:
    """Only responsible for writing to BigQuery"""
    def load(self, trades):
        # Write to BigQuery
        pass

class AlertManager:
    """Only responsible for sending alerts"""
    def send_alert(self, message):
        # Send notification
        pass

class MetricsLogger:
    """Only responsible for logging metrics"""
    def log(self, metric_name, value):
        # Log to monitoring system
        pass

# Benefits:
# 1. Each class has ONE reason to change
# 2. If Kafka API changes → Only change KafkaTradeExtractor
# 3. If BigQuery API changes → Only change BigQueryTradeLoader
# 4. Can test TradeTransformer in isolation (no Kafka needed!)
# 5. Can reuse TradeTransformer in other pipelines
# 6. One failure is isolated to single component
# 7. Easy to understand each class (single responsibility)
```

### How to Use Them Together

```python
class TradeProcessingPipeline:
    """Orchestrates the entire pipeline"""
    
    def __init__(self):
        self.extractor = KafkaTradeExtractor()
        self.transformer = TradeTransformer()
        self.validator = TradeValidator()
        self.loader = BigQueryTradeLoader()
        self.alert_manager = AlertManager()
        self.metrics = MetricsLogger()
    
    def run(self):
        # Each component handles ONE responsibility
        trades = self.extractor.extract()  # Extract
        trades = self.transformer.transform(trades)  # Transform
        trades = self.validator.validate(trades)  # Validate
        self.loader.load(trades)  # Load
        
        # Send alerts and log metrics
        self.alert_manager.send_alert(f"Processed {len(trades)} trades")
        self.metrics.log("trades_processed", len(trades))

# Usage:
pipeline = TradeProcessingPipeline()
pipeline.run()
```

### Benefits of SRP

```
1. Easy to understand
   ├─ KafkaTradeExtractor clearly extracts from Kafka
   ├─ TradeTransformer clearly transforms data
   └─ Each class has obvious responsibility

2. Easy to change
   ├─ Swap KafkaTradeExtractor for RedisTradeExtractor
   ├─ Only change one class
   └─ Rest of system unaffected

3. Easy to test
   ├─ Test TradeTransformer without external systems
   ├─ Can mock KafkaTradeExtractor
   └─ Fast, reliable tests

4. Easy to reuse
   ├─ Use TradeTransformer in multiple pipelines
   ├─ Use AlertManager in multiple systems
   └─ Components compose well

5. Easy to maintain
   ├─ Bug in TradeTransformer is isolated
   ├─ Fix doesn't affect extraction or loading
   └─ Fewer cascading failures
```

### SRP in Your Data Pipeline

```
Your CDM Next platform likely has:

Before SRP:
├─ One class handling Teradata extraction + transformation
├─ One class handling Oracle extraction + transformation
├─ One class handling Kafka ingestion + transformation
└─ Everything is mixed together

After SRP:
├─ TeradataExtractor (only extracts from Teradata)
├─ OracleExtractor (only extracts from Oracle)
├─ KafkaConsumer (only consumes from Kafka)
├─ DataTransformer (only transforms data, reusable!)
├─ BigQueryLoader (only loads to BigQuery)
└─ Each has single responsibility

Benefits for CDM Next:
├─ Add new source? Write new Extractor (don't touch others)
├─ Change transformation logic? Update DataTransformer only
├─ Swap BigQuery for Snowflake? Change BigQueryLoader only
└─ Very flexible, very maintainable system
```

---

## O - Open/Closed Principle

### Definition

**"Software entities should be OPEN for extension, CLOSED for modification"**

Meaning: You should be able to ADD new features without CHANGING existing code.

### The Problem (Without OCP)

```python
# BAD: Need to modify existing code to add features

class TradeValidator:
    def validate(self, trade, source_type):
        if source_type == "teradata":
            return self._validate_teradata(trade)
        elif source_type == "oracle":
            return self._validate_oracle(trade)
        elif source_type == "hadoop":
            return self._validate_hadoop(trade)
        elif source_type == "kafka":
            return self._validate_kafka(trade)
        # If new source added (Redis), must modify this class!
    
    def _validate_teradata(self, trade):
        # Teradata validation logic
        pass
    
    def _validate_oracle(self, trade):
        # Oracle validation logic
        pass
    
    def _validate_hadoop(self, trade):
        # Hadoop validation logic
        pass
    
    def _validate_kafka(self, trade):
        # Kafka validation logic
        pass

# Problems:
# 1. Adding new data source requires modifying TradeValidator
# 2. Modification means testing ENTIRE class again
# 3. Risk of breaking existing validation logic
# 4. Class grows larger with every new source
# 5. Violates "closed for modification"
```

### The Solution (With OCP)

```python
# GOOD: Extend functionality without modifying existing code

# Define interface (contract) for all validators
class SourceValidator:
    def validate(self, trade):
        raise NotImplementedError

# Implement specific validator for each source
class TeradataValidator(SourceValidator):
    def validate(self, trade):
        # Teradata validation logic
        pass

class OracleValidator(SourceValidator):
    def validate(self, trade):
        # Oracle validation logic
        pass

class HadoopValidator(SourceValidator):
    def validate(self, trade):
        # Hadoop validation logic
        pass

class KafkaValidator(SourceValidator):
    def validate(self, trade):
        # Kafka validation logic
        pass

# NEW SOURCE? Just add new class, don't modify existing!
class RedisValidator(SourceValidator):
    def validate(self, trade):
        # Redis validation logic
        pass

# Main validation logic (CLOSED for modification)
class TradeProcessor:
    def __init__(self, validator: SourceValidator):
        self.validator = validator  # Can be ANY validator!
    
    def process(self, trade):
        if self.validator.validate(trade):
            # Process trade
            pass
        else:
            # Handle invalid trade
            pass

# Usage:
# For Teradata
teradata_processor = TradeProcessor(TeradataValidator())
teradata_processor.process(trade)

# For Oracle
oracle_processor = TradeProcessor(OracleValidator())
oracle_processor.process(trade)

# For NEW source (Redis)? No code modification needed!
redis_processor = TradeProcessor(RedisValidator())
redis_processor.process(trade)

# Benefits:
# 1. TradeProcessor never changed (closed for modification)
# 2. Added RedisValidator (open for extension)
# 3. No risk of breaking existing validation
# 4. Each validator tested independently
# 5. New sources plug in seamlessly
```

### Key Concept: Abstraction

```
The SECRET to OCP is ABSTRACTION:

Instead of:
    if source == "teradata": do X
    elif source == "oracle": do Y
    elif source == "kafka": do Z

Use:
    validator.validate()  # Works for ANY validator!

The abstraction (SourceValidator interface) is CLOSED.
The implementation details are OPEN for extension.
```

### OCP in Your Data Platform

```
Current challenge:
├─ CDM Next supports Teradata, Oracle, Hadoop, Kafka
├─ Each requires different extraction logic
├─ Adding new source means touching existing code
└─ Risk of breaking production

With OCP:
├─ Base Extractor class (abstract)
├─ TeradataExtractor, OracleExtractor, etc. (implementations)
├─ DataProcessor accepts any Extractor
├─ Add new source (Delta Lake)? Write DeltaLakeExtractor
├─ No existing code changes needed
└─ Safe, scalable, maintainable
```

---

## L - Liskov Substitution Principle

### Definition

**"Derived classes should be substitutable for base classes"**

Meaning: A subclass should work wherever the parent class is expected.

### The Problem (Without LSP)

```python
# BAD: Subclass violates parent class contract

class DataExtractor:
    def extract(self, config):
        """Extract data from source"""
        # Return list of records
        return records

class TeradataExtractor(DataExtractor):
    def extract(self, config):
        # Returns list of records
        return records

class BrokenExtractor(DataExtractor):
    def extract(self, config):
        # Violates contract! Returns None instead of list
        # This breaks code expecting a list!
        return None
    
    def extract_async(self, config):
        # Completely different interface
        # Can't be used where extract() expected
        pass

# Usage that breaks:
def process_records(extractor: DataExtractor, config):
    records = extractor.extract(config)
    # Code assumes records is a list!
    for record in records:  # CRASH if None!
        process(record)

# BrokenExtractor violates LSP:
# 1. Returns None instead of list (violates contract)
# 2. Has different interface (extract_async)
# 3. Can't be substituted for DataExtractor
# 4. Breaks code expecting DataExtractor
```

### The Solution (With LSP)

```python
# GOOD: All subclasses honor the parent contract

class DataExtractor:
    """Base class defines contract"""
    def extract(self, config):
        raise NotImplementedError
        # Contract: Always return list of records (never None)

class TeradataExtractor(DataExtractor):
    def extract(self, config):
        # Always returns list (might be empty)
        return [record1, record2, ...]

class OracleExtractor(DataExtractor):
    def extract(self, config):
        # Always returns list (might be empty)
        return [record1, record2, ...]

class NoDataExtractor(DataExtractor):
    def extract(self, config):
        # Always returns list (empty in this case)
        return []  # Honors contract: returns list, not None

# All subclasses can be used interchangeably:
def process_records(extractor: DataExtractor, config):
    records = extractor.extract(config)
    # Can be ANY extractor! All honor the contract
    for record in records:  # Always safe, never None!
        process(record)

# All these work the same way:
process_records(TeradataExtractor(), config)
process_records(OracleExtractor(), config)
process_records(NoDataExtractor(), config)  # Even empty list works!

# Benefits:
# 1. Code using extractor doesn't know which type
# 2. Can swap extractors without changing code
# 3. All extractors follow same contract
# 4. No surprises or broken assumptions
```

### LSP Contract Example

```
Contract of DataExtractor.extract():
├─ Input: config dict with connection details
├─ Output: List of record dicts (can be empty)
├─ Behavior: Connects to source, reads data, returns list
└─ Never returns: None, raises exceptions without handling, returns dict instead of list

Liskov Substitution means:
├─ Every subclass MUST return list (not None, not dict)
├─ Every subclass MUST handle connection errors gracefully
├─ Every subclass MUST not raise unexpected exceptions
└─ Code depending on extract() always works the same way

Violating LSP:
├─ Return None instead of empty list
├─ Raise exception without handling
├─ Return different data structure
└─ Breaks code expecting contract
```

### LSP in Your Context

```
In CDM Next, you have multiple extractors:
TeradataExtractor, OracleExtractor, HadoopExtractor, KafkaConsumer

Without LSP:
├─ Each might return different data structures
├─ Some might raise exceptions, others not
├─ Code using them has to handle each differently
└─ Fragile, hard to maintain

With LSP:
├─ All follow same contract (return list of dicts)
├─ All handle errors the same way
├─ Code using them doesn't care which type
└─ Robust, composable, maintainable
```

---

## I - Interface Segregation Principle

### Definition

**"Clients should not depend on interfaces they don't use"**

Meaning: Don't create "fat" interfaces; split them into smaller, focused ones.

### The Problem (Without ISP)

```python
# BAD: One fat interface with everything

class DataSource:
    def connect(self):
        pass
    
    def extract(self):
        pass
    
    def transform(self):
        pass
    
    def load(self):
        pass
    
    def delete(self):
        pass
    
    def backup(self):
        pass
    
    def monitor(self):
        pass

# Some implementations don't need all methods:

class ReadOnlyDatabase(DataSource):
    def connect(self):
        pass
    
    def extract(self):
        pass
    
    # DON'T NEED: transform, load, delete, backup, monitor
    # But forced to implement them anyway!
    def transform(self):
        raise NotImplementedError("Read-only DB doesn't transform")
    
    def load(self):
        raise NotImplementedError("Read-only DB can't load")
    
    def delete(self):
        raise NotImplementedError("Read-only DB can't delete")
    
    def backup(self):
        raise NotImplementedError("Read-only DB doesn't backup")
    
    def monitor(self):
        raise NotImplementedError("Read-only DB doesn't monitor")

# Problems:
# 1. ReadOnlyDatabase forced to implement 5 unwanted methods
# 2. Implementation = raising exceptions (confusing!)
# 3. Code calling backup() on ReadOnlyDatabase crashes
# 4. Wastes time implementing unused methods
# 5. Violates ISP (depends on interfaces it doesn't use)
```

### The Solution (With ISP)

```python
# GOOD: Split fat interface into smaller, focused interfaces

# Small, focused interfaces
class Connectable:
    def connect(self):
        pass

class Readable:
    def extract(self):
        pass

class Writable:
    def load(self):
        pass

class Transformable:
    def transform(self):
        pass

class Deletable:
    def delete(self):
        pass

class Backupable:
    def backup(self):
        pass

class Monitorable:
    def monitor(self):
        pass

# Implement only what you need:

class ReadOnlyDatabase(Connectable, Readable):
    """Only needs to connect and read"""
    def connect(self):
        # Connect to database
        pass
    
    def extract(self):
        # Read from database
        pass
    # That's it! No unwanted methods!

class FullDatabase(Connectable, Readable, Writable, Transformable, 
                   Deletable, Backupable, Monitorable):
    """Implements everything"""
    def connect(self):
        pass
    
    def extract(self):
        pass
    
    def load(self):
        pass
    
    def transform(self):
        pass
    
    def delete(self):
        pass
    
    def backup(self):
        pass
    
    def monitor(self):
        pass

# Usage:
def read_from_source(source: Readable):
    """Only needs Readable interface"""
    data = source.extract()
    return data

# Works with ANY Readable:
data = read_from_source(ReadOnlyDatabase())  # Works!
data = read_from_source(FullDatabase())  # Also works!

def write_to_sink(sink: Writable):
    """Only needs Writable interface"""
    sink.load(data)

# write_to_sink(ReadOnlyDatabase())  # Type error! Can't call Writable methods
write_to_sink(FullDatabase())  # Works!

# Benefits:
# 1. ReadOnlyDatabase only implements needed methods
# 2. No confusing "not implemented" exceptions
# 3. Client specifies exact interface needed
# 4. Cleaner, more honest code
```

### ISP Design Pattern

```
ISP suggests:
├─ Many small interfaces (each with few methods)
├─ Each interface does ONE thing
├─ Classes implement only what they need
└─ Code depends on small, focused interfaces

NOT:
├─ Few large interfaces (many methods)
├─ Each interface tries to be everything
├─ Classes implement unused methods
└─ Code depends on large, bloated interfaces
```

### ISP in Your Data Platform

```
Without ISP:
├─ Pipeline interface: extract(), transform(), load(), monitor(), alert(), etc.
├─ SimpleReader forced to implement all methods
└─ Half implementation is raising exceptions

With ISP:
├─ Extractor interface: extract()
├─ Transformer interface: transform()
├─ Loader interface: load()
├─ Monitor interface: send_alert()
├─ SimpleReader implements just Extractor
└─ Clean, focused, honest code
```

---

## D - Dependency Inversion Principle

### Definition

**"High-level modules should not depend on low-level modules. Both should depend on abstractions."**

Meaning: Depend on abstractions (interfaces), not concrete implementations.

### The Problem (Without DIP)

```python
# BAD: High-level code depends on low-level implementation

class PostgresqlDatabase:
    """Low-level database implementation"""
    def connect(self):
        # Connect to PostgreSQL
        pass
    
    def read(self, query):
        # Read from PostgreSQL
        pass

class TradeProcessor:
    """High-level business logic"""
    def __init__(self):
        # TIGHTLY COUPLED to PostgreSQL!
        self.database = PostgresqlDatabase()
    
    def process_trades(self):
        trades = self.database.read("SELECT * FROM trades")
        # Process trades
        pass

# Problems:
# 1. TradeProcessor tightly coupled to PostgresqlDatabase
# 2. Can't use BigQuery (would have to change TradeProcessor!)
# 3. Can't test TradeProcessor without real database
# 4. Adding new database requires modifying TradeProcessor
# 5. TradeProcessor depends on low-level details (PostgreSQL API)
```

### The Solution (With DIP)

```python
# GOOD: Depend on abstractions, not implementations

# Define abstraction (interface)
class DatabaseInterface:
    """High-level abstraction"""
    def read(self, query):
        raise NotImplementedError

# Low-level implementations
class PostgresqlDatabase(DatabaseInterface):
    def read(self, query):
        # PostgreSQL implementation
        pass

class BigQueryDatabase(DatabaseInterface):
    def read(self, query):
        # BigQuery implementation
        pass

# High-level code
class TradeProcessor:
    def __init__(self, database: DatabaseInterface):
        # Depends on ABSTRACTION, not PostgreSQL!
        self.database = database
    
    def process_trades(self):
        trades = self.database.read("SELECT * FROM trades")
        # Process trades (same for any database!)
        pass

# Usage:
# With PostgreSQL:
processor = TradeProcessor(PostgresqlDatabase())
processor.process_trades()

# With BigQuery:
processor = TradeProcessor(BigQueryDatabase())
processor.process_trades()

# Same TradeProcessor, different databases!
# No code changes needed!

# Testing:
class MockDatabase(DatabaseInterface):
    def read(self, query):
        return [mock_trade1, mock_trade2]

processor = TradeProcessor(MockDatabase())
# Test without real database! Fast, isolated tests.

# Benefits:
# 1. TradeProcessor depends on abstraction (stable)
# 2. Can swap databases without changing TradeProcessor
# 3. Can test with mock database
# 4. Adding new database is straightforward
# 5. Business logic separated from infrastructure details
```

### Dependency Diagram

```
WITHOUT DIP (Bad):
TradeProcessor (high-level)
    ↓ depends on
PostgresqlDatabase (low-level)

If you want to use BigQuery:
├─ Must modify TradeProcessor
└─ High and low levels tightly coupled

WITH DIP (Good):
TradeProcessor (high-level)
    ↓ depends on
DatabaseInterface (abstraction)
    ↑ implemented by
PostgresqlDatabase (low-level)
BigQueryDatabase (low-level)

Both depend on abstraction!
Easy to add new databases!
High-level unaffected by changes!
```

### DIP in Your CDM Next Platform

```
Current (potential problem):
├─ DataMigrationPipeline depends on TeradataExtractor
├─ DataMigrationPipeline depends on OracleExtractor
├─ DataMigrationPipeline depends on BigQueryLoader
└─ Tightly coupled to specific implementations

With DIP:
├─ DataMigrationPipeline depends on Extractor interface
├─ DataMigrationPipeline depends on Loader interface
├─ Specific implementations (Teradata, Oracle, BigQuery) implement interfaces
├─ Add new source (Delta Lake)? Implement Extractor interface
└─ No changes to DataMigrationPipeline!
```

---

## SOLID in Practice

### Complete Example: Building a Data Pipeline

```python
# Let's apply all 5 SOLID principles together

# D - Depend on abstractions
class DataExtractor:
    def extract(self):
        raise NotImplementedError

class DataTransformer:
    def transform(self, data):
        raise NotImplementedError

class DataLoader:
    def load(self, data):
        raise NotImplementedError

# S - Single Responsibility
class BigQueryExtractor(DataExtractor):
    def extract(self):
        # Only extracts from BigQuery
        return big_query_client.query(...)

class TradeTransformer(DataTransformer):
    def transform(self, data):
        # Only transforms trades
        return [apply_business_logic(record) for record in data]

class PostgresLoader(DataLoader):
    def load(self, data):
        # Only loads to Postgres
        return postgres_client.insert(data)

# I - Interface Segregation
class Monitorable:
    def send_alert(self, message):
        raise NotImplementedError

class AlertManager(Monitorable):
    def send_alert(self, message):
        # Send alert via email/Slack
        pass

# O - Open/Closed Principle
class DataPipeline:
    def __init__(self, extractor: DataExtractor, 
                 transformer: DataTransformer,
                 loader: DataLoader,
                 alert_manager: Monitorable):
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader
        self.alert_manager = alert_manager
    
    def run(self):
        try:
            data = self.extractor.extract()
            data = self.transformer.transform(data)
            self.loader.load(data)
            self.alert_manager.send_alert("Pipeline succeeded")
        except Exception as e:
            self.alert_manager.send_alert(f"Pipeline failed: {e}")

# L - Liskov Substitution (all components honor their contracts)
# Can swap any extractor, transformer, or loader!

# Usage:
pipeline = DataPipeline(
    extractor=BigQueryExtractor(),
    transformer=TradeTransformer(),
    loader=PostgresLoader(),
    alert_manager=AlertManager()
)

pipeline.run()

# Want to use different database?
# Create new loader, plug it in, no other changes!

# Want to test?
class MockExtractor(DataExtractor):
    def extract(self):
        return [mock_trade1, mock_trade2]

test_pipeline = DataPipeline(
    extractor=MockExtractor(),  # Use mock
    transformer=TradeTransformer(),
    loader=PostgresLoader(),
    alert_manager=AlertManager()
)

test_pipeline.run()  # Fast test, no real data!

# Benefits of SOLID in this example:
# 1. Each class has ONE responsibility (S)
# 2. Can add new extractors without modifying Pipeline (O)
# 3. All extractors work the same way (L)
# 4. Components don't depend on unused methods (I)
# 5. Pipeline depends on abstractions, not implementations (D)
```

---

## Common SOLID Violations

### Violation 1: God Object (Violates SRP)

```python
# BAD: One class doing everything
class TradeManager:
    def extract_from_kafka(self):
        pass
    
    def parse_json(self):
        pass
    
    def validate(self):
        pass
    
    def store_to_postgres(self):
        pass
    
    def send_alerts(self):
        pass
    
    def generate_reports(self):
        pass
    # ... 20 more methods ...

# FIX: Split into multiple classes with single responsibilities
class KafkaExtractor:
    def extract(self): pass

class JsonParser:
    def parse(self): pass

class TradeValidator:
    def validate(self): pass

class PostgresLoader:
    def load(self): pass

class AlertManager:
    def send_alert(self): pass

class ReportGenerator:
    def generate(self): pass
```

### Violation 2: Fragile Base Class (Violates OCP)

```python
# BAD: Base class changes break all subclasses
class Database:
    def connect(self):
        pass
    
    def query(self, sql):
        pass
    
    def close(self):
        pass

class PostgresDatabase(Database):
    def connect(self):
        pass
    
    def query(self, sql):
        pass
    
    def close(self):
        pass

# Someone modifies Database.connect() signature:
# Now PostgresDatabase is broken!

# FIX: Use composition or more stable abstractions
class Connectable:
    def connect(self):
        pass

class Queryable:
    def query(self, sql):
        pass

# Each can evolve independently
```

### Violation 3: Tight Coupling (Violates DIP)

```python
# BAD: Depends on concrete implementation
class ReportGenerator:
    def __init__(self):
        self.db = PostgresqlDatabase()  # Hardcoded!

# FIX: Depend on abstraction
class ReportGenerator:
    def __init__(self, database: Database):
        self.db = database  # Can be any database!
```

---

## SOLID Summary

```
S - Single Responsibility
  └─ One reason to change
  └─ Do one thing well
  └─ Example: TradeValidator (validates only)

O - Open/Closed
  └─ Open for extension, closed for modification
  └─ Add features without changing existing code
  └─ Example: Add new Validator without modifying others

L - Liskov Substitution
  └─ Subclasses must honor parent contracts
  └─ Can swap implementations transparently
  └─ Example: Any Extractor works the same way

I - Interface Segregation
  └─ Don't depend on methods you don't use
  └─ Many small interfaces, not one fat interface
  └─ Example: ReadOnlyDatabase only implements read()

D - Dependency Inversion
  └─ Depend on abstractions, not implementations
  └─ High and low-level modules depend on abstractions
  └─ Example: Pipeline depends on interfaces, not PostgreSQL
```

---

**You now understand SOLID principles.** 

**Next: Design Patterns show you how to apply these principles to solve common problems!**
