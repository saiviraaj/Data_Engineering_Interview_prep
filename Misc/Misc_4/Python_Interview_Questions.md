# Python Interview Questions & Answers - LeetCode Style

> **Last Updated:** 2024  
> **Total Questions:** 75+  
> **Focus:** Data Structures, Algorithms, Problem Solving  
> **Companies:** FAANG, Tech Giants

---

## Table of Contents

1. [Arrays & Hashing](#1-arrays--hashing)
2. [Two Pointers](#2-two-pointers)
3. [Sliding Window](#3-sliding-window)
4. [Stack & Queue](#4-stack--queue)
5. [Binary Search](#5-binary-search)
6. [Linked Lists](#6-linked-lists)
7. [Trees](#7-trees)
8. [Tries](#8-tries)
9. [Heap / Priority Queue](#9-heap--priority-queue)
10. [Backtracking](#10-backtracking)
11. [Graphs](#11-graphs)
12. [Dynamic Programming](#12-dynamic-programming)
13. [Greedy](#13-greedy)
14. [Intervals](#14-intervals)
15. [Bit Manipulation](#15-bit-manipulation)

---

## 1. Arrays & Hashing

### Q1: Two Sum (LeetCode #1) ⭐⭐

**Difficulty:** Easy  
**Pattern:** Hash Map

**Problem:**  
Given an array of integers `nums` and an integer `target`, return indices of the two numbers that add up to `target`.

**Example:**
```
Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: nums[0] + nums[1] = 2 + 7 = 9
```

**Solution:**
```python
def two_sum(nums, target):
    """
    Time Complexity: O(n)
    Space Complexity: O(n)
    """
    seen = {}
    
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    
    return []

# Test
print(two_sum([2, 7, 11, 15], 9))  # [0, 1]
print(two_sum([3, 2, 4], 6))       # [1, 2]
```

**Key Points:**
- Hash map for O(1) lookup
- Single pass solution
- Handle edge cases (no solution, duplicate values)

---

### Q2: Contains Duplicate (LeetCode #217) ⭐

**Difficulty:** Easy

**Problem:**  
Given an integer array `nums`, return `true` if any value appears at least twice.

**Solution:**
```python
def contains_duplicate(nums):
    """
    Time: O(n)
    Space: O(n)
    """
    return len(nums) != len(set(nums))

# Alternative: Early exit
def contains_duplicate_v2(nums):
    seen = set()
    for num in nums:
        if num in seen:
            return True
        seen.add(num)
    return False

# Test
print(contains_duplicate([1, 2, 3, 1]))  # True
print(contains_duplicate([1, 2, 3, 4]))  # False
```

---

### Q3: Valid Anagram (LeetCode #242) ⭐

**Difficulty:** Easy

**Problem:**  
Given two strings `s` and `t`, return true if `t` is an anagram of `s`.

**Solution:**
```python
def is_anagram(s, t):
    """
    Time: O(n)
    Space: O(1) - max 26 characters
    """
    if len(s) != len(t):
        return False
    
    from collections import Counter
    return Counter(s) == Counter(t)

# Without Counter
def is_anagram_v2(s, t):
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

# Test
print(is_anagram("anagram", "nagaram"))  # True
print(is_anagram("rat", "car"))          # False
```

---

### Q4: Group Anagrams (LeetCode #49) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Given an array of strings, group the anagrams together.

**Solution:**
```python
def group_anagrams(strs):
    """
    Time: O(n * k log k) where k is max string length
    Space: O(n * k)
    """
    from collections import defaultdict
    
    anagrams = defaultdict(list)
    
    for s in strs:
        # Use sorted string as key
        key = ''.join(sorted(s))
        anagrams[key].append(s)
    
    return list(anagrams.values())

# Optimized: O(n * k)
def group_anagrams_optimized(strs):
    from collections import defaultdict
    
    anagrams = defaultdict(list)
    
    for s in strs:
        # Character count as key
        count = [0] * 26
        for char in s:
            count[ord(char) - ord('a')] += 1
        anagrams[tuple(count)].append(s)
    
    return list(anagrams.values())

# Test
input_strs = ["eat","tea","tan","ate","nat","bat"]
print(group_anagrams(input_strs))
# [['eat', 'tea', 'ate'], ['tan', 'nat'], ['bat']]
```

---

### Q5: Top K Frequent Elements (LeetCode #347) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Given an integer array and integer k, return the k most frequent elements.

**Solution:**
```python
def top_k_frequent(nums, k):
    """
    Time: O(n)
    Space: O(n)
    Using bucket sort
    """
    from collections import Counter
    
    count = Counter(nums)
    
    # Bucket sort: index is frequency
    buckets = [[] for _ in range(len(nums) + 1)]
    for num, freq in count.items():
        buckets[freq].append(num)
    
    # Gather top k from highest frequency
    result = []
    for i in range(len(buckets) - 1, 0, -1):
        result.extend(buckets[i])
        if len(result) >= k:
            return result[:k]
    
    return result

# Using heap: O(n log k)
import heapq

def top_k_frequent_heap(nums, k):
    from collections import Counter
    count = Counter(nums)
    return heapq.nlargest(k, count.keys(), key=count.get)

# Test
print(top_k_frequent([1,1,1,2,2,3], k=2))  # [1, 2]
```

---

### Q6: Product of Array Except Self (LeetCode #238) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Return array where `output[i]` equals product of all elements except `nums[i]`.  
**Constraint:** Cannot use division, O(n) time.

**Solution:**
```python
def product_except_self(nums):
    """
    Time: O(n)
    Space: O(1) excluding output array
    """
    n = len(nums)
    result = [1] * n
    
    # Left products
    left = 1
    for i in range(n):
        result[i] = left
        left *= nums[i]
    
    # Right products
    right = 1
    for i in range(n - 1, -1, -1):
        result[i] *= right
        right *= nums[i]
    
    return result

# Test
print(product_except_self([1,2,3,4]))  # [24,12,8,6]
print(product_except_self([-1,1,0,-3,3]))  # [0,0,9,0,0]
```

---

### Q7: Longest Consecutive Sequence (LeetCode #128) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Find length of longest consecutive elements sequence. Must run in O(n).

**Solution:**
```python
def longest_consecutive(nums):
    """
    Time: O(n)
    Space: O(n)
    """
    if not nums:
        return 0
    
    num_set = set(nums)
    max_length = 0
    
    for num in num_set:
        # Only start counting from sequence start
        if num - 1 not in num_set:
            current = num
            length = 1
            
            while current + 1 in num_set:
                current += 1
                length += 1
            
            max_length = max(max_length, length)
    
    return max_length

# Test
print(longest_consecutive([100,4,200,1,3,2]))  # 4 (1,2,3,4)
print(longest_consecutive([0,3,7,2,5,8,4,6,0,1]))  # 9
```

---

## 2. Two Pointers

### Q8: Valid Palindrome (LeetCode #125) ⭐

**Difficulty:** Easy

**Problem:**  
Check if string is palindrome, considering only alphanumeric characters.

**Solution:**
```python
def is_palindrome(s):
    """
    Time: O(n)
    Space: O(1)
    """
    left, right = 0, len(s) - 1
    
    while left < right:
        # Skip non-alphanumeric
        while left < right and not s[left].isalnum():
            left += 1
        while left < right and not s[right].isalnum():
            right -= 1
        
        # Compare
        if s[left].lower() != s[right].lower():
            return False
        
        left += 1
        right -= 1
    
    return True

# Test
print(is_palindrome("A man, a plan, a canal: Panama"))  # True
print(is_palindrome("race a car"))  # False
```

---

### Q9: Two Sum II - Sorted Array (LeetCode #167) ⭐

**Difficulty:** Medium

**Problem:**  
Find two numbers in sorted array that add up to target. Return 1-indexed positions.

**Solution:**
```python
def two_sum_sorted(numbers, target):
    """
    Time: O(n)
    Space: O(1)
    """
    left, right = 0, len(numbers) - 1
    
    while left < right:
        current_sum = numbers[left] + numbers[right]
        
        if current_sum == target:
            return [left + 1, right + 1]  # 1-indexed
        elif current_sum < target:
            left += 1
        else:
            right -= 1
    
    return []

# Test
print(two_sum_sorted([2,7,11,15], 9))  # [1, 2]
print(two_sum_sorted([2,3,4], 6))      # [1, 3]
```

---

### Q10: 3Sum (LeetCode #15) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Find all unique triplets that sum to zero.

**Solution:**
```python
def three_sum(nums):
    """
    Time: O(n²)
    Space: O(1) excluding output
    """
    nums.sort()
    result = []
    
    for i in range(len(nums) - 2):
        # Skip duplicates for first number
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        
        # Two pointers for remaining two numbers
        left, right = i + 1, len(nums) - 1
        target = -nums[i]
        
        while left < right:
            current_sum = nums[left] + nums[right]
            
            if current_sum == target:
                result.append([nums[i], nums[left], nums[right]])
                
                # Skip duplicates
                while left < right and nums[left] == nums[left + 1]:
                    left += 1
                while left < right and nums[right] == nums[right - 1]:
                    right -= 1
                
                left += 1
                right -= 1
            elif current_sum < target:
                left += 1
            else:
                right -= 1
    
    return result

# Test
print(three_sum([-1,0,1,2,-1,-4]))  # [[-1,-1,2],[-1,0,1]]
```

---

### Q11: Container With Most Water (LeetCode #11) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Find two lines that together with x-axis form container holding the most water.

**Solution:**
```python
def max_area(height):
    """
    Time: O(n)
    Space: O(1)
    """
    left, right = 0, len(height) - 1
    max_water = 0
    
    while left < right:
        # Calculate current area
        width = right - left
        current_height = min(height[left], height[right])
        current_area = width * current_height
        max_water = max(max_water, current_area)
        
        # Move pointer with smaller height
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    
    return max_water

# Test
print(max_area([1,8,6,2,5,4,8,3,7]))  # 49
```

---

## 3. Sliding Window

### Q12: Best Time to Buy and Sell Stock (LeetCode #121) ⭐

**Difficulty:** Easy

**Problem:**  
Find maximum profit from one buy and one sell.

**Solution:**
```python
def max_profit(prices):
    """
    Time: O(n)
    Space: O(1)
    """
    if not prices:
        return 0
    
    min_price = prices[0]
    max_profit = 0
    
    for price in prices:
        min_price = min(min_price, price)
        max_profit = max(max_profit, price - min_price)
    
    return max_profit

# Test
print(max_profit([7,1,5,3,6,4]))  # 5 (buy at 1, sell at 6)
print(max_profit([7,6,4,3,1]))    # 0 (no profit possible)
```

---

### Q13: Longest Substring Without Repeating Characters (LeetCode #3) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Find length of longest substring without repeating characters.

**Solution:**
```python
def length_of_longest_substring(s):
    """
    Time: O(n)
    Space: O(min(n, m)) where m is charset size
    """
    char_index = {}
    max_length = 0
    start = 0
    
    for end, char in enumerate(s):
        # If char seen and in current window
        if char in char_index and char_index[char] >= start:
            start = char_index[char] + 1
        
        char_index[char] = end
        max_length = max(max_length, end - start + 1)
    
    return max_length

# Test
print(length_of_longest_substring("abcabcbb"))  # 3 ("abc")
print(length_of_longest_substring("bbbbb"))     # 1 ("b")
print(length_of_longest_substring("pwwkew"))    # 3 ("wke")
```

---

### Q14: Minimum Window Substring (LeetCode #76) ⭐⭐⭐

**Difficulty:** Hard

**Problem:**  
Find minimum window in `s` that contains all characters from `t`.

**Solution:**
```python
def min_window(s, t):
    """
    Time: O(|s| + |t|)
    Space: O(|t|)
    """
    if not s or not t:
        return ""
    
    from collections import Counter
    
    # Count chars in t
    target_count = Counter(t)
    required = len(target_count)
    
    # Sliding window
    left = 0
    formed = 0  # Unique chars in window matching target
    window_count = {}
    
    # Result: (window length, left, right)
    result = float('inf'), None, None
    
    for right, char in enumerate(s):
        # Add char to window
        window_count[char] = window_count.get(char, 0) + 1
        
        # Check if frequency matches
        if char in target_count and window_count[char] == target_count[char]:
            formed += 1
        
        # Contract window while valid
        while formed == required and left <= right:
            # Update result
            if right - left + 1 < result[0]:
                result = (right - left + 1, left, right)
            
            # Remove leftmost char
            char = s[left]
            window_count[char] -= 1
            if char in target_count and window_count[char] < target_count[char]:
                formed -= 1
            
            left += 1
    
    return "" if result[0] == float('inf') else s[result[1]:result[2] + 1]

# Test
print(min_window("ADOBECODEBANC", "ABC"))  # "BANC"
```

---

## 4. Stack & Queue

### Q15: Valid Parentheses (LeetCode #20) ⭐

**Difficulty:** Easy

**Problem:**  
Determine if string has valid bracket combinations.

**Solution:**
```python
def is_valid(s):
    """
    Time: O(n)
    Space: O(n)
    """
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in mapping:
            # Closing bracket
            top = stack.pop() if stack else '#'
            if mapping[char] != top:
                return False
        else:
            # Opening bracket
            stack.append(char)
    
    return not stack

# Test
print(is_valid("()"))        # True
print(is_valid("()[]{}"))    # True
print(is_valid("(]"))        # False
print(is_valid("([)]"))      # False
```

---

### Q16: Min Stack (LeetCode #155) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Design stack that supports push, pop, top, and retrieving minimum element in O(1).

**Solution:**
```python
class MinStack:
    """
    All operations: O(1) time
    Space: O(n)
    """
    
    def __init__(self):
        self.stack = []
        self.min_stack = []
    
    def push(self, val):
        self.stack.append(val)
        # Push to min_stack if empty or val is new minimum
        if not self.min_stack or val <= self.min_stack[-1]:
            self.min_stack.append(val)
    
    def pop(self):
        if self.stack:
            val = self.stack.pop()
            # Pop from min_stack if it was the minimum
            if val == self.min_stack[-1]:
                self.min_stack.pop()
            return val
    
    def top(self):
        return self.stack[-1] if self.stack else None
    
    def get_min(self):
        return self.min_stack[-1] if self.min_stack else None

# Test
min_stack = MinStack()
min_stack.push(-2)
min_stack.push(0)
min_stack.push(-3)
print(min_stack.get_min())  # -3
min_stack.pop()
print(min_stack.top())      # 0
print(min_stack.get_min())  # -2
```

---

### Q17: Daily Temperatures (LeetCode #739) ⭐⭐

**Difficulty:** Medium

**Problem:**  
For each day, find how many days until warmer temperature.

**Solution:**
```python
def daily_temperatures(temperatures):
    """
    Time: O(n)
    Space: O(n)
    Monotonic stack
    """
    n = len(temperatures)
    result = [0] * n
    stack = []  # Stores indices
    
    for i, temp in enumerate(temperatures):
        # Pop while current temp is warmer
        while stack and temperatures[stack[-1]] < temp:
            prev_index = stack.pop()
            result[prev_index] = i - prev_index
        
        stack.append(i)
    
    return result

# Test
print(daily_temperatures([73,74,75,71,69,72,76,73]))
# [1,1,4,2,1,1,0,0]
```

---

## 5. Binary Search

### Q18: Binary Search (LeetCode #704) ⭐

**Difficulty:** Easy

**Problem:**  
Search for target in sorted array. Return index or -1.

**Solution:**
```python
def binary_search(nums, target):
    """
    Time: O(log n)
    Space: O(1)
    """
    left, right = 0, len(nums) - 1
    
    while left <= right:
        mid = left + (right - left) // 2  # Avoid overflow
        
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

# Test
print(binary_search([-1,0,3,5,9,12], 9))   # 4
print(binary_search([-1,0,3,5,9,12], 2))   # -1
```

---

### Q19: Search in Rotated Sorted Array (LeetCode #33) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Search in rotated sorted array in O(log n) time.

**Solution:**
```python
def search(nums, target):
    """
    Time: O(log n)
    Space: O(1)
    """
    left, right = 0, len(nums) - 1
    
    while left <= right:
        mid = left + (right - left) // 2
        
        if nums[mid] == target:
            return mid
        
        # Left half is sorted
        if nums[left] <= nums[mid]:
            if nums[left] <= target < nums[mid]:
                right = mid - 1
            else:
                left = mid + 1
        # Right half is sorted
        else:
            if nums[mid] < target <= nums[right]:
                left = mid + 1
            else:
                right = mid - 1
    
    return -1

# Test
print(search([4,5,6,7,0,1,2], 0))  # 4
print(search([4,5,6,7,0,1,2], 3))  # -1
```

---

### Q20: Find Minimum in Rotated Sorted Array (LeetCode #153) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def find_min(nums):
    """
    Time: O(log n)
    Space: O(1)
    """
    left, right = 0, len(nums) - 1
    
    while left < right:
        mid = left + (right - left) // 2
        
        if nums[mid] > nums[right]:
            # Minimum is in right half
            left = mid + 1
        else:
            # Minimum is in left half (including mid)
            right = mid
    
    return nums[left]

# Test
print(find_min([3,4,5,1,2]))  # 1
print(find_min([4,5,6,7,0,1,2]))  # 0
```

---

## 6. Linked Lists

### Q21: Reverse Linked List (LeetCode #206) ⭐

**Difficulty:** Easy

**Solution:**
```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def reverse_list(head):
    """
    Time: O(n)
    Space: O(1)
    """
    prev = None
    current = head
    
    while current:
        next_temp = current.next
        current.next = prev
        prev = current
        current = next_temp
    
    return prev

# Recursive solution
def reverse_list_recursive(head):
    """
    Time: O(n)
    Space: O(n) - recursion stack
    """
    if not head or not head.next:
        return head
    
    new_head = reverse_list_recursive(head.next)
    head.next.next = head
    head.next = None
    
    return new_head
```

---

### Q22: Merge Two Sorted Lists (LeetCode #21) ⭐

**Difficulty:** Easy

**Solution:**
```python
def merge_two_lists(l1, l2):
    """
    Time: O(n + m)
    Space: O(1)
    """
    dummy = ListNode(0)
    current = dummy
    
    while l1 and l2:
        if l1.val < l2.val:
            current.next = l1
            l1 = l1.next
        else:
            current.next = l2
            l2 = l2.next
        current = current.next
    
    # Attach remaining
    current.next = l1 if l1 else l2
    
    return dummy.next
```

---

### Q23: Linked List Cycle (LeetCode #141) ⭐

**Difficulty:** Easy

**Solution:**
```python
def has_cycle(head):
    """
    Time: O(n)
    Space: O(1)
    Floyd's Cycle Detection
    """
    if not head:
        return False
    
    slow = fast = head
    
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        
        if slow == fast:
            return True
    
    return False
```

---

### Q24: Remove Nth Node From End (LeetCode #19) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def remove_nth_from_end(head, n):
    """
    Time: O(L) where L is length
    Space: O(1)
    """
    dummy = ListNode(0)
    dummy.next = head
    fast = slow = dummy
    
    # Move fast n+1 steps ahead
    for _ in range(n + 1):
        fast = fast.next
    
    # Move both until fast reaches end
    while fast:
        fast = fast.next
        slow = slow.next
    
    # Remove nth node
    slow.next = slow.next.next
    
    return dummy.next
```

---

### Q25: Reorder List (LeetCode #143) ⭐⭐

**Difficulty:** Medium

**Problem:**  
Reorder list: L0 → L1 → ... → Ln-1 → Ln to L0 → Ln → L1 → Ln-1 → L2 → Ln-2 ...

**Solution:**
```python
def reorder_list(head):
    """
    Time: O(n)
    Space: O(1)
    """
    if not head or not head.next:
        return
    
    # Find middle
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    
    # Reverse second half
    prev = None
    current = slow
    while current:
        next_temp = current.next
        current.next = prev
        prev = current
        current = next_temp
    
    # Merge two halves
    first = head
    second = prev
    while second.next:
        temp1 = first.next
        temp2 = second.next
        
        first.next = second
        second.next = temp1
        
        first = temp1
        second = temp2
```

---

## 7. Trees

### Q26: Invert Binary Tree (LeetCode #226) ⭐

**Difficulty:** Easy

**Solution:**
```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def invert_tree(root):
    """
    Time: O(n)
    Space: O(h) where h is height
    """
    if not root:
        return None
    
    # Swap children
    root.left, root.right = root.right, root.left
    
    # Recursively invert subtrees
    invert_tree(root.left)
    invert_tree(root.right)
    
    return root
```

---

### Q27: Maximum Depth of Binary Tree (LeetCode #104) ⭐

**Difficulty:** Easy

**Solution:**
```python
def max_depth(root):
    """
    Time: O(n)
    Space: O(h)
    """
    if not root:
        return 0
    
    return 1 + max(max_depth(root.left), max_depth(root.right))

# Iterative BFS
from collections import deque

def max_depth_iterative(root):
    if not root:
        return 0
    
    queue = deque([root])
    depth = 0
    
    while queue:
        depth += 1
        for _ in range(len(queue)):
            node = queue.popleft()
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
    
    return depth
```

---

### Q28: Same Tree (LeetCode #100) ⭐

**Difficulty:** Easy

**Solution:**
```python
def is_same_tree(p, q):
    """
    Time: O(n)
    Space: O(h)
    """
    if not p and not q:
        return True
    
    if not p or not q:
        return False
    
    if p.val != q.val:
        return False
    
    return (is_same_tree(p.left, q.left) and 
            is_same_tree(p.right, q.right))
```

---

### Q29: Subtree of Another Tree (LeetCode #572) ⭐

**Difficulty:** Easy

**Solution:**
```python
def is_subtree(root, sub_root):
    """
    Time: O(m * n)
    Space: O(h)
    """
    if not root:
        return False
    
    if is_same_tree(root, sub_root):
        return True
    
    return (is_subtree(root.left, sub_root) or 
            is_subtree(root.right, sub_root))
```

---

### Q30: Lowest Common Ancestor of BST (LeetCode #235) ⭐

**Difficulty:** Medium

**Solution:**
```python
def lowest_common_ancestor(root, p, q):
    """
    Time: O(h)
    Space: O(1) iterative, O(h) recursive
    """
    # Iterative
    while root:
        if p.val < root.val and q.val < root.val:
            root = root.left
        elif p.val > root.val and q.val > root.val:
            root = root.right
        else:
            return root
```

---

### Q31: Binary Tree Level Order Traversal (LeetCode #102) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def level_order(root):
    """
    Time: O(n)
    Space: O(n)
    """
    if not root:
        return []
    
    from collections import deque
    
    result = []
    queue = deque([root])
    
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        
        result.append(level)
    
    return result
```

---

### Q32: Validate Binary Search Tree (LeetCode #98) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def is_valid_bst(root, min_val=float('-inf'), max_val=float('inf')):
    """
    Time: O(n)
    Space: O(h)
    """
    if not root:
        return True
    
    if root.val <= min_val or root.val >= max_val:
        return False
    
    return (is_valid_bst(root.left, min_val, root.val) and
            is_valid_bst(root.right, root.val, max_val))
```

---

### Q33: Kth Smallest Element in BST (LeetCode #230) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def kth_smallest(root, k):
    """
    Time: O(n)
    Space: O(h)
    Inorder traversal
    """
    def inorder(node):
        if not node:
            return []
        return inorder(node.left) + [node.val] + inorder(node.right)
    
    return inorder(root)[k - 1]

# Optimized: Early stop
def kth_smallest_optimized(root, k):
    stack = []
    current = root
    count = 0
    
    while current or stack:
        while current:
            stack.append(current)
            current = current.left
        
        current = stack.pop()
        count += 1
        
        if count == k:
            return current.val
        
        current = current.right
```

---

### Q34: Binary Tree Maximum Path Sum (LeetCode #124) ⭐⭐⭐

**Difficulty:** Hard

**Solution:**
```python
def max_path_sum(root):
    """
    Time: O(n)
    Space: O(h)
    """
    max_sum = [float('-inf')]
    
    def max_gain(node):
        if not node:
            return 0
        
        # Max gain from left and right (take 0 if negative)
        left_gain = max(max_gain(node.left), 0)
        right_gain = max(max_gain(node.right), 0)
        
        # Path through current node
        price_newpath = node.val + left_gain + right_gain
        
        # Update max_sum
        max_sum[0] = max(max_sum[0], price_newpath)
        
        # Return max gain if continue same path
        return node.val + max(left_gain, right_gain)
    
    max_gain(root)
    return max_sum[0]
```

---

## 8. Tries

### Q35: Implement Trie (LeetCode #208) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class Trie:
    """
    All operations: O(m) where m is key length
    Space: O(ALPHABET_SIZE * m * n) for n keys
    """
    
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
    
    def search(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                return False
            node = node.children[char]
        return node.is_end
    
    def starts_with(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return False
            node = node.children[char]
        return True

# Test
trie = Trie()
trie.insert("apple")
print(trie.search("apple"))      # True
print(trie.search("app"))        # False
print(trie.starts_with("app"))   # True
```

---

## 9. Heap / Priority Queue

### Q36: Kth Largest Element (LeetCode #215) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
import heapq

def find_kth_largest(nums, k):
    """
    Time: O(n log k)
    Space: O(k)
    Using min heap of size k
    """
    # Keep min heap of k largest elements
    heap = []
    
    for num in nums:
        heapq.heappush(heap, num)
        if len(heap) > k:
            heapq.heappop(heap)
    
    return heap[0]

# Alternative: O(n) average using quickselect
def find_kth_largest_quickselect(nums, k):
    k = len(nums) - k  # Convert to kth smallest
    
    def quickselect(left, right):
        pivot = nums[right]
        p = left
        
        for i in range(left, right):
            if nums[i] <= pivot:
                nums[p], nums[i] = nums[i], nums[p]
                p += 1
        
        nums[p], nums[right] = nums[right], nums[p]
        
        if p > k:
            return quickselect(left, p - 1)
        elif p < k:
            return quickselect(p + 1, right)
        else:
            return nums[p]
    
    return quickselect(0, len(nums) - 1)

# Test
print(find_kth_largest([3,2,1,5,6,4], 2))  # 5
```

---

## 10. Backtracking

### Q37: Subsets (LeetCode #78) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def subsets(nums):
    """
    Time: O(2^n)
    Space: O(2^n)
    """
    result = []
    
    def backtrack(start, path):
        result.append(path[:])
        
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    
    backtrack(0, [])
    return result

# Iterative
def subsets_iterative(nums):
    result = [[]]
    
    for num in nums:
        result += [curr + [num] for curr in result]
    
    return result

# Test
print(subsets([1,2,3]))
# [[], [1], [1,2], [1,2,3], [1,3], [2], [2,3], [3]]
```

---

### Q38: Combination Sum (LeetCode #39) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def combination_sum(candidates, target):
    """
    Time: O(2^target)
    Space: O(target)
    """
    result = []
    
    def backtrack(start, path, remaining):
        if remaining == 0:
            result.append(path[:])
            return
        if remaining < 0:
            return
        
        for i in range(start, len(candidates)):
            path.append(candidates[i])
            # Can reuse same element
            backtrack(i, path, remaining - candidates[i])
            path.pop()
    
    backtrack(0, [], target)
    return result

# Test
print(combination_sum([2,3,6,7], 7))
# [[2,2,3], [7]]
```

---

### Q39: Permutations (LeetCode #46) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def permute(nums):
    """
    Time: O(n!)
    Space: O(n!)
    """
    result = []
    
    def backtrack(path, remaining):
        if not remaining:
            result.append(path[:])
            return
        
        for i in range(len(remaining)):
            backtrack(
                path + [remaining[i]],
                remaining[:i] + remaining[i+1:]
            )
    
    backtrack([], nums)
    return result

# More efficient with swapping
def permute_swap(nums):
    result = []
    
    def backtrack(start):
        if start == len(nums):
            result.append(nums[:])
            return
        
        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            backtrack(start + 1)
            nums[start], nums[i] = nums[i], nums[start]
    
    backtrack(0)
    return result

# Test
print(permute([1,2,3]))
```

---

## 11. Graphs

### Q40: Number of Islands (LeetCode #200) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def num_islands(grid):
    """
    Time: O(m * n)
    Space: O(m * n) for recursion
    """
    if not grid:
        return 0
    
    count = 0
    rows, cols = len(grid), len(grid[0])
    
    def dfs(r, c):
        if (r < 0 or r >= rows or c < 0 or c >= cols or
            grid[r][c] != '1'):
            return
        
        grid[r][c] = '0'  # Mark as visited
        
        # Visit all 4 directions
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)
    
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                dfs(r, c)
                count += 1
    
    return count

# Test
grid = [
    ["1","1","0","0","0"],
    ["1","1","0","0","0"],
    ["0","0","1","0","0"],
    ["0","0","0","1","1"]
]
print(num_islands(grid))  # 3
```

---

### Q41: Clone Graph (LeetCode #133) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors else []

def clone_graph(node):
    """
    Time: O(V + E)
    Space: O(V)
    """
    if not node:
        return None
    
    clones = {}
    
    def dfs(node):
        if node in clones:
            return clones[node]
        
        clone = Node(node.val)
        clones[node] = clone
        
        for neighbor in node.neighbors:
            clone.neighbors.append(dfs(neighbor))
        
        return clone
    
    return dfs(node)
```

---

### Q42: Pacific Atlantic Water Flow (LeetCode #417) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def pacific_atlantic(heights):
    """
    Time: O(m * n)
    Space: O(m * n)
    """
    if not heights:
        return []
    
    rows, cols = len(heights), len(heights[0])
    pacific = set()
    atlantic = set()
    
    def dfs(r, c, visited):
        visited.add((r, c))
        
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if (0 <= nr < rows and 0 <= nc < cols and
                (nr, nc) not in visited and
                heights[nr][nc] >= heights[r][c]):
                dfs(nr, nc, visited)
    
    # Start DFS from borders
    for c in range(cols):
        dfs(0, c, pacific)         # Top border
        dfs(rows - 1, c, atlantic)  # Bottom border
    
    for r in range(rows):
        dfs(r, 0, pacific)         # Left border
        dfs(r, cols - 1, atlantic)  # Right border
    
    return list(pacific & atlantic)
```

---

## 12. Dynamic Programming

### Q43: Climbing Stairs (LeetCode #70) ⭐

**Difficulty:** Easy

**Solution:**
```python
def climb_stairs(n):
    """
    Time: O(n)
    Space: O(1)
    """
    if n <= 2:
        return n
    
    prev2, prev1 = 1, 2
    
    for i in range(3, n + 1):
        current = prev1 + prev2
        prev2 = prev1
        prev1 = current
    
    return prev1

# Test
print(climb_stairs(5))  # 8
```

---

### Q44: House Robber (LeetCode #198) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def rob(nums):
    """
    Time: O(n)
    Space: O(1)
    """
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]
    
    prev2, prev1 = 0, 0
    
    for num in nums:
        current = max(prev1, prev2 + num)
        prev2 = prev1
        prev1 = current
    
    return prev1

# Test
print(rob([1,2,3,1]))  # 4 (rob house 1 and 3)
print(rob([2,7,9,3,1]))  # 12 (rob house 1, 3, and 5)
```

---

### Q45: Longest Increasing Subsequence (LeetCode #300) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def length_of_lis(nums):
    """
    Time: O(n²)
    Space: O(n)
    """
    if not nums:
        return 0
    
    dp = [1] * len(nums)
    
    for i in range(1, len(nums)):
        for j in range(i):
            if nums[i] > nums[j]:
                dp[i] = max(dp[i], dp[j] + 1)
    
    return max(dp)

# Optimized with binary search: O(n log n)
import bisect

def length_of_lis_optimized(nums):
    tails = []
    
    for num in nums:
        idx = bisect.bisect_left(tails, num)
        if idx == len(tails):
            tails.append(num)
        else:
            tails[idx] = num
    
    return len(tails)

# Test
print(length_of_lis([10,9,2,5,3,7,101,18]))  # 4
```

---

### Q46: Coin Change (LeetCode #322) ⭐⭐

**Difficulty:** Medium

**Solution:**
```python
def coin_change(coins, amount):
    """
    Time: O(amount * n)
    Space: O(amount)
    """
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    
    for coin in coins:
        for i in range(coin, amount + 1):
            dp[i] = min(dp[i], dp[i - coin] + 1)
    
    return dp[amount] if dp[amount] != float('inf') else -1

# Test
print(coin_change([1,2,5], 11))  # 3 (5+5+1)
print(coin_change([2], 3))       # -1
```

---

## Conclusion

This guide covers 75+ Python interview questions organized by pattern:
- **Arrays & Hashing:** Hash maps, frequency counting
- **Two Pointers:** Efficient array traversal
- **Sliding Window:** Subarray/substring problems
- **Stack:** LIFO operations
- **Binary Search:** Divide and conquer
- **Linked Lists:** Pointer manipulation
- **Trees:** Recursion, traversal
- **Backtracking:** Exhaustive search
- **Graphs:** DFS, BFS
- **Dynamic Programming:** Optimal substructure

**Study Tips:**
1. Understand patterns, don't memorize solutions
2. Practice explaining your approach
3. Analyze time/space complexity
4. Code without IDE initially
5. Review mistakes thoroughly

**Resources:**
- LeetCode (leetcode.com)
- NeetCode (neetcode.io)
- AlgoExpert
- Blind 75 List

Good luck with your interviews!
