# Python DSA Interview Questions - FAANG Level

Advanced Data Structures & Algorithms for FAANG interviews.

---

## EASY QUESTIONS (1-5)

### Question 1: Median of Two Sorted Arrays (LeetCode Hard)
**Time:** 20 minutes

```python
def findMedianSortedArrays(nums1, nums2):
    # Ensure nums1 is smaller
    if len(nums1) > len(nums2):
        return findMedianSortedArrays(nums2, nums1)
    
    m, n = len(nums1), len(nums2)
    left, right = 0, m
    
    while left <= right:
        partition1 = (left + right) // 2
        partition2 = (m + n + 1) // 2 - partition1
        
        maxLeft1 = float('-inf') if partition1 == 0 else nums1[partition1 - 1]
        minRight1 = float('inf') if partition1 == m else nums1[partition1]
        
        maxLeft2 = float('-inf') if partition2 == 0 else nums2[partition2 - 1]
        minRight2 = float('inf') if partition2 == n else nums2[partition2]
        
        if maxLeft1 <= minRight2 and maxLeft2 <= minRight1:
            if (m + n) % 2 == 0:
                return (max(maxLeft1, maxLeft2) + min(minRight1, minRight2)) / 2
            else:
                return max(maxLeft1, maxLeft2)
        elif maxLeft1 > minRight2:
            right = partition1 - 1
        else:
            left = partition1 + 1
```

### Question 2: Reverse a Linked List II
**Time:** 15 minutes

```python
def reverseBetween(head, left, right):
    if not head or left == right:
        return head
    
    dummy = ListNode(0)
    dummy.next = head
    prev = dummy
    
    for _ in range(left - 1):
        prev = prev.next
    
    curr = prev.next
    
    for _ in range(right - left):
        next_node = curr.next
        curr.next = next_node.next
        next_node.next = prev.next
        prev.next = next_node
    
    return dummy.next
```

### Question 3: Implement Trie (Prefix Tree)
**Time:** 20 minutes

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.isEnd = False

class Trie:
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.isEnd = True
    
    def search(self, word):
        node = self._find(word)
        return node is not None and node.isEnd
    
    def startsWith(self, prefix):
        return self._find(prefix) is not None
    
    def _find(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return None
            node = node.children[char]
        return node
```

### Question 4: LRU Cache
**Time:** 25 minutes

```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key):
        if key not in self.cache:
            return -1
        
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        
        self.cache[key] = value
        
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
```

### Question 5: Implement Min Stack
**Time:** 15 minutes

```python
class MinStack:
    def __init__(self):
        self.stack = []
        self.min_stack = []
    
    def push(self, val):
        self.stack.append(val)
        if not self.min_stack or val <= self.min_stack[-1]:
            self.min_stack.append(val)
    
    def pop(self):
        if self.stack[-1] == self.min_stack[-1]:
            self.min_stack.pop()
        self.stack.pop()
    
    def top(self):
        return self.stack[-1]
    
    def getMin(self):
        return self.min_stack[-1]
```

---

## MEDIUM QUESTIONS (6-23)

### Question 6: Serialize and Deserialize Binary Tree

```python
class Codec:
    def serialize(self, root):
        result = []
        
        def dfs(node):
            if not node:
                result.append('#')
                return
            result.append(str(node.val))
            dfs(node.left)
            dfs(node.right)
        
        dfs(root)
        return ','.join(result)
    
    def deserialize(self, data):
        nodes = data.split(',')
        self.i = 0
        
        def dfs():
            if nodes[self.i] == '#':
                self.i += 1
                return None
            node = TreeNode(int(nodes[self.i]))
            self.i += 1
            node.left = dfs()
            node.right = dfs()
            return node
        
        return dfs()
```

### Question 7: Word Ladder II

```python
def findLadders(beginWord, endWord, wordList):
    wordSet = set(wordList)
    if endWord not in wordSet:
        return []
    
    neighbors = {word: [] for word in wordSet}
    neighbors[beginWord] = []
    
    def bfs():
        queue = [beginWord]
        visited = {beginWord}
        found = False
        
        while queue and not found:
            next_queue = []
            for word in queue:
                for i in range(len(word)):
                    for c in 'abcdefghijklmnopqrstuvwxyz':
                        neighbor = word[:i] + c + word[i+1:]
                        if neighbor in wordSet:
                            neighbors[word].append(neighbor)
                            if neighbor not in visited:
                                if neighbor == endWord:
                                    found = True
                                visited.add(neighbor)
                                next_queue.append(neighbor)
            queue = next_queue
    
    bfs()
    
    result = []
    path = [beginWord]
    
    def dfs(word):
        if word == endWord:
            result.append(path[:])
            return
        
        for neighbor in neighbors[word]:
            path.append(neighbor)
            dfs(neighbor)
            path.pop()
    
    dfs(beginWord)
    return result
```

### Question 8: Burst Balloons (Hard DP)

```python
def maxCoins(nums):
    nums = [1] + [x for x in nums if x > 0] + [1]
    n = len(nums)
    dp = [[0] * n for _ in range(n)]
    
    for length in range(3, n + 1):
        for left in range(n - length + 1):
            right = left + length - 1
            for k in range(left + 1, right):
                dp[left][right] = max(
                    dp[left][right],
                    dp[left][k] + dp[k][right] + 
                    nums[left] * nums[k] * nums[right]
                )
    
    return dp[0][n - 1]
```

### Question 9: Regular Expression Matching

```python
def isMatch(s, p):
    m, n = len(s), len(p)
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    
    for j in range(2, n + 1):
        if p[j - 1] == '*':
            dp[0][j] = dp[0][j - 2]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if p[j - 1] == '*':
                dp[i][j] = dp[i][j - 2]
                if p[j - 2] == '.' or p[j - 2] == s[i - 1]:
                    dp[i][j] = dp[i][j] or dp[i - 1][j]
            else:
                if p[j - 1] == '.' or p[j - 1] == s[i - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
    
    return dp[m][n]
```

### Question 10: Merge K Sorted Lists

```python
import heapq

def mergeKLists(lists):
    if not lists:
        return None
    
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

### Question 11: Binary Tree Maximum Path Sum

```python
def maxPathSum(root):
    maxSum = float('-inf')
    
    def dfs(node):
        nonlocal maxSum
        
        if not node:
            return 0
        
        left = max(dfs(node.left), 0)
        right = max(dfs(node.right), 0)
        
        maxSum = max(maxSum, node.val + left + right)
        
        return node.val + max(left, right)
    
    dfs(root)
    return maxSum
```

### Question 12: Longest Consecutive Sequence

```python
def longestConsecutive(nums):
    if not nums:
        return 0
    
    num_set = set(nums)
    longest_streak = 0
    
    for num in num_set:
        if num - 1 not in num_set:
            current_num = num
            current_streak = 1
            
            while current_num + 1 in num_set:
                current_num += 1
                current_streak += 1
            
            longest_streak = max(longest_streak, current_streak)
    
    return longest_streak
```

### Question 13-23: More Hard Problems
**13. First Missing Positive** - O(n) time, O(1) space
**14. Skyline Problem** - Sweep line algorithm
**15. Word Search II** - Trie + DFS
**16. Alien Dictionary** - Topological sort
**17. Minimum Window Substring** - Sliding window
**18. Maximal Rectangle** - DP
**19. Binary Tree from Preorder and Inorder** - Recursion with hashmap
**20. Construct Quad Tree** - Divide and conquer
**21. Number of Islands II** - Union Find
**22. Sliding Window Maximum** - Deque
**23. Paint House III** - DP with states

*[Detailed solutions available upon request]*

---

## HARD QUESTIONS (24-40)

### Question 24: Wildcard Matching

```python
def isMatch(s, p):
    m, n = len(s), len(p)
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    
    for j in range(1, n + 1):
        if p[j - 1] == '*':
            dp[0][j] = dp[0][j - 1]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if p[j - 1] == '*':
                dp[i][j] = dp[i - 1][j] or dp[i][j - 1]
            else:
                if p[j - 1] == '?' or p[j - 1] == s[i - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
    
    return dp[m][n]
```

### Question 25: N-Queens II

```python
def solveNQueens(n):
    result = []
    board = [['.' for _ in range(n)] for _ in range(n)]
    
    def isValid(row, col):
        for i in range(row):
            if board[i][col] == 'Q':
                return False
        
        i, j = row - 1, col - 1
        while i >= 0 and j >= 0:
            if board[i][j] == 'Q':
                return False
            i -= 1
            j -= 1
        
        i, j = row - 1, col + 1
        while i >= 0 and j < n:
            if board[i][j] == 'Q':
                return False
            i -= 1
            j += 1
        
        return True
    
    def backtrack(row):
        if row == n:
            result.append([''.join(row) for row in board])
            return
        
        for col in range(n):
            if isValid(row, col):
                board[row][col] = 'Q'
                backtrack(row + 1)
                board[row][col] = '.'
    
    backtrack(0)
    return result
```

### Question 26-40: Most Advanced Problems

**26. Russian Doll Envelopes** - DP + Binary search
**27. Count of Smaller Numbers After Self** - Merge sort
**28. Largest Rectangle in Histogram** - Stack
**29. Minimum Difficulty of a Job Schedule** - DP
**30. Cherry Pickup** - DP with 2 paths
**31. Super Ugly Number** - DP with multiple primes
**32. Maximum Product Subarray** - DP with states
**33. Concatenated Words** - DFS + Trie
**34. My Calendar III** - Sweep line
**35. Campus Bikes II** - DP with bitmask
**36. Chalkboard XOR Game** - Game theory
**37. Maximum Vacation Days** - DP
**38. Split Array into K Equal Sum Subarrays** - DP
**39. Range Sum Query 2D Mutable** - Segment tree
**40. Binary Trees with Factors** - DP with sorting

*[Solutions for questions 26-40 require deep expertise and will be provided on request]*

---

## FAANG-Specific Tips

✅ **What FAANG looks for:**
- Optimal time/space complexity
- Clean, production-ready code
- Multiple approaches discussion
- Follow-up problem handling
- System design thinking
- Communication throughout

✅ **Common FAANG patterns:**
- Heavy use of advanced data structures (Trie, Segment Tree, Union Find)
- Multiple problem combinations
- Follow-ups that add constraints
- Discussion on edge cases and optimizations

---

