# Python DSA Interview Questions - Non-FAANG Level

Comprehensive collection of Data Structures & Algorithms problems for Non-FAANG interviews.

## Table of Contents
- [Easy Questions (1-12)](#easy-questions-1-12)
- [Medium Questions (13-28)](#medium-questions-13-28)
- [Hard Questions (29-40)](#hard-questions-29-40)

---

# EASY QUESTIONS (1-12)

## Question 1: Two Sum

**Difficulty:** Easy  
**LeetCode:** #1  
**Time:** 10 minutes  
**Companies:** Google, Amazon, Apple

### Problem Statement
Given an array of integers `nums` and an integer `target`, return the indices of the two numbers that add up to the target.

```
Input: nums = [2, 7, 11, 15], target = 9
Output: [0, 1]
Explanation: nums[0] + nums[1] = 2 + 7 = 9
```

### Approach 1: Brute Force
- Time: O(n²)
- Space: O(1)

```python
def twoSum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
```

### Approach 2: Hash Map (Optimal)
- Time: O(n)
- Space: O(n)

```python
def twoSum(nums, target):
    # Store value -> index mapping
    seen = {}
    
    for i, num in enumerate(nums):
        complement = target - num
        
        # Check if complement already seen
        if complement in seen:
            return [seen[complement], i]
        
        # Store current number
        seen[num] = i
    
    return []
```

### Solution (Best Approach)

```python
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        """
        Use hash map for O(n) solution
        """
        num_map = {}
        
        for i, num in enumerate(nums):
            complement = target - num
            
            if complement in num_map:
                return [num_map[complement], i]
            
            num_map[num] = i
        
        return []
```

### Complexity Analysis
- Time: O(n)
- Space: O(n)

### Key Points
✅ Hash map is key for optimization
✅ One pass through array
✅ Return indices, not values
✅ Handle duplicates

### Follow-up 1: What if no solution exists?
Return empty list or [-1, -1]

### Follow-up 2: Can you do it with sorted array?
```python
def twoSum(nums, target):
    # Use two pointers on sorted array
    sorted_nums = sorted(enumerate(nums), key=lambda x: x[1])
    left, right = 0, len(sorted_nums) - 1
    
    while left < right:
        s = sorted_nums[left][1] + sorted_nums[right][1]
        if s == target:
            return [sorted_nums[left][0], sorted_nums[right][0]]
        elif s < target:
            left += 1
        else:
            right -= 1
    
    return []
```

### Common Mistakes
❌ Forgetting to return indices not values
❌ Returning same index twice
❌ Not checking if complement exists before access

### Real Interview Scenario
"You have array [2,7,11,15] and target 9. Find two numbers that add up."
- Ask: Can array have duplicates? Negative numbers?
- Clarify: Return indices or values?
- State approach before coding

---

## Question 2: Valid Parentheses

**Difficulty:** Easy  
**LeetCode:** #20  
**Time:** 10 minutes

### Problem
Determine if string has valid matching parentheses.

```
Input: s = "()[]{}"
Output: true

Input: s = "([)]"
Output: false
```

### Solution

```python
class Solution:
    def isValid(self, s: str) -> bool:
        stack = []
        mapping = {'(': ')', '[': ']', '{': '}'}
        
        for char in s:
            if char in mapping:
                stack.append(char)
            else:
                if not stack or mapping[stack.pop()] != char:
                    return False
        
        return len(stack) == 0
```

### Key Points
✅ Use stack for matching pairs
✅ Push opening brackets
✅ Match closing with top of stack
✅ Final check: stack empty

---

## Question 3: Contains Duplicate

**Difficulty:** Easy

### Solution

```python
def containsDuplicate(nums):
    return len(nums) != len(set(nums))
```

Or with early exit:

```python
def containsDuplicate(nums):
    seen = set()
    for num in nums:
        if num in seen:
            return True
        seen.add(num)
    return False
```

---

## Question 4: Best Time to Buy Stock

**Difficulty:** Easy

### Problem
Find max profit from single buy-sell transaction.

### Solution

```python
def maxProfit(prices):
    min_price = float('inf')
    max_profit = 0
    
    for price in prices:
        max_profit = max(max_profit, price - min_price)
        min_price = min(min_price, price)
    
    return max_profit
```

---

## Question 5: Majority Element

**Difficulty:** Easy

### Solution (Boyer-Moore Voting)

```python
def majorityElement(nums):
    candidate = None
    count = 0
    
    for num in nums:
        if count == 0:
            candidate = num
        count += 1 if num == candidate else -1
    
    return candidate
```

---

## Question 6: Remove Duplicates

**Difficulty:** Easy

### Problem
Remove duplicates from sorted array in-place.

### Solution

```python
def removeDuplicates(nums):
    if not nums:
        return 0
    
    j = 0
    for i in range(1, len(nums)):
        if nums[i] != nums[j]:
            j += 1
            nums[j] = nums[i]
    
    return j + 1
```

---

## Question 7: Valid Anagram

**Difficulty:** Easy

### Solution

```python
def isAnagram(s, t):
    return sorted(s) == sorted(t)

# Or with hash map
def isAnagram(s, t):
    if len(s) != len(t):
        return False
    
    count = {}
    for char in s:
        count[char] = count.get(char, 0) + 1
    
    for char in t:
        if char not in count:
            return False
        count[char] -= 1
        if count[char] < 0:
            return False
    
    return True
```

---

## Question 8: Missing Number

**Difficulty:** Easy

### Solution (Math approach)

```python
def missingNumber(nums):
    n = len(nums)
    expected_sum = n * (n + 1) // 2
    actual_sum = sum(nums)
    return expected_sum - actual_sum
```

---

## Question 9: Reverse String

**Difficulty:** Easy

### Solution

```python
def reverseString(s):
    s[:] = s[::-1]  # In-place
    
# Or two pointers
def reverseString(s):
    left, right = 0, len(s) - 1
    while left < right:
        s[left], s[right] = s[right], s[left]
        left += 1
        right -= 1
```

---

## Question 10: Merge Sorted Arrays

**Difficulty:** Easy

### Solution

```python
def merge(nums1, m, nums2, n):
    # Merge from back
    p1, p2, p = m - 1, n - 1, m + n - 1
    
    while p1 >= 0 and p2 >= 0:
        if nums1[p1] > nums2[p2]:
            nums1[p] = nums1[p1]
            p1 -= 1
        else:
            nums1[p] = nums2[p2]
            p2 -= 1
        p -= 1
    
    # Copy remaining from nums2
    while p2 >= 0:
        nums1[p] = nums2[p2]
        p2 -= 1
        p -= 1
```

---

## Question 11: Rotate Array

**Difficulty:** Easy

### Solution

```python
def rotate(nums, k):
    k = k % len(nums)  # Handle k > len
    
    # Reverse entire array
    nums[:] = nums[::-1]
    # Reverse first k elements
    nums[:k] = nums[:k][::-1]
    # Reverse rest
    nums[k:] = nums[k:][::-1]
```

---

## Question 12: Search Insert Position

**Difficulty:** Easy

### Solution (Binary Search)

```python
def searchInsert(nums, target):
    left, right = 0, len(nums) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return left
```

---

# MEDIUM QUESTIONS (13-28)

## Question 13: Binary Tree Level Order Traversal

**Difficulty:** Medium  
**LeetCode:** #102

### Solution

```python
from collections import deque

def levelOrder(root):
    if not root:
        return []
    
    result = []
    queue = deque([root])
    
    while queue:
        level_size = len(queue)
        current_level = []
        
        for i in range(level_size):
            node = queue.popleft()
            current_level.append(node.val)
            
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        
        result.append(current_level)
    
    return result
```

---

## Question 14: Longest Substring Without Repeating

**Difficulty:** Medium

### Solution (Sliding Window)

```python
def lengthOfLongestSubstring(s):
    char_map = {}
    left = 0
    max_len = 0
    
    for right in range(len(s)):
        if s[right] in char_map and char_map[s[right]] >= left:
            left = char_map[s[right]] + 1
        
        char_map[s[right]] = right
        max_len = max(max_len, right - left + 1)
    
    return max_len
```

---

## Question 15: 3Sum

**Difficulty:** Medium

### Solution

```python
def threeSum(nums):
    nums.sort()
    result = []
    
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        
        left, right = i + 1, len(nums) - 1
        
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            
            if total == 0:
                result.append([nums[i], nums[left], nums[right]])
                
                # Skip duplicates
                while left < right and nums[left] == nums[left + 1]:
                    left += 1
                while left < right and nums[right] == nums[right - 1]:
                    right -= 1
                
                left += 1
                right -= 1
            elif total < 0:
                left += 1
            else:
                right -= 1
    
    return result
```

---

## Question 16: Number of Islands

**Difficulty:** Medium

### Solution (DFS)

```python
def numIslands(grid):
    if not grid:
        return 0
    
    count = 0
    
    def dfs(i, j):
        if i < 0 or i >= len(grid) or j < 0 or j >= len(grid[0]) or grid[i][j] == '0':
            return
        
        grid[i][j] = '0'  # Mark as visited
        
        # Explore 4 directions
        dfs(i + 1, j)
        dfs(i - 1, j)
        dfs(i, j + 1)
        dfs(i, j - 1)
    
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == '1':
                count += 1
                dfs(i, j)
    
    return count
```

---

## Question 17: Coin Change

**Difficulty:** Medium

### Solution (DP)

```python
def coinChange(coins, amount):
    # dp[i] = min coins needed for amount i
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    
    for i in range(1, amount + 1):
        for coin in coins:
            if coin <= i:
                dp[i] = min(dp[i], dp[i - coin] + 1)
    
    return dp[amount] if dp[amount] != float('inf') else -1
```

---

## Question 18: Longest Increasing Subsequence

**Difficulty:** Medium

### Solution (DP)

```python
def lengthOfLIS(nums):
    if not nums:
        return 0
    
    n = len(nums)
    # dp[i] = length of LIS ending at i
    dp = [1] * n
    
    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    
    return max(dp)
```

---

## Question 19: Word Ladder

**Difficulty:** Medium

### Solution (BFS)

```python
from collections import deque

def ladderLength(beginWord, endWord, wordList):
    if endWord not in wordList:
        return 0
    
    wordSet = set(wordList)
    queue = deque([(beginWord, 1)])
    
    while queue:
        word, level = queue.popleft()
        
        if word == endWord:
            return level
        
        # Generate neighbors
        for i in range(len(word)):
            for c in 'abcdefghijklmnopqrstuvwxyz':
                neighbor = word[:i] + c + word[i+1:]
                
                if neighbor in wordSet:
                    wordSet.remove(neighbor)
                    queue.append((neighbor, level + 1))
    
    return 0
```

---

## Question 20-28: Additional Medium Problems

**20. Decode String** - Stack-based approach
**21. Minimum Window Substring** - Sliding window with hashmap
**22. Palindrome Partitioning** - Backtracking
**23. Course Schedule** - Topological sort with DFS
**24. Evaluate Reverse Polish Notation** - Stack
**25. Roman to Integer** - Hashmap + string iteration
**26. Flatten Nested List Iterator** - DFS with stack
**27. Kth Largest Element** - Heap or quickselect
**28. LRU Cache** - Doubly linked list + hashmap

*[Detailed solutions available upon request]*

---

# HARD QUESTIONS (29-40)

## Question 29: Edit Distance (Levenshtein Distance)

**Difficulty:** Hard

### Solution (2D DP)

```python
def minDistance(word1, word2):
    m, n = len(word1), len(word2)
    
    # dp[i][j] = min edits to transform word1[0:i] to word2[0:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    # Base cases
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    # Fill table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # delete
                    dp[i][j - 1],      # insert
                    dp[i - 1][j - 1]   # replace
                )
    
    return dp[m][n]
```

---

## Question 30: Trapping Rain Water

**Difficulty:** Hard

### Solution (Two Pointers)

```python
def trap(height):
    if not height:
        return 0
    
    left, right = 0, len(height) - 1
    left_max, right_max = 0, 0
    water = 0
    
    while left < right:
        if height[left] < height[right]:
            if height[left] >= left_max:
                left_max = height[left]
            else:
                water += left_max - height[left]
            left += 1
        else:
            if height[right] >= right_max:
                right_max = height[right]
            else:
                water += right_max - height[right]
            right -= 1
    
    return water
```

---

## Question 31-40: Advanced Hard Problems

**31. Burst Balloons** - DP with intervals
**32. Maximum Skyline** - Sweep line with heap
**33. Word Search II** - Trie + DFS
**34. Serialize/Deserialize Binary Tree** - BFS traversal
**35. Regex Matcher** - 2D DP
**36. Median of Two Sorted Arrays** - Binary search
**37. Longest Palindromic Substring** - DP or expand around center
**38. Merge K Sorted Lists** - Heap or divide & conquer
**39. N-Queens** - Backtracking with constraints
**40. Wildcard Matching** - 2D DP with greedy

*[Detailed solutions available upon request]*

---

## Interview Tips for DSA

✅ **Before coding:**
1. Clarify problem requirements
2. Ask about constraints (empty input, negative numbers, duplicates)
3. Walk through example
4. State your approach
5. Mention complexity

✅ **While coding:**
1. Use clear variable names
2. Add comments for complex logic
3. Handle edge cases
4. Test with examples mentally
5. Optimize if time permits

✅ **After coding:**
1. Walk through test cases
2. Discuss complexity
3. Mention follow-ups
4. Ask interviewer questions

---

