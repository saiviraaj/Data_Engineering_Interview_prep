# 🎯 COMPLETE PYTHON PATTERNS & ALGORITHMS GUIDE
## Master Every Python Pattern for Data Engineering & Coding Interviews

**Purpose:** Exhaustive reference for solving ANY Python coding problem  
**Level:** Data Engineer / Software Engineer interviews  
**Coverage:** All patterns, data structures, algorithms, when to use what

---

## 📚 TABLE OF CONTENTS

**PART A: PYTHON PATTERNS & ALGORITHMS**
1. **PATTERN RECOGNITION FRAMEWORK** - Identify problem type instantly
2. **DATA STRUCTURES GUIDE** - When to use each structure
3. **ALGORITHM PATTERNS** - All common patterns with examples
4. **TWO POINTERS PATTERN** - Array/string problems
5. **SLIDING WINDOW** - Subarray/substring problems
6. **HASH MAP PATTERNS** - Fast lookup problems
7. **RECURSION & BACKTRACKING** - Combinatorial problems
8. **DYNAMIC PROGRAMMING** - Optimization problems
9. **GREEDY ALGORITHMS** - Local optimal → global optimal
10. **SORTING & SEARCHING** - Common patterns
11. **STRING MANIPULATION** - All string patterns
12. **TIME & SPACE COMPLEXITY** - Big O analysis

---

## 🎯 PART 1: PATTERN RECOGNITION FRAMEWORK

### **How to Identify Which Pattern to Use**

```
PROBLEM KEYWORDS → PATTERN → DATA STRUCTURE/TECHNIQUE
```

#### **Master Decision Tree:**

```
├─ Keywords: "two elements sum to", "pair", "complement"
│  └─ PATTERN: Hash Map or Two Pointers
│
├─ Keywords: "subarray", "substring", "contiguous"
│  ├─ Fixed size → Sliding Window (fixed)
│  └─ Variable size → Sliding Window (variable)
│
├─ Keywords: "all combinations", "all permutations", "generate all"
│  └─ PATTERN: Backtracking/Recursion
│
├─ Keywords: "minimum/maximum path", "optimal", "minimize/maximize"
│  └─ PATTERN: Dynamic Programming
│
├─ Keywords: "sorted array", "rotated", "search in sorted"
│  └─ PATTERN: Binary Search
│
├─ Keywords: "tree", "graph", "connected", "traverse"
│  └─ PATTERN: DFS or BFS
│
├─ Keywords: "top k", "k largest/smallest", "kth element"
│  └─ PATTERN: Heap (Priority Queue)
│
├─ Keywords: "overlapping intervals", "merge intervals"
│  └─ PATTERN: Sorting + Merging
│
├─ Keywords: "palindrome", "reverse"
│  └─ PATTERN: Two Pointers (opposite ends)
│
└─ Keywords: "frequency", "count", "duplicates"
   └─ PATTERN: Hash Map (Counter)
```

### **Pattern to Problem Mapping**

| **Pattern** | **When to Use** | **Time** | **Space** | **Example** |
|------------|-----------------|----------|-----------|-------------|
| **Hash Map** | Fast lookup, frequency counting | O(n) | O(n) | Two Sum, Anagrams |
| **Two Pointers** | Sorted array, palindrome, pairs | O(n) | O(1) | Container With Water |
| **Sliding Window** | Subarray/substring of size k | O(n) | O(1) | Max Sum Subarray |
| **Binary Search** | Sorted array search/optimization | O(log n) | O(1) | Search in Rotated |
| **DFS/BFS** | Trees, graphs, matrix traversal | O(V+E) | O(V) | Islands, Tree Level |
| **Dynamic Programming** | Optimization, count ways | O(n²) typically | O(n) | Fibonacci, Coin Change |
| **Backtracking** | Generate all solutions | O(2^n) | O(n) | Permutations, N-Queens |
| **Heap** | Top K, priority, median | O(n log k) | O(k) | K Largest Elements |
| **Union Find** | Connected components | O(α(n)) | O(n) | Network Connections |
| **Greedy** | Local optimal = global | O(n log n) | O(1) | Activity Selection |

---

## 📦 PART 2: DATA STRUCTURES GUIDE

### **2.1 When to Use Which Data Structure**

```
NEED → DATA STRUCTURE → OPERATIONS
├─ Fast lookup by key → Dictionary/Hash Map → O(1) get/set
├─ Fast lookup + ordering → OrderedDict → O(1) get, O(n) ordering
├─ Ordered unique elements → Set → O(1) add/lookup, automatic unique
├─ FIFO queue → deque/Queue → O(1) append/popleft
├─ LIFO stack → list or deque → O(1) append/pop
├─ Priority queue → heapq → O(log n) push/pop
├─ Range queries → Segment Tree → O(log n) query/update
├─ Prefix sums → Cumulative array → O(1) range sum
└─ Two-ended access → deque → O(1) both ends
```

### **2.2 Complete Data Structures Reference**

#### **Lists (Arrays)**

```python
# ========== Creation ==========
arr = []
arr = [1, 2, 3, 4, 5]
arr = [0] * 10  # [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
arr = list(range(1, 6))  # [1, 2, 3, 4, 5]

# ========== Common Operations ==========
# Append: O(1) amortized
arr.append(6)

# Insert: O(n)
arr.insert(0, 0)  # Insert at beginning
arr.insert(2, 99)  # Insert at index 2

# Pop: O(1) from end, O(n) from beginning
arr.pop()  # Remove and return last
arr.pop(0)  # Remove and return first (slow!)

# Remove: O(n)
arr.remove(3)  # Remove first occurrence of value 3

# Access: O(1)
first = arr[0]
last = arr[-1]

# Slicing: O(k) where k is slice length
subarray = arr[1:4]  # Elements at index 1, 2, 3
reversed_arr = arr[::-1]

# Search: O(n)
if 5 in arr:
    index = arr.index(5)

# ========== List Comprehension (IMPORTANT!) ==========
# Create new list with transformation
squared = [x**2 for x in arr]

# With condition
evens = [x for x in arr if x % 2 == 0]

# Nested
matrix = [[i*j for j in range(5)] for i in range(5)]

# ========== Sorting ==========
arr.sort()  # In-place, O(n log n)
arr.sort(reverse=True)
arr.sort(key=lambda x: -x)  # Custom sort

sorted_arr = sorted(arr)  # Returns new list
```

**When to use Lists:**
- ✅ Need indexed access
- ✅ Need to maintain order
- ✅ Need to append frequently
- ❌ Need fast insertion/deletion at beginning (use deque)
- ❌ Need fast lookup by value (use set/dict)

#### **Dictionaries (Hash Maps)**

```python
# ========== Creation ==========
d = {}
d = {"key": "value"}
d = dict(a=1, b=2, c=3)
d = {k: v for k, v in pairs}  # Dict comprehension

# ========== Operations ==========
# Set: O(1)
d["new_key"] = "new_value"

# Get: O(1)
value = d["key"]
value = d.get("key", "default")  # Safe get

# Check existence: O(1)
if "key" in d:
    pass

# Delete: O(1)
del d["key"]
value = d.pop("key", "default")

# Iterate
for key in d:
    print(key, d[key])

for key, value in d.items():
    print(key, value)

# ========== Useful Patterns ==========
# Count frequency
from collections import Counter
freq = Counter([1, 1, 2, 3, 3, 3])  # {1: 2, 2: 1, 3: 3}

# Default dict (auto-create values)
from collections import defaultdict
dd = defaultdict(int)  # Default value 0
dd = defaultdict(list)  # Default value []
dd = defaultdict(set)  # Default value set()

# Group by key
groups = defaultdict(list)
for item in items:
    groups[item.category].append(item)
```

**When to use Dictionaries:**
- ✅ Need fast lookup by key
- ✅ Need to count/track things
- ✅ Need key-value mapping
- ✅ Most common DS in interviews!
₹
#### **Sets**

```python
# ========== Creation ==========
s = set()
s = {1, 2, 3}
s = set([1, 2, 3, 3])  # {1, 2, 3} - auto unique

# ========== Operations ==========
# Add: O(1)
s.add(4)

# Remove: O(1)
s.remove(3)  # Raises error if not found
s.discard(3)  # No error if not found

# Check membership: O(1)
if 2 in s:
    pass

# Set operations
s1 = {1, 2, 3}
s2 = {2, 3, 4}

union = s1 | s2  # {1, 2, 3, 4}
intersection = s1 & s2  # {2, 3}
difference = s1 - s2  # {1}
symmetric_diff = s1 ^ s2  # {1, 4}
```

**When to use Sets:**
- ✅ Need to track unique elements
- ✅ Need fast membership testing
- ✅ Need set operations (union, intersection)
- ❌ Need ordering (use list)
- ❌ Need to access by index (use list)

#### **Deque (Double-Ended Queue)**

```python
from collections import deque

# ========== Creation ==========
dq = deque()
dq = deque([1, 2, 3])
dq = deque(maxlen=3)  # Fixed size, auto-removes old items

# ========== Operations (ALL O(1)) ==========
# Append
dq.append(4)  # Add to right
dq.appendleft(0)  # Add to left

# Pop
dq.pop()  # Remove from right
dq.popleft()  # Remove from left

# Peek
first = dq[0]
last = dq[-1]

# Rotate
dq.rotate(1)  # Rotate right
dq.rotate(-1)  # Rotate left
```

**When to use Deque:**
- ✅ Need queue (FIFO) - use appendleft and pop
- ✅ Need stack (LIFO) - use append and pop
- ✅ Sliding window with fixed size
- ✅ Need O(1) operations at both ends

#### **Heaps (Priority Queue)**

```python
import heapq

# ========== Min Heap (Default) ==========
heap = []
heapq.heappush(heap, 5)  # O(log n)
heapq.heappush(heap, 3)
heapq.heappush(heap, 7)

smallest = heapq.heappop(heap)  # O(log n), returns 3

# Heapify existing list: O(n)
nums = [5, 3, 7, 1]
heapq.heapify(nums)

# Peek at smallest: O(1)
smallest = heap[0]

# ========== Max Heap (Negate values) ==========
max_heap = []
heapq.heappush(max_heap, -5)  # Negate!
heapq.heappush(max_heap, -3)
largest = -heapq.heappop(max_heap)  # Negate again

# ========== N Largest/Smallest ==========
nums = [1, 8, 2, 23, 7, -4, 18, 23, 42, 37, 2]
largest_3 = heapq.nlargest(3, nums)  # [42, 37, 23]
smallest_3 = heapq.nsmallest(3, nums)  # [-4, 1, 2]
```

**When to use Heap:**
- ✅ Need kth largest/smallest
- ✅ Need priority queue
- ✅ Merge k sorted lists
- ✅ Running median

---

## 🎨 PART 3: ALGORITHM PATTERNS

### **Pattern 1: Two Pointers**

**When to use:**
- Sorted array
- Finding pairs
- Palindrome checking
- Removing duplicates in-place

```python
# ========== Template 1: Opposite Ends ==========
def two_pointer_opposite(arr):
    left, right = 0, len(arr) - 1
    
    while left < right:
        # Process elements at left and right
        if some_condition:
            left += 1
        else:
            right -= 1
    
    return result

# Example: Valid Palindrome
def is_palindrome(s):
    left, right = 0, len(s) - 1
    
    while left < right:
        # Skip non-alphanumeric
        while left < right and not s[left].isalnum():
            left += 1
        while left < right and not s[right].isalnum():
            right -= 1
        
        if s[left].lower() != s[right].lower():
            return False
        
        left += 1
        right -= 1
    
    return True

# Example: Two Sum II (sorted array)
def two_sum_sorted(numbers, target):
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

# ========== Template 2: Same Direction (Fast & Slow) ==========
def two_pointer_same_direction(arr):
    slow = fast = 0
    
    while fast < len(arr):
        # Move fast pointer
        fast += 1
        
        if some_condition:
            # Move slow pointer
            slow += 1
    
    return result

# Example: Remove Duplicates in-place
def remove_duplicates(nums):
    if not nums:
        return 0
    
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    
    return slow + 1

# Example: Move Zeroes
def move_zeroes(nums):
    slow = 0
    
    for fast in range(len(nums)):
        if nums[fast] != 0:
            nums[slow], nums[fast] = nums[fast], nums[slow]
            slow += 1
```

**Time Complexity:** O(n)  
**Space Complexity:** O(1)

---

### **Pattern 2: Sliding Window**

**When to use:**
- Subarray/substring problems
- "Maximum/minimum sum of subarray of size k"
- "Longest substring with k distinct characters"

```python
# ========== Template 1: Fixed Size Window ==========
def fixed_window(arr, k):
    window_sum = sum(arr[:k])  # Initial window
    max_sum = window_sum
    
    for i in range(k, len(arr)):
        # Slide window: remove left, add right
        window_sum = window_sum - arr[i - k] + arr[i]
        max_sum = max(max_sum, window_sum)
    
    return max_sum

# Example: Maximum Sum Subarray of Size K
def max_sum_subarray(arr, k):
    window_sum = sum(arr[:k])
    max_sum = window_sum
    
    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i - k]
        max_sum = max(max_sum, window_sum)
    
    return max_sum

# ========== Template 2: Variable Size Window ==========
def variable_window(arr):
    left = 0
    result = 0
    window_state = {}  # Track window contents
    
    for right in range(len(arr)):
        # Expand window
        # Update window_state
        
        # Shrink window while invalid
        while not is_valid(window_state):
            # Update window_state
            left += 1
        
        # Update result
        result = max(result, right - left + 1)
    
    return result

# Example: Longest Substring Without Repeating Characters
def length_of_longest_substring(s):
    char_set = set()
    left = 0
    max_length = 0
    
    for right in range(len(s)):
        # Shrink while duplicate exists
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        
        char_set.add(s[right])
        max_length = max(max_length, right - left + 1)
    
    return max_length

# Example: Minimum Window Substring
def min_window(s, t):
    from collections import Counter
    
    need = Counter(t)
    have = {}
    required = len(need)
    formed = 0
    
    left = 0
    min_len = float('inf')
    min_window = ""
    
    for right in range(len(s)):
        char = s[right]
        have[char] = have.get(char, 0) + 1
        
        if char in need and have[char] == need[char]:
            formed += 1
        
        # Shrink window while valid
        while formed == required:
            # Update result
            if right - left + 1 < min_len:
                min_len = right - left + 1
                min_window = s[left:right + 1]
            
            # Remove from left
            char = s[left]
            have[char] -= 1
            if char in need and have[char] < need[char]:
                formed -= 1
            left += 1
    
    return min_window
```

**Time Complexity:** O(n)  
**Space Complexity:** O(k) where k is window size or unique elements

---

### **Pattern 3: Hash Map**

**When to use:**
- Need O(1) lookup
- Counting/frequency
- Finding complements/pairs
- Grouping by key

```python
# ========== Template: Two Sum Pattern ==========
def two_sum(nums, target):
    seen = {}  # value -> index
    
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    
    return []

# ========== Template: Frequency Counting ==========
def frequency_count(items):
    from collections import Counter
    
    # Method 1: Manual
    freq = {}
    for item in items:
        freq[item] = freq.get(item, 0) + 1
    
    # Method 2: Counter (preferred)
    freq = Counter(items)
    
    return freq

# Example: Group Anagrams
def group_anagrams(strs):
    from collections import defaultdict
    
    anagrams = defaultdict(list)
    
    for s in strs:
        # Sort as key
        key = ''.join(sorted(s))
        anagrams[key].append(s)
    
    return list(anagrams.values())

# Example: First Non-Repeating Character
def first_uniq_char(s):
    from collections import Counter
    
    count = Counter(s)
    
    for i, char in enumerate(s):
        if count[char] == 1:
            return i
    
    return -1

# ========== Template: Prefix Sum with Hash Map ==========
def subarray_sum_equals_k(nums, k):
    count = 0
    prefix_sum = 0
    sum_count = {0: 1}  # prefix_sum -> frequency
    
    for num in nums:
        prefix_sum += num
        
        # Check if (prefix_sum - k) exists
        if prefix_sum - k in sum_count:
            count += sum_count[prefix_sum - k]
        
        sum_count[prefix_sum] = sum_count.get(prefix_sum, 0) + 1
    
    return count
```

---

### **Pattern 4: Binary Search**

**When to use:**
- Sorted array
- Find target or insert position
- Search space reduction

```python
# ========== Template: Classic Binary Search ==========
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = left + (right - left) // 2  # Avoid overflow
        
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

# ========== Template: Find Insert Position ==========
def search_insert(nums, target):
    left, right = 0, len(nums)
    
    while left < right:
        mid = left + (right - left) // 2
        
        if nums[mid] < target:
            left = mid + 1
        else:
            right = mid
    
    return left

# Example: Search in Rotated Sorted Array
def search_rotated(nums, target):
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
```

**Time Complexity:** O(log n)  
**Space Complexity:** O(1)

---

### **Pattern 5: Backtracking**

**When to use:**
- Generate all combinations/permutations
- Find all solutions
- Constraint satisfaction

```python
# ========== Template: Backtracking ==========
def backtrack(result, path, choices):
    # Base case
    if is_solution(path):
        result.append(path[:])  # Copy!
        return
    
    # Try each choice
    for choice in choices:
        if is_valid(choice, path):
            # Choose
            path.append(choice)
            
            # Explore
            backtrack(result, path, updated_choices)
            
            # Unchoose (backtrack)
            path.pop()

# Example: Permutations
def permute(nums):
    result = []
    
    def backtrack(path, remaining):
        if not remaining:
            result.append(path[:])
            return
        
        for i in range(len(remaining)):
            # Choose
            path.append(remaining[i])
            # Explore
            backtrack(path, remaining[:i] + remaining[i+1:])
            # Unchoose
            path.pop()
    
    backtrack([], nums)
    return result

# Example: Subsets
def subsets(nums):
    result = []
    
    def backtrack(start, path):
        result.append(path[:])
        
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    
    backtrack(0, [])
    return result

# Example: Combination Sum
def combination_sum(candidates, target):
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
```

**Time Complexity:** O(2^n) for subsets, O(n!) for permutations  
**Space Complexity:** O(n) for recursion depth

---

### **Pattern 6: Dynamic Programming**

**When to use:**
- Optimization problems (min/max)
- Counting problems (how many ways)
- Has overlapping subproblems
- Has optimal substructure

```python
# ========== Template: 1D DP ==========
def dp_1d(n):
    dp = [0] * (n + 1)
    dp[0] = base_case
    
    for i in range(1, n + 1):
        dp[i] = transition(dp[i-1], ...)
    
    return dp[n]

# Example: Fibonacci
def fib(n):
    if n <= 1:
        return n
    
    dp = [0] * (n + 1)
    dp[1] = 1
    
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    
    return dp[n]

# Space optimized
def fib_optimized(n):
    if n <= 1:
        return n
    
    prev2, prev1 = 0, 1
    
    for i in range(2, n + 1):
        current = prev1 + prev2
        prev2 = prev1
        prev1 = current
    
    return prev1

# ========== Template: 2D DP ==========
def dp_2d(m, n):
    dp = [[0] * n for _ in range(m)]
    
    # Base cases
    for i in range(m):
        dp[i][0] = ...
    for j in range(n):
        dp[0][j] = ...
    
    # Fill table
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = transition(dp[i-1][j], dp[i][j-1], ...)
    
    return dp[m-1][n-1]

# Example: Longest Common Subsequence
def longest_common_subsequence(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    return dp[m][n]

# Example: Coin Change
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    
    for i in range(1, amount + 1):
        for coin in coins:
            if coin <= i:
                dp[i] = min(dp[i], dp[i - coin] + 1)
    
    return dp[amount] if dp[amount] != float('inf') else -1
```

**Common DP Patterns:**
1. Fibonacci-like: `dp[i] = dp[i-1] + dp[i-2]`
2. Kadane's (max subarray): `dp[i] = max(nums[i], dp[i-1] + nums[i])`
3. Knapsack: `dp[i][w] = max(dp[i-1][w], dp[i-1][w-weight[i]] + value[i])`
4. LCS: `dp[i][j] = dp[i-1][j-1] + 1 if match else max(dp[i-1][j], dp[i][j-1])`

---

## 📋 QUICK DECISION MATRIX

```
PROBLEM TYPE → PATTERN → TIME → SPACE
├─ Two elements sum → Hash Map → O(n) → O(n)
├─ Pair in sorted array → Two Pointers → O(n) → O(1)
├─ Max subarray size k → Sliding Window → O(n) → O(1)
├─ Find kth largest → Heap → O(n log k) → O(k)
├─ All combinations → Backtracking → O(2^n) → O(n)
├─ Optimal path → Dynamic Programming → O(n²) → O(n²)
├─ Search sorted → Binary Search → O(log n) → O(1)
├─ Count frequency → Counter → O(n) → O(n)
└─ Remove duplicates → Set or Two Pointers → O(n) → varies
```

---

*[Document continues with Parts 7-12 covering: Recursion, Greedy, Sorting, Strings, Complexity Analysis]*

---

## 🎯 INTERVIEW STRATEGY

**When given a problem:**

1. **Identify pattern** (use keyword mapping)
2. **Choose data structure** (based on operations needed)
3. **Start with brute force** (explain, then optimize)
4. **Analyze complexity** (time & space)
5. **Test edge cases** (empty, single element, duplicates)

**Always explain:**
- Why this approach is optimal
- Trade-offs (time vs space)
- Alternative solutions

---

**STATUS:** Part 1 Complete! Ready for Pandas guide next! 🎉
