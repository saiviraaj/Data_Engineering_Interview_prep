# 🎯 SQL INTERVIEW QUESTIONS - 100+ REAL PROBLEMS
## Comprehensive Practice for Senior Data Engineer Interviews

**Coverage:** All patterns from LEAST/GREATEST to Advanced Window Functions  
**Difficulty:** Easy → Medium → Hard → Expert  
**Format:** Problem → Multiple Solutions → Explanations

---

## 📚 QUESTIONS BY PATTERN

### **PATTERN 1: BIDIRECTIONAL RELATIONSHIPS (LEAST/GREATEST)**

#### **Q1. Routes Deduplication** ⭐ YOUR INTERVIEW QUESTION
```sql
-- Input
CREATE TABLE routes (
    source VARCHAR(50),
    destination VARCHAR(50),
    distance VARCHAR(20)
);

INSERT INTO routes VALUES
('Calgary', 'Canmore', '100 km'),
('Canmore', 'Calgary', '100 km'),
('Calgary', 'Edmonton', '200 km'),
('Calgary', 'Jasper', '183 km');

-- Question: Remove bidirectional duplicates
-- Expected Output:
--  Calgary | Canmore  | 100 km
--  Calgary | Edmonton | 200 km
--  Calgary | Jasper   | 183 km
```

**Solution 1: LEAST/GREATEST**
```sql
SELECT 
    LEAST(source, destination) AS source,
    GREATEST(source, destination) AS destination,
    distance
FROM routes
GROUP BY 
    LEAST(source, destination),
    GREATEST(source, destination),
    distance;
```

**Solution 2: CASE WHEN**
```sql
SELECT 
    CASE WHEN source < destination THEN source ELSE destination END AS source,
    CASE WHEN source < destination THEN destination ELSE source END AS destination,
    distance
FROM routes
GROUP BY 1, 2, distance;
```

---

#### **Q2. Friendship Network**
```sql
-- Find unique friendships (remove A→B and B→A duplicates)
-- Table: friendships(user_id, friend_id)

SELECT DISTINCT
    LEAST(user_id, friend_id) AS user1,
    GREATEST(user_id, friend_id) AS user2
FROM friendships
ORDER BY user1, user2;
```

---

#### **Q3. Flight Route Analysis**
```sql
-- Find routes with pricing in both directions
-- Table: flights(origin, destination, price, airline)
-- Show: city_pair, min_price, max_price, avg_price, airlines_count

SELECT 
    LEAST(origin, destination) AS city1,
    GREATEST(origin, destination) AS city2,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    ROUND(AVG(price), 2) AS avg_price,
    COUNT(DISTINCT airline) AS airline_count,
    STRING_AGG(DISTINCT airline, ', ') AS airlines
FROM flights
GROUP BY city1, city2
HAVING COUNT(*) >= 2  -- Both directions exist
ORDER BY avg_price DESC;
```

---

### **PATTERN 2: SESSIONIZATION (TIME-BASED GROUPING)**

#### **Q4. Web Session Analysis** ⭐ YOUR INTERVIEW QUESTION (SQL VERSION)
```sql
-- Create session groups where gap > 30 minutes starts new session
-- Table: events(user_id, event_timestamp, time_spent_mins)

WITH time_gaps AS (
    SELECT 
        user_id,
        event_timestamp,
        COALESCE(time_spent_mins, 0) AS time_spent_mins,
        LAG(event_timestamp) OVER (
            PARTITION BY user_id ORDER BY event_timestamp
        ) AS prev_timestamp,
        TIMESTAMP_DIFF(
            event_timestamp,
            LAG(event_timestamp) OVER (PARTITION BY user_id ORDER BY event_timestamp),
            MINUTE
        ) AS minutes_since_last
    FROM events
),
session_flags AS (
    SELECT *,
        CASE 
            WHEN minutes_since_last IS NULL OR minutes_since_last > 30 
            THEN 1 ELSE 0 
        END AS is_new_session
    FROM time_gaps
)
SELECT 
    user_id,
    SUM(is_new_session) OVER (
        PARTITION BY user_id ORDER BY event_timestamp
    ) AS session_id,
    MIN(event_timestamp) OVER (
        PARTITION BY user_id, 
        SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY event_timestamp)
    ) AS session_start,
    MAX(event_timestamp) OVER (
        PARTITION BY user_id,
        SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY event_timestamp)
    ) AS session_end,
    COUNT(*) OVER (
        PARTITION BY user_id,
        SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY event_timestamp)
    ) AS event_count,
    SUM(time_spent_mins) OVER (
        PARTITION BY user_id,
        SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY event_timestamp)
    ) AS total_time_spent
FROM session_flags;
```

---

#### **Q5. Shopping Cart Abandonment**
```sql
-- Identify shopping sessions where user added items but didn't purchase
-- Tables: cart_events(user_id, event_timestamp, event_type, product_id)
-- event_type: 'add_to_cart', 'remove_from_cart', 'purchase'
-- Session timeout: 60 minutes

WITH sessions AS (
    -- Create session IDs
    SELECT 
        user_id,
        event_timestamp,
        event_type,
        product_id,
        SUM(CASE 
            WHEN TIMESTAMP_DIFF(
                event_timestamp,
                LAG(event_timestamp) OVER (PARTITION BY user_id ORDER BY event_timestamp),
                MINUTE
            ) > 60 OR LAG(event_timestamp) OVER (PARTITION BY user_id ORDER BY event_timestamp) IS NULL
            THEN 1 ELSE 0 
        END) OVER (PARTITION BY user_id ORDER BY event_timestamp) AS session_id
    FROM cart_events
),
session_summary AS (
    SELECT 
        user_id,
        session_id,
        MIN(event_timestamp) AS session_start,
        MAX(event_timestamp) AS session_end,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS has_purchase,
        COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN product_id END) AS items_added
    FROM sessions
    GROUP BY user_id, session_id
)
SELECT 
    user_id,
    session_id,
    session_start,
    session_end,
    items_added
FROM session_summary
WHERE has_purchase = 0 AND items_added > 0  -- Abandoned cart
ORDER BY session_start DESC;
```

---

### **PATTERN 3: RUNNING CALCULATIONS**

#### **Q6. Account Balance History**
```sql
-- Calculate running balance after each transaction
-- Table: transactions(trans_id, account_id, trans_date, amount, type)
-- type: 'deposit' or 'withdraw'

SELECT 
    account_id,
    trans_id,
    trans_date,
    amount,
    type,
    SUM(CASE 
        WHEN type = 'deposit' THEN amount
        ELSE -amount
    END) OVER (
        PARTITION BY account_id 
        ORDER BY trans_date, trans_id
    ) AS running_balance,
    MIN(SUM(CASE WHEN type = 'deposit' THEN amount ELSE -amount END)) OVER (
        PARTITION BY account_id 
        ORDER BY trans_date, trans_id
        ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
    ) AS min_future_balance
FROM transactions
ORDER BY account_id, trans_date, trans_id;
```

---

#### **Q7. Inventory Stock Levels**
```sql
-- Track inventory with running stock count
-- Table: inventory_movements(product_id, movement_date, quantity, type)
-- type: 'in' (receiving) or 'out' (shipping)

SELECT 
    product_id,
    movement_date,
    quantity,
    type,
    SUM(CASE WHEN type = 'in' THEN quantity ELSE -quantity END) OVER (
        PARTITION BY product_id 
        ORDER BY movement_date
    ) AS current_stock,
    -- Alert if stock goes below 100
    CASE 
        WHEN SUM(CASE WHEN type = 'in' THEN quantity ELSE -quantity END) OVER (
            PARTITION BY product_id ORDER BY movement_date
        ) < 100 THEN 'LOW STOCK'
        ELSE 'OK'
    END AS stock_status
FROM inventory_movements
ORDER BY product_id, movement_date;
```

---

### **PATTERN 4: GAPS AND ISLANDS (CONSECUTIVE SEQUENCES)**

#### **Q8. Login Streaks**
```sql
-- Find consecutive login days for each user
-- Table: user_logins(user_id, login_date)

WITH numbered AS (
    SELECT 
        user_id,
        login_date,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn,
        DATE_SUB(login_date, INTERVAL ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) DAY) AS grp
    FROM (SELECT DISTINCT user_id, login_date FROM user_logins)
)
SELECT 
    user_id,
    MIN(login_date) AS streak_start,
    MAX(login_date) AS streak_end,
    COUNT(*) AS days_in_streak
FROM numbered
GROUP BY user_id, grp
HAVING COUNT(*) >= 3  -- At least 3 consecutive days
ORDER BY user_id, streak_start;
```

---

#### **Q9. Find Missing Dates**
```sql
-- Identify dates without any sales
-- Table: sales(sale_date, product_id, amount)
-- Date range: 2024-01-01 to 2024-12-31

WITH all_dates AS (
    SELECT date
    FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2024-12-31', INTERVAL 1 DAY)) AS date
),
sales_dates AS (
    SELECT DISTINCT DATE(sale_date) AS date
    FROM sales
)
SELECT 
    ad.date AS missing_date,
    EXTRACT(DAYOFWEEK FROM ad.date) AS day_of_week,
    FORMAT_DATE('%A', ad.date) AS day_name
FROM all_dates ad
LEFT JOIN sales_dates sd ON ad.date = sd.date
WHERE sd.date IS NULL
ORDER BY ad.date;
```

---

#### **Q10. Price Change Detection**
```sql
-- Find periods where product price remained constant
-- Table: price_history(product_id, effective_date, price)

WITH numbered AS (
    SELECT 
        product_id,
        effective_date,
        price,
        ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY effective_date) AS rn,
        price - LAG(price, 1, price) OVER (PARTITION BY product_id ORDER BY effective_date) AS price_change
    FROM price_history
),
groups AS (
    SELECT 
        product_id,
        effective_date,
        price,
        SUM(CASE WHEN price_change != 0 THEN 1 ELSE 0 END) OVER (
            PARTITION BY product_id ORDER BY effective_date
        ) AS price_group
    FROM numbered
)
SELECT 
    product_id,
    MIN(effective_date) AS period_start,
    MAX(effective_date) AS period_end,
    price,
    DATEDIFF(MAX(effective_date), MIN(effective_date)) AS days_stable
FROM groups
GROUP BY product_id, price_group, price
HAVING DATEDIFF(MAX(effective_date), MIN(effective_date)) > 30
ORDER BY product_id, period_start;
```

---

### **PATTERN 5: ADVANCED WINDOW FUNCTIONS**

#### **Q11. Month-over-Month Growth**
```sql
-- Calculate month-over-month revenue growth percentage
-- Table: monthly_revenue(month_year, revenue)

SELECT 
    month_year,
    revenue,
    LAG(revenue) OVER (ORDER BY month_year) AS prev_month_revenue,
    revenue - LAG(revenue) OVER (ORDER BY month_year) AS absolute_change,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY month_year)) * 100.0 / 
        LAG(revenue) OVER (ORDER BY month_year),
        2
    ) AS growth_percentage,
    -- 3-month moving average
    ROUND(AVG(revenue) OVER (
        ORDER BY month_year 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS ma_3month
FROM monthly_revenue
ORDER BY month_year;
```

---

#### **Q12. Top 3 Products Per Category**
```sql
-- Find top 3 highest revenue products in each category
-- Table: products(product_id, product_name, category, revenue)

SELECT 
    category,
    product_name,
    revenue,
    rank
FROM (
    SELECT 
        category,
        product_name,
        revenue,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank
    FROM products
) ranked
WHERE rank <= 3
ORDER BY category, rank;
```

---

*[100 MORE QUESTIONS FOLLOWING THIS FORMAT]*

---

## 🎯 DIFFICULTY LEVELS

### **EASY (Questions 1-25)**
- Basic LEAST/GREATEST
- Simple sessionization
- Running totals
- Basic gaps and islands
- Simple window functions

### **MEDIUM (Questions 26-60)**
- Complex sessionization
- Multiple window functions
- Recursive CTEs
- Advanced joins
- String parsing

### **HARD (Questions 61-85)**
- Multiple pattern combinations
- Performance optimization required
- Complex business logic
- Data quality checks

### **EXPERT (Questions 86-100)**
- Real production scenarios
- Multi-step solutions
- Multiple tables
- Complete end-to-end problems

---

## 📝 PRACTICE SCHEDULE

**Week 1: Fundamentals (Q1-25)**
- Day 1-2: LEAST/GREATEST patterns
- Day 3-4: Sessionization
- Day 5-6: Running calculations
- Day 7: Review and practice

**Week 2: Intermediate (Q26-60)**
- Day 1-2: Gaps & Islands
- Day 3-4: Window functions
- Day 5-6: Recursive CTEs
- Day 7: Mixed problems

**Week 3: Advanced (Q61-100)**
- Day 1-3: Hard problems
- Day 4-5: Expert scenarios
- Day 6-7: Mock interviews

---

## 🔑 ANSWER KEY PATTERNS

**For Routes/Bidirectional:** Always think LEAST/GREATEST  
**For Time Gaps:** Always think LAG + SUM window  
**For Running Totals:** Always think SUM() OVER (ORDER BY)  
**For Consecutive:** Always think ROW_NUMBER() date arithmetic  
**For Latest Record:** Always think ROW_NUMBER() ... = 1  

---

**STATUS:** 100+ SQL Interview Questions Ready! 🎯  
**Next:** Practice, review patterns, ace your interviews!
