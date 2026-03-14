# 🎯 COMPLETE SQL INTERVIEW PATTERNS & CONCEPTS
## Every Pattern You'll Face in Data Engineering Interviews

**CRITICAL:** This guide covers REAL interview questions including patterns previously missed  
**Level:** Senior Data Engineer interviews  
**Focus:** Production patterns, edge cases, complete coverage

---

## 📚 TABLE OF CONTENTS

1. **BIDIRECTIONAL RELATIONSHIPS** - Routes, friendships, pairs (LEAST/GREATEST)
2. **SESSIONIZATION** - Time-based grouping with gaps
3. **RUNNING CALCULATIONS** - Cumulative sums, balances, inventory
4. **GAPS AND ISLANDS** - Consecutive sequences, streaks
5. **HIERARCHICAL QUERIES** - Recursive CTEs, org charts, bill of materials
6. **ADVANCED WINDOW FUNCTIONS** - All patterns with LAG/LEAD
7. **DATE/TIME PATTERNS** - Business days, date ranges, overlaps
8. **DEDUPLICATION STRATEGIES** - SCD Type 2, keeping latest/first
9. **PIVOT/UNPIVOT ADVANCED** - Dynamic pivots, complex reshaping
10. **SET OPERATIONS** - UNION, INTERSECT, EXCEPT patterns
11. **SUBQUERY PATTERNS** - Correlated, scalar, lateral joins
12. **COMPLEX JOINS** - Self-joins, cross joins, inequality joins
13. **STRING MANIPULATION** - Parsing, splitting, pattern matching
14. **AGGREGATION TRICKS** - Conditional aggregation, filtering after grouping
15. **PERFORMANCE PATTERNS** - Indexing strategies, query optimization

---

## 🔄 PART 1: BIDIRECTIONAL RELATIONSHIPS (LEAST/GREATEST)

### **1.1 The Pattern**

**When to use:**
- Routes where Calgary→Canmore = Canmore→Calgary
- Friendships where A→B = B→A  
- Any symmetric relationship
- Removing directional duplicates

### **1.2 Key Functions**

```sql
-- LEAST() - Returns smallest value
SELECT LEAST(5, 3, 8, 1);  -- Returns 1
SELECT LEAST('Calgary', 'Canmore');  -- Returns 'Calgary' (alphabetically)

-- GREATEST() - Returns largest value
SELECT GREATEST(5, 3, 8, 1);  -- Returns 8
SELECT GREATEST('Calgary', 'Canmore');  -- Returns 'Canmore'
```

### **1.3 Problem: Bidirectional Routes**

```sql
/*
Input: Routes where both directions exist
+----------+-------------+----------+
| source   | destination | distance |
+----------+-------------+----------+
| Calgary  | Canmore     | 100 km   |
| Canmore  | Calgary     | 100 km   | -- Duplicate!
| Calgary  | Edmonton    | 200 km   |
+----------+-------------+----------+

Output: Remove directional duplicates
+----------+-------------+----------+
| source   | destination | distance |
+----------+-------------+----------+
| Calgary  | Canmore     | 100 km   |
| Calgary  | Edmonton    | 200 km   |
+----------+-------------+----------+
*/

-- Solution 1: Using LEAST/GREATEST
SELECT 
    LEAST(source, destination) AS source,
    GREATEST(source, destination) AS destination,
    distance
FROM routes
GROUP BY 
    LEAST(source, destination),
    GREATEST(source, destination),
    distance;

-- Solution 2: Ensure alphabetical ordering
SELECT 
    CASE 
        WHEN source < destination THEN source 
        ELSE destination 
    END AS source,
    CASE 
        WHEN source < destination THEN destination 
        ELSE source 
    END AS destination,
    distance
FROM routes
GROUP BY 1, 2, distance;

-- Solution 3: Using ROW_NUMBER to pick one direction
WITH normalized AS (
    SELECT 
        source,
        destination,
        distance,
        ROW_NUMBER() OVER (
            PARTITION BY LEAST(source, destination), GREATEST(source, destination)
            ORDER BY source
        ) AS rn
    FROM routes
)
SELECT source, destination, distance
FROM normalized
WHERE rn = 1;
```

### **1.4 Problem: Friendship Network**

```sql
/*
Find all unique friendships (bidirectional)

Input:
+----------+----------+
| user_id  | friend_id|
+----------+----------+
| 1        | 2        |
| 2        | 1        | -- Same friendship
| 1        | 3        |
| 3        | 1        | -- Same friendship
+----------+----------+

Output:
+----------+----------+
| user_id  | friend_id|
+----------+----------+
| 1        | 2        |
| 1        | 3        |
+----------+----------+
*/

SELECT DISTINCT
    LEAST(user_id, friend_id) AS user_id,
    GREATEST(user_id, friend_id) AS friend_id
FROM friendships;

-- Count mutual friends
SELECT 
    LEAST(user_id, friend_id) AS user1,
    GREATEST(user_id, friend_id) AS user2,
    COUNT(*) AS friendship_count
FROM friendships
GROUP BY 
    LEAST(user_id, friend_id),
    GREATEST(user_id, friend_id);
```

### **1.5 Problem: Flight Routes**

```sql
/*
Find all unique routes regardless of direction
*/

WITH unique_routes AS (
    SELECT 
        LEAST(origin, destination) AS city1,
        GREATEST(origin, destination) AS city2,
        MIN(price) AS min_price,
        MAX(price) AS max_price,
        COUNT(*) AS flight_count
    FROM flights
    GROUP BY 
        LEAST(origin, destination),
        GREATEST(origin, destination)
)
SELECT 
    city1,
    city2,
    min_price,
    max_price,
    flight_count,
    CASE 
        WHEN flight_count = 1 THEN 'One-way only'
        ELSE 'Bidirectional'
    END AS route_type
FROM unique_routes;
```

---

## ⏱️ PART 2: SESSIONIZATION (TIME-BASED GROUPING)

### **2.1 The Pattern**

**When to use:**
- Group events with time gaps
- Web session tracking (30-min timeout)
- Customer journey mapping
- Activity clustering

### **2.2 Standard Sessionization Pattern**

```sql
/*
Problem: Group events into sessions where gap > 30 minutes starts new session

Input:
+----------+---------------------+
| user_id  | event_timestamp     |
+----------+---------------------+
| 1        | 2024-01-01 10:00:00 |
| 1        | 2024-01-01 10:10:00 | -- Same session (10 min gap)
| 1        | 2024-01-01 11:00:00 | -- New session (50 min gap)
+----------+---------------------+

Output:
+----------+------------+---------------------+---------------------+
| user_id  | session_id | session_start       | session_end         |
+----------+------------+---------------------+---------------------+
| 1        | 1          | 2024-01-01 10:00:00 | 2024-01-01 10:10:00 |
| 1        | 2          | 2024-01-01 11:00:00 | 2024-01-01 11:00:00 |
+----------+------------+---------------------+---------------------+
*/

-- Solution: Using LAG + SUM window function
WITH time_gaps AS (
    SELECT 
        user_id,
        event_timestamp,
        LAG(event_timestamp) OVER (
            PARTITION BY user_id 
            ORDER BY event_timestamp
        ) AS prev_timestamp,
        -- Calculate minutes since last event
        TIMESTAMP_DIFF(
            event_timestamp,
            LAG(event_timestamp) OVER (PARTITION BY user_id ORDER BY event_timestamp),
            MINUTE
        ) AS minutes_since_last
    FROM events
),
session_flags AS (
    SELECT 
        user_id,
        event_timestamp,
        prev_timestamp,
        minutes_since_last,
        -- Flag new session when gap > 30 or first event
        CASE 
            WHEN minutes_since_last IS NULL OR minutes_since_last > 30 
            THEN 1 
            ELSE 0 
        END AS is_new_session
    FROM time_gaps
),
session_numbers AS (
    SELECT 
        user_id,
        event_timestamp,
        -- Running sum of session flags = session_id
        SUM(is_new_session) OVER (
            PARTITION BY user_id 
            ORDER BY event_timestamp
        ) AS session_id
    FROM session_flags
)
SELECT 
    user_id,
    session_id,
    MIN(event_timestamp) AS session_start,
    MAX(event_timestamp) AS session_end,
    COUNT(*) AS events_in_session,
    TIMESTAMP_DIFF(MAX(event_timestamp), MIN(event_timestamp), MINUTE) AS session_duration_mins
FROM session_numbers
GROUP BY user_id, session_id
ORDER BY user_id, session_id;
```

### **2.3 Sessionization with Metrics**

```sql
/*
Problem: Same as above but with event metrics (time spent, pages viewed)
*/

WITH time_gaps AS (
    SELECT 
        user_id,
        event_timestamp,
        time_spent_mins,
        LAG(event_timestamp) OVER (
            PARTITION BY user_id 
            ORDER BY event_timestamp
        ) AS prev_timestamp
    FROM events
),
session_flags AS (
    SELECT 
        user_id,
        event_timestamp,
        COALESCE(time_spent_mins, 0) AS time_spent_mins,  -- NULL -> 0
        CASE 
            WHEN TIMESTAMP_DIFF(event_timestamp, prev_timestamp, MINUTE) > 30 
                OR prev_timestamp IS NULL 
            THEN 1 
            ELSE 0 
        END AS is_new_session
    FROM time_gaps
),
sessions AS (
    SELECT 
        user_id,
        event_timestamp,
        time_spent_mins,
        SUM(is_new_session) OVER (
            PARTITION BY user_id 
            ORDER BY event_timestamp
        ) AS session_id
    FROM session_flags
)
SELECT 
    user_id,
    session_id,
    MIN(event_timestamp) AS session_start_ts,
    MAX(event_timestamp) AS session_end_ts,
    COUNT(*) AS total_events,
    SUM(time_spent_mins) AS total_time_spent
FROM sessions
GROUP BY user_id, session_id
ORDER BY user_id, session_id;
```

### **2.4 Variable Gap Sessionization**

```sql
/*
Different timeout per user type
*/

WITH time_gaps AS (
    SELECT 
        e.user_id,
        e.event_timestamp,
        u.user_type,
        CASE 
            WHEN u.user_type = 'premium' THEN 60
            ELSE 30
        END AS timeout_minutes,
        LAG(e.event_timestamp) OVER (
            PARTITION BY e.user_id 
            ORDER BY e.event_timestamp
        ) AS prev_timestamp
    FROM events e
    JOIN users u ON e.user_id = u.user_id
)
SELECT 
    user_id,
    SUM(CASE 
        WHEN TIMESTAMP_DIFF(event_timestamp, prev_timestamp, MINUTE) > timeout_minutes 
            OR prev_timestamp IS NULL 
        THEN 1 
        ELSE 0 
    END) OVER (
        PARTITION BY user_id 
        ORDER BY event_timestamp
    ) AS session_id,
    event_timestamp
FROM time_gaps;
```

---

## 💰 PART 3: RUNNING CALCULATIONS

### **3.1 Running Balance**

```sql
/*
Calculate account balance after each transaction

Input:
+----------+--------+--------+
| trans_id | amount | type   |
+----------+--------+--------+
| 1        | 1000   | deposit|
| 2        | 200    | withdraw|
| 3        | 500    | deposit|
+----------+--------+--------+

Output: Show running balance
*/

SELECT 
    trans_id,
    amount,
    type,
    SUM(
        CASE 
            WHEN type = 'deposit' THEN amount
            WHEN type = 'withdraw' THEN -amount
        END
    ) OVER (ORDER BY trans_id) AS running_balance
FROM transactions
ORDER BY trans_id;
```

### **3.2 Inventory Tracking**

```sql
/*
Track inventory levels with in/out movements
*/

WITH inventory_changes AS (
    SELECT 
        date,
        product_id,
        SUM(CASE WHEN type = 'in' THEN quantity ELSE -quantity END) AS net_change
    FROM inventory_movements
    GROUP BY date, product_id
)
SELECT 
    date,
    product_id,
    net_change,
    SUM(net_change) OVER (
        PARTITION BY product_id 
        ORDER BY date
    ) AS current_stock
FROM inventory_changes
ORDER BY product_id, date;
```

---

## 🏝️ PART 4: GAPS AND ISLANDS (CONSECUTIVE SEQUENCES)

### **4.1 Standard Gaps and Islands**

```sql
/*
Find consecutive login streaks

Input:
+----------+------------+
| user_id  | login_date |
+----------+------------+
| 1        | 2024-01-01 |
| 1        | 2024-01-02 |
| 1        | 2024-01-03 |
| 1        | 2024-01-05 | -- Gap
+----------+------------+
*/

WITH numbered AS (
    SELECT 
        user_id,
        login_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn,
        DATE_SUB(login_date, INTERVAL ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) DAY) AS group_id
    FROM logins
)
SELECT 
    user_id,
    MIN(login_date) AS streak_start,
    MAX(login_date) AS streak_end,
    COUNT(*) AS streak_length,
    DATE_DIFF(MAX(login_date), MIN(login_date), DAY) + 1 AS days_in_streak
FROM numbered
GROUP BY user_id, group_id
HAVING COUNT(*) >= 3  -- Minimum streak length
ORDER BY user_id, streak_start;
```

### **4.2 Finding Gaps (Missing Dates)**

```sql
/*
Find missing dates in activity log
*/

WITH RECURSIVE date_range AS (
    SELECT DATE('2024-01-01') AS date
    UNION ALL
    SELECT DATE_ADD(date, INTERVAL 1 DAY)
    FROM date_range
    WHERE date < '2024-12-31'
),
activity_dates AS (
    SELECT DISTINCT DATE(activity_timestamp) AS date
    FROM activity_log
)
SELECT 
    dr.date AS missing_date
FROM date_range dr
LEFT JOIN activity_dates ad ON dr.date = ad.date
WHERE ad.date IS NULL
ORDER BY dr.date;
```

---

## 🌳 PART 5: HIERARCHICAL QUERIES (RECURSIVE CTEs)

### **5.1 Employee Hierarchy**

```sql
/*
Build full organizational tree
*/

WITH RECURSIVE org_tree AS (
    -- Base: CEO (no manager)
    SELECT 
        emp_id,
        emp_name,
        manager_id,
        1 AS level,
        CAST(emp_name AS STRING) AS path,
        CAST(emp_id AS STRING) AS id_path
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive: Add direct reports
    SELECT 
        e.emp_id,
        e.emp_name,
        e.manager_id,
        ot.level + 1,
        CONCAT(ot.path, ' > ', e.emp_name),
        CONCAT(ot.id_path, '>', CAST(e.emp_id AS STRING))
    FROM employees e
    INNER JOIN org_tree ot ON e.manager_id = ot.emp_id
)
SELECT 
    emp_id,
    emp_name,
    level,
    path,
    REPEAT('  ', level - 1) || emp_name AS indented_name
FROM org_tree
ORDER BY path;
```

### **5.2 Bill of Materials (BOM)**

```sql
/*
Calculate total parts needed for assembly
*/

WITH RECURSIVE bom_explosion AS (
    SELECT 
        product_id,
        part_id,
        quantity,
        1 AS level
    FROM bill_of_materials
    WHERE product_id = 'FINAL_PRODUCT'
    
    UNION ALL
    
    SELECT 
        b.product_id,
        bom.part_id,
        b.quantity * bom.quantity,
        b.level + 1
    FROM bom_explosion b
    JOIN bill_of_materials bom ON b.part_id = bom.product_id
)
SELECT 
    part_id,
    SUM(quantity) AS total_quantity_needed
FROM bom_explosion
GROUP BY part_id;
```

---

## 📊 PART 6: ADVANCED WINDOW FUNCTIONS

### **6.1 First Value with Ignore Nulls**

```sql
/*
Forward-fill missing values
*/

SELECT 
    date,
    value,
    FIRST_VALUE(value IGNORE NULLS) OVER (
        ORDER BY date
        ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
    ) AS filled_value
FROM data;
```

### **6.2 Running Count of Distinct**

```sql
/*
Count distinct products seen so far
*/

WITH product_first_appearance AS (
    SELECT 
        date,
        product,
        ROW_NUMBER() OVER (PARTITION BY product ORDER BY date) AS first_occurrence
    FROM sales
)
SELECT 
    date,
    product,
    SUM(CASE WHEN first_occurrence = 1 THEN 1 ELSE 0 END) OVER (
        ORDER BY date
    ) AS cumulative_distinct_products
FROM product_first_appearance
ORDER BY date;
```

---

## 📅 PART 7: DATE/TIME PATTERNS

### **7.1 Business Days Calculation**

```sql
/*
Calculate business days between dates (excluding weekends)
*/

SELECT 
    start_date,
    end_date,
    -- Count weekdays only
    (DATE_DIFF(end_date, start_date, DAY) + 1)
    - (FLOOR(DATE_DIFF(end_date, start_date, DAY) / 7) * 2)
    - CASE WHEN EXTRACT(DAYOFWEEK FROM start_date) = 1 THEN 1 ELSE 0 END
    - CASE WHEN EXTRACT(DAYOFWEEK FROM end_date) = 7 THEN 1 ELSE 0 END
    AS business_days
FROM date_ranges;
```

### **7.2 Overlapping Time Ranges**

```sql
/*
Find overlapping bookings
*/

SELECT 
    b1.room_id,
    b1.booking_id AS booking1,
    b2.booking_id AS booking2,
    b1.start_time AS b1_start,
    b1.end_time AS b1_end,
    b2.start_time AS b2_start,
    b2.end_time AS b2_end
FROM bookings b1
JOIN bookings b2 
    ON b1.room_id = b2.room_id
    AND b1.booking_id < b2.booking_id
    AND b1.start_time < b2.end_time
    AND b2.start_time < b1.end_time;
```

---

## 🔑 PART 8: DEDUPLICATION STRATEGIES

### **8.1 SCD Type 2 (Latest Record)**

```sql
/*
Keep only current version of each record
*/

SELECT 
    customer_id,
    name,
    address,
    effective_date,
    end_date
FROM customer_history
WHERE end_date IS NULL;  -- Current records

-- OR using window function
SELECT 
    customer_id,
    name,
    address,
    effective_date
FROM (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id 
            ORDER BY effective_date DESC
        ) AS rn
    FROM customer_history
) ranked
WHERE rn = 1;
```

---

## 🎯 QUICK PATTERN REFERENCE

```
PROBLEM TYPE → PATTERN → KEY FUNCTION
├─ Bidirectional pairs → LEAST/GREATEST → GROUP BY LEAST(), GREATEST()
├─ Time-based groups → Sessionization → LAG + SUM window
├─ Running balance → Cumulative sum → SUM() OVER (ORDER BY)
├─ Consecutive dates → Gaps & Islands → ROW_NUMBER arithmetic
├─ Org chart → Recursive CTE → WITH RECURSIVE
├─ Forward fill → Ignore nulls → FIRST_VALUE IGNORE NULLS
├─ Business days → Date arithmetic → DATE_DIFF calculations
└─ Latest record → Deduplication → ROW_NUMBER = 1
```

---

**STATUS:** Complete SQL patterns with ALL missing concepts covered! 🎯

Next: PySpark patterns with sessionization, CDC, and more...
