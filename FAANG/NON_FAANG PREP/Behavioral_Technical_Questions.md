# Behavioral & Technical Interview Questions

How to answer behavioral questions that data engineers encounter.

---

## Behavioral Questions (1-10)

### Q1: "Tell me about a time you faced a production issue"

**Situation:** Describe the context
"At Wells Fargo, I was managing a large-scale data migration from Teradata to BigQuery serving 60+ teams..."

**Complication:** What went wrong
"During migration, query performance degraded 10x. Users reported 5-minute query timeouts vs previous 30 seconds..."

**Action:** What did you do
"I analyzed the execution plans and found:
1. Queries doing full table scans instead of partition pruning
2. Missing clustering on frequently filtered columns
3. SELECT * instead of specific columns

I implemented:
- Added DATE partitioning with partition pruning in queries
- Added clustering on user_id and category (most filtered columns)
- Updated 200+ queries to select only needed columns
- Created materialized views for common aggregations"

**Result:** What was the outcome
"Reduced query latency from 5 minutes to 10 seconds (99.9% improvement). User satisfaction increased. Saved company ~$500K annually on query costs through optimization."

**Learning:** What did you learn
"I learned the importance of understanding execution plans deeply and optimizing from first principles. I also improved my communication with stakeholders about technical tradeoffs."

---

### Q2: "Describe a time you had to learn something new quickly"

Structure: STAR method with emphasis on learning

"Challenge: New job required PySpark but I only knew Python
Action: 
- Spent 2 weeks learning PySpark fundamentals
- Built 3 progressively complex projects
- Collaborated with team members for code reviews
Result: Within 4 weeks, led implementation of new PySpark-based ETL pipeline
Processing 10TB of data daily, 99.9% uptime"

---

### Q3: "Tell me about a project where you disagreed with your team"

"Situation: Team wanted to use traditional Hadoop/Hive for new pipeline. I proposed BigQuery.

Disagreement: 
- Team: Cost concerns (1M per month vs Hadoop $200K)
- Me: TCO analysis showed BigQuery better

Resolution:
- I created proof of concept with sample data
- Demonstrated query speed (10x faster)
- Showed operational complexity reduction
- Provided cost analysis: includes data scientists' time saved

Outcome: Team agreed. 2-year savings: $3M+ with better performance."

---

### Q4: "Describe your biggest failure"

"Challenge: Designed data pipeline that failed under 10x load growth
Analysis:
- Architecture couldn't handle concurrent writes
- Lack of load testing before deployment

Actions Taken:
- Implemented horizontal scaling with partitioning
- Added circuit breakers and rate limiting
- Created comprehensive load testing suite
- Documented lessons learned

Growth:
- Now handles 100x original load
- Zero production incidents since fix
- Created standards for all future pipelines"

---

### Q5: "How do you approach a complex problem?"

1. **Understand the problem**
   - Ask clarifying questions
   - Identify constraints and requirements
   - Define success metrics

2. **Break it down**
   - Decompose into smaller subproblems
   - Identify dependencies
   - Prioritize

3. **Design the solution**
   - Research options
   - Compare tradeoffs
   - Choose best approach

4. **Implement and test**
   - Write clean, testable code
   - Test edge cases
   - Document

5. **Monitor and improve**
   - Set up monitoring
   - Collect feedback
   - Iterate

Example: "When designing the 40PB migration, I..."

---

### Q6: "How do you handle pressure?"

Good Answer: "I focus on clear communication and breaking problems into manageable pieces. During urgent issues, I:
- Stay calm and systematic
- Communicate status regularly
- Prioritize fixes by impact
- Involve team for faster resolution
- Document for future prevention"

Avoid: "I work extra hard" or "I stay late" - companies want sustainable approaches

---

### Q7: "What's your greatest strength?"

Related to your work: "I excel at breaking down complex systems into understandable components. I enjoy finding optimization opportunities - like the 99.9% query latency improvement. This strength helps me architect scalable systems and communicate technical complexity to non-technical stakeholders."

---

### Q8: "What area do you want to improve?"

Good: "I want to deepen my distributed systems knowledge, particularly around consistency models. I'm taking an online course and implementing a mini distributed cache to understand tradeoffs better."

Bad: "I'm bad at timelines" or negative traits

---

### Q9: "Why do you want to work here?"

Research the company:
- Their tech stack
- Scale of problems
- Company culture
- Your growth opportunity

Answer: "I'm attracted to [Company] because:
1. You process petabytes of data - exactly the scale problems I enjoy
2. Your focus on developer productivity aligns with my values
3. Opportunity to work with cutting-edge technologies like BigQuery/Dataflow
4. I can contribute experience from large-scale migrations
5. Chance to grow into staff engineer role"

---

### Q10: "Do you have any questions for us?"

Ask intelligent questions:
- "What do you see as the biggest data engineering challenge?"
- "How do you approach hiring in this team?"
- "What does success look like in this role after 6 months/1 year?"
- "What's the biggest mistake the team made and what did you learn?"

Avoid: "What are the benefits?" (research this yourself)

---

## Follow-up Technical Questions

### After STAR: They may ask depth questions

**Scenario: You said you optimized queries**
- "How exactly did you identify the bottleneck?"
- "Walk me through the query plan"
- "What other optimization techniques did you try?"
- "Why didn't you use approach X?"

**Preparation:**
- Know your project deeply
- Understand all technical decisions
- Be ready to explain tradeoffs
- Have numbers ready (latency, cost, throughput)

---

## Interview Day Tips

✅ **Before:**
- Research the company and team
- Practice STAR method
- Prepare 5-7 stories with metrics
- Get good sleep

✅ **During:**
- Be authentic - don't oversell
- Use specific numbers and metrics
- Show learning mindset
- Ask thoughtful questions

✅ **Communication:**
- Speak clearly and confidently
- Explain technical concepts simply
- Listen carefully to questions
- Don't interrupt

---

