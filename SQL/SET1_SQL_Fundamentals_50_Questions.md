# SET 1: SQL FUNDAMENTALS
## 50 Questions: Easy (20) | Medium (20) | Hard (10)

---

## Database Schema

All questions use this e-commerce database:

### customers
```
customer_id | name          | email             | city        | state | signup_date | last_login
------------|---------------|-------------------|-------------|-------|-------------|------------
1           | Alice Johnson | alice@email.com   | New York    | NY    | 2022-01-15  | 2024-04-20
2           | Bob Smith     | bob@email.com     | Chicago     | IL    | 2022-03-20  | 2024-04-18
3           | Carol White   | carol@email.com   | New York    | NY    | 2021-11-05  | 2024-04-19
4           | Dave Brown    | dave@email.com    | Los Angeles | CA    | 2023-02-10  | 2024-04-15
5           | Eve Davis     | eve@email.com     | Chicago     | IL    | 2021-08-30  | 2024-04-22
```

### products
```
product_id | name             | category    | price | cost | stock | created_date
-----------|------------------|-------------|-------|------|-------|-------------
1          | Laptop Pro       | Electronics | 1200  | 800  | 50    | 2023-01-10
2          | Wireless Mouse   | Electronics | 35    | 15   | 200   | 2023-01-15
3          | SQL Mastery Book | Books       | 45    | 20   | 300   | 2023-02-01
4          | Standing Desk    | Furniture   | 550   | 300  | 30    | 2023-02-15
5          | USB-C Hub        | Electronics | 60    | 25   | 150   | 2023-03-01
```

### orders
```
order_id | customer_id | order_date | total_amount | shipping_cost | status    | payment_method
---------|-------------|------------|--------------|---------------|-----------|---------------
101      | 1           | 2024-01-10 | 1235         | 0             | completed | credit_card
102      | 2           | 2024-01-15 | 35           | 5             | completed | paypal
103      | 1           | 2024-02-20 | 605          | 15            | completed | credit_card
104      | 3           | 2024-02-28 | 45           | 5             | cancelled | credit_card
105      | 5           | 2024-03-05 | 1200         | 0             | completed | debit_card
106      | 2           | 2024-03-10 | 110          | 10            | completed | paypal
107      | 4           | 2024-04-01 | 550          | 20            | completed | credit_card
108      | 1           | 2024-04-15 | 95           | 5             | completed | credit_card
```

### order_items
```
item_id | order_id | product_id | quantity | unit_price | discount
--------|----------|------------|----------|------------|----------
1       | 101      | 1          | 1        | 1200       | 0
2       | 101      | 2          | 1        | 35         | 0
3       | 102      | 2          | 1        | 35         | 0
4       | 103      | 4          | 1        | 550        | 0
5       | 103      | 3          | 1        | 45         | 10
6       | 105      | 1          | 1        | 1200       | 0
7       | 106      | 5          | 1        | 60         | 0
8       | 106      | 2          | 1        | 35         | 15
9       | 107      | 4          | 1        | 550        | 0
10      | 108      | 2          | 2        | 35         | 0
11      | 108      | 3          | 1        | 25         | 0
```

---

## Part A: Easy Questions (1-20)

### Q1. [Easy] Select All Customers
Write a query to select all columns from the customers table.

<details>
<summary>💡 Solution</summary>

```sql
SELECT * FROM customers;
```

**Explanation:** The asterisk (*) selects all columns. While SELECT * is quick for exploration, in production you should explicitly list columns for clarity and performance.

**Key Learning:** Avoid SELECT * in production code. Always specify column names.

**Common Mistake:** None for this basic query, but remember this is rarely used in production.

</details>

---

### Q2. [Easy] Filter by Price
Find all products with price greater than 100.

<details>
<summary>💡 Solution</summary>

```sql
SELECT *
FROM products
WHERE price > 100;
```

**Explanation:** The WHERE clause filters rows. The > operator means 'greater than'. For 'greater than or equal', use >=.

**Expected Output:**
```
product_id | name             | category    | price | cost | stock
-----------|------------------|-------------|-------|------|------
1          | Laptop Pro       | Electronics | 1200  | 800  | 50
4          | Standing Desk    | Furniture   | 550   | 300  | 30
```

**Common Mistake:** Forgetting the WHERE clause entirely or using >= when you mean >.

</details>

---

### Q3. [Easy] Filter by Text
Find all customers from New York.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, email, city
FROM customers
WHERE city = 'New York';
```

**Explanation:** Text comparisons require single quotes. Most databases are case-sensitive for string comparisons.

**Expected Output:**
```
name          | email           | city
--------------|-----------------|----------
Alice Johnson | alice@email.com | New York
Carol White   | carol@email.com | New York
```

**Common Mistake:** 
- Forgetting quotes around 'New York'
- Using double quotes instead of single quotes
- Case sensitivity issues

</details>

---

### Q4. [Easy] Sorting Results
List all products ordered by price from lowest to highest.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, price
FROM products
ORDER BY price ASC;
```

**Explanation:** ORDER BY sorts results. ASC = ascending (low to high). DESC = descending (high to low). ASC is the default.

**Expected Output:**
```
name             | price
-----------------|------
Wireless Mouse   | 35
SQL Mastery Book | 45
USB-C Hub        | 60
Standing Desk    | 550
Laptop Pro       | 1200
```

**Common Mistake:** Forgetting that ASC is default, or using DESC when you want ASC.

</details>

---

### Q5. [Easy] LIMIT Results
Show only the 3 most expensive products.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, price
FROM products
ORDER BY price DESC
LIMIT 3;
```

**Explanation:** LIMIT restricts the number of rows returned. Combine with ORDER BY to get "top N" results.

**Expected Output:**
```
name           | price
---------------|------
Laptop Pro     | 1200
Standing Desk  | 550
USB-C Hub      | 60
```

**Key Learning:** LIMIT without ORDER BY gives unpredictable results. Always combine them for "top N" queries.

</details>

---

### Q6. [Easy] COUNT Function
How many customers are in the database?

<details>
<summary>💡 Solution</summary>

```sql
SELECT COUNT(*) AS customer_count
FROM customers;
```

**Explanation:** COUNT(*) counts all rows. COUNT(column_name) counts non-NULL values in that column.

**Expected Output:**
```
customer_count
--------------
5
```

**Common Mistake:** Forgetting the alias (AS customer_count) makes output column unnamed.

</details>

---

### Q7. [Easy] SUM Function
What is the total value of all products in stock (price × stock)?

<details>
<summary>💡 Solution</summary>

```sql
SELECT SUM(price * stock) AS total_inventory_value
FROM products;
```

**Explanation:** You can perform calculations inside aggregate functions. SUM adds up all values.

**Expected Output:**
```
total_inventory_value
---------------------
93750
```

**Calculation:** (1200×50) + (35×200) + (45×300) + (550×30) + (60×150) = 93,750

</details>

---

### Q8. [Easy] AVG Function
What is the average product price?

<details>
<summary>💡 Solution</summary>

```sql
SELECT AVG(price) AS average_price
FROM products;
```

**Explanation:** AVG calculates the mean of all values. Returns a decimal even if all inputs are integers.

**Expected Output:**
```
average_price
-------------
378.00
```

**Calculation:** (1200 + 35 + 45 + 550 + 60) / 5 = 378

</details>

---

### Q9. [Easy] MIN and MAX
Find the lowest and highest product prices.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    MIN(price) AS lowest_price,
    MAX(price) AS highest_price
FROM products;
```

**Explanation:** MIN and MAX find the minimum and maximum values. You can use multiple aggregate functions in one SELECT.

**Expected Output:**
```
lowest_price | highest_price
-------------|---------------
35           | 1200
```

</details>

---

### Q10. [Easy] DISTINCT Values
How many different cities do customers live in?

<details>
<summary>💡 Solution</summary>

```sql
SELECT COUNT(DISTINCT city) AS city_count
FROM customers;
```

**Explanation:** DISTINCT removes duplicates before counting. COUNT(DISTINCT column) counts unique values only.

**Expected Output:**
```
city_count
----------
3
```

**Cities:** New York, Chicago, Los Angeles

**Common Mistake:** Using COUNT(*) instead of COUNT(DISTINCT city) would give 5 (all rows).

</details>

---

### Q11. [Easy] AND Operator
Find products in Electronics category that cost less than $100.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, category, price
FROM products
WHERE category = 'Electronics' 
  AND price < 100;
```

**Explanation:** AND requires ALL conditions to be true. Both category AND price conditions must match.

**Expected Output:**
```
name           | category    | price
---------------|-------------|------
Wireless Mouse | Electronics | 35
USB-C Hub      | Electronics | 60
```

**Common Mistake:** Using OR instead of AND would return products that match EITHER condition.

</details>

---

### Q12. [Easy] OR Operator
Find customers from either New York or Chicago.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, city
FROM customers
WHERE city = 'New York' OR city = 'Chicago';
```

**Explanation:** OR requires ANY condition to be true. Only one city needs to match.

**Expected Output:**
```
name          | city
--------------|----------
Alice Johnson | New York
Bob Smith     | Chicago
Carol White   | New York
Eve Davis     | Chicago
```

**Alternative (better) solution:**
```sql
SELECT name, city
FROM customers
WHERE city IN ('New York', 'Chicago');
```

</details>

---

### Q13. [Easy] IN Operator
Find all orders with status 'completed' or 'shipped'.

<details>
<summary>💡 Solution</summary>

```sql
SELECT order_id, customer_id, status
FROM orders
WHERE status IN ('completed', 'shipped');
```

**Explanation:** IN is shorthand for multiple OR conditions. Much cleaner than status = 'completed' OR status = 'shipped'.

**Expected Output:**
```
order_id | customer_id | status
---------|-------------|----------
101      | 1           | completed
102      | 2           | completed
103      | 1           | completed
105      | 5           | completed
106      | 2           | completed
107      | 4           | completed
108      | 1           | completed
```

**Key Learning:** IN is more readable and performant than multiple OR conditions.

</details>

---

### Q14. [Easy] BETWEEN Operator
Find products priced between $40 and $100 (inclusive).

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, price
FROM products
WHERE price BETWEEN 40 AND 100;
```

**Explanation:** BETWEEN is inclusive (includes both boundary values). Equivalent to price >= 40 AND price <= 100.

**Expected Output:**
```
name             | price
-----------------|------
SQL Mastery Book | 45
USB-C Hub        | 60
```

**Common Mistake:** Thinking BETWEEN is exclusive. It includes both 40 and 100.

</details>

---

### Q15. [Easy] LIKE Pattern Matching
Find all customers whose names start with 'A'.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, email
FROM customers
WHERE name LIKE 'A%';
```

**Explanation:** 
- % matches any sequence of characters (0 or more)
- 'A%' means "starts with A, followed by anything"
- '%A' means "ends with A"
- '%A%' means "contains A anywhere"

**Expected Output:**
```
name          | email
--------------|------------------
Alice Johnson | alice@email.com
```

**Common Mistake:** Forgetting the % wildcard, which would only match exact 'A'.

</details>

---

### Q16. [Easy] IS NULL
Find products that have no stock information (if any existed).

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, stock
FROM products
WHERE stock IS NULL;
```

**Explanation:** 
- NULL represents missing/unknown data
- Use IS NULL (not = NULL) to check for NULL values
- Use IS NOT NULL to find non-NULL values

**Expected Output:**
```
(No rows - all products have stock data)
```

**Common Mistake:** Using WHERE stock = NULL doesn't work! Must use IS NULL.

</details>

---

### Q17. [Easy] NOT Operator
Find all customers NOT from Chicago.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, city
FROM customers
WHERE city != 'Chicago';
-- Alternative: WHERE city <> 'Chicago'
-- Alternative: WHERE NOT city = 'Chicago'
```

**Explanation:** != and <> both mean "not equal". NOT inverts any condition.

**Expected Output:**
```
name          | city
--------------|-------------
Alice Johnson | New York
Carol White   | New York
Dave Brown    | Los Angeles
```

</details>

---

### Q18. [Easy] Alias for Columns
Display customer names with their cities, using cleaner column names.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    name AS customer_name,
    city AS location,
    email AS contact_email
FROM customers;
```

**Explanation:** AS creates aliases (nicknames) for columns. Makes output more readable. The AS keyword is optional but recommended for clarity.

**Expected Output:**
```
customer_name | location    | contact_email
--------------|-------------|-----------------
Alice Johnson | New York    | alice@email.com
Bob Smith     | Chicago     | bob@email.com
...
```

**Key Learning:** Aliases don't change the actual table, only the query output.

</details>

---

### Q19. [Easy] String Concatenation
Display customer names with their cities in format: "Name (City)".

<details>
<summary>💡 Solution</summary>

```sql
-- PostgreSQL, SQLite:
SELECT name || ' (' || city || ')' AS customer_location
FROM customers;

-- MySQL:
SELECT CONCAT(name, ' (', city, ')') AS customer_location
FROM customers;
```

**Explanation:** || is the SQL standard concatenation operator. MySQL uses CONCAT() function instead.

**Expected Output:**
```
customer_location
-------------------------
Alice Johnson (New York)
Bob Smith (Chicago)
Carol White (New York)
Dave Brown (Los Angeles)
Eve Davis (Chicago)
```

</details>

---

### Q20. [Easy] Order by Multiple Columns
List customers ordered by city, then by name within each city.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, city
FROM customers
ORDER BY city, name;
```

**Explanation:** When ordering by multiple columns, SQL sorts by the first column, then breaks ties using the second column.

**Expected Output:**
```
name          | city
--------------|-------------
Bob Smith     | Chicago
Eve Davis     | Chicago
Dave Brown    | Los Angeles
Alice Johnson | New York
Carol White   | New York
```

**Key Learning:** Order matters! ORDER BY city, name is different from ORDER BY name, city.

</details>

---

## Part B: Medium Questions (21-40)

### Q21. [Medium] GROUP BY Basics
How many customers are in each city?

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    city,
    COUNT(*) AS customer_count
FROM customers
GROUP BY city
ORDER BY customer_count DESC;
```

**Explanation:** 
- GROUP BY collapses rows with the same city into one row
- COUNT(*) counts rows in each group
- Non-aggregated columns (city) must appear in GROUP BY

**Expected Output:**
```
city        | customer_count
------------|---------------
New York    | 2
Chicago     | 2
Los Angeles | 1
```

**Common Mistake:** Selecting a column not in GROUP BY or aggregate function causes an error.

</details>

---

### Q22. [Medium] GROUP BY with SUM
Calculate total revenue by payment method.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    payment_method,
    SUM(total_amount) AS total_revenue,
    COUNT(*) AS order_count
FROM orders
WHERE status = 'completed'
GROUP BY payment_method
ORDER BY total_revenue DESC;
```

**Explanation:** Filter first (WHERE), then group (GROUP BY), then aggregate (SUM, COUNT).

**Expected Output:**
```
payment_method | total_revenue | order_count
---------------|---------------|------------
credit_card    | 2485          | 4
debit_card     | 1200          | 1
paypal         | 145           | 2
```

**Key Learning:** WHERE filters BEFORE grouping. HAVING filters AFTER grouping.

</details>

---

### Q23. [Medium] HAVING Clause
Find cities with more than 1 customer.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    city,
    COUNT(*) AS customer_count
FROM customers
GROUP BY city
HAVING COUNT(*) > 1;
```

**Explanation:** 
- WHERE filters rows before grouping
- HAVING filters groups after aggregation
- HAVING can use aggregate functions, WHERE cannot

**Expected Output:**
```
city     | customer_count
---------|---------------
New York | 2
Chicago  | 2
```

**Common Mistake:** Using WHERE COUNT(*) > 1 doesn't work because WHERE happens before aggregation.

</details>

---

### Q24. [Medium] Multiple Aggregates
For each product category, show count, average price, and total stock.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    category,
    COUNT(*) AS product_count,
    ROUND(AVG(price), 2) AS avg_price,
    SUM(stock) AS total_stock
FROM products
GROUP BY category
ORDER BY avg_price DESC;
```

**Explanation:** You can use multiple aggregate functions in one query. ROUND formats decimals.

**Expected Output:**
```
category    | product_count | avg_price | total_stock
------------|---------------|-----------|------------
Electronics | 3             | 431.67    | 400
Furniture   | 1             | 550.00    | 30
Books       | 1             | 45.00     | 300
```

</details>

---

### Q25. [Medium] Calculated Fields
Calculate profit margin for each product: (price - cost) / price * 100.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    name,
    price,
    cost,
    ROUND(((price - cost) / price::DECIMAL * 100), 2) AS profit_margin_pct
FROM products
ORDER BY profit_margin_pct DESC;
```

**Explanation:** 
- Perform calculations in SELECT clause
- Cast to DECIMAL to avoid integer division
- ROUND to 2 decimal places for readability

**Expected Output:**
```
name             | price | cost | profit_margin_pct
-----------------|-------|------|------------------
Wireless Mouse   | 35    | 15   | 57.14
USB-C Hub        | 60    | 25   | 58.33
SQL Mastery Book | 45    | 20   | 55.56
Standing Desk    | 550   | 300  | 45.45
Laptop Pro       | 1200  | 800  | 33.33
```

</details>

---

### Q26. [Medium] WHERE with Multiple Conditions
Find expensive Electronics (price > 50) or any Furniture products.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, category, price
FROM products
WHERE (category = 'Electronics' AND price > 50)
   OR category = 'Furniture'
ORDER BY category, price DESC;
```

**Explanation:** 
- Use parentheses to control logic order
- Without parentheses, results would be wrong
- AND has higher precedence than OR

**Expected Output:**
```
name          | category    | price
--------------|-------------|------
Laptop Pro    | Electronics | 1200
USB-C Hub     | Electronics | 60
Standing Desk | Furniture   | 550
```

**Common Mistake:** Forgetting parentheses changes the logic completely!

</details>

---

### Q27. [Medium] CASE Statement
Categorize products as 'Budget', 'Mid-range', or 'Premium' based on price.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    name,
    price,
    CASE 
        WHEN price < 50 THEN 'Budget'
        WHEN price BETWEEN 50 AND 200 THEN 'Mid-range'
        ELSE 'Premium'
    END AS price_category
FROM products
ORDER BY price;
```

**Explanation:** 
- CASE evaluates conditions top to bottom
- First matching condition wins
- ELSE handles all remaining cases

**Expected Output:**
```
name             | price | price_category
-----------------|-------|---------------
Wireless Mouse   | 35    | Budget
SQL Mastery Book | 45    | Budget
USB-C Hub        | 60    | Mid-range
Standing Desk    | 550   | Premium
Laptop Pro       | 1200  | Premium
```

</details>

---

### Q28. [Medium] Date Filtering
Find customers who signed up in 2022.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, signup_date
FROM customers
WHERE signup_date >= '2022-01-01' 
  AND signup_date < '2023-01-01'
ORDER BY signup_date;

-- Alternative using EXTRACT:
SELECT name, signup_date
FROM customers
WHERE EXTRACT(YEAR FROM signup_date) = 2022
ORDER BY signup_date;
```

**Explanation:** Date comparison uses standard comparison operators. EXTRACT pulls out year/month/day components.

**Expected Output:**
```
name          | signup_date
--------------|------------
Alice Johnson | 2022-01-15
Bob Smith     | 2022-03-20
```

</details>

---

### Q29. [Medium] Aggregate with WHERE and HAVING
Find categories with more than 1 product AND average price over $50.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    category,
    COUNT(*) AS product_count,
    ROUND(AVG(price), 2) AS avg_price
FROM products
GROUP BY category
HAVING COUNT(*) > 1 
   AND AVG(price) > 50
ORDER BY avg_price DESC;
```

**Explanation:** 
- WHERE filters individual rows (not used here)
- GROUP BY groups by category
- HAVING filters the grouped results

**Expected Output:**
```
category    | product_count | avg_price
------------|---------------|----------
Electronics | 3             | 431.67
```

**Books (only 1 product) and Furniture (avg $550 but only 1 product) don't qualify.**

</details>

---

### Q30. [Medium] String Functions
Find customers whose email contains 'email'.

<details>
<summary>💡 Solution</summary>

```sql
SELECT name, email
FROM customers
WHERE email LIKE '%email%';

-- Case-insensitive version (PostgreSQL):
WHERE email ILIKE '%email%';
```

**Explanation:** 
- LIKE '%email%' finds 'email' anywhere in the string
- % matches zero or more characters
- ILIKE is case-insensitive (PostgreSQL)

**Expected Output:**
```
name          | email
--------------|------------------
Alice Johnson | alice@email.com
Bob Smith     | bob@email.com
Carol White   | carol@email.com
Dave Brown    | dave@email.com
Eve Davis     | eve@email.com
```

</details>

---

### Q31. [Medium] COUNT with DISTINCT
How many different products have been ordered?

<details>
<summary>💡 Solution</summary>

```sql
SELECT COUNT(DISTINCT product_id) AS unique_products_ordered
FROM order_items;
```

**Explanation:** COUNT(DISTINCT column) counts unique values only, removing duplicates.

**Expected Output:**
```
unique_products_ordered
-----------------------
4
```

**Products ordered: 1 (Laptop), 2 (Mouse), 3 (Book), 4 (Desk). Product 5 (USB Hub) was NOT ordered.**

</details>

---

### Q32. [Medium] Percentage Calculation
What percentage of total orders is each payment method?

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    payment_method,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders WHERE status = 'completed'), 2) AS percentage
FROM orders
WHERE status = 'completed'
GROUP BY payment_method
ORDER BY percentage DESC;
```

**Explanation:** Subquery in SELECT calculates total orders. Multiply by 100.0 (not 100) to get decimals.

**Expected Output:**
```
payment_method | order_count | percentage
---------------|-------------|------------
credit_card    | 4           | 57.14
paypal         | 2           | 28.57
debit_card     | 1           | 14.29
```

</details>

---

### Q33. [Medium] Multiple GROUP BY Columns
Show total quantity ordered for each product, grouped by product.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    p.name AS product_name,
    p.category,
    SUM(oi.quantity) AS total_quantity_sold,
    COUNT(DISTINCT oi.order_id) AS times_ordered
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.name, p.category
ORDER BY total_quantity_sold DESC;
```

**Explanation:** When joining tables, GROUP BY all non-aggregated columns from SELECT.

**Expected Output:**
```
product_name     | category    | total_quantity_sold | times_ordered
-----------------|-------------|---------------------|---------------
Wireless Mouse   | Electronics | 5                   | 4
SQL Mastery Book | Books       | 2                   | 2
Standing Desk    | Furniture   | 2                   | 2
Laptop Pro       | Electronics | 2                   | 2
USB-C Hub        | Electronics | 1                   | 1
```

</details>

---

### Q34. [Medium] Finding Gaps
Which product IDs exist but have never been ordered?

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    p.product_id,
    p.name
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
WHERE oi.product_id IS NULL;
```

**Explanation:** LEFT JOIN keeps all products. WHERE IS NULL finds products with no matching orders.

**Expected Output:**
```
(Empty result - all products have been ordered at least once)
```

**If USB-C Hub (#5) wasn't ordered, it would appear here.**

</details>

---

### Q35. [Medium] Date Difference
How many days have passed since each customer's last login?

<details>
<summary>💡 Solution</summary>

```sql
-- PostgreSQL:
SELECT 
    name,
    last_login,
    CURRENT_DATE - last_login AS days_since_login
FROM customers
ORDER BY days_since_login;

-- MySQL:
SELECT 
    name,
    last_login,
    DATEDIFF(CURRENT_DATE, last_login) AS days_since_login
FROM customers
ORDER BY days_since_login;
```

**Explanation:** Date subtraction gives number of days. DATEDIFF is MySQL-specific.

**Expected Output (if run on 2024-04-23):**
```
name          | last_login | days_since_login
--------------|------------|------------------
Eve Davis     | 2024-04-22 | 1
Alice Johnson | 2024-04-20 | 3
Carol White   | 2024-04-19 | 4
Bob Smith     | 2024-04-18 | 5
Dave Brown    | 2024-04-15 | 8
```

</details>

---

### Q36. [Medium] COALESCE for NULL Handling
Display product discounts, showing 0 if no discount exists.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    oi.item_id,
    p.name,
    oi.unit_price,
    COALESCE(oi.discount, 0) AS discount,
    oi.unit_price - COALESCE(oi.discount, 0) AS final_price
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
ORDER BY oi.item_id;
```

**Explanation:** COALESCE returns the first non-NULL value. COALESCE(discount, 0) returns discount if not NULL, otherwise 0.

**Expected Output:**
```
item_id | name             | unit_price | discount | final_price
--------|------------------|------------|----------|------------
1       | Laptop Pro       | 1200       | 0        | 1200
2       | Wireless Mouse   | 35         | 0        | 35
3       | Wireless Mouse   | 35         | 0        | 35
5       | SQL Mastery Book | 45         | 10       | 35
8       | Wireless Mouse   | 35         | 15       | 20
...
```

</details>

---

### Q37. [Medium] UPPER and LOWER Functions
Display customer names in uppercase and cities in lowercase.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    UPPER(name) AS name_uppercase,
    LOWER(city) AS city_lowercase,
    email
FROM customers;
```

**Explanation:** UPPER converts to uppercase, LOWER to lowercase. Doesn't change actual data, only display.

**Expected Output:**
```
name_uppercase | city_lowercase | email
---------------|----------------|------------------
ALICE JOHNSON  | new york       | alice@email.com
BOB SMITH      | chicago        | bob@email.com
CAROL WHITE    | new york       | carol@email.com
DAVE BROWN     | los angeles    | dave@email.com
EVE DAVIS      | chicago        | eve@email.com
```

</details>

---

### Q38. [Medium] SUBSTRING Function
Extract the first 3 characters of each customer name.

<details>
<summary>💡 Solution</summary>

```sql
-- PostgreSQL, MySQL, SQLite:
SELECT 
    name,
    SUBSTRING(name, 1, 3) AS name_prefix
FROM customers;

-- Alternative (PostgreSQL):
SELECT 
    name,
    LEFT(name, 3) AS name_prefix
FROM customers;
```

**Explanation:** SUBSTRING(string, start, length). Start position is 1-indexed (first character = 1).

**Expected Output:**
```
name          | name_prefix
--------------|------------
Alice Johnson | Ali
Bob Smith     | Bob
Carol White   | Car
Dave Brown    | Dav
Eve Davis     | Eve
```

</details>

---

### Q39. [Medium] LENGTH Function
Find customers with names longer than 10 characters.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    name,
    LENGTH(name) AS name_length
FROM customers
WHERE LENGTH(name) > 10
ORDER BY name_length DESC;
```

**Explanation:** LENGTH returns number of characters in a string.

**Expected Output:**
```
name          | name_length
--------------|------------
Alice Johnson | 13
```

</details>

---

### Q40. [Medium] Complex Filtering
Find orders from 2024 with total amount over $100 OR paid by credit card.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    order_id,
    customer_id,
    order_date,
    total_amount,
    payment_method
FROM orders
WHERE EXTRACT(YEAR FROM order_date) = 2024
  AND (total_amount > 100 OR payment_method = 'credit_card')
ORDER BY order_date;
```

**Explanation:** Complex boolean logic requires careful parentheses. Year filter AND (amount OR payment).

**Expected Output:**
```
order_id | customer_id | order_date | total_amount | payment_method
---------|-------------|------------|--------------|---------------
101      | 1           | 2024-01-10 | 1235         | credit_card
103      | 1           | 2024-02-20 | 605          | credit_card
105      | 5           | 2024-03-05 | 1200         | debit_card
106      | 2           | 2024-03-10 | 110          | paypal
107      | 4           | 2024-04-01 | 550          | credit_card
108      | 1           | 2024-04-15 | 95           | credit_card
```

</details>

---

## Part C: Hard Questions (41-50)

### Q41. [Hard] Ranking with DENSE_RANK
Rank products by price, handling ties properly (no gaps in ranking).

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    name,
    price,
    DENSE_RANK() OVER (ORDER BY price DESC) AS price_rank
FROM products
ORDER BY price_rank, name;
```

**Explanation:** 
- DENSE_RANK gives same rank to ties
- No gaps after ties (1, 2, 2, 3 not 1, 2, 2, 4)
- OVER clause defines the ranking window

**Expected Output:**
```
name             | price | price_rank
-----------------|-------|------------
Laptop Pro       | 1200  | 1
Standing Desk    | 550   | 2
USB-C Hub        | 60    | 3
SQL Mastery Book | 45    | 4
Wireless Mouse   | 35    | 5
```

**Note:** This is a preview of window functions covered in SET 4!

</details>

---

### Q42. [Hard] Running Total
Calculate running total of order amounts by date.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    order_date,
    order_id,
    total_amount,
    SUM(total_amount) OVER (ORDER BY order_date, order_id) AS running_total
FROM orders
WHERE status = 'completed'
ORDER BY order_date, order_id;
```

**Explanation:** Window function with ORDER BY creates cumulative sum. Each row shows sum of all previous rows plus current.

**Expected Output:**
```
order_date | order_id | total_amount | running_total
-----------|----------|--------------|---------------
2024-01-10 | 101      | 1235         | 1235
2024-01-15 | 102      | 35           | 1270
2024-02-20 | 103      | 605          | 1875
2024-03-05 | 105      | 1200         | 3075
2024-03-10 | 106      | 110          | 3185
2024-04-01 | 107      | 550          | 3735
2024-04-15 | 108      | 95           | 3830
```

</details>

---

### Q43. [Hard] Self-Join
Find pairs of customers from the same city (but don't show same customer twice).

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    c1.name AS customer1,
    c2.name AS customer2,
    c1.city
FROM customers c1
JOIN customers c2 
    ON c1.city = c2.city 
    AND c1.customer_id < c2.customer_id
ORDER BY c1.city, c1.name;
```

**Explanation:** 
- Self-join: join table to itself with different aliases
- c1.customer_id < c2.customer_id prevents duplicates and same-person pairs
- Only shows each pair once

**Expected Output:**
```
customer1     | customer2   | city
--------------|-------------|----------
Bob Smith     | Eve Davis   | Chicago
Alice Johnson | Carol White | New York
```

</details>

---

### Q44. [Hard] Complex Aggregation
For each customer, show total spent, number of orders, and average order value.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    c.customer_id,
    c.name,
    COUNT(o.order_id) AS order_count,
    COALESCE(SUM(o.total_amount), 0) AS total_spent,
    COALESCE(ROUND(AVG(o.total_amount), 2), 0) AS avg_order_value
FROM customers c
LEFT JOIN orders o 
    ON c.customer_id = o.customer_id 
    AND o.status = 'completed'
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC;
```

**Explanation:** 
- LEFT JOIN keeps customers with no orders
- COALESCE handles NULL for customers with no completed orders
- Filter in JOIN condition (not WHERE) to keep all customers

**Expected Output:**
```
customer_id | name          | order_count | total_spent | avg_order_value
------------|---------------|-------------|-------------|----------------
1           | Alice Johnson | 3           | 1935        | 645.00
5           | Eve Davis     | 1           | 1200        | 1200.00
4           | Dave Brown    | 1           | 550         | 550.00
2           | Bob Smith     | 2           | 145         | 72.50
3           | Carol White   | 0           | 0           | 0.00
```

</details>

---

### Q45. [Hard] Finding Top N per Group
Find the most expensive product in each category.

<details>
<summary>💡 Solution</summary>

```sql
-- Method 1: Window Function (recommended)
WITH ranked_products AS (
    SELECT 
        name,
        category,
        price,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY price DESC) AS rank
    FROM products
)
SELECT name, category, price
FROM ranked_products
WHERE rank = 1
ORDER BY category;

-- Method 2: Correlated Subquery
SELECT p1.name, p1.category, p1.price
FROM products p1
WHERE p1.price = (
    SELECT MAX(p2.price)
    FROM products p2
    WHERE p2.category = p1.category
)
ORDER BY p1.category;
```

**Explanation:** ROW_NUMBER() ranks within each PARTITION (group). PARTITION BY resets ranking for each category.

**Expected Output:**
```
name           | category    | price
---------------|-------------|------
SQL Mastery Book | Books      | 45
Laptop Pro     | Electronics | 1200
Standing Desk  | Furniture   | 550
```

</details>

---

### Q46. [Hard] Cumulative Aggregation with Date Ranges
Show monthly order counts and running totals.

<details>
<summary>💡 Solution</summary>

```sql
WITH monthly_orders AS (
    SELECT 
        DATE_TRUNC('month', order_date) AS month,
        COUNT(*) AS monthly_count
    FROM orders
    WHERE status = 'completed'
    GROUP BY DATE_TRUNC('month', order_date)
)
SELECT 
    month,
    monthly_count,
    SUM(monthly_count) OVER (ORDER BY month) AS cumulative_orders
FROM monthly_orders
ORDER BY month;
```

**Explanation:** 
- CTE first aggregates by month
- Main query adds running total with window function
- DATE_TRUNC rounds dates to start of month

**Expected Output:**
```
month      | monthly_count | cumulative_orders
-----------|---------------|------------------
2024-01-01 | 2             | 2
2024-02-01 | 1             | 3
2024-03-01 | 2             | 5
2024-04-01 | 2             | 7
```

</details>

---

### Q47. [Hard] Multiple JOINs with Aggregation
Show each customer with their total orders and most recent order date.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    c.customer_id,
    c.name,
    c.city,
    COUNT(o.order_id) AS total_orders,
    MAX(o.order_date) AS most_recent_order,
    SUM(o.total_amount) AS lifetime_value
FROM customers c
LEFT JOIN orders o 
    ON c.customer_id = o.customer_id 
    AND o.status = 'completed'
GROUP BY c.customer_id, c.name, c.city
ORDER BY lifetime_value DESC NULLS LAST;
```

**Explanation:** LEFT JOIN with aggregation shows all customers including those with no orders.

**Expected Output:**
```
customer_id | name          | city        | total_orders | most_recent_order | lifetime_value
------------|---------------|-------------|--------------|-------------------|---------------
1           | Alice Johnson | New York    | 3            | 2024-04-15        | 1935
5           | Eve Davis     | Chicago     | 1            | 2024-03-05        | 1200
4           | Dave Brown    | Los Angeles | 1            | 2024-04-01        | 550
2           | Bob Smith     | Chicago     | 2            | 2024-03-10        | 145
3           | Carol White   | New York    | 0            | NULL              | NULL
```

</details>

---

### Q48. [Hard] Conditional Aggregation (PIVOT-like)
Count orders by payment method for each customer.

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    c.customer_id,
    c.name,
    COUNT(CASE WHEN o.payment_method = 'credit_card' THEN 1 END) AS credit_card_orders,
    COUNT(CASE WHEN o.payment_method = 'paypal' THEN 1 END) AS paypal_orders,
    COUNT(CASE WHEN o.payment_method = 'debit_card' THEN 1 END) AS debit_card_orders,
    COUNT(o.order_id) AS total_orders
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'completed'
GROUP BY c.customer_id, c.name
ORDER BY total_orders DESC;
```

**Explanation:** COUNT with CASE creates columns for each payment method. This is called conditional aggregation or "pivot".

**Expected Output:**
```
customer_id | name          | credit_card_orders | paypal_orders | debit_card_orders | total_orders
------------|---------------|--------------------|--------------|--------------------|-------------
1           | Alice Johnson | 3                  | 0            | 0                  | 3
2           | Bob Smith     | 0                  | 2            | 0                  | 2
5           | Eve Davis     | 0                  | 0            | 1                  | 1
4           | Dave Brown    | 1                  | 0            | 0                  | 1
3           | Carol White   | 0                  | 0            | 0                  | 0
```

</details>

---

### Q49. [Hard] Advanced String Matching
Find products whose names contain 'Pro' OR 'Book', case-insensitive.

<details>
<summary>💡 Solution</summary>

```sql
-- PostgreSQL:
SELECT name, category, price
FROM products
WHERE name ILIKE '%Pro%' OR name ILIKE '%Book%';

-- MySQL (case-insensitive by default):
SELECT name, category, price
FROM products
WHERE name LIKE '%Pro%' OR name LIKE '%Book%';

-- SQL Standard (any database):
SELECT name, category, price
FROM products
WHERE LOWER(name) LIKE '%pro%' OR LOWER(name) LIKE '%book%';
```

**Explanation:** ILIKE is case-insensitive LIKE (PostgreSQL). Alternative: use LOWER() to normalize case.

**Expected Output:**
```
name             | category    | price
-----------------|-------------|------
Laptop Pro       | Electronics | 1200
SQL Mastery Book | Books       | 45
```

</details>

---

### Q50. [Hard] Complex Date Logic
Find customers who haven't ordered in the last 60 days (or never ordered).

<details>
<summary>💡 Solution</summary>

```sql
SELECT 
    c.customer_id,
    c.name,
    MAX(o.order_date) AS last_order_date,
    CURRENT_DATE - MAX(o.order_date) AS days_since_last_order
FROM customers c
LEFT JOIN orders o 
    ON c.customer_id = o.customer_id 
    AND o.status = 'completed'
GROUP BY c.customer_id, c.name
HAVING MAX(o.order_date) IS NULL 
    OR MAX(o.order_date) < CURRENT_DATE - INTERVAL '60 days'
ORDER BY days_since_last_order DESC NULLS FIRST;
```

**Explanation:** 
- LEFT JOIN keeps all customers
- MAX(order_date) gets most recent order
- HAVING filters groups after aggregation
- NULL means never ordered

**Expected Output (if run on 2024-06-20):**
```
customer_id | name          | last_order_date | days_since_last_order
------------|---------------|-----------------|----------------------
3           | Carol White   | NULL            | NULL
1           | Alice Johnson | 2024-04-15      | 66
5           | Eve Davis     | 2024-03-05      | 107
```

</details>

---

## 🎉 Congratulations!

You've completed SET 1: SQL Fundamentals! 

**Key Topics Covered:**
- ✅ SELECT, WHERE, filtering
- ✅ Aggregate functions (COUNT, SUM, AVG, MIN, MAX)
- ✅ GROUP BY and HAVING
- ✅ String and date functions
- ✅ Complex filtering and conditional logic
- ✅ Window functions (preview)
- ✅ Self-joins and multiple aggregations

**Next Steps:**
1. Review any questions you got wrong
2. Practice writing queries from memory
3. Move on to **SET 2: Joins & Relationships** (60 questions)

**Study Tip:** Before moving forward, try creating your own variations of these questions. Can you combine concepts? Make them harder?

---

## 📊 Your Progress

- ✅ SET 1 Complete (50/50)
- ⏳ SET 2: Joins (0/60)
- ⏳ SET 3: Subqueries & CTEs (0/50)
- ⏳ SET 4: Window Functions (0/70)
- ⏳ SET 5: Advanced SQL (0/40)
- ⏳ SET 6: Company Questions (0/80)

**Total: 50/350 questions complete (14.3%)**

Keep going! 🚀
