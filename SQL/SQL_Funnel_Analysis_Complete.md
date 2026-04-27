# SQL Funnel Analysis — Complete Deep Dive
## From Zero to Expert | Costco Sr. Data Engineer Prep

---

## HOW TO READ THIS FILE

This file teaches funnel analysis the way a senior engineer thinks about it — not just "here is the SQL" but "here is WHY we write it this way, what can go wrong, and how interviewers will try to trick you."

Read it front to back the first time. Each section builds on the previous one. By the end, you should be able to:

- Explain what a funnel is and why businesses care about it
- Write correct funnel SQL for any variant an interviewer throws at you
- Recognize the pattern and approach from the question description alone
- Answer every level of question with confidence

---

# PART 1: WHAT IS A FUNNEL AND WHY DOES IT EXIST?

---

## 1.1 The Real-World Problem Funnels Solve

Every business wants users to take a sequence of actions that leads to a desired outcome — a purchase, a sign-up, a subscription renewal. But users don't always complete every step. They drop off at various points.

The questions every marketing and product team asks:

```
"We sent 100,000 people to our website from ads.
 Only 120 of them bought something.
 WHERE did the other 99,880 people go?
 Which step is broken?"
```

Without funnel analysis, you have no answer. You just know you spent money and got purchases. With funnel analysis, you see EXACTLY where the drop-off is happening.

```
THE COSTCO AD FUNNEL EXAMPLE:

Step 1: 100,000  people saw a Costco ad (Impression)
Step 2:   2,000  people clicked the ad (Click)
Step 3:   1,200  people landed on the Costco membership page (Page View)
Step 4:     300  people added membership to cart (Add to Cart)
Step 5:     120  people completed the purchase (Purchase)

Now I can see:
  Impression → Click:     2.0%  conversion  (100,000 → 2,000)
  Click → Page View:     60.0%  conversion  (2,000 → 1,200)
  Page View → Cart:      25.0%  conversion  (1,200 → 300)
  Cart → Purchase:       40.0%  conversion  (300 → 120)
  Overall:                0.12% end-to-end  (100,000 → 120)

Immediate insight:
  Page View → Cart is the WORST step (only 25% convert).
  This means 75% of people who land on the page DON'T add to cart.
  Fix: improve the landing page, offer, or pricing.
  
  Cart → Purchase is not bad (40%), but can be improved.
  Fix: streamline checkout, reduce friction.

THIS IS THE VALUE OF FUNNEL ANALYSIS.
Without it: "our conversion rate is 0.12% — it's bad"
With it:    "our landing page → cart step is broken — here's what to fix"
```

---

## 1.2 What Is a Funnel? — Formal Definition

A **funnel** is a sequence of steps (events or actions) that a user must pass through to reach a final goal, where:

1. Steps happen **in a defined order** (Step 2 must happen after Step 1)
2. Each subsequent step has **fewer users** than the prior (people drop off)
3. The goal is to measure **how many users complete each step** and **where they drop off**

The name "funnel" comes from the shape: wide at the top (many users), narrow at the bottom (few complete all steps).

```
FUNNEL SHAPE:

  ████████████████████████████  100,000  Impressions
  ████████████                    2,000  Clicks
  ███████                         1,200  Page Views
  ██                                300  Add to Cart
  █                                 120  Purchase
```

---

## 1.3 Types of Funnels — Know These Before Writing SQL

Before writing a single line of SQL, you must identify WHICH TYPE of funnel the question is asking for. Getting this wrong means your entire solution is wrong.

```
TYPE 1: UNORDERED FUNNEL (Session-Based)
  Question says: "how many users performed ALL of these events?"
  Steps don't need to happen in sequence — just within the same session/day.
  
  Example: "Users who saw an ad AND clicked AND bought in the same session"
  No requirement that click happened AFTER impression — just that all three occurred.
  
  SQL approach: MAX(CASE WHEN event_type = 'X' THEN 1 ELSE 0 END)
  Simple, fast, no self-joins needed.

TYPE 2: ORDERED FUNNEL (Strict Sequence)
  Question says: "users who clicked THEN viewed THEN added to cart THEN purchased"
  Each step MUST happen AFTER the previous step.
  
  Example: "Users who clicked at 2 PM then viewed the page at 2:05 PM then bought at 2:20 PM"
  A purchase that happened BEFORE a click should NOT count.
  
  SQL approach: MIN timestamp per event, check each MIN > prior MIN
  Slightly more complex but the CORRECT answer for most real-world funnels.

TYPE 3: TIME-WINDOWED FUNNEL
  Question says: "completed all steps within N hours/days"
  Steps must happen in order AND within a time window.
  
  Example: "Users who clicked an ad and purchased within 30 days"
  A click in January and a purchase in July should NOT count.
  
  SQL approach: MIN timestamps + TIMESTAMP_DIFF check
  
TYPE 4: COHORT FUNNEL
  Question says: "compare funnel conversion by segment/cohort"
  Compute funnel metrics separately for different user groups.
  
  Example: "Compare funnel for new members vs returning members"
  "Which campaign has the highest funnel conversion rate?"
  
  SQL approach: Add GROUP BY segment/cohort to any of the above patterns.
```

---

# PART 2: THE BUILDING BLOCKS OF FUNNEL SQL

---

## 2.1 The Core Technique: Conditional Aggregation

This is the single most important pattern in funnel SQL. Learn it cold.

**The pattern**: For a table of events (one row per event), you want to collapse all events per user into ONE ROW, with one column per funnel step showing whether that user performed that step.

```
INPUT (events table — many rows per user):

user_id | event_type   | event_time
────────┼──────────────┼────────────────────
U001    | impression   | 2024-01-15 14:00:00
U001    | click        | 2024-01-15 14:02:00
U001    | page_view    | 2024-01-15 14:02:30
U001    | purchase     | 2024-01-15 14:25:00
U002    | impression   | 2024-01-15 14:01:00
U002    | click        | 2024-01-15 14:03:00
U003    | impression   | 2024-01-15 14:05:00

OUTPUT (one row per user with step flags):

user_id | had_impression | had_click | had_page_view | had_purchase
────────┼───────────────┼───────────┼───────────────┼─────────────
U001    |       1        |     1     |       1       |      1
U002    |       1        |     1     |       0       |      0
U003    |       1        |     0     |       0       |      0
```

**How to do this with SQL**:

```sql
-- THE FUNDAMENTAL FUNNEL PATTERN
-- Step 1: Pivot events into columns using conditional aggregation

SELECT
    user_id,
    
    -- MAX(CASE WHEN ...) pattern:
    -- For each row of this user, if event_type = 'impression', return 1, else 0
    -- MAX across all rows: if ANY row had event_type='impression', result = 1
    -- If NO row had 'impression', result = 0
    
    MAX(CASE WHEN event_type = 'impression'  THEN 1 ELSE 0 END) AS had_impression,
    MAX(CASE WHEN event_type = 'click'       THEN 1 ELSE 0 END) AS had_click,
    MAX(CASE WHEN event_type = 'page_view'   THEN 1 ELSE 0 END) AS had_page_view,
    MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS had_add_to_cart,
    MAX(CASE WHEN event_type = 'purchase'    THEN 1 ELSE 0 END) AS had_purchase

FROM user_events
WHERE event_date = '2024-01-15'
GROUP BY user_id;

-- WHY MAX and not SUM or COUNT?
-- MAX: returns 1 if user had that event AT LEAST ONCE, 0 if never
--      (we just want to know "did it happen", not "how many times")
-- SUM: would give total count (3 clicks = 3, not "had a click = yes")
-- COUNT: similar issue
-- MAX is the cleanest "did this event happen for this user?" aggregation

-- WHY NOT COUNT(DISTINCT) as a flag?
-- COUNT(DISTINCT event_type='click') doesn't work directly
-- MAX(CASE WHEN...) is the standard idiom
```

---

## 2.2 Going From Per-User Flags to Funnel Counts

After creating the per-user pivot table, you aggregate to get the funnel counts:

```sql
-- Step 1: Per-user flags (CTE)
WITH user_flags AS (
    SELECT
        user_id,
        MAX(CASE WHEN event_type = 'impression'  THEN 1 ELSE 0 END) AS had_impression,
        MAX(CASE WHEN event_type = 'click'       THEN 1 ELSE 0 END) AS had_click,
        MAX(CASE WHEN event_type = 'page_view'   THEN 1 ELSE 0 END) AS had_page_view,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS had_add_to_cart,
        MAX(CASE WHEN event_type = 'purchase'    THEN 1 ELSE 0 END) AS had_purchase
    FROM user_events
    WHERE event_date = '2024-01-15'
    GROUP BY user_id
)

-- Step 2: Aggregate to funnel counts
SELECT
    COUNT(*)                        AS total_users,
    SUM(had_impression)             AS step1_impressions,
    SUM(had_click)                  AS step2_clicks,
    SUM(had_page_view)              AS step3_page_views,
    SUM(had_add_to_cart)            AS step4_add_to_cart,
    SUM(had_purchase)               AS step5_purchases,
    
    -- Step-to-step conversion rates
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_click),         SUM(had_impression)),    2) AS step1_to_2_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_page_view),     SUM(had_click)),         2) AS step2_to_3_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_add_to_cart),   SUM(had_page_view)),     2) AS step3_to_4_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase),      SUM(had_add_to_cart)),   2) AS step4_to_5_pct,
    
    -- Overall end-to-end conversion
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase),      SUM(had_impression)),    4) AS overall_cvr_pct

FROM user_flags;

-- RESULT:
-- total_users | step1_impressions | step2_clicks | ... | overall_cvr_pct
--    10,000   |       9,800       |    2,000     | ... |     0.12%
```

---

## 2.3 The Timestamp Pattern — For Ordered Funnels

When the question requires ORDERED steps (each must happen AFTER the previous), you need to capture the FIRST timestamp for each event type per user:

```sql
-- WHY MIN(timestamp) and not MAX?
-- MIN = the FIRST time the user did that action
-- We want: did their first click happen before their first purchase?
-- Using MAX would give the LAST time — which might give false positives

WITH user_timestamps AS (
    SELECT
        user_id,
        
        -- Capture FIRST timestamp of each event type
        MIN(CASE WHEN event_type = 'impression'  THEN event_time END) AS first_impression,
        MIN(CASE WHEN event_type = 'click'       THEN event_time END) AS first_click,
        MIN(CASE WHEN event_type = 'page_view'   THEN event_time END) AS first_page_view,
        MIN(CASE WHEN event_type = 'add_to_cart' THEN event_time END) AS first_add_to_cart,
        MIN(CASE WHEN event_type = 'purchase'    THEN event_time END) AS first_purchase
        
    FROM user_events
    WHERE event_date >= '2024-01-01'
    GROUP BY user_id
)
-- Note: if a user never had 'click', MIN(CASE WHEN...) returns NULL
-- NULL means "never happened" — we use IS NOT NULL to check

SELECT * FROM user_timestamps LIMIT 5;

-- sample output:
-- user_id | first_impression     | first_click          | first_page_view      | first_add_to_cart | first_purchase
-- U001    | 2024-01-15 14:00:00  | 2024-01-15 14:02:00  | 2024-01-15 14:02:30  | NULL              | 2024-01-15 14:25:00
-- (U001 never added to cart but still purchased — ordered funnel would NOT count this!)
```

---

## 2.4 The Ordered Funnel Check — The Critical Logic

This is where most candidates make mistakes. The ordering logic must be bulletproof:

```sql
WITH user_timestamps AS (
    SELECT
        user_id,
        MIN(CASE WHEN event_type = 'impression'  THEN event_time END) AS t_impression,
        MIN(CASE WHEN event_type = 'click'       THEN event_time END) AS t_click,
        MIN(CASE WHEN event_type = 'page_view'   THEN event_time END) AS t_page_view,
        MIN(CASE WHEN event_type = 'add_to_cart' THEN event_time END) AS t_cart,
        MIN(CASE WHEN event_type = 'purchase'    THEN event_time END) AS t_purchase
    FROM user_events
    GROUP BY user_id
)

SELECT
    COUNT(*) AS total_users,
    
    -- Step 1: had an impression (no ordering requirement for first step)
    COUNTIF(t_impression IS NOT NULL)
        AS reached_step1,
    
    -- Step 2: had a click AFTER an impression
    -- Both must exist AND click happened at or after impression
    COUNTIF(t_click IS NOT NULL
            AND t_impression IS NOT NULL
            AND t_click >= t_impression)
        AS reached_step2,
    
    -- Step 3: had a page view AFTER a click (which was after impression)
    -- Must check the ENTIRE chain, not just adjacent steps
    COUNTIF(t_page_view IS NOT NULL
            AND t_click IS NOT NULL
            AND t_impression IS NOT NULL
            AND t_page_view >= t_click
            AND t_click >= t_impression)
        AS reached_step3,
    
    -- Step 4: added to cart after page view (full chain check)
    COUNTIF(t_cart IS NOT NULL
            AND t_page_view IS NOT NULL
            AND t_click IS NOT NULL
            AND t_impression IS NOT NULL
            AND t_cart >= t_page_view
            AND t_page_view >= t_click
            AND t_click >= t_impression)
        AS reached_step4,
    
    -- Step 5: purchased after adding to cart (full chain check)
    COUNTIF(t_purchase IS NOT NULL
            AND t_cart IS NOT NULL
            AND t_page_view IS NOT NULL
            AND t_click IS NOT NULL
            AND t_impression IS NOT NULL
            AND t_purchase >= t_cart
            AND t_cart >= t_page_view
            AND t_page_view >= t_click
            AND t_click >= t_impression)
        AS reached_step5

FROM user_timestamps;

-- WHY CHECK THE FULL CHAIN AT EACH STEP?
-- Consider this user:
-- impression at 10:00, click at 9:00 (BEFORE impression!), page_view at 10:30
-- If you only check page_view >= click: 10:30 >= 9:00 = TRUE (wrong!)
-- If you check full chain: click >= impression fails: 9:00 >= 10:00 = FALSE (correct!)
-- User did NOT go through the funnel in the right order.
```

---

# PART 3: FUNNEL VARIANTS — EVERY PATTERN

---

## 3.1 Variant 1: Simple Unordered Funnel (Same Session)

**When to use**: Question asks about events within the same session, no strict ordering.

```sql
-- "How many sessions converted at each funnel step?"
-- Session = all events with the same session_id

WITH session_funnel AS (
    SELECT
        session_id,
        user_id,
        campaign_id,
        MAX(CASE WHEN event_type = 'impression'  THEN 1 ELSE 0 END) AS had_impression,
        MAX(CASE WHEN event_type = 'click'       THEN 1 ELSE 0 END) AS had_click,
        MAX(CASE WHEN event_type = 'page_view'   THEN 1 ELSE 0 END) AS had_page_view,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS had_cart,
        MAX(CASE WHEN event_type = 'purchase'    THEN 1 ELSE 0 END) AS had_purchase
    FROM events
    WHERE event_date = '2024-01-15'
    GROUP BY session_id, user_id, campaign_id
)
SELECT
    campaign_id,
    COUNT(*)                                             AS total_sessions,
    SUM(had_impression)                                  AS impressions,
    SUM(had_click)                                       AS clicks,
    SUM(had_page_view)                                   AS page_views,
    SUM(had_cart)                                        AS add_to_carts,
    SUM(had_purchase)                                    AS purchases,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_click), SUM(had_impression)),    2) AS imp_to_click_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_page_view), SUM(had_click)),     2) AS click_to_view_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_cart), SUM(had_page_view)),      2) AS view_to_cart_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase), SUM(had_cart)),       2) AS cart_to_purchase_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase), SUM(had_impression)), 4) AS overall_cvr_pct
FROM session_funnel
GROUP BY campaign_id
ORDER BY total_sessions DESC;
```

---

## 3.2 Variant 2: Ordered Funnel with Time Constraint

**When to use**: Steps must happen in order AND within N days.

```sql
-- "Users who clicked an ad and purchased within 30 days"
-- The 30-day window prevents someone who clicked in January counting
-- as a conversion for a purchase they made in July.

WITH user_first_events AS (
    SELECT
        user_id,
        campaign_id,
        MIN(CASE WHEN event_type = 'click'    THEN event_time END) AS first_click,
        MIN(CASE WHEN event_type = 'page_view' THEN event_time END) AS first_view,
        MIN(CASE WHEN event_type = 'purchase' THEN event_time END) AS first_purchase
    FROM events
    WHERE event_date >= '2024-01-01'
    GROUP BY user_id, campaign_id
)
SELECT
    campaign_id,
    COUNT(*) AS total_users_who_clicked,
    
    -- Converted: purchased within 30 days of first click
    COUNTIF(
        first_purchase IS NOT NULL
        AND first_purchase >= first_click
        AND TIMESTAMP_DIFF(first_purchase, first_click, DAY) <= 30
    ) AS purchased_within_30d,
    
    -- Average time to purchase (for those who converted)
    ROUND(AVG(
        CASE
            WHEN first_purchase IS NOT NULL
             AND first_purchase >= first_click
             AND TIMESTAMP_DIFF(first_purchase, first_click, DAY) <= 30
            THEN TIMESTAMP_DIFF(first_purchase, first_click, HOUR)
        END
    ), 1) AS avg_hours_to_purchase,
    
    -- Conversion rate
    ROUND(100.0 * SAFE_DIVIDE(
        COUNTIF(
            first_purchase IS NOT NULL
            AND first_purchase >= first_click
            AND TIMESTAMP_DIFF(first_purchase, first_click, DAY) <= 30
        ),
        COUNT(*)
    ), 2) AS click_to_purchase_30d_cvr_pct

FROM user_first_events
WHERE first_click IS NOT NULL
GROUP BY campaign_id
ORDER BY total_users_who_clicked DESC;
```

---

## 3.3 Variant 3: Drop-Off Analysis — WHERE is the Biggest Leak?

**When to use**: Asked to identify which step loses the most users.

```sql
-- "Find the step with the highest absolute drop-off AND the step
--  with the worst conversion rate."

WITH user_flags AS (
    SELECT
        user_id,
        MAX(CASE WHEN event_type = 'impression'  THEN 1 ELSE 0 END) AS s1,
        MAX(CASE WHEN event_type = 'click'       THEN 1 ELSE 0 END) AS s2,
        MAX(CASE WHEN event_type = 'page_view'   THEN 1 ELSE 0 END) AS s3,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS s4,
        MAX(CASE WHEN event_type = 'purchase'    THEN 1 ELSE 0 END) AS s5
    FROM events GROUP BY user_id
),
funnel_counts AS (
    SELECT
        SUM(s1) AS step1, SUM(s2) AS step2, SUM(s3) AS step3,
        SUM(s4) AS step4, SUM(s5) AS step5
    FROM user_flags
),
-- Convert to rows for easier analysis (UNPIVOT the funnel)
funnel_steps AS (
    SELECT 1 AS step_num, 'Impression'  AS step_name, step1 AS users FROM funnel_counts UNION ALL
    SELECT 2,             'Click',                    step2           FROM funnel_counts UNION ALL
    SELECT 3,             'Page View',                step3           FROM funnel_counts UNION ALL
    SELECT 4,             'Add to Cart',              step4           FROM funnel_counts UNION ALL
    SELECT 5,             'Purchase',                 step5           FROM funnel_counts
)
SELECT
    step_num,
    step_name,
    users,
    LAG(users) OVER (ORDER BY step_num)                                 AS prev_step_users,
    LAG(users) OVER (ORDER BY step_num) - users                        AS users_dropped,
    ROUND(100.0 * SAFE_DIVIDE(
        users, LAG(users) OVER (ORDER BY step_num)), 2)                AS step_cvr_pct,
    ROUND(100.0 * (1 - SAFE_DIVIDE(
        users, LAG(users) OVER (ORDER BY step_num))), 2)               AS drop_off_pct,
    -- Rank: which step has worst conversion?
    RANK() OVER (ORDER BY SAFE_DIVIDE(
        users, LAG(users) OVER (ORDER BY step_num)) ASC)               AS worst_step_rank
FROM funnel_steps
ORDER BY step_num;

-- SAMPLE OUTPUT:
-- step | step_name    | users  | prev | dropped | cvr%  | dropoff% | rank
--  1   | Impression   | 10,000 | NULL |  NULL   | NULL  |  NULL    | NULL
--  2   | Click        |  2,000 | 10000|  8,000  | 20.0% |  80.0%   |  2
--  3   | Page View    |  1,200 |  2000|    800  | 60.0% |  40.0%   |  4
--  4   | Add to Cart  |    300 |  1200|    900  | 25.0% |  75.0%   |  3 ← worst cvr
--  5   | Purchase     |    120 |   300|    180  | 40.0% |  60.0%   |  (not meaningful with LAG)
-- INSIGHT: Click step has worst absolute drop-off (8,000 users lost)
--          Add to Cart has worst conversion rate (only 25%)
```

---

## 3.4 Variant 4: Funnel by Cohort / Segment

**When to use**: Compare funnel performance across different groups.

```sql
-- "Compare funnel conversion for new members vs returning members,
--  broken down by acquisition channel"

WITH user_flags AS (
    SELECT
        e.user_id,
        m.member_type,        -- 'new' or 'returning'
        m.acquisition_channel, -- 'google', 'meta', 'organic'
        MAX(CASE WHEN e.event_type = 'click'       THEN 1 ELSE 0 END) AS had_click,
        MAX(CASE WHEN e.event_type = 'page_view'   THEN 1 ELSE 0 END) AS had_view,
        MAX(CASE WHEN e.event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS had_cart,
        MAX(CASE WHEN e.event_type = 'purchase'    THEN 1 ELSE 0 END) AS had_purchase
    FROM events e
    JOIN dim_members m ON e.user_id = m.user_id
    WHERE e.event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY e.user_id, m.member_type, m.acquisition_channel
)
SELECT
    member_type,
    acquisition_channel,
    COUNT(*)                                                        AS total_users,
    SUM(had_click)                                                  AS clicks,
    SUM(had_cart)                                                   AS add_to_carts,
    SUM(had_purchase)                                               AS purchases,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase), COUNT(*)),     2)  AS overall_cvr_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(had_purchase), SUM(had_cart)), 2) AS cart_to_purchase_pct
FROM user_flags
GROUP BY member_type, acquisition_channel
ORDER BY member_type, overall_cvr_pct DESC;

-- INSIGHT PATTERN:
-- If new_member + google has 0.5% CVR but returning_member + google has 3.0% CVR:
-- Retargeting campaigns for existing members are 6x more efficient than prospecting.
-- Recommendation: increase retargeting budget, reduce prospecting spend.
```

---

## 3.5 Variant 5: Time-to-Complete Each Step (Funnel Velocity)

**When to use**: "How long does each step take on average? Where are users taking too long?"

```sql
-- Compute average time spent at each step before advancing to the next

WITH user_timestamps AS (
    SELECT
        user_id,
        MIN(CASE WHEN event_type = 'impression'  THEN event_time END) AS t1_impression,
        MIN(CASE WHEN event_type = 'click'       THEN event_time END) AS t2_click,
        MIN(CASE WHEN event_type = 'page_view'   THEN event_time END) AS t3_view,
        MIN(CASE WHEN event_type = 'add_to_cart' THEN event_time END) AS t4_cart,
        MIN(CASE WHEN event_type = 'purchase'    THEN event_time END) AS t5_purchase
    FROM events
    GROUP BY user_id
),
users_who_completed AS (
    -- Only users who went through ALL 5 steps in order
    SELECT *
    FROM user_timestamps
    WHERE t1_impression IS NOT NULL
      AND t2_click     >= t1_impression
      AND t3_view      >= t2_click
      AND t4_cart      >= t3_view
      AND t5_purchase  >= t4_cart
)
SELECT
    -- Time between each step (in minutes)
    ROUND(AVG(TIMESTAMP_DIFF(t2_click,    t1_impression, MINUTE)), 1) AS avg_min_impression_to_click,
    ROUND(AVG(TIMESTAMP_DIFF(t3_view,     t2_click,      MINUTE)), 1) AS avg_min_click_to_view,
    ROUND(AVG(TIMESTAMP_DIFF(t4_cart,     t3_view,       MINUTE)), 1) AS avg_min_view_to_cart,
    ROUND(AVG(TIMESTAMP_DIFF(t5_purchase, t4_cart,       MINUTE)), 1) AS avg_min_cart_to_purchase,
    ROUND(AVG(TIMESTAMP_DIFF(t5_purchase, t1_impression, MINUTE)), 1) AS avg_min_total_funnel,
    
    -- Percentiles: median and 90th percentile
    ROUND(PERCENTILE_CONT(
        TIMESTAMP_DIFF(t5_purchase, t1_impression, MINUTE), 0.5
    ) OVER (), 1) AS median_total_funnel_min,
    
    COUNT(*) AS users_who_completed_all_steps

FROM users_who_completed;

-- INSIGHT: If avg cart_to_purchase = 45 minutes, users are hesitating at checkout.
-- Trigger: send a "Don't forget to complete your order!" push notification after 30 minutes.
```

---

## 3.6 Variant 6: Funnel with Re-Entry (Users Can Restart)

**When to use**: A user can go through the funnel multiple times (e.g., multiple sessions, multiple purchase attempts).

```sql
-- Each session is an independent funnel entry.
-- Same user can be counted multiple times (once per session that starts with an impression).

WITH session_level AS (
    SELECT
        session_id,
        user_id,
        
        -- For each session: what was the DEEPEST step reached?
        MAX(CASE
            WHEN event_type = 'purchase'    THEN 5
            WHEN event_type = 'add_to_cart' THEN 4
            WHEN event_type = 'page_view'   THEN 3
            WHEN event_type = 'click'       THEN 2
            WHEN event_type = 'impression'  THEN 1
            ELSE 0
        END) AS deepest_step,
        
        -- Count of each event in session
        COUNTIF(event_type = 'impression')  AS impression_count,
        COUNTIF(event_type = 'click')       AS click_count,
        COUNTIF(event_type = 'page_view')   AS view_count,
        COUNTIF(event_type = 'add_to_cart') AS cart_count,
        COUNTIF(event_type = 'purchase')    AS purchase_count
        
    FROM events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY session_id, user_id
)
SELECT
    deepest_step,
    CASE deepest_step
        WHEN 1 THEN 'Impression only'
        WHEN 2 THEN 'Click (no view)'
        WHEN 3 THEN 'Page View (no cart)'
        WHEN 4 THEN 'Add to Cart (no purchase)'
        WHEN 5 THEN 'Purchased'
    END AS stage_name,
    COUNT(*)                                            AS session_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_sessions
FROM session_level
GROUP BY deepest_step
ORDER BY deepest_step DESC;

-- This shows: of ALL sessions, what % ended at each stage?
-- E.g., 60% of sessions end at "Impression only" (never clicked)
--        25% end at "Page View (no cart)"
--         5% actually purchased
```

---

## 3.7 Variant 7: Multi-Touch Funnel with Attribution

**When to use**: User went through MULTIPLE funnels (via different campaigns) before converting.

```sql
-- "Which campaign had the most users enter the funnel?
--  Which campaign had the last touch before purchase?"

WITH user_touchpoints AS (
    SELECT
        user_id,
        campaign_id,
        event_type,
        event_time,
        -- Tag first and last touchpoint per user
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time ASC)  AS touch_num_first,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time DESC) AS touch_num_last
    FROM events
    WHERE event_type IN ('impression', 'click', 'purchase')
),
user_funnel AS (
    SELECT
        user_id,
        -- First campaign user interacted with (first touch)
        MAX(CASE WHEN touch_num_first = 1 THEN campaign_id END) AS first_touch_campaign,
        -- Last campaign before purchase (last touch)
        MAX(CASE WHEN event_type = 'click' THEN campaign_id END) AS last_click_campaign,
        MAX(CASE WHEN event_type = 'purchase' THEN event_time END) AS purchase_time,
        MAX(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END) AS had_impression,
        MAX(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END) AS had_click,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS had_purchase
    FROM user_touchpoints
    GROUP BY user_id
)
SELECT
    last_click_campaign AS campaign_id,
    COUNT(*) AS users_entered_funnel,
    COUNTIF(had_purchase = 1) AS conversions,
    ROUND(100.0 * SAFE_DIVIDE(COUNTIF(had_purchase = 1), COUNT(*)), 2) AS cvr_pct
FROM user_funnel
WHERE had_click = 1
GROUP BY last_click_campaign
ORDER BY cvr_pct DESC;
```

---

# PART 4: COMMON MISTAKES AND HOW TO AVOID THEM

---

## 4.1 Mistake 1: Forgetting the Full Chain in Ordered Funnels

```sql
-- WRONG: Only checking adjacent steps
WHERE t_cart >= t_view    -- Only checks view → cart
  AND t_purchase >= t_cart -- Only checks cart → purchase
-- BUT: doesn't verify view >= click >= impression
-- A user who: viewed at 10:00, clicked at 10:30 (AFTER view!), carted at 11:00
-- Would PASS this check even though they skipped the correct order!

-- CORRECT: Check the ENTIRE chain
WHERE t_impression IS NOT NULL
  AND t_click      >= t_impression  -- click after impression
  AND t_view       >= t_click       -- view after click
  AND t_cart       >= t_view        -- cart after view
  AND t_purchase   >= t_cart        -- purchase after cart
```

---

## 4.2 Mistake 2: Using Unordered Funnel When Order is Required

```sql
-- WRONG for "ordered funnel" question:
MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS had_purchase
-- This just checks IF they purchased, not WHEN relative to other steps.
-- A user who purchased BEFORE clicking still gets had_purchase = 1.
-- The ordered funnel would incorrectly count them as converted.

-- CORRECT for ordered funnel:
MIN(CASE WHEN event_type = 'purchase' THEN event_time END) AS first_purchase
-- Then later:
COUNTIF(first_purchase IS NOT NULL AND first_purchase >= first_cart AND ...)
```

---

## 4.3 Mistake 3: Division by Zero Without SAFE_DIVIDE

```sql
-- WRONG: Will throw an error if impressions = 0
clicks / impressions * 100

-- CORRECT: Handle zero denominator
SAFE_DIVIDE(clicks, impressions) * 100      -- BigQuery: returns NULL if denominator = 0
NULLIF(impressions, 0)                      -- Standard SQL: clicks / NULLIF(impressions, 0)

-- Why NULL is better than 0:
-- If impressions = 0, we have NO DATA for that step, not a 0% conversion rate.
-- NULL correctly represents "unknown/no data" vs 0 which means "zero conversion."
```

---

## 4.4 Mistake 4: Counting Users vs Sessions vs Events

```sql
-- These are THREE DIFFERENT things and give THREE DIFFERENT answers:

-- USERS: each person counted ONCE regardless of how many times they visited
COUNT(DISTINCT user_id) -- 1,200 unique people clicked
-- Use for: "how many people clicked our ad?"

-- SESSIONS: each visit counted once, same user can appear multiple times
COUNT(DISTINCT session_id) -- 1,500 sessions had a click (same user clicked in 3 sessions = 3)
-- Use for: "how many ad click sessions did we have?"

-- EVENTS: every single click, including multiple clicks by same user in same session
COUNT(*) -- 1,800 click events (some users double-clicked)
-- Use for: "total number of clicks (for billing purposes)"

-- Funnel analysis almost always wants USERS (people who converted),
-- not events (which inflates numbers from power users).
-- When in doubt: COUNT(DISTINCT user_id), not COUNT(*)
```

---

## 4.5 Mistake 5: Not Filtering to Funnel-Eligible Users at the Start

```sql
-- WRONG: Computing funnel on ALL users, even those who never started the funnel
SELECT
    COUNT(*) AS total_users,  -- includes users who never saw an ad
    COUNTIF(had_click = 1) AS clicked
FROM user_flags
-- "total_users" = 10 million (all users in DB)
-- "clicked" = 500
-- "conversion rate" = 0.005% -- MEANINGLESSLY LOW
-- Most of those 10 million never even entered the funnel!

-- CORRECT: Start from users who entered the top of the funnel
SELECT
    COUNT(*) AS users_who_saw_ad,  -- only users with had_impression = 1
    COUNTIF(had_click = 1) AS clicked
FROM user_flags
WHERE had_impression = 1   -- ONLY users who started the funnel
-- Now: users_who_saw_ad = 100,000, clicked = 2,000
-- Click rate = 2% -- meaningful!
```

---

# PART 5: FUNNEL ANALYSIS IN BIGQUERY — ADVANCED PATTERNS

---

## 5.1 Funnel with COUNTIF (BigQuery Shorthand)

BigQuery has `COUNTIF` which is a cleaner shorthand for `COUNT(CASE WHEN ...)`:

```sql
-- Standard SQL (works everywhere):
COUNT(CASE WHEN had_purchase = 1 THEN 1 END) AS purchases

-- BigQuery shorthand (cleaner):
COUNTIF(had_purchase = 1) AS purchases

-- Full funnel using COUNTIF (BigQuery style):
SELECT
    campaign_id,
    COUNTIF(had_impression = 1) AS impressions,
    COUNTIF(had_click = 1)      AS clicks,
    COUNTIF(had_view = 1)       AS views,
    COUNTIF(had_cart = 1)       AS add_to_carts,
    COUNTIF(had_purchase = 1)   AS purchases,
    ROUND(100.0 * SAFE_DIVIDE(COUNTIF(had_click = 1),    COUNTIF(had_impression = 1)), 2) AS ctr_pct,
    ROUND(100.0 * SAFE_DIVIDE(COUNTIF(had_purchase = 1), COUNTIF(had_impression = 1)), 4) AS overall_cvr_pct
FROM user_flags
GROUP BY campaign_id
ORDER BY overall_cvr_pct DESC;
```

---

## 5.2 Funnel Presented as Rows (Better for Dashboards)

Sometimes the output is better as rows (one row per funnel step) rather than columns:

```sql
-- Output as rows for BI tool visualization (Looker bar chart of funnel)
WITH user_flags AS (
    SELECT
        user_id,
        campaign_id,
        MAX(CASE WHEN event_type = 'impression'  THEN 1 ELSE 0 END) AS s1,
        MAX(CASE WHEN event_type = 'click'       THEN 1 ELSE 0 END) AS s2,
        MAX(CASE WHEN event_type = 'page_view'   THEN 1 ELSE 0 END) AS s3,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS s4,
        MAX(CASE WHEN event_type = 'purchase'    THEN 1 ELSE 0 END) AS s5
    FROM events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY user_id, campaign_id
),
funnel_agg AS (
    SELECT
        campaign_id,
        SUM(s1) AS step1, SUM(s2) AS step2, SUM(s3) AS step3,
        SUM(s4) AS step4, SUM(s5) AS step5
    FROM user_flags
    GROUP BY campaign_id
)
-- Unpivot to rows using UNION ALL
SELECT campaign_id, 1 AS step_num, 'Impression'   AS step_name, step1 AS users FROM funnel_agg UNION ALL
SELECT campaign_id, 2,             'Click',                       step2          FROM funnel_agg UNION ALL
SELECT campaign_id, 3,             'Page View',                   step3          FROM funnel_agg UNION ALL
SELECT campaign_id, 4,             'Add to Cart',                 step4          FROM funnel_agg UNION ALL
SELECT campaign_id, 5,             'Purchase',                    step5          FROM funnel_agg
ORDER BY campaign_id, step_num;
```

---

## 5.3 Funnel with Running Total (Cumulative Users Remaining)

```sql
-- Show: at each step, how many users from the ORIGINAL cohort are still in the funnel?
-- This is different from step-to-step rates — it's absolute funnel shrinkage.

WITH funnel_counts AS (
    SELECT
        1 AS step, 'Impression' AS name, 10000 AS users UNION ALL
        SELECT 2, 'Click',        2000 UNION ALL
        SELECT 3, 'Page View',    1200 UNION ALL
        SELECT 4, 'Add to Cart',   300 UNION ALL
        SELECT 5, 'Purchase',      120
)
SELECT
    step,
    name,
    users,
    FIRST_VALUE(users) OVER (ORDER BY step)         AS top_of_funnel,
    ROUND(100.0 * users
          / FIRST_VALUE(users) OVER (ORDER BY step), 2) AS pct_of_original_cohort,
    LAG(users) OVER (ORDER BY step) - users         AS users_lost_at_this_step
FROM funnel_counts
ORDER BY step;

-- OUTPUT:
-- step | name        | users | top_of_funnel | pct_of_original | lost_here
--  1   | Impression  | 10000 |     10000     |    100.00%      |   NULL
--  2   | Click       |  2000 |     10000     |     20.00%      |   8000
--  3   | Page View   |  1200 |     10000     |     12.00%      |    800
--  4   | Add to Cart |   300 |     10000     |      3.00%      |    900
--  5   | Purchase    |   120 |     10000     |      1.20%      |    180
```

---

# PART 6: PRACTICE QUESTIONS WITH SOLUTIONS

---

## Practice Question 1 (Easy): Basic Funnel Count

**Question**: You have a table `app_events(user_id, event_type, event_date)`. Events include: `app_open`, `product_view`, `add_to_wishlist`, `purchase`. Write a query to show how many users reached each step of this funnel for the month of January 2024.

**Approach**: Simple unordered funnel. No strict ordering required — just whether each event type occurred.

```sql
WITH user_flags AS (
    SELECT
        user_id,
        MAX(CASE WHEN event_type = 'app_open'         THEN 1 ELSE 0 END) AS opened_app,
        MAX(CASE WHEN event_type = 'product_view'     THEN 1 ELSE 0 END) AS viewed_product,
        MAX(CASE WHEN event_type = 'add_to_wishlist'  THEN 1 ELSE 0 END) AS added_wishlist,
        MAX(CASE WHEN event_type = 'purchase'         THEN 1 ELSE 0 END) AS purchased
    FROM app_events
    WHERE event_date BETWEEN '2024-01-01' AND '2024-01-31'
    GROUP BY user_id
)
SELECT
    SUM(opened_app)    AS step1_app_opens,
    SUM(viewed_product) AS step2_product_views,
    SUM(added_wishlist) AS step3_wishlisted,
    SUM(purchased)     AS step4_purchases,

    ROUND(100.0 * SAFE_DIVIDE(SUM(viewed_product), SUM(opened_app)),  2) AS open_to_view_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(added_wishlist), SUM(viewed_product)), 2) AS view_to_wish_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(purchased),      SUM(added_wishlist)), 2) AS wish_to_buy_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(purchased),      SUM(opened_app)),   4) AS overall_cvr_pct
FROM user_flags;
```

---

## Practice Question 2 (Medium): Ordered Funnel — Find Users Who Completed in Sequence

**Question**: Table: `events(user_id, event_type, event_time)`. Find all users who: (1) clicked an ad, THEN (2) viewed the product page, THEN (3) purchased — in strict order. Return user_id and time taken from click to purchase.

**Approach**: Ordered funnel. Need MIN timestamps per event type, then check ordering.

```sql
WITH user_steps AS (
    SELECT
        user_id,
        MIN(CASE WHEN event_type = 'ad_click'      THEN event_time END) AS t_click,
        MIN(CASE WHEN event_type = 'product_view'  THEN event_time END) AS t_view,
        MIN(CASE WHEN event_type = 'purchase'      THEN event_time END) AS t_purchase
    FROM events
    GROUP BY user_id
)
SELECT
    user_id,
    t_click,
    t_view,
    t_purchase,
    ROUND(TIMESTAMP_DIFF(t_purchase, t_click, MINUTE), 1) AS minutes_click_to_purchase
FROM user_steps
WHERE
    -- All three steps occurred
    t_click    IS NOT NULL
    AND t_view     IS NOT NULL
    AND t_purchase IS NOT NULL
    -- AND in the correct order
    AND t_view     >= t_click
    AND t_purchase >= t_view
ORDER BY minutes_click_to_purchase ASC;
```

---

## Practice Question 3 (Medium): Funnel Drop-Off Rate Per Campaign

**Question**: Table: `ad_events(user_id, campaign_id, event_type, event_time)`. For each campaign, compute the funnel conversion at each step and identify which campaign has the highest drop-off at the "Add to Cart" step.

```sql
WITH user_campaign_flags AS (
    SELECT
        user_id,
        campaign_id,
        MAX(CASE WHEN event_type = 'impression'   THEN 1 ELSE 0 END) AS s1,
        MAX(CASE WHEN event_type = 'click'        THEN 1 ELSE 0 END) AS s2,
        MAX(CASE WHEN event_type = 'page_view'    THEN 1 ELSE 0 END) AS s3,
        MAX(CASE WHEN event_type = 'add_to_cart'  THEN 1 ELSE 0 END) AS s4,
        MAX(CASE WHEN event_type = 'purchase'     THEN 1 ELSE 0 END) AS s5
    FROM ad_events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY user_id, campaign_id
),
campaign_funnel AS (
    SELECT
        campaign_id,
        COUNT(*) AS total_users,
        SUM(s1) AS impressions,
        SUM(s2) AS clicks,
        SUM(s3) AS page_views,
        SUM(s4) AS add_to_carts,
        SUM(s5) AS purchases
    FROM user_campaign_flags
    WHERE s1 = 1   -- only users who entered the funnel (had an impression)
    GROUP BY campaign_id
)
SELECT
    campaign_id,
    impressions,
    clicks,
    page_views,
    add_to_carts,
    purchases,

    -- Focus: view to cart conversion (the "Add to Cart" step drop-off)
    ROUND(100.0 * SAFE_DIVIDE(add_to_carts, page_views), 2)   AS view_to_cart_pct,
    100 - ROUND(100.0 * SAFE_DIVIDE(add_to_carts, page_views), 2) AS view_to_cart_dropoff_pct,

    -- Rank by worst view-to-cart rate (highest drop-off = worst performance)
    RANK() OVER (ORDER BY SAFE_DIVIDE(add_to_carts, page_views) ASC) AS worst_cart_rank

FROM campaign_funnel
WHERE page_views >= 100   -- statistical significance: at least 100 page views
ORDER BY view_to_cart_dropoff_pct DESC;
```

---

## Practice Question 4 (Hard): Funnel Within Time Window + Cohort Comparison

**Question**: Table: `events(user_id, event_type, event_time, channel)`. Compare 30-day funnel conversion (click → purchase within 30 days) for users acquired via `google_search` vs `meta_social`. Only include users whose first ever event was in Q1 2024 (new users only).

```sql
-- Step 1: Find new users (first event in Q1 2024)
WITH new_users AS (
    SELECT
        user_id,
        MIN(event_time) AS first_event_time,
        -- Acquisition channel = channel of their FIRST event
        FIRST_VALUE(channel) OVER (
            PARTITION BY user_id ORDER BY event_time ASC
        ) AS acquisition_channel
    FROM events
    GROUP BY user_id
    HAVING DATE(MIN(event_time)) BETWEEN '2024-01-01' AND '2024-03-31'
),

-- Step 2: For each new user, get funnel timestamps
user_funnel AS (
    SELECT
        e.user_id,
        nu.acquisition_channel,
        MIN(CASE WHEN e.event_type = 'click'    THEN e.event_time END) AS t_click,
        MIN(CASE WHEN e.event_type = 'purchase' THEN e.event_time END) AS t_purchase
    FROM events e
    JOIN new_users nu ON e.user_id = nu.user_id
    WHERE nu.acquisition_channel IN ('google_search', 'meta_social')
    GROUP BY e.user_id, nu.acquisition_channel
),

-- Step 3: Apply 30-day window constraint
funnel_with_window AS (
    SELECT
        user_id,
        acquisition_channel,
        t_click,
        t_purchase,
        CASE
            WHEN t_click IS NOT NULL
             AND t_purchase IS NOT NULL
             AND t_purchase >= t_click
             AND TIMESTAMP_DIFF(t_purchase, t_click, DAY) <= 30
            THEN 1 ELSE 0
        END AS converted_within_30d
    FROM user_funnel
)

-- Step 4: Compare by channel
SELECT
    acquisition_channel,
    COUNT(*)                                                    AS total_new_users,
    COUNTIF(t_click IS NOT NULL)                                AS users_who_clicked,
    COUNTIF(converted_within_30d = 1)                           AS converted_30d,
    ROUND(100.0 * SAFE_DIVIDE(
        COUNTIF(t_click IS NOT NULL), COUNT(*)), 2)             AS click_rate_pct,
    ROUND(100.0 * SAFE_DIVIDE(
        COUNTIF(converted_within_30d = 1),
        COUNTIF(t_click IS NOT NULL)), 2)                       AS click_to_purchase_30d_pct,
    ROUND(AVG(CASE WHEN converted_within_30d = 1
        THEN TIMESTAMP_DIFF(t_purchase, t_click, HOUR) END), 1) AS avg_hours_to_convert
FROM funnel_with_window
GROUP BY acquisition_channel
ORDER BY click_to_purchase_30d_pct DESC;
```

---

## Practice Question 5 (Very Hard): Multi-Level Funnel with Re-Entry and Attribution

**Question**: Table: `events(event_id, user_id, session_id, campaign_id, event_type, event_time)`. A user can have multiple sessions and enter the funnel multiple times. Write a query that:
1. Counts converting sessions (sessions that ended in purchase) vs non-converting
2. For converting sessions, shows which step had the longest average time
3. Attributes the conversion to the campaign from the LAST click before purchase

```sql
-- Step 1: Compute per-session funnel
WITH session_events AS (
    SELECT
        session_id,
        user_id,
        -- Last campaign clicked in this session
        MAX(CASE WHEN event_type = 'click' THEN campaign_id END) AS last_clicked_campaign,

        -- First timestamp of each step within session
        MIN(CASE WHEN event_type = 'impression'  THEN event_time END) AS t1,
        MIN(CASE WHEN event_type = 'click'       THEN event_time END) AS t2,
        MIN(CASE WHEN event_type = 'page_view'   THEN event_time END) AS t3,
        MIN(CASE WHEN event_type = 'add_to_cart' THEN event_time END) AS t4,
        MIN(CASE WHEN event_type = 'purchase'    THEN event_time END) AS t5,

        -- Deepest ordered step reached
        MAX(CASE
            WHEN event_type = 'purchase'    THEN 5
            WHEN event_type = 'add_to_cart' THEN 4
            WHEN event_type = 'page_view'   THEN 3
            WHEN event_type = 'click'       THEN 2
            WHEN event_type = 'impression'  THEN 1
        END) AS deepest_step

    FROM events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY session_id, user_id
),

-- Step 2: Classify sessions and compute step timings
session_classified AS (
    SELECT
        session_id,
        user_id,
        last_clicked_campaign,
        deepest_step,

        -- Is this session a converting session?
        CASE WHEN t5 IS NOT NULL AND t5 >= t4 AND t4 >= t3 AND t3 >= t2 THEN 1 ELSE 0 END
            AS is_converting_session,

        -- Time at each step (minutes)
        TIMESTAMP_DIFF(t2, t1, MINUTE) AS min_impression_to_click,
        TIMESTAMP_DIFF(t3, t2, MINUTE) AS min_click_to_view,
        TIMESTAMP_DIFF(t4, t3, MINUTE) AS min_view_to_cart,
        TIMESTAMP_DIFF(t5, t4, MINUTE) AS min_cart_to_purchase
    FROM session_events
    WHERE t1 IS NOT NULL   -- must have entered the funnel
),

-- Step 3: Summary stats
summary AS (
    SELECT
        COUNTIF(is_converting_session = 1)   AS converting_sessions,
        COUNTIF(is_converting_session = 0)   AS non_converting_sessions,
        COUNT(*)                             AS total_sessions,
        ROUND(100.0 * SAFE_DIVIDE(
            COUNTIF(is_converting_session = 1), COUNT(*)), 2) AS session_cvr_pct,

        -- Average step timing FOR CONVERTING SESSIONS only
        ROUND(AVG(CASE WHEN is_converting_session = 1 THEN min_impression_to_click END), 1) AS avg_imp_to_click,
        ROUND(AVG(CASE WHEN is_converting_session = 1 THEN min_click_to_view END),       1) AS avg_click_to_view,
        ROUND(AVG(CASE WHEN is_converting_session = 1 THEN min_view_to_cart END),        1) AS avg_view_to_cart,
        ROUND(AVG(CASE WHEN is_converting_session = 1 THEN min_cart_to_purchase END),    1) AS avg_cart_to_purch
    FROM session_classified
),

-- Step 4: Attribution — which campaign gets credit for converting sessions?
campaign_attribution AS (
    SELECT
        last_clicked_campaign AS campaign_id,
        COUNT(*) AS attributed_conversions
    FROM session_classified
    WHERE is_converting_session = 1
      AND last_clicked_campaign IS NOT NULL
    GROUP BY last_clicked_campaign
)

-- Final output
SELECT
    s.*,
    ca.campaign_id AS top_attributed_campaign,
    ca.attributed_conversions
FROM summary s
CROSS JOIN (
    SELECT campaign_id, attributed_conversions
    FROM campaign_attribution
    ORDER BY attributed_conversions DESC
    LIMIT 1
) ca;
```

---

# PART 7: INTERVIEW QUESTIONS AND ANSWERS

---

## EASY

### Q1: "What is a funnel in SQL and why is it used?"

**Answer**: A funnel tracks how users move through a sequence of steps toward a goal, measuring how many complete each step and where they drop off.

In data engineering, you build funnel analysis in SQL to answer business questions like: "We sent 100,000 people to our website from ads. Only 120 bought something. Where did the other 99,880 go?" The funnel tells you: 98% never clicked, of those who clicked 40% never viewed the page, of those who viewed 75% never added to cart. Now you know EXACTLY which step to fix.

The core SQL technique is conditional aggregation: `MAX(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END)` per user, then summing across users to get counts per step, then dividing adjacent steps to get conversion rates.

---

### Q2: "When should you use an ordered funnel vs an unordered funnel?"

**Answer**: Use an unordered funnel when you just want to know IF a user performed each event, regardless of sequence — for example, "how many users saw an ad AND purchased in the same session?" The sequence doesn't matter.

Use an ordered funnel when the business logic requires steps in sequence — for example, "users who clicked an ad THEN viewed the page THEN purchased." If a user purchased before clicking, that shouldn't count as a funnel conversion. For ordered funnels, I capture `MIN(event_time)` per step per user and then check that each timestamp is greater than or equal to the previous one.

In real-world ad analytics, ordered funnels are almost always more correct — a purchase that happened before a click can't be attributed to that click.

---

## MEDIUM

### Q3: "Write a SQL query to compute funnel conversion at each step for an e-commerce site. Table: events(user_id, event_type, event_time). Steps: page_view → add_to_cart → checkout_start → purchase."

**Approach to state before writing**: *"This is an ordered funnel — each step must happen after the previous. I'll use MIN timestamps per step, check the ordering chain, and compute step-to-step rates."*

```sql
WITH user_steps AS (
    SELECT
        user_id,
        MIN(CASE WHEN event_type = 'page_view'       THEN event_time END) AS t_view,
        MIN(CASE WHEN event_type = 'add_to_cart'     THEN event_time END) AS t_cart,
        MIN(CASE WHEN event_type = 'checkout_start'  THEN event_time END) AS t_checkout,
        MIN(CASE WHEN event_type = 'purchase'        THEN event_time END) AS t_purchase
    FROM events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY user_id
)
SELECT
    COUNTIF(t_view IS NOT NULL)                                                AS step1_views,
    COUNTIF(t_cart IS NOT NULL     AND t_cart     >= t_view)                   AS step2_carts,
    COUNTIF(t_checkout IS NOT NULL AND t_checkout >= t_cart AND t_cart >= t_view) AS step3_checkouts,
    COUNTIF(t_purchase IS NOT NULL AND t_purchase >= t_checkout
            AND t_checkout >= t_cart AND t_cart >= t_view)                     AS step4_purchases,

    ROUND(100.0 * SAFE_DIVIDE(
        COUNTIF(t_cart IS NOT NULL AND t_cart >= t_view),
        COUNTIF(t_view IS NOT NULL)), 2)                                       AS view_to_cart_pct,
    ROUND(100.0 * SAFE_DIVIDE(
        COUNTIF(t_purchase IS NOT NULL AND t_purchase >= t_checkout
                AND t_checkout >= t_cart AND t_cart >= t_view),
        COUNTIF(t_view IS NOT NULL)), 4)                                       AS overall_cvr_pct
FROM user_steps;
```

---

### Q4: "A marketing analyst says campaign A has a 3% overall funnel conversion rate and campaign B has a 1% rate. Should we cut campaign B? What SQL would you write to investigate further?"

**Answer**: Not necessarily — the overall rate doesn't tell you WHY. I'd look at where each campaign's funnel breaks. Maybe campaign B has great CTR but poor landing page. Maybe campaign A converts well because it targets existing members, not because it's genuinely more effective at acquiring new users.

```sql
-- Compare funnel step-by-step between campaigns
WITH user_campaign_flags AS (
    SELECT
        user_id, campaign_id,
        MAX(CASE WHEN event_type = 'impression'   THEN 1 ELSE 0 END) AS s1,
        MAX(CASE WHEN event_type = 'click'        THEN 1 ELSE 0 END) AS s2,
        MAX(CASE WHEN event_type = 'page_view'    THEN 1 ELSE 0 END) AS s3,
        MAX(CASE WHEN event_type = 'add_to_cart'  THEN 1 ELSE 0 END) AS s4,
        MAX(CASE WHEN event_type = 'purchase'     THEN 1 ELSE 0 END) AS s5
    FROM events GROUP BY user_id, campaign_id
)
SELECT
    campaign_id,
    SUM(s1) AS impressions, SUM(s2) AS clicks,
    SUM(s3) AS views, SUM(s4) AS carts, SUM(s5) AS purchases,
    ROUND(100.0 * SAFE_DIVIDE(SUM(s2), SUM(s1)), 2) AS ctr_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(s3), SUM(s2)), 2) AS click_to_view_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(s4), SUM(s3)), 2) AS view_to_cart_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(s5), SUM(s4)), 2) AS cart_to_purchase_pct,
    ROUND(100.0 * SAFE_DIVIDE(SUM(s5), SUM(s1)), 4) AS overall_cvr_pct
FROM user_campaign_flags WHERE s1 = 1
GROUP BY campaign_id
ORDER BY campaign_id;
```

*"If campaign B has 8% CTR (higher than A's 4%) but 5% view-to-cart (vs A's 20%), the problem is the landing page experience for B's audience — not the campaign itself. Cutting B loses those high-CTR users. The fix is A/B testing the landing page for B's audience."*

---

## HARD

### Q5: "You have a 3-step funnel. Users can restart the funnel (multiple sessions). Your analyst reports that funnel conversion is 5%, but feels too high. What could cause inflation and how would you detect it?"

**Answer**: Several patterns can inflate funnel conversion:

**Inflation cause 1: Counting users who converted before entering the funnel**

A user who already purchased yesterday comes back today and views a product. In an unordered funnel, they'd show as "had_purchase = 1" even though the purchase had nothing to do with today's impression. Fix: use ordered funnel with time constraints — purchase must happen AFTER the impression, and within a reasonable window.

```sql
-- Check: how many "conversions" have purchase BEFORE first click?
SELECT COUNT(*) AS suspiciously_backwards
FROM user_timestamps
WHERE t_purchase < t_click   -- purchased before clicking — shouldn't count
```

**Inflation cause 2: Attributing returning members as "funnel conversions"**

If your funnel includes all purchases and you run an impression campaign, existing members who would have purchased anyway get counted as funnel conversions. True incrementality requires a holdout group.

```sql
-- Check: what % of "converted" users already had prior purchases?
SELECT
    COUNTIF(prior_purchase_count > 0) AS returning_buyers,
    COUNTIF(prior_purchase_count = 0) AS new_buyers,
    ROUND(100.0 * SAFE_DIVIDE(COUNTIF(prior_purchase_count > 0),
          COUNT(*)), 2) AS pct_returning
FROM user_funnel_conversion_results
JOIN (SELECT user_id, COUNT(*) AS prior_purchase_count
      FROM purchases WHERE purchase_date < funnel_start_date
      GROUP BY user_id) USING (user_id);
```

**Inflation cause 3: Duplicate events causing same user to be counted twice**

If event deduplication is not applied before the funnel, a user with 2 duplicate click events might appear in the funnel calculation twice.

```sql
-- Check: are there duplicate event_ids?
SELECT COUNT(*) - COUNT(DISTINCT event_id) AS duplicate_events
FROM events
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);
```

---

## VERY HARD

### Q6: "Design a complete SQL-based funnel analysis system for Costco's MarTech team. Requirements: daily automated funnel report across 5 channels and 3 member segments, identifies statistically significant drops in conversion rates vs prior week, and flags the specific step and channel that degraded."

**Answer**:

*"I'd build this in 4 layers as a DBT project: raw events → user funnel flags → daily funnel metrics → anomaly detection with statistical significance."*

```sql
-- LAYER 1: user_funnel_daily (one row per user per day per channel)
-- (DBT incremental model, partition by event_date)

CREATE TABLE mart_user_funnel_daily AS
WITH user_channel_flags AS (
    SELECT
        DATE(event_time) AS event_date,
        user_id,
        channel,
        member_segment,    -- 'new', 'gold', 'executive'
        MIN(CASE WHEN event_type = 'impression'   THEN event_time END) AS t1,
        MIN(CASE WHEN event_type = 'click'        THEN event_time END) AS t2,
        MIN(CASE WHEN event_type = 'page_view'    THEN event_time END) AS t3,
        MIN(CASE WHEN event_type = 'add_to_cart'  THEN event_time END) AS t4,
        MIN(CASE WHEN event_type = 'purchase'     THEN event_time END) AS t5
    FROM events e
    JOIN dim_members m USING (user_id)
    GROUP BY 1, 2, 3, 4
)
SELECT
    event_date,
    channel,
    member_segment,
    -- Ordered funnel counts
    COUNTIF(t1 IS NOT NULL) AS s1,
    COUNTIF(t2 >= t1 AND t2 IS NOT NULL) AS s2,
    COUNTIF(t3 >= t2 AND t2 >= t1 AND t3 IS NOT NULL) AS s3,
    COUNTIF(t4 >= t3 AND t3 >= t2 AND t2 >= t1 AND t4 IS NOT NULL) AS s4,
    COUNTIF(t5 >= t4 AND t4 >= t3 AND t3 >= t2 AND t2 >= t1 AND t5 IS NOT NULL) AS s5
FROM user_channel_flags
GROUP BY event_date, channel, member_segment;

-- LAYER 2: Anomaly detection with WoW comparison and Z-score
WITH current_week AS (
    SELECT channel, member_segment,
           SUM(s1) AS s1, SUM(s2) AS s2, SUM(s3) AS s3, SUM(s4) AS s4, SUM(s5) AS s5,
           SAFE_DIVIDE(SUM(s2), SUM(s1)) AS ctr,
           SAFE_DIVIDE(SUM(s3), SUM(s2)) AS ctvr,
           SAFE_DIVIDE(SUM(s4), SUM(s3)) AS vcar,
           SAFE_DIVIDE(SUM(s5), SUM(s4)) AS capr
    FROM mart_user_funnel_daily
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY 1, 2
),
prior_week AS (
    SELECT channel, member_segment,
           SAFE_DIVIDE(SUM(s2), SUM(s1)) AS ctr_pw,
           SAFE_DIVIDE(SUM(s3), SUM(s2)) AS ctvr_pw,
           SAFE_DIVIDE(SUM(s4), SUM(s3)) AS vcar_pw,
           SAFE_DIVIDE(SUM(s5), SUM(s4)) AS capr_pw
    FROM mart_user_funnel_daily
    WHERE event_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
                         AND DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY 1, 2
)
SELECT
    c.channel,
    c.member_segment,
    -- Step rates and WoW change
    ROUND(c.ctr  * 100, 2) AS ctr_pct,
    ROUND(c.vcar * 100, 2) AS view_to_cart_pct,
    ROUND(c.capr * 100, 2) AS cart_to_purchase_pct,
    -- Biggest degradation (which step is worst WoW?)
    ROUND((c.ctr  - p.ctr_pw)  / NULLIF(p.ctr_pw,  0) * 100, 2) AS ctr_wow_chg_pct,
    ROUND((c.vcar - p.vcar_pw) / NULLIF(p.vcar_pw, 0) * 100, 2) AS vcar_wow_chg_pct,
    ROUND((c.capr - p.capr_pw) / NULLIF(p.capr_pw, 0) * 100, 2) AS capr_wow_chg_pct,
    -- Flag: is any step down > 20% WoW? (alert threshold)
    CASE
        WHEN (c.ctr - p.ctr_pw) / NULLIF(p.ctr_pw, 0) < -0.20
            THEN 'ALERT: CTR dropped >20% WoW'
        WHEN (c.vcar - p.vcar_pw) / NULLIF(p.vcar_pw, 0) < -0.20
            THEN 'ALERT: View→Cart dropped >20% WoW'
        WHEN (c.capr - p.capr_pw) / NULLIF(p.capr_pw, 0) < -0.20
            THEN 'ALERT: Cart→Purchase dropped >20% WoW'
        ELSE 'Normal'
    END AS alert_status
FROM current_week c
JOIN prior_week p USING (channel, member_segment)
ORDER BY
    CASE WHEN alert_status != 'Normal' THEN 0 ELSE 1 END,
    channel;
```

*"This system: runs daily as a DBT job, covers all 5 channels × 3 segments = 15 combinations, computes step-by-step rates, compares to prior week, and flags any step that dropped >20% with the exact step name and channel. The marketing team can act on 'ALERT: View→Cart dropped >20% on meta_social for gold_members' by investigating the landing page experience for that specific combination."*

---

# FINAL CHEAT SHEET: FUNNEL SQL PATTERN RECOGNITION

```
WHEN THE QUESTION SAYS:           WHAT TO DO:
──────────────────────────────────────────────────────────────────────────────
"How many users did each step"    → MAX(CASE WHEN event_type='X' THEN 1) per user
                                    SUM() across users
                                    
"Steps must happen in order"      → MIN(CASE WHEN event_type='X' THEN event_time)
                                    Check: each timestamp >= prior timestamp
                                    
"Within N days/hours"             → TIMESTAMP_DIFF(t_later, t_earlier, DAY) <= N
                                    
"By campaign/channel/segment"     → Add GROUP BY dimension to user_flags CTE
                                    
"Where is the biggest drop-off"   → UNPIVOT funnel to rows → LAG() to find drop
                                    RANK() by (1 - cvr) to find worst step
                                    
"How long does each step take"    → TIMESTAMP_DIFF between consecutive timestamps
                                    AVG only for users who completed the full funnel
                                    
"Multi-session, user re-enters"   → GROUP BY session_id instead of user_id
                                    
"Which campaign converted most"   → Last click before purchase = attributed campaign
                                    
"Detect conversion rate drop"     → LAG(cvr, 7) OVER (ORDER BY date) = last week
                                    (current - prior) / prior * 100 = % change
                                    Alert if < -20%

THE 3-STEP RECIPE FOR ANY FUNNEL QUESTION:
  Step 1: Build per-user (or per-session) flags CTE
          → MAX(CASE WHEN) for unordered
          → MIN(CASE WHEN) for ordered
  Step 2: COUNTIF / SUM flags to get funnel counts
  Step 3: SAFE_DIVIDE adjacent steps for conversion rates
  
ALWAYS REMEMBER:
  → Filter to funnel-entrants only (WHERE s1 = 1)
  → Use SAFE_DIVIDE not raw division (handles zero denominators)
  → Count DISTINCT users, not events (unless events are specifically asked for)
  → For ordered: check FULL chain at each step, not just adjacent pair
```
