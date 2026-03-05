# Complete Coding Round Problems

Full LeetCode-style problems for interview prep.

---

## Easy Problems (1-5)

### Problem 1: Two Sum

Given array and target, find two numbers that add up to target.

```python
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Test cases
assert twoSum([2,7,11,15], 9) == [0,1]
assert twoSum([3,2,4], 6) == [1,2]
assert twoSum([3,3], 6) == [0,1]
```

### Problem 2: Valid Parentheses

Check if parentheses are balanced and properly nested.

```python
def isValid(s):
    stack = []
    mapping = {'(': ')', '[': ']', '{': '}'}
    
    for char in s:
        if char in mapping:
            stack.append(char)
        else:
            if not stack or mapping[stack.pop()] != char:
                return False
    
    return len(stack) == 0

# Test cases
assert isValid("()") == True
assert isValid("()[]{}") == True
assert isValid("([)]") == False
assert isValid("") == True
```

### Problem 3: Merge Sorted Arrays

Merge two sorted arrays in-place.

```python
def merge(nums1, m, nums2, n):
    p1, p2, p = m - 1, n - 1, m + n - 1
    
    while p1 >= 0 and p2 >= 0:
        if nums1[p1] > nums2[p2]:
            nums1[p] = nums1[p1]
            p1 -= 1
        else:
            nums1[p] = nums2[p2]
            p2 -= 1
        p -= 1
    
    while p2 >= 0:
        nums1[p] = nums2[p2]
        p2 -= 1
        p -= 1

# Modify in-place
nums1 = [1,2,3,0,0,0]
nums2 = [2,5,6]
merge(nums1, 3, nums2, 3)
# nums1 becomes [1,2,2,3,5,6]
```

### Problem 4: Best Time to Buy Stock

Find max profit from single buy-sell transaction.

```python
def maxProfit(prices):
    min_price = float('inf')
    max_profit = 0
    
    for price in prices:
        max_profit = max(max_profit, price - min_price)
        min_price = min(min_price, price)
    
    return max_profit

# Test
assert maxProfit([7,1,5,3,6,4]) == 5  # Buy at 1, sell at 6
assert maxProfit([7,6,4,3,1]) == 0    # No profit possible
```

### Problem 5: Majority Element

Find element appearing > n/2 times.

```python
def majorityElement(nums):
    candidate = None
    count = 0
    
    for num in nums:
        if count == 0:
            candidate = num
        count += (1 if num == candidate else -1)
    
    return candidate

# Test
assert majorityElement([3,2,3]) == 3
assert majorityElement([2,2,1,1,1,2,2]) == 2
```

---

## Medium Problems (6-15)

### Problem 6: LongestSubstringWithoutRepeatingCharacters

Find length of longest substring without repeating characters.

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

# Test
assert lengthOfLongestSubstring("abcabcbb") == 3  # "abc"
assert lengthOfLongestSubstring("bbbbb") == 1      # "b"
assert lengthOfLongestSubstring("pwwkew") == 3     # "wke"
```

### Problem 7: 3Sum

Find all unique triplets that sum to zero.

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

# Test
assert threeSum([-1,0,1,2,-1,-4]) == [[-1,-1,2],[-1,0,1]]
```

### Problem 8: Binary Tree Level Order Traversal

Traverse tree level by level.

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
        
        for _ in range(level_size):
            node = queue.popleft()
            current_level.append(node.val)
            
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        
        result.append(current_level)
    
    return result
```

### Problem 9: Coin Change

Minimum coins to make amount.

```python
def coinChange(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    
    for i in range(1, amount + 1):
        for coin in coins:
            if coin <= i:
                dp[i] = min(dp[i], dp[i - coin] + 1)
    
    return dp[amount] if dp[amount] != float('inf') else -1

# Test
assert coinChange([1,2,5], 5) == 1    # 5 is one coin
assert coinChange([2], 3) == -1       # Impossible
assert coinChange([10], 10) == 1
```

### Problem 10: Longest Increasing Subsequence

Find length of LIS.

```python
def lengthOfLIS(nums):
    n = len(nums)
    if n == 0:
        return 0
    
    dp = [1] * n
    
    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    
    return max(dp)

# Test
assert lengthOfLIS([10,9,2,5,3,7,101,18]) == 4  # [2,3,7,101]
assert lengthOfLIS([0,1,0,4,4,4,4,2,0,4,2,2,2,12,2,5,8,7,7,7,2,12]) == 6
```

### Problems 11-15: Additional
**11. Number of Islands** - DFS/BFS
**12. Word Ladder** - BFS shortest path
**13. Decode String** - Stack
**14. Palindrome Partitioning** - Backtracking
**15. Course Schedule** - Topological sort

---

## Hard Problems (16-20)

### Problem 16: Edit Distance (Levenshtein)

Minimum edits to transform one string to another.

```python
def minDistance(word1, word2):
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i-1] == word2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(
                    dp[i-1][j],      # delete
                    dp[i][j-1],      # insert
                    dp[i-1][j-1]     # replace
                )
    
    return dp[m][n]

# Test
assert minDistance("horse", "ros") == 3
assert minDistance("intention", "execution") == 5
```

### Problem 17: Merge K Sorted Lists

Merge K sorted linked lists efficiently.

```python
import heapq

def mergeKLists(lists):
    heap = []
    
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst.val, i, lst))
    
    dummy = ListNode(0)
    curr = dummy
    
    while heap:
        val, i, node = heapq.heappop(heap)
        curr.next = node
        curr = curr.next
        
        if node.next:
            heapq.heappush(heap, (node.next.val, i, node.next))
    
    return dummy.next
```

### Problem 18: Trapping Rain Water

Calculate water trapped between elevations.

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

# Test
assert trap([0,1,0,2,1,0,1,3,2,1,2,1]) == 6
```

### Problems 19-20: Most Advanced
**19. Burst Balloons** - DP with intervals
**20. Maximum Skyline** - Sweep line algorithm

---

## Interview Strategy

✅ **During coding round:**
1. Clarify problem (5%)
2. Design approach (15%)
3. Code (60%)
4. Test (15%)
5. Optimize (10%)

✅ **Time management:**
- Easy: 10-15 minutes
- Medium: 20-30 minutes
- Hard: 30-45 minutes

✅ **Best practices:**
- Clear variable names
- Add comments
- Test with examples
- Handle edge cases
- Discuss complexity

---

