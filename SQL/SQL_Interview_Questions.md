# SQL Interview Questions & Answers - Comprehensive Guide

> **Last Updated:** 2024  
> **Total Questions:** 100+  
> **Difficulty Levels:** Basic → Intermediate → Advanced → Expert

---

## Table of Contents

1. [Basic SELECT & Filtering](#1-basic-select--filtering)
2. [Aggregate Functions & GROUP BY](#2-aggregate-functions--group-by)
3. [JOIN Operations](#3-join-operations)
4. [Subqueries & Nested Queries](#4-subqueries--nested-queries)
5. [Window Functions](#5-window-functions)
6. [String Functions](#6-string-functions)
7. [Date & Time Functions](#7-date--time-functions)
8. [CASE Statements & Conditional Logic](#8-case-statements--conditional-logic)
9. [Common Table Expressions (CTEs)](#9-common-table-expressions-ctes)
10. [Set Operations](#10-set-operations)
11. [Complex Scenarios](#11-complex-scenarios)
12. [Data Transformation](#12-data-transformation)
13. [Performance Optimization](#13-performance-optimization)
14. [Transaction Control](#14-transaction-control)
15. [Advanced Topics](#15-advanced-topics)

---

## 1. Basic SELECT & Filtering

### Q1: Retrieve all columns from a table

**Question:** Write a query to select all employees from the 'employees' table.

**Answer:**
```sql
SELECT * FROM employees;
```

**Time Complexity:** O(n)

---

### Q2: Select specific columns with WHERE clause

**Question:** Retrieve employee names and salaries where salary is greater than 50000.

**Answer:**
```sql
SELECT 
    name, 
    salary
FROM employees
WHERE salary > 50000;
```

---

### Q3: Using DISTINCT to remove duplicates

**Question:** Get all unique department names from the employees table.

**Answer:**
```sql
SELECT DISTINCT department
FROM employees;
```

---

### Q4: Multiple conditions with AND/OR

**Question:** Find employees in IT department with salary > 60000.

**Answer:**
```sql
SELECT 
    name, 
    department, 
    salary
FROM employees
WHERE department = 'IT' 
    AND salary > 60000;
```

---

### Q5: IN operator for multiple values

**Question:** Retrieve employees from departments 'HR', 'IT', and 'Finance'.

**Answer:**
```sql
SELECT 
    name, 
    department
FROM employees
WHERE department IN ('HR', 'IT', 'Finance');
```

---

### Q6: BETWEEN operator for range queries

**Question:** Find employees with age between 25 and 35.

**Answer:**
```sql
SELECT 
    name, 
    age
FROM employees
WHERE age BETWEEN 25 AND 35;
```

---

### Q7: LIKE operator for pattern matching

**Question:** Find all employees whose names start with 'A'.

**Answer:**
```sql
SELECT 
    name
FROM employees
WHERE name LIKE 'A%';

-- Other LIKE patterns:
-- 'A%' - Starts with A
-- '%A' - Ends with A
-- '%A%' - Contains A
-- 'A_' - A followed by exactly one character
-- 'A__' - A followed by exactly two characters
```

---

### Q8: NULL value handling

**Question:** Find employees with no manager assigned.

**Answer:**
```sql
SELECT 
    name, 
    manager_id
FROM employees
WHERE manager_id IS NULL;

-- NOT NULL check
SELECT name 
FROM employees 
WHERE manager_id IS NOT NULL;
```

---

### Q9: ORDER BY for sorting

**Question:** List all employees sorted by salary in descending order.

**Answer:**
```sql
SELECT 
    name, 
    salary
FROM employees
ORDER BY salary DESC;

-- Multiple column sorting
SELECT name, department, salary
FROM employees
ORDER BY department ASC, salary DESC;
```

---

### Q10: LIMIT/TOP for result pagination

**Question:** Get top 5 highest paid employees.

**Answer:**
```sql
-- MySQL, PostgreSQL
SELECT 
    name, 
    salary
FROM employees
ORDER BY salary DESC
LIMIT 5;

-- SQL Server
SELECT TOP 5 
    name, 
    salary
FROM employees
ORDER BY salary DESC;

-- Oracle
SELECT 
    name, 
    salary
FROM employees
ORDER BY salary DESC
FETCH FIRST 5 ROWS ONLY;
```

---

## 2. Aggregate Functions & GROUP BY

### Q11: COUNT, SUM, AVG, MAX, MIN

**Question:** Calculate basic statistics for employee salaries.

**Answer:**
```sql
SELECT 
    COUNT(*) AS total_employees,
    SUM(salary) AS total_salary,
    AVG(salary) AS avg_salary,
    MAX(salary) AS max_salary,
    MIN(salary) AS min_salary
FROM employees;
```

---

### Q12: GROUP BY with aggregations

**Question:** Find average salary by department.

**Answer:**
```sql
SELECT 
    department,
    COUNT(*) AS employee_count,
    AVG(salary) AS avg_salary,
    MAX(salary) AS max_salary
FROM employees
GROUP BY department
ORDER BY avg_salary DESC;
```

---

### Q13: HAVING clause for filtering groups

**Question:** Find departments with average salary greater than 60000.

**Answer:**
```sql
SELECT 
    department,
    AVG(salary) AS avg_salary
FROM employees
GROUP BY department
HAVING AVG(salary) > 60000;
```

**Note:** WHERE filters rows before grouping, HAVING filters groups after aggregation.

---

### Q14: GROUP BY with multiple columns

**Question:** Count employees by department and gender.

**Answer:**
```sql
SELECT 
    department,
    gender,
    COUNT(*) AS employee_count
FROM employees
GROUP BY department, gender
ORDER BY department, gender;
```

---

### Q15: DISTINCT COUNT

**Question:** Count unique job titles in each department.

**Answer:**
```sql
SELECT 
    department,
    COUNT(DISTINCT job_title) AS unique_jobs
FROM employees
GROUP BY department;
```

---

## 3. JOIN Operations

### Q16: INNER JOIN

**Question:** Retrieve employee names with their department names.

**Answer:**
```sql
SELECT 
    e.name,
    d.department_name
FROM employees e
INNER JOIN departments d ON e.department_id = d.department_id;
```

**Result:** Returns only matching rows from both tables.

---

### Q17: LEFT JOIN (LEFT OUTER JOIN)

**Question:** Get all employees and their departments, including those without departments.

**Answer:**
```sql
SELECT 
    e.name,
    COALESCE(d.department_name, 'No Department') AS department
FROM employees e
LEFT JOIN departments d ON e.department_id = d.department_id;
```

**Result:** All rows from left table + matching rows from right table (NULL for non-matches).

---

### Q18: RIGHT JOIN (RIGHT OUTER JOIN)

**Question:** List all departments and their employees, including departments with no employees.

**Answer:**
```sql
SELECT 
    d.department_name,
    e.name
FROM employees e
RIGHT JOIN departments d ON e.department_id = d.department_id;
```

---

### Q19: FULL OUTER JOIN

**Question:** Get all employees and all departments, showing NULLs where there's no match.

**Answer:**
```sql
SELECT 
    e.name,
    d.department_name
FROM employees e
FULL OUTER JOIN departments d ON e.department_id = d.department_id;
```

---

### Q20: SELF JOIN

**Question:** Find employees and their managers.

**Answer:**
```sql
SELECT 
    e.name AS employee,
    m.name AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.employee_id;
```

---

### Q21: Multiple JOINs

**Question:** Get employee, department, and project information.

**Answer:**
```sql
SELECT 
    e.name,
    d.department_name,
    p.project_name
FROM employees e
INNER JOIN departments d ON e.department_id = d.department_id
INNER JOIN projects p ON e.project_id = p.project_id;
```

---

### Q22: JOIN with aggregations

**Question:** Find total salary per department with department names.

**Answer:**
```sql
SELECT 
    d.department_name,
    COUNT(e.employee_id) AS employee_count,
    SUM(e.salary) AS total_salary
FROM departments d
LEFT JOIN employees e ON d.department_id = e.department_id
GROUP BY d.department_name;
```

---

### Q23: CROSS JOIN (Cartesian Product)

**Question:** Generate all possible combinations of products and colors.

**Answer:**
```sql
SELECT 
    p.product_name,
    c.color_name
FROM products p
CROSS JOIN colors c;
```

**Use Case:** Creating combinations, generating test data.

---

## 4. Subqueries & Nested Queries

### Q24: Subquery in WHERE clause

**Question:** Find employees with salary greater than the average salary.

**Answer:**
```sql
SELECT 
    name, 
    salary
FROM employees
WHERE salary > (
    SELECT AVG(salary) 
    FROM employees
);
```

---

### Q25: Subquery with IN operator

**Question:** Find employees working in departments located in 'New York'.

**Answer:**
```sql
SELECT 
    name
FROM employees
WHERE department_id IN (
    SELECT department_id 
    FROM departments 
    WHERE location = 'New York'
);
```

---

### Q26: Correlated subquery

**Question:** Find employees earning more than the average salary in their department.

**Answer:**
```sql
SELECT 
    e1.name,
    e1.salary,
    e1.department_id
FROM employees e1
WHERE e1.salary > (
    SELECT AVG(e2.salary)
    FROM employees e2
    WHERE e2.department_id = e1.department_id
);
```

---

### Q27: Subquery in SELECT clause

**Question:** Show each employee's salary and the maximum salary in the company.

**Answer:**
```sql
SELECT 
    name,
    salary,
    (SELECT MAX(salary) FROM employees) AS max_salary,
    salary - (SELECT MAX(salary) FROM employees) AS difference
FROM employees;
```

---

### Q28: EXISTS clause

**Question:** Find departments that have at least one employee.

**Answer:**
```sql
SELECT 
    department_name
FROM departments d
WHERE EXISTS (
    SELECT 1 
    FROM employees e 
    WHERE e.department_id = d.department_id
);
```

**Performance:** EXISTS is often faster than IN for large datasets.

---

### Q29: NOT EXISTS clause

**Question:** Find departments with no employees.

**Answer:**
```sql
SELECT 
    department_name
FROM departments d
WHERE NOT EXISTS (
    SELECT 1 
    FROM employees e 
    WHERE e.department_id = d.department_id
);
```

---

### Q30: Subquery in FROM clause (Derived Table)

**Question:** Find departments with average salary above 60000.

**Answer:**
```sql
SELECT 
    dept_name,
    avg_salary
FROM (
    SELECT 
        d.department_name AS dept_name,
        AVG(e.salary) AS avg_salary
    FROM departments d
    JOIN employees e ON d.department_id = e.department_id
    GROUP BY d.department_name
) AS dept_stats
WHERE avg_salary > 60000;
```

---

## 5. Window Functions

### Q31: ROW_NUMBER()

**Question:** Assign row numbers to employees ordered by salary within each department.

**Answer:**
```sql
SELECT 
    name,
    department_id,
    salary,
    ROW_NUMBER() OVER (
        PARTITION BY department_id 
        ORDER BY salary DESC
    ) AS row_num
FROM employees;
```

---

### Q32: RANK() and DENSE_RANK()

**Question:** Rank employees by salary showing both RANK and DENSE_RANK.

**Answer:**
```sql
SELECT 
    name,
    salary,
    RANK() OVER (ORDER BY salary DESC) AS rank,
    DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rank
FROM employees;
```

**Difference:**
- RANK(): 1, 2, 2, 4, 5 (skips ranks after ties)
- DENSE_RANK(): 1, 2, 2, 3, 4 (no gaps)

---

### Q33: NTILE()

**Question:** Divide employees into 4 salary quartiles.

**Answer:**
```sql
SELECT 
    name,
    salary,
    NTILE(4) OVER (ORDER BY salary DESC) AS quartile
FROM employees;
```

---

### Q34: LAG() and LEAD()

**Question:** Show each employee's salary along with previous and next employee's salary.

**Answer:**
```sql
SELECT 
    name,
    salary,
    LAG(salary, 1) OVER (ORDER BY salary) AS prev_salary,
    LEAD(salary, 1) OVER (ORDER BY salary) AS next_salary,aw3   
    salary - LAG(salary, 1) OVER (ORDER BY salary) AS diff_from_prev
FROM employees;
```

---

### Q35: Running Total (Cumulative Sum)

**Question:** Calculate running total of salaries ordered by employee_id.

**Answer:**
```sql
SELECT 
    employee_id,
    name,
    salary,
    SUM(salary) OVER (
        ORDER BY employee_id 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total
FROM employees;
```

---

### Q36: Moving Average

**Question:** Calculate 3-row moving average of salaries.

**Answer:**
```sql
SELECT 
    name,
    salary,
    AVG(salary) OVER (
        ORDER BY employee_id 
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ) AS moving_avg_3
FROM employees;
```

---

### Q37: FIRST_VALUE() and LAST_VALUE()

**Question:** Show first and last salary in each department.

**Answer:**
```sql
SELECT 
    department_id,
    name,
    salary,
    FIRST_VALUE(salary) OVER (
        PARTITION BY department_id 
        ORDER BY hire_date
    ) AS first_hire_salary,
    LAST_VALUE(salary) OVER (
        PARTITION BY department_id 
        ORDER BY hire_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_hire_salary
FROM employees;
```

---

### Q38: Cumulative Percentage

**Question:** Calculate cumulative percentage of total salary.

**Answer:**
```sql
SELECT 
    name,
    salary,
    SUM(salary) OVER (ORDER BY employee_id) AS running_total,
    ROUND(
        SUM(salary) OVER (ORDER BY employee_id) * 100.0 / 
        SUM(salary) OVER (), 
        2
    ) AS cumulative_percentage
FROM employees;
```

---

## 6. String Functions

### Q39: CONCAT and string manipulation

**Question:** Concatenate first_name and last_name with a space.

**Answer:**
```sql
SELECT 
    CONCAT(first_name, ' ', last_name) AS full_name
FROM employees;

-- Alternative (SQL Server)
SELECT first_name + ' ' + last_name AS full_name
FROM employees;

-- With NULL handling
SELECT CONCAT_WS(' ', first_name, middle_name, last_name) AS full_name
FROM employees;
```

---

### Q40: UPPER, LOWER, INITCAP

**Question:** Convert names to different cases.

**Answer:**
```sql
SELECT 
    name,
    UPPER(name) AS upper_name,
    LOWER(name) AS lower_name,
    INITCAP(name) AS title_case
FROM employees;
```

---

### Q41: SUBSTRING and string extraction

**Question:** Extract first 3 characters and last 3 characters of names.

**Answer:**
```sql
SELECT 
    name,
    SUBSTRING(name, 1, 3) AS first_3,
    RIGHT(name, 3) AS last_3,
    SUBSTRING(name, 2, 4) AS middle_4
FROM employees;
```

---

### Q42: LENGTH and TRIM

**Question:** Find length of names after trimming spaces.

**Answer:**
```sql
SELECT 
    name,
    LENGTH(name) AS original_length,
    LENGTH(TRIM(name)) AS trimmed_length,
    LTRIM(name) AS left_trimmed,
    RTRIM(name) AS right_trimmed
FROM employees;
```

---

### Q43: REPLACE and pattern replacement

**Question:** Replace 'Manager' with 'Lead' in job titles.

**Answer:**
```sql
SELECT 
    job_title,
    REPLACE(job_title, 'Manager', 'Lead') AS new_title
FROM employees;
```

---

### Q44: String splitting and CHARINDEX

**Question:** Extract domain from email addresses.

**Answer:**
```sql
-- MySQL
SELECT 
    email,
    SUBSTRING_INDEX(email, '@', -1) AS domain
FROM employees;

-- SQL Server
SELECT 
    email,
    SUBSTRING(
        email, 
        CHARINDEX('@', email) + 1, 
        LEN(email)
    ) AS domain
FROM employees;
```

---

## 7. Date & Time Functions

### Q45: CURRENT_DATE and CURRENT_TIMESTAMP

**Question:** Get current date and timestamp.

**Answer:**
```sql
SELECT 
    CURRENT_DATE AS today,
    CURRENT_TIMESTAMP AS now,
    GETDATE() AS now_sql_server;
```

---

### Q46: Date arithmetic (DATEADD, DATE_ADD)

**Question:** Calculate probation end date (90 days after hire date).

**Answer:**
```sql
-- MySQL
SELECT 
    name,
    hire_date,
    DATE_ADD(hire_date, INTERVAL 90 DAY) AS probation_end
FROM employees;

-- SQL Server
SELECT 
    name,
    hire_date,
    DATEADD(DAY, 90, hire_date) AS probation_end
FROM employees;

-- PostgreSQL
SELECT 
    name,
    hire_date,
    hire_date + INTERVAL '90 days' AS probation_end
FROM employees;
```

---

### Q47: DATEDIFF - calculate days between dates

**Question:** Calculate number of days since hire date.

**Answer:**
```sql
-- MySQL
SELECT 
    name,
    hire_date,
    DATEDIFF(CURRENT_DATE, hire_date) AS days_employed
FROM employees;

-- SQL Server
SELECT 
    name,
    hire_date,
    DATEDIFF(DAY, hire_date, GETDATE()) AS days_employed
FROM employees;
```

---

### Q48: Extract date parts (YEAR, MONTH, DAY)

**Question:** Extract year, month, and day from hire date.

**Answer:**
```sql
SELECT 
    hire_date,
    YEAR(hire_date) AS hire_year,
    MONTH(hire_date) AS hire_month,
    DAY(hire_date) AS hire_day,
    DAYOFWEEK(hire_date) AS day_of_week,
    DAYOFYEAR(hire_date) AS day_of_year,
    WEEK(hire_date) AS week_num
FROM employees;
```

---

### Q49: DATE_FORMAT - custom date formatting

**Question:** Format hire date as 'Month DD, YYYY'.

**Answer:**
```sql
-- MySQL
SELECT 
    name,
    DATE_FORMAT(hire_date, '%M %d, %Y') AS formatted_date,
    DATE_FORMAT(hire_date, '%d/%m/%Y') AS dd_mm_yyyy
FROM employees;

-- SQL Server
SELECT 
    name,
    FORMAT(hire_date, 'MMMM dd, yyyy') AS formatted_date,
    FORMAT(hire_date, 'dd/MM/yyyy') AS dd_mm_yyyy
FROM employees;
```

---

### Q50: Date comparison and filtering

**Question:** Find employees hired in the last 6 months.

**Answer:**
```sql
SELECT 
    name,
    hire_date
FROM employees
WHERE hire_date >= DATE_SUB(CURRENT_DATE, INTERVAL 6 MONTH);

-- Alternative
WHERE hire_date >= CURRENT_DATE - INTERVAL '6 months';
```

---

## 8. CASE Statements & Conditional Logic

### Q51: Simple CASE statement

**Question:** Categorize salaries as 'Low', 'Medium', or 'High'.

**Answer:**
```sql
SELECT 
    name,
    salary,
    CASE
        WHEN salary < 40000 THEN 'Low'
        WHEN salary BETWEEN 40000 AND 70000 THEN 'Medium'
        ELSE 'High'
    END AS salary_category
FROM employees;
```

---

### Q52: CASE with aggregation

**Question:** Count employees in each salary category.

**Answer:**
```sql
SELECT 
    SUM(CASE WHEN salary < 40000 THEN 1 ELSE 0 END) AS low_salary,
    SUM(CASE WHEN salary BETWEEN 40000 AND 70000 THEN 1 ELSE 0 END) AS medium_salary,
    SUM(CASE WHEN salary > 70000 THEN 1 ELSE 0 END) AS high_salary
FROM employees;
```

---

### Q53: Pivot table using CASE

**Question:** Create pivot showing employee count by department and gender.

**Answer:**
```sql
SELECT 
    department,
    SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) AS male_count,
    SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) AS female_count,
    SUM(CASE WHEN gender = 'Other' THEN 1 ELSE 0 END) AS other_count
FROM employees
GROUP BY department;
```

---

### Q54: Nested CASE statements

**Question:** Complex salary classification with multiple criteria.

**Answer:**
```sql
SELECT 
    name,
    salary,
    department,
    CASE 
        WHEN department = 'IT' THEN
            CASE 
                WHEN salary > 80000 THEN 'IT Senior'
                WHEN salary > 50000 THEN 'IT Mid'
                ELSE 'IT Junior'
            END
        WHEN department = 'Sales' THEN
            CASE 
                WHEN salary > 70000 THEN 'Sales Senior'
                ELSE 'Sales Associate'
            END
        ELSE 'Other'
    END AS classification
FROM employees;
```

---

### Q55: CASE in ORDER BY

**Question:** Sort employees with custom priority.

**Answer:**
```sql
SELECT 
    name,
    department,
    salary
FROM employees
ORDER BY 
    CASE department
        WHEN 'Executive' THEN 1
        WHEN 'IT' THEN 2
        WHEN 'Sales' THEN 3
        ELSE 4
    END,
    salary DESC;
```

---

## 9. Common Table Expressions (CTEs)

### Q56: Simple CTE

**Question:** Use CTE to find employees with above-average salary.

**Answer:**
```sql
WITH avg_salary AS (
    SELECT AVG(salary) AS avg_sal 
    FROM employees
)
SELECT 
    e.name,
    e.salary,
    a.avg_sal
FROM employees e, avg_salary a
WHERE e.salary > a.avg_sal;
```

---

### Q57: Multiple CTEs

**Question:** Compare each employee to their department average.

**Answer:**
```sql
WITH dept_avg AS (
    SELECT 
        department_id,
        AVG(salary) AS avg_salary
    FROM employees
    GROUP BY department_id
),
emp_comparison AS (
    SELECT 
        e.name,
        e.salary,
        e.department_id,
        d.avg_salary
    FROM employees e
    JOIN dept_avg d ON e.department_id = d.department_id
)
SELECT 
    name,
    salary,
    avg_salary,
    ROUND((salary - avg_salary) / avg_salary * 100, 2) AS pct_diff
FROM emp_comparison;
```

---

### Q58: Recursive CTE - hierarchical data

**Question:** Find all employees in a reporting hierarchy.

**Answer:**
```sql
WITH RECURSIVE employee_hierarchy AS (
    -- Base case: top-level managers
    SELECT 
        employee_id,
        name,
        manager_id,
        1 AS level,
        CAST(name AS VARCHAR(1000)) AS path
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Recursive case
    SELECT 
        e.employee_id,
        e.name,
        e.manager_id,
        eh.level + 1,
        CONCAT(eh.path, ' -> ', e.name)
    FROM employees e
    JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
)
SELECT * 
FROM employee_hierarchy 
ORDER BY level, name;
```

---

### Q59: Recursive CTE - bill of materials

**Question:** Find all components of a product (multi-level BOM).

**Answer:**
```sql
WITH RECURSIVE bom AS (
    -- Top level
    SELECT 
        product_id,
        component_id,
        quantity,
        1 AS level
    FROM product_components
    WHERE product_id = 100
    
    UNION ALL
    
    -- Sub-components
    SELECT 
        pc.product_id,
        pc.component_id,
        pc.quantity * bom.quantity,
        bom.level + 1
    FROM product_components pc
    JOIN bom ON pc.product_id = bom.component_id
)
SELECT * FROM bom;
```

---

### Q60: CTE with window functions

**Question:** Find top 3 earners per department using CTE.

**Answer:**
```sql
WITH ranked_employees AS (
    SELECT 
        name,
        department,
        salary,
        ROW_NUMBER() OVER (
            PARTITION BY department 
            ORDER BY salary DESC
        ) AS rank
    FROM employees
)
SELECT 
    name,
    department,
    salary
FROM ranked_employees
WHERE rank <= 3;
```

---

## 10. Set Operations

### Q61: UNION - combine results

**Question:** Combine employee and contractor names.

**Answer:**
```sql
SELECT name, 'Employee' AS type
FROM employees

UNION

SELECT name, 'Contractor' AS type
FROM contractors;
```

**Note:** UNION removes duplicates automatically.

---

### Q62: UNION ALL - include duplicates

**Question:** Combine all records including duplicates.

**Answer:**
```sql
SELECT name, 'Employee' AS type
FROM employees

UNION ALL

SELECT name, 'Contractor' AS type
FROM contractors;
```

**Performance:** UNION ALL is faster as it doesn't remove duplicates.

---

### Q63: INTERSECT - common records

**Question:** Find names appearing in both employees and contractors.

**Answer:**
```sql
SELECT name FROM employees

INTERSECT

SELECT name FROM contractors;
```

---

### Q64: EXCEPT (or MINUS) - difference

**Question:** Find employees who are not contractors.

**Answer:**
```sql
-- PostgreSQL, SQL Server
SELECT name FROM employees

EXCEPT

SELECT name FROM contractors;

-- Oracle
SELECT name FROM employees

MINUS

SELECT name FROM contractors;
```

---

## 11. Complex Scenarios

### Q65: Find duplicate records

**Question:** Identify employees with duplicate email addresses.

**Answer:**
```sql
SELECT 
    email,
    COUNT(*) AS duplicate_count
FROM employees
GROUP BY email
HAVING COUNT(*) > 1;

-- With details
SELECT * 
FROM employees
WHERE email IN (
    SELECT email
    FROM employees
    GROUP BY email
    HAVING COUNT(*) > 1
);
```

---

### Q66: Delete duplicates keeping one

**Question:** Delete duplicate employees, keeping the one with lowest employee_id.

**Answer:**
```sql
-- Using CTE (PostgreSQL, SQL Server)
WITH cte AS (
    SELECT 
        employee_id,
        ROW_NUMBER() OVER (
            PARTITION BY email 
            ORDER BY employee_id
        ) AS rn
    FROM employees
)
DELETE FROM employees
WHERE employee_id IN (
    SELECT employee_id 
    FROM cte 
    WHERE rn > 1
);

-- Alternative (MySQL)
DELETE e1 FROM employees e1
INNER JOIN employees e2 
WHERE e1.employee_id > e2.employee_id 
    AND e1.email = e2.email;
```

---

### Q67: Second highest salary

**Question:** Find the second highest salary in the company.

**Answer:**
```sql
-- Method 1: Using LIMIT
SELECT DISTINCT salary
FROM employees
ORDER BY salary DESC
LIMIT 1 OFFSET 1;

-- Method 2: Using subquery
SELECT MAX(salary) AS second_highest
FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);

-- Method 3: Using DENSE_RANK
WITH ranked_salaries AS (
    SELECT 
        salary,
        DENSE_RANK() OVER (ORDER BY salary DESC) AS rank
    FROM employees
)
SELECT DISTINCT salary
FROM ranked_salaries
WHERE rank = 2;
```

---

### Q68: Nth highest salary

**Question:** Find the Nth highest salary (generic solution).

**Answer:**
```sql
-- Using DENSE_RANK (N=5)
WITH ranked_salaries AS (
    SELECT 
        salary,
        DENSE_RANK() OVER (ORDER BY salary DESC) AS rank
    FROM employees
)
SELECT DISTINCT salary
FROM ranked_salaries
WHERE rank = 5;

-- Using LIMIT/OFFSET
SELECT DISTINCT salary
FROM employees
ORDER BY salary DESC
LIMIT 1 OFFSET 4;  -- For 5th highest
```

---

### Q69: Find gaps in sequence

**Question:** Find missing employee_ids in a sequence.

**Answer:**
```sql
WITH RECURSIVE all_ids AS (
    SELECT MIN(employee_id) AS id FROM employees
    UNION ALL
    SELECT id + 1
    FROM all_ids
    WHERE id < (SELECT MAX(employee_id) FROM employees)
)
SELECT a.id AS missing_id
FROM all_ids a
LEFT JOIN employees e ON a.id = e.employee_id
WHERE e.employee_id IS NULL;

-- Alternative (more efficient)
SELECT 
    e1.employee_id + 1 AS missing_id
FROM employees e1
LEFT JOIN employees e2 ON e1.employee_id + 1 = e2.employee_idhh 
WHERE e2.employee_id IS NULL
    AND e1.employee_id < (SELECT MAX(employee_id) FROM employees)
ORDER BY missing_id;
```

---

### Q70: Running difference calculation

**Question:** Calculate difference between current and previous salary.

**Answer:**
```sql
SELECT 
    name,
    salary,
    LAG(salary) OVER (ORDER BY employee_id) AS prev_salary,
    salary - LAG(salary) OVER (ORDER BY employee_id) AS salary_diff,
    ROUND(
        (salary - LAG(salary) OVER (ORDER BY employee_id)) * 100.0 / 
        LAG(salary) OVER (ORDER BY employee_id), 
        2
    ) AS pct_change
FROM employees;
```

---

## 12. Data Transformation

### Q71: Unpivot data (rows to columns)

**Question:** Convert quarterly sales columns to rows.

**Answer:**
```sql
SELECT product, 'Q1' AS quarter, q1_sales AS sales
FROM sales_data

UNION ALL

SELECT product, 'Q2', q2_sales
FROM sales_data

UNION ALL

SELECT product, 'Q3', q3_sales
FROM sales_data

UNION ALL

SELECT product, 'Q4', q4_sales
FROM sales_data;
```

---

### Q72: Pivot data (columns to rows)

**Question:** Convert monthly sales rows into columns.

**Answer:**
```sql
SELECT 
    product,
    SUM(CASE WHEN month = 'Jan' THEN sales ELSE 0 END) AS Jan,
    SUM(CASE WHEN month = 'Feb' THEN sales ELSE 0 END) AS Feb,
    SUM(CASE WHEN month = 'Mar' THEN sales ELSE 0 END) AS Mar,
    SUM(CASE WHEN month = 'Apr' THEN sales ELSE 0 END) AS Apr,
    SUM(CASE WHEN month = 'May' THEN sales ELSE 0 END) AS May,
    SUM(CASE WHEN month = 'Jun' THEN sales ELSE 0 END) AS Jun
FROM sales
GROUP BY product;

-- Using PIVOT (SQL Server)
SELECT *
FROM (
    SELECT product, month, sales
    FROM sales
) AS source_table
PIVOT (
    SUM(sales)
    FOR month IN ([Jan], [Feb], [Mar], [Apr], [May], [Jun])
) AS pivot_table;
```

---

### Q73: Generate date series

**Question:** Create a series of dates for the last 30 days.

**Answer:**
```sql
-- PostgreSQL
SELECT DATE(generate_series)
FROM generate_series(
    CURRENT_DATE - INTERVAL '29 days',
    CURRENT_DATE,
    '1 day'
);

-- MySQL using recursive CTE
WITH RECURSIVE date_series AS (
    SELECT CURRENT_DATE - INTERVAL 29 DAY AS date
    
    UNION ALL
    
    SELECT date + INTERVAL 1 DAY
    FROM date_series
    WHERE date < CURRENT_DATE
)
SELECT date FROM date_series;
```

---

### Q74: Fill missing dates with zero values

**Question:** Show sales for all dates in range, filling gaps with 0.

**Answer:**
```sql
WITH RECURSIVE date_range AS (
    SELECT DATE('2024-01-01') AS date
    
    UNION ALL
    
    SELECT date + INTERVAL 1 DAY
    FROM date_range
    WHERE date < '2024-01-31'
)
SELECT 
    dr.date,
    COALESCE(s.sales, 0) AS sales
FROM date_range dr
LEFT JOIN sales s ON dr.date = s.sale_date
ORDER BY dr.date;
```

---

### Q75: Split comma-separated values

**Question:** Split comma-separated skills into individual rows.

**Answer:**
```sql
-- PostgreSQL
SELECT 
    name,
    UNNEST(STRING_TO_ARRAY(skills, ',')) AS skill
FROM employees;

-- MySQL (requires numbers table)
SELECT 
    e.name,
    TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(e.skills, ',', n.n), ',', -1)) AS skill
FROM employees e
CROSS JOIN (
    SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 
    UNION SELECT 4 UNION SELECT 5
) n
WHERE n.n <= LENGTH(e.skills) - LENGTH(REPLACE(e.skills, ',', '')) + 1;
```

---

## 13. Performance Optimization

### Q76: Using EXISTS instead of IN

**Question:** Optimize query to find employees in specific departments.

**Answer:**
```sql
-- Less efficient
SELECT *
FROM employees
WHERE department_id IN (
    SELECT department_id 
    FROM departments 
    WHERE location = 'NY'
);

-- More efficient
SELECT *
FROM employees e
WHERE EXISTS (
    SELECT 1 
    FROM departments d 
    WHERE d.department_id = e.department_id 
        AND d.location = 'NY'
);
```

**Why:** EXISTS stops as soon as it finds a match.

---

### Q77: Using JOIN instead of correlated subquery

**Question:** Rewrite correlated subquery as JOIN.

**Answer:**
```sql
-- Slower: Correlated subquery
SELECT 
    e1.name,
    e1.salary
FROM employees e1
WHERE salary > (
    SELECT AVG(salary)
    FROM employees e2
    WHERE e2.department_id = e1.department_id
);

-- Faster: JOIN
SELECT 
    e.name,
    e.salary
FROM employees e
JOIN (
    SELECT 
        department_id,
        AVG(salary) AS avg_sal
    FROM employees
    GROUP BY department_id
) dept_avg ON e.department_id = dept_avg.department_id
WHERE e.salary > dept_avg.avg_sal;
```

---

### Q78: Index usage demonstration

**Question:** Create index and show execution plan.

**Answer:**
```sql
-- Create index
CREATE INDEX idx_employee_salary 
ON employees(salary);

-- Composite index
CREATE INDEX idx_dept_salary 
ON employees(department_id, salary);

-- View execution plan
EXPLAIN SELECT * 
FROM employees 
WHERE salary > 50000;

-- SQL Server
SET SHOWPLAN_ALL ON;
SELECT * FROM employees WHERE salary > 50000;
SET SHOWPLAN_ALL OFF;
```

---

### Q79: Avoiding SELECT *

**Question:** Write optimized query selecting only needed columns.

**Answer:**
```sql
-- Bad
SELECT * 
FROM employees e
JOIN departments d ON e.department_id = d.department_id;

-- Good
SELECT 
    e.employee_id,
    e.name,
    e.salary,
    d.department_name
FROM employees e
JOIN departments d ON e.department_id = d.department_id;
```

**Why:** Reduces I/O, network traffic, and memory usage.

---

### Q80: Using UNION ALL instead of UNION

**Question:** When to use UNION ALL for better performance.

**Answer:**
```sql
-- If you know there are no duplicates, use UNION ALL
SELECT name FROM employees WHERE department = 'IT'

UNION ALL

SELECT name FROM employees WHERE department = 'HR';

-- UNION ALL is faster because it doesn't:
-- 1. Sort results
-- 2. Remove duplicates
```

---

## 14. Transaction Control

### Q81: Basic transaction

**Question:** Demonstrate transaction with COMMIT and ROLLBACK.

**Answer:**
```sql
BEGIN TRANSACTION;

UPDATE employees
SET salary = salary * 1.1
WHERE department_id = 5;

-- Check results
SELECT * FROM employees WHERE department_id = 5;

-- If satisfied
COMMIT;

-- If not satisfied
-- ROLLBACK;
```

---

### Q82: INSERT with SELECT

**Question:** Insert employees from staging table into main table.

**Answer:**
```sql
INSERT INTO employees (name, department_id, salary)
SELECT 
    name,
    department_id,
    salary
FROM staging_employees
WHERE status = 'approved';
```

---

### Q83: UPDATE with JOIN

**Question:** Update employee salaries based on department average.

**Answer:**
```sql
-- MySQL
UPDATE employees e
JOIN (
    SELECT 
        department_id,
        AVG(salary) * 1.1 AS new_avg
    FROM employees
    GROUP BY department_id
) d ON e.department_id = d.department_id
SET e.salary = d.new_avg;

-- SQL Server
UPDATE e
SET e.salary = d.new_avg
FROM employees e
JOIN (
    SELECT 
        department_id,
        AVG(salary) * 1.1 AS new_avg
    FROM employees
    GROUP BY department_id
) d ON e.department_id = d.department_id;
```

---

### Q84: MERGE / UPSERT operation

**Question:** Insert new records or update existing ones.

**Answer:**
```sql
-- PostgreSQL ON CONFLICT
INSERT INTO employees (employee_id, name, salary)
VALUES (1, 'John Doe', 50000)
ON CONFLICT (employee_id) 
DO UPDATE SET 
    name = EXCLUDED.name,
    salary = EXCLUDED.salary;

-- MySQL ON DUPLICATE KEY
INSERT INTO employees (employee_id, name, salary)
VALUES (1, 'John Doe', 50000)
ON DUPLICATE KEY UPDATE 
    name = VALUES(name),
    salary = VALUES(salary);

-- SQL Server MERGE
MERGE INTO employees AS target
USING staging_employees AS source
ON target.employee_id = source.employee_id
WHEN MATCHED THEN
    UPDATE SET 
        name = source.name,
        salary = source.salary
WHEN NOT MATCHED THEN
    INSERT (employee_id, name, salary)
    VALUES (source.employee_id, source.name, source.salary);
```

---

## 15. Advanced Topics

### Q85: JSON data extraction

**Question:** Extract values from JSON column.

**Answer:**
```sql
-- PostgreSQL
SELECT 
    name,
    profile->>'email' AS email,
    profile->'address'->>'city' AS city
FROM employees;

-- MySQL
SELECT 
    name,
    JSON_EXTRACT(profile, '$.email') AS email,
    JSON_EXTRACT(profile, '$.address.city') AS city
FROM employees;

-- Or using ->>
SELECT 
    name,
    profile->>'$.email' AS email
FROM employees;
```

---

### Q86: Regular expressions

**Question:** Find emails matching a specific pattern.

**Answer:**
```sql
-- PostgreSQL
SELECT 
    name,
    email
FROM employees
WHERE email ~ '^[a-z0-9._%+-]+@company\.com$';

-- MySQL
SELECT 
    name,
    email
FROM employees
WHERE email REGEXP '^[a-z0-9._%+-]+@company\\.com$';

-- SQL Server
SELECT 
    name,
    email
FROM employees
WHERE email LIKE '%@company.com'
    AND email NOT LIKE '%[^a-z0-9._%+-]%@%';
```

---

### Q87: Window function with FILTER clause

**Question:** Calculate conditional aggregations using FILTER.

**Answer:**
```sql
-- PostgreSQL
SELECT 
    department,
    COUNT(*) AS total_employees,
    COUNT(*) FILTER (WHERE salary > 50000) AS high_earners,
    AVG(salary) FILTER (WHERE gender = 'F') AS avg_female_salary
FROM employees
GROUP BY department;
```

---

### Q88: Lateral join (CROSS APPLY)

**Question:** Use lateral join to get top 3 employees per department.

**Answer:**
```sql
-- PostgreSQL LATERAL
SELECT 
    d.department_name,
    e.name,
    e.salary
FROM departments d
CROSS JOIN LATERAL (
    SELECT name, salary
    FROM employees e
    WHERE e.department_id = d.department_id
    ORDER BY salary DESC
    LIMIT 3
) e;

-- SQL Server CROSS APPLY
SELECT 
    d.department_name,
    e.name,
    e.salary
FROM departments d
CROSS APPLY (
    SELECT TOP 3 name, salary
    FROM employees e
    WHERE e.department_id = d.department_id
    ORDER BY salary DESC
) e;
```

---

### Q89: Hierarchical queries with CONNECT BY (Oracle)

**Question:** Traverse organizational hierarchy in Oracle.

**Answer:**
```sql
SELECT 
    LEVEL,
    employee_id,
    name,
    manager_id,
    SYS_CONNECT_BY_PATH(name, '/') AS path
FROM employees
START WITH manager_id IS NULL
CONNECT BY PRIOR employee_id = manager_id
ORDER SIBLINGS BY name;
```

---

### Q90: CREATE VIEW

**Question:** Create view for high-earning employees.

**Answer:**
```sql
CREATE VIEW high_earners AS
SELECT 
    e.name,
    e.salary,
    d.department_name
FROM employees e
JOIN departments d ON e.department_id = d.department_id
WHERE e.salary > 70000;

-- Use the view
SELECT * FROM high_earners 
WHERE department_name = 'Engineering';

-- Update view (if updatable)
UPDATE high_earners
SET salary = salary * 1.1
WHERE name = 'John Doe';
```

---

### Q91: Materialized view

**Question:** Create and refresh materialized view.

**Answer:**
```sql
-- PostgreSQL
CREATE MATERIALIZED VIEW dept_summary AS
SELECT 
    department_id,
    COUNT(*) AS emp_count,
    AVG(salary) AS avg_salary,
    MAX(salary) AS max_salary
FROM employees
GROUP BY department_id;

-- Refresh the view
REFRESH MATERIALIZED VIEW dept_summary;

-- Concurrent refresh (doesn't lock)
REFRESH MATERIALIZED VIEW CONCURRENTLY dept_summary;
```

---

### Q92: Stored procedure

**Question:** Create stored procedure to give salary raise.

**Answer:**
```sql
-- PostgreSQL
CREATE OR REPLACE PROCEDURE give_raise(
    emp_id INTEGER,
    raise_pct DECIMAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE employees
    SET salary = salary * (1 + raise_pct / 100)
    WHERE employee_id = emp_id;
    
    RAISE NOTICE 'Salary updated for employee %', emp_id;
END;
$$;

-- Call the procedure
CALL give_raise(101, 10);

-- SQL Server
CREATE PROCEDURE give_raise
    @emp_id INT,
    @raise_pct DECIMAL(5,2)
AS
BEGIN
    UPDATE employees
    SET salary = salary * (1 + @raise_pct / 100)
    WHERE employee_id = @emp_id;
    
    PRINT 'Salary updated';
END;

-- Execute
EXEC give_raise @emp_id = 101, @raise_pct = 10;
```

---

### Q93: Trigger creation

**Question:** Create trigger to log salary changes.

**Answer:**
```sql
-- Create audit table
CREATE TABLE salary_audit (
    audit_id SERIAL PRIMARY KEY,
    employee_id INTEGER,
    old_salary DECIMAL(10,2),
    new_salary DECIMAL(10,2),
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PostgreSQL trigger function
CREATE OR REPLACE FUNCTION log_salary_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.salary IS DISTINCT FROM OLD.salary THEN
        INSERT INTO salary_audit (employee_id, old_salary, new_salary)
        VALUES (NEW.employee_id, OLD.salary, NEW.salary);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER salary_change_trigger
AFTER UPDATE ON employees
FOR EACH ROW
EXECUTE FUNCTION log_salary_change();

-- SQL Server trigger
CREATE TRIGGER salary_change_trigger
ON employees
AFTER UPDATE
AS
BEGIN
    INSERT INTO salary_audit (employee_id, old_salary, new_salary)
    SELECT 
        i.employee_id,
        d.salary,
        i.salary
    FROM inserted i
    JOIN deleted d ON i.employee_id = d.employee_id
    WHERE i.salary <> d.salary;
END;
```

---

### Q94: Partitioning

**Question:** Create partitioned table by date range.

**Answer:**
```sql
-- PostgreSQL
CREATE TABLE sales (
    sale_id SERIAL,
    sale_date DATE NOT NULL,
    amount DECIMAL(10,2),
    product_id INTEGER
) PARTITION BY RANGE (sale_date);

-- Create partitions
CREATE TABLE sales_2023 PARTITION OF sales
FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE sales_2024 PARTITION OF sales
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Insert automatically routes to correct partition
INSERT INTO sales (sale_date, amount, product_id)
VALUES ('2024-06-15', 100.00, 1);
```

---

### Q95: Full-text search

**Question:** Implement full-text search on employee profiles.

**Answer:**
```sql
-- PostgreSQL
SELECT 
    name,
    bio
FROM employees
WHERE to_tsvector('english', bio) @@ to_tsquery('english', 'engineer & python');

-- Create index for performance
CREATE INDEX idx_bio_fts ON employees 
USING gin(to_tsvector('english', bio));

-- MySQL
CREATE FULLTEXT INDEX ft_bio ON employees(bio);

SELECT 
    name,
    bio,
    MATCH(bio) AGAINST('engineer python' IN BOOLEAN MODE) AS relevance
FROM employees
WHERE MATCH(bio) AGAINST('engineer python' IN BOOLEAN MODE)
ORDER BY relevance DESC;
```

---

### Q96: Calculate median

**Question:** Calculate median salary.

**Answer:**
```sql
-- Using PERCENTILE_CONT (PostgreSQL, SQL Server)
SELECT 
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) AS median_salary
FROM employees;

-- Alternative method
WITH ordered_salaries AS (
    SELECT 
        salary,
        ROW_NUMBER() OVER (ORDER BY salary) AS row_num,
        COUNT(*) OVER () AS total_count
    FROM employees
)
SELECT AVG(salary) AS median_salary
FROM ordered_salaries
WHERE row_num IN (
    FLOOR((total_count + 1) / 2.0),
    CEIL((total_count + 1) / 2.0)
);
```

---

### Q97: Calculate mode (most frequent value)

**Question:** Find most common salary.

**Answer:**
```sql
WITH salary_counts AS (
    SELECT 
        salary,
        COUNT(*) AS frequency
    FROM employees
    GROUP BY salary
)
SELECT salary AS mode_salary
FROM salary_counts
WHERE frequency = (SELECT MAX(frequency) FROM salary_counts);
```

---

### Q98: Running total with reset

**Question:** Calculate running total that resets each month.

**Answer:**
```sql
SELECT 
    sale_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY DATE_TRUNC('month', sale_date)
        ORDER BY sale_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS monthly_running_total
FROM sales
ORDER BY sale_date;
```

---

### Q99: Year-over-Year growth

**Question:** Calculate YoY sales growth.

**Answer:**
```sql
WITH yearly_sales AS (
    SELECT 
        EXTRACT(YEAR FROM sale_date) AS year,
        SUM(amount) AS total_sales
    FROM sales
    GROUP BY EXTRACT(YEAR FROM sale_date)
)
SELECT 
    year,
    total_sales,
    LAG(total_sales) OVER (ORDER BY year) AS prev_year_sales,
    ROUND(
        (total_sales - LAG(total_sales) OVER (ORDER BY year)) * 100.0 / 
        LAG(total_sales) OVER (ORDER BY year),
        2
    ) AS yoy_growth_pct
FROM yearly_sales;
```

---

### Q100: Complex data quality check

**Question:** Identify data quality issues across multiple dimensions.

**Answer:**
```sql
WITH data_quality_checks AS (
    SELECT 
        employee_id,
        name,
        -- Check for NULL values
        CASE WHEN email IS NULL THEN 1 ELSE 0 END AS missing_email,
        CASE WHEN phone IS NULL THEN 1 ELSE 0 END AS missing_phone,
        
        -- Check for invalid formats
        CASE 
            WHEN email NOT LIKE '%@%.%' THEN 1 
            ELSE 0 
        END AS invalid_email,
        
        -- Check for outliers
        CASE 
            WHEN salary > (SELECT AVG(salary) + 3 * STDDEV(salary) FROM employees)
                OR salary < (SELECT AVG(salary) - 3 * STDDEV(salary) FROM employees)
            THEN 1
            ELSE 0
        END AS salary_outlier,
        
        -- Check for duplicates
        CASE 
            WHEN COUNT(*) OVER (PARTITION BY email) > 1 THEN 1 
            ELSE 0 
        END AS duplicate_email
    FROM employees
)
SELECT 
    employee_id,
    name,
    missing_email + missing_phone + invalid_email + 
    salary_outlier + duplicate_email AS total_issues,
    CASE 
        WHEN missing_email = 1 THEN 'Missing Email, ' 
        ELSE '' 
    END ||
    CASE 
        WHEN missing_phone = 1 THEN 'Missing Phone, ' 
        ELSE '' 
    END ||
    CASE 
        WHEN invalid_email = 1 THEN 'Invalid Email, ' 
        ELSE '' 
    END ||
    CASE 
        WHEN salary_outlier = 1 THEN 'Salary Outlier, ' 
        ELSE '' 
    END ||
    CASE 
        WHEN duplicate_email = 1 THEN 'Duplicate Email' 
        ELSE '' 
    END AS issues_description
FROM data_quality_checks
WHERE missing_email + missing_phone + invalid_email + 
      salary_outlier + duplicate_email > 0;
```

---

## Conclusion

This comprehensive guide covers 100+ SQL interview questions ranging from basic to advanced topics. Key takeaways:

1. **Master the fundamentals:** SELECT, WHERE, JOINs, GROUP BY
2. **Understand window functions:** Essential for analytics
3. **Learn CTEs:** Improve query readability and maintainability
4. **Practice optimization:** Indexes, execution plans, query tuning
5. **Know your SQL dialect:** MySQL, PostgreSQL, SQL Server, Oracle have differences

**Practice Resources:**
- LeetCode SQL problems
- HackerRank SQL challenges
- Mode Analytics SQL tutorial
- SQLZoo interactive tutorials

**Interview Tips:**
- Always explain your thought process
- Discuss time complexity
- Mention alternative approaches
- Ask about data volume and performance requirements
- Write clean, readable code with proper formatting

Good luck with your SQL interviews!
