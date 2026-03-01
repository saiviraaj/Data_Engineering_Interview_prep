
# Data Engineer Interview Handbook (Senior Level – 10+ Years)

This document is a comprehensive reference for senior Cloud/Data Engineers.
It is designed for quick interview revision and long-term reuse.

---

## 1. PYTHON FOR DATA ENGINEERS

### Core Concepts
Python is used for orchestration, ETL logic, validation, and pipeline glue code.

Data types:
- int, float, str
- list, tuple
- set, dict

Mutability:
- Mutable: list, dict, set
- Immutable: int, float, str, tuple

```python
a = [1,2]
b = a
b.append(3)
# a becomes [1,2,3]
```

### Common Patterns

Frequency map:
```python
freq = {}
for x in data:
    freq[x] = freq.get(x,0) + 1
```

Two sum:
```python
seen = set()
for n in nums:
    if target-n in seen:
        return True
    seen.add(n)
```

Sliding window (fixed):
```python
def max_sum(nums,k):
    s = sum(nums[:k])
    best = s
    for i in range(k,len(nums)):
        s += nums[i] - nums[i-k]
        best = max(best,s)
    return best
```

Sliding window (variable):
```python
def longest_unique(s):
    seen=set(); l=0; res=0
    for r in range(len(s)):
        while s[r] in seen:
            seen.remove(s[l]); l+=1
        seen.add(s[r])
        res=max(res,r-l+1)
    return res
```

---

## 2. SQL

Core SQL:
```sql
SELECT dept, COUNT(*)
FROM employees
WHERE salary > 100
GROUP BY dept
HAVING COUNT(*) > 3;
```

Joins:
```sql
SELECT *
FROM customers c
LEFT JOIN orders o
ON c.customer_id = o.customer_id;
```

Self join:
```sql
SELECT e.name, m.name
FROM employees e
LEFT JOIN employees m
ON e.manager_id = m.emp_id;
```

Window functions:
```sql
SELECT emp_id,
DENSE_RANK() OVER(PARTITION BY dept ORDER BY salary DESC) r
FROM employees;
```

Top-N per group:
```sql
SELECT *
FROM (
  SELECT *, DENSE_RANK() OVER(PARTITION BY dept ORDER BY salary DESC) r
  FROM employees
) t WHERE r <= 2;
```

---

## 3. DATA ENGINEERING CONCEPTS

- ETL vs ELT
- Batch vs Streaming
- Idempotency
- Late data
- Backfills

---

## 4. PYSPARK

```python
df.select("col")
df.filter(df.col > 10)
df.groupBy("dept").agg(sum("salary"))
df.join(other,"id","left")
```

---

## 5. SPARK INTERNALS

- Driver vs Executors
- Lazy evaluation
- Shuffles
- Partitioning

---

## 6. DATA WAREHOUSING

- Star vs Snowflake
- Fact vs Dimension
- SCD Type 1 & 2
- Partitioning & Clustering
