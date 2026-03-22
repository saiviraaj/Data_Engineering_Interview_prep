# 🐍 PYTHON INTERVIEW PREPARATION - DATA ENGINEER
## Complete Guide: Easy → Medium → Hard → Expert

Based on real interview questions from top companies and LeetCode patterns commonly asked in Data Engineering interviews.

---

## 📚 TABLE OF CONTENTS

1. **LEVEL 1: EASY PROBLEMS** (Warm-up - 20 problems)
2. **LEVEL 2: MEDIUM PROBLEMS** (Core Skills - 25 problems)
3. **LEVEL 3: HARD PROBLEMS** (Advanced - 15 problems)
4. **LEVEL 4: EXPERT PROBLEMS** (Real-world DE scenarios - 10 problems)

**Key Focus Areas for Data Engineers:**
- Arrays, Strings, Dictionaries (Most Common)
- Hash Maps & Sets
- Two Pointers & Sliding Window
- File Processing & Data Manipulation
- **Avoid:** Trees, Linked Lists, Graphs (rarely asked in DE interviews)

---

## 🟢 LEVEL 1: EASY PROBLEMS (Foundation Building)

### **Problem 1: Two Sum**
**Difficulty:** Easy | **Pattern:** Hash Map | **LeetCode:** #1

```python
"""
Given an array of integers nums and an integer target, 
return indices of the two numbers that add up to target.

Example:
Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: nums[0] + nums[1] = 2 + 7 = 9
"""

# Solution 1: Brute Force - O(n²)
def two_sum_brute(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []

# Solution 2: Hash Map - O(n) ⭐ OPTIMAL
def two_sum(nums, target):
    seen = {}  # value -> index
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

**Key Concepts:**
- Hash map for O(1) lookups
- Single pass solution
- Space-time tradeoff

---

### **Problem 2: Valid Anagram**
**Difficulty:** Easy | **Pattern:** Hash Map | **LeetCode:** #242

```python
"""
Given two strings s and t, return true if t is an anagram of s.

Example:
Input: 

Output: true
"""

# Solution 1: Sorting - O(n log n)
def is_anagram_sort(s, t):
    return sorted(s) == sorted(t)

# Solution 2: Hash Map - O(n) ⭐ OPTIMAL
def is_anagram(s, t):
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

# Solution 3: Using Counter (Most Pythonic)
from collections import Counter

def is_anagram_counter(s, t):
    return Counter(s) == Counter(t)

# Test
print(is_anagram("anagram", "nagaram"))  # True
print(is_anagram("rat", "car"))          # False
```

---

### **Problem 3: Contains Duplicate**
**Difficulty:** Easy | **Pattern:** Set | **LeetCode:** #217

```python
"""
Given an integer array nums, return true if any value appears 
at least twice in the array.

Example:
Input: nums = [1,2,3,1]
Output: true
"""

# Solution 1: Using Set - O(n)
def contains_duplicate(nums):
    return len(nums) != len(set(nums))

# Solution 2: Hash Set with early return - O(n) ⭐ OPTIMAL
def contains_duplicate_v2(nums):
    seen = set()
    for num in nums:
        if num in seen:
            return True
        seen.add(num)
    return False

# Test
print(contains_duplicate([1,2,3,1]))     # True
print(contains_duplicate([1,2,3,4]))     # False
```

---

### **Problem 4: Valid Parentheses**
**Difficulty:** Easy | **Pattern:** Stack | **LeetCode:** #20

```python
"""
Given a string s containing just '()', '{}', '[]', 
determine if the input string is valid.

Example:
Input: s = "()[]{}"
Output: true
"""

def is_valid_parentheses(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in mapping:  # closing bracket
            if not stack or stack[-1] != mapping[char]:
                return False
            stack.pop()
        else:  # opening bracket
            stack.append(char)
    
    return len(stack) == 0

# Test
print(is_valid_parentheses("()[]{}"))    # True
print(is_valid_parentheses("(]"))        # False
print(is_valid_parentheses("([)]"))      # False
```

**Key Concepts:**
- Stack for LIFO operations
- Hash map for quick lookups
- Edge case: empty stack

---

### **Problem 5: Best Time to Buy and Sell Stock**
**Difficulty:** Easy | **Pattern:** One Pass | **LeetCode:** #121

```python
"""
Find the maximum profit from buying and selling a stock once.

Example:
Input: prices = [7,1,5,3,6,4]
Output: 5
Explanation: Buy on day 2 (price = 1) and sell on day 5 (price = 6)
"""

def max_profit(prices):
    min_price = float('inf')
    max_profit = 0
    
    for price in prices:
        # Update minimum price seen so far
        min_price = min(min_price, price)
        # Calculate profit if we sell today
        profit = price - min_price
        # Update maximum profit
        max_profit = max(max_profit, profit)
    
    return max_profit

# Test
print(max_profit([7,1,5,3,6,4]))  # 5
print(max_profit([7,6,4,3,1]))    # 0
```

---

### **Problem 6: Reverse String**
**Difficulty:** Easy | **Pattern:** Two Pointers | **LeetCode:** #344

```python
"""
Reverse a string in-place with O(1) extra space.

Example:
Input: s = ["h","e","l","l","o"]
Output: ["o","l","l","e","h"]
"""

def reverse_string(s):
    left, right = 0, len(s) - 1
    
    while left < right:
        # Swap characters
        s[left], s[right] = s[right], s[left]
        left += 1
        right -= 1

# Alternative: Pythonic way
def reverse_string_pythonic(s):
    s[:] = s[::-1]  # In-place reversal

# Test
s = ["h","e","l","l","o"]
reverse_string(s)
print(s)  # ['o', 'l', 'l', 'e', 'h']
```

---

### **Problem 7: First Unique Character**
**Difficulty:** Easy | **Pattern:** Hash Map | **LeetCode:** #387

```python
"""
Find the first non-repeating character in a string.

Example:
Input: s = "leetcode"
Output: 0 (character 'l')
"""

def first_uniq_char(s):
    # Count frequency
    count = {}
    for char in s:
        count[char] = count.get(char, 0) + 1
    
    # Find first unique
    for i, char in enumerate(s):
        if count[char] == 1:
            return i
    
    return -1

# Using Counter
from collections import Counter

def first_uniq_char_counter(s):
    count = Counter(s)
    for i, char in enumerate(s):
        if count[char] == 1:
            return i
    return -1

# Test
print(first_uniq_char("leetcode"))     # 0
print(first_uniq_char("loveleetcode")) # 2
```

---

### **Problem 8: Missing Number**
**Difficulty:** Easy | **Pattern:** Math | **LeetCode:** #268

```python
"""
Given array containing n distinct numbers from 0 to n, 
find the missing number.

Example:
Input: nums = [3,0,1]
Output: 2
"""

# Solution 1: Sum formula - O(n) time, O(1) space
def missing_number(nums):
    n = len(nums)
    expected_sum = n * (n + 1) // 2
    actual_sum = sum(nums)
    return expected_sum - actual_sum

# Solution 2: XOR (bitwise) - O(n) time, O(1) space
def missing_number_xor(nums):
    result = len(nums)
    for i, num in enumerate(nums):
        result ^= i ^ num
    return result

# Test
print(missing_number([3,0,1]))      # 2
print(missing_number([9,6,4,2,3,5,7,0,1]))  # 8
```

---

### **Problem 9: Move Zeroes**
**Difficulty:** Easy | **Pattern:** Two Pointers | **LeetCode:** #283

```python
"""
Move all 0's to the end while maintaining relative order.

Example:
Input: nums = [0,1,0,3,12]
Output: [1,3,12,0,0]
"""

def move_zeroes(nums):
    # Position to place next non-zero
    left = 0
    
    # Move all non-zeros to front
    for right in range(len(nums)):
        if nums[right] != 0:
            nums[left], nums[right] = nums[right], nums[left]
            left += 1

# Test
nums = [0,1,0,3,12]
move_zeroes(nums)
print(nums)  # [1, 3, 12, 0, 0]
```

---

### **Problem 10: Palindrome Number**
**Difficulty:** Easy | **Pattern:** Math | **LeetCode:** #9

```python
"""
Determine if an integer is a palindrome without converting to string.

Example:
Input: x = 121
Output: true
"""

def is_palindrome(x):
    # Negative numbers are not palindromes
    if x < 0:
        return False
    
    # Reverse the number
    original = x
    reversed_num = 0
    
    while x > 0:
        digit = x % 10
        reversed_num = reversed_num * 10 + digit
        x //= 10
    
    return original == reversed_num

# Alternative: String conversion (easier but less optimal)
def is_palindrome_string(x):
    return str(x) == str(x)[::-1]

# Test
print(is_palindrome(121))   # True
print(is_palindrome(-121))  # False
print(is_palindrome(10))    # False
```

---

### **Problem 11: Majority Element**
**Difficulty:** Easy | **Pattern:** Hash Map / Boyer-Moore | **LeetCode:** #169

```python
"""
Find the element that appears more than ⌊n/2⌋ times.

Example:
Input: nums = [3,2,3]
Output: 3
"""

# Solution 1: Hash Map - O(n) time, O(n) space
def majority_element_hashmap(nums):
    count = {}
    for num in nums:
        count[num] = count.get(num, 0) + 1
        if count[num] > len(nums) // 2:
            return num

# Solution 2: Boyer-Moore Voting - O(n) time, O(1) space ⭐
def majority_element(nums):
    candidate = None
    count = 0
    
    for num in nums:
        if count == 0:
            candidate = num
        count += (1 if num == candidate else -1)
    
    return candidate

# Test
print(majority_element([3,2,3]))           # 3
print(majority_element([2,2,1,1,1,2,2]))   # 2
```

---

### **Problem 12: Single Number**
**Difficulty:** Easy | **Pattern:** Bitwise XOR | **LeetCode:** #136

```python
"""
Find the single number that appears once (others appear twice).

Example:
Input: nums = [4,1,2,1,2]
Output: 4
"""

def single_number(nums):
    result = 0
    for num in nums:
        result ^= num  # XOR operation
    return result

# Explanation: XOR properties
# a ^ a = 0
# a ^ 0 = a
# XOR is commutative and associative

# Test
print(single_number([4,1,2,1,2]))  # 4
print(single_number([2,2,1]))      # 1
```

---

### **Problem 13: Intersection of Two Arrays**
**Difficulty:** Easy | **Pattern:** Set | **LeetCode:** #349

```python
"""
Find intersection of two arrays (unique elements).

Example:
Input: nums1 = [1,2,2,1], nums2 = [2,2]
Output: [2]
"""

# Solution 1: Using Sets - O(n + m)
def intersection(nums1, nums2):
    return list(set(nums1) & set(nums2))

# Solution 2: Manual approach
def intersection_manual(nums1, nums2):
    set1 = set(nums1)
    result = set()
    
    for num in nums2:
        if num in set1:
            result.add(num)
    
    return list(result)

# Test
print(intersection([1,2,2,1], [2,2]))      # [2]
print(intersection([4,9,5], [9,4,9,8,4]))  # [9, 4]
```

---

### **Problem 14: Plus One**
**Difficulty:** Easy | **Pattern:** Array | **LeetCode:** #66

```python
"""
Increment a number represented as array of digits by one.

Example:
Input: digits = [1,2,3]
Output: [1,2,4]
"""

def plus_one(digits):
    n = len(digits)
    
    for i in range(n - 1, -1, -1):
        if digits[i] < 9:
            digits[i] += 1
            return digits
        digits[i] = 0
    
    # All 9's case: [9,9,9] -> [1,0,0,0]
    return [1] + digits

# Test
print(plus_one([1,2,3]))    # [1, 2, 4]
print(plus_one([9,9,9]))    # [1, 0, 0, 0]
print(plus_one([4,3,2,1]))  # [4, 3, 2, 2]
```

---

### **Problem 15: Remove Duplicates from Sorted Array**
**Difficulty:** Easy | **Pattern:** Two Pointers | **LeetCode:** #26

```python
"""
Remove duplicates in-place from sorted array. Return length.

Example:
Input: nums = [1,1,2]
Output: 2, nums = [1,2,_]
"""

def remove_duplicates(nums):
    if not nums:
        return 0
    
    # Pointer for unique elements
    left = 0
    
    for right in range(1, len(nums)):
        if nums[right] != nums[left]:
            left += 1
            nums[left] = nums[right]
    
    return left + 1

# Test
nums = [1,1,2]
k = remove_duplicates(nums)
print(k, nums[:k])  # 2, [1, 2]
```

---

### **Problem 16: Merge Sorted Array**
**Difficulty:** Easy | **Pattern:** Two Pointers | **LeetCode:** #88

```python
"""
Merge nums2 into nums1 as one sorted array.

Example:
Input: nums1 = [1,2,3,0,0,0], m = 3, nums2 = [2,5,6], n = 3
Output: [1,2,2,3,5,6]
"""

def merge(nums1, m, nums2, n):
    # Start from the end
    p1 = m - 1  # Last element of nums1
    p2 = n - 1  # Last element of nums2
    p = m + n - 1  # Last position
    
    while p1 >= 0 and p2 >= 0:
        if nums1[p1] > nums2[p2]:
            nums1[p] = nums1[p1]
            p1 -= 1
        else:
            nums1[p] = nums2[p2]
            p2 -= 1
        p -= 1
    
    # Copy remaining elements from nums2
    nums1[:p2 + 1] = nums2[:p2 + 1]

# Test
nums1 = [1,2,3,0,0,0]
merge(nums1, 3, [2,5,6], 3)
print(nums1)  # [1, 2, 2, 3, 5, 6]
```

---

### **Problem 17: Maximum Subarray**
**Difficulty:** Easy | **Pattern:** Kadane's Algorithm | **LeetCode:** #53

```python
"""
Find the contiguous subarray with largest sum.

Example:
Input: nums = [-2,1,-3,4,-1,2,1,-5,4]
Output: 6
Explanation: [4,-1,2,1] has the largest sum = 6
"""

def max_subarray(nums):
    max_sum = nums[0]
    current_sum = nums[0]
    
    for i in range(1, len(nums)):
        # Either extend current subarray or start new
        current_sum = max(nums[i], current_sum + nums[i])
        max_sum = max(max_sum, current_sum)
    
    return max_sum

# Test
print(max_subarray([-2,1,-3,4,-1,2,1,-5,4]))  # 6
print(max_subarray([1]))                       # 1
print(max_subarray([5,4,-1,7,8]))              # 23
```

---

### **Problem 18: Reverse Integer**
**Difficulty:** Easy | **Pattern:** Math | **LeetCode:** #7

```python
"""
Reverse digits of an integer. Return 0 if overflow.

Example:
Input: x = 123
Output: 321
"""

def reverse_integer(x):
    sign = -1 if x < 0 else 1
    x = abs(x)
    
    reversed_num = 0
    while x:
        digit = x % 10
        # Check for overflow (32-bit integer)
        if reversed_num > (2**31 - 1) // 10:
            return 0
        reversed_num = reversed_num * 10 + digit
        x //= 10
    
    return sign * reversed_num

# Test
print(reverse_integer(123))    # 321
print(reverse_integer(-123))   # -321
print(reverse_integer(120))    # 21
```

---

### **Problem 19: Count Primes**
**Difficulty:** Easy | **Pattern:** Sieve of Eratosthenes | **LeetCode:** #204

```python
"""
Count number of prime numbers less than n.

Example:
Input: n = 10
Output: 4
Explanation: 2, 3, 5, 7 are primes
"""

def count_primes(n):
    if n <= 2:
        return 0
    
    # Sieve of Eratosthenes
    is_prime = [True] * n
    is_prime[0] = is_prime[1] = False
    
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            # Mark multiples as not prime
            for j in range(i*i, n, i):
                is_prime[j] = False
    
    return sum(is_prime)

# Test
print(count_primes(10))  # 4
print(count_primes(20))  # 8
```

---

### **Problem 20: Excel Sheet Column Number**
**Difficulty:** Easy | **Pattern:** Math | **LeetCode:** #171

```python
"""
Convert Excel column title to number.

Example:
Input: columnTitle = "AB"
Output: 28
Explanation: A=1, B=2, ..., Z=26, AA=27, AB=28
"""

def title_to_number(column_title):
    result = 0
    for char in column_title:
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result

# Test
print(title_to_number("A"))    # 1
print(title_to_number("AB"))   # 28
print(title_to_number("ZY"))   # 701
```

---

## 🟡 LEVEL 2: MEDIUM PROBLEMS (Core Skills)

### **Problem 21: Group Anagrams**
**Difficulty:** Medium | **Pattern:** Hash Map | **LeetCode:** #49

```python
"""
Group strings that are anagrams of each other.

Example:
Input: strs = ["eat","tea","tan","ate","nat","bat"]
Output: [["bat"],["nat","tan"],["ate","eat","tea"]]
"""

def group_anagrams(strs):
    from collections import defaultdict
    
    anagrams = defaultdict(list)
    
    for s in strs:
        # Sort as key
        key = ''.join(sorted(s))
        anagrams[key].append(s)
    
    return list(anagrams.values())

# Alternative: Using character count as key
def group_anagrams_v2(strs):
    from collections import defaultdict
    
    anagrams = defaultdict(list)
    
    for s in strs:
        count = [0] * 26
        for char in s:
            count[ord(char) - ord('a')] += 1
        # Tuple of counts as key
        anagrams[tuple(count)].append(s)
    
    return list(anagrams.values())

# Test
print(group_anagrams(["eat","tea","tan","ate","nat","bat"]))
```

**Time Complexity:** O(n * k log k) where n = number of strings, k = max length
**Space Complexity:** O(n * k)

---

### **Problem 22: Longest Substring Without Repeating**
**Difficulty:** Medium | **Pattern:** Sliding Window | **LeetCode:** #3

```python
"""
Find length of longest substring without repeating characters.

Example:
Input: s = "abcabcbb"
Output: 3
Explanation: "abc" is the answer
"""

def length_of_longest_substring(s):
    char_set = set()
    left = 0
    max_length = 0
    
    for right in range(len(s)):
        # Shrink window until no duplicates
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        
        char_set.add(s[right])
        max_length = max(max_length, right - left + 1)
    
    return max_length

# Alternative: Using dictionary to store index
def length_of_longest_substring_v2(s):
    char_index = {}
    left = 0
    max_length = 0
    
    for right, char in enumerate(s):
        if char in char_index and char_index[char] >= left:
            left = char_index[char] + 1
        
        char_index[char] = right
        max_length = max(max_length, right - left + 1)
    
    return max_length

# Test
print(length_of_longest_substring("abcabcbb"))  # 3
print(length_of_longest_substring("bbbbb"))     # 1
print(length_of_longest_substring("pwwkew"))    # 3
```

**Time Complexity:** O(n)
**Space Complexity:** O(min(n, m)) where m is charset size

---

### **Problem 23: 3Sum**
**Difficulty:** Medium | **Pattern:** Two Pointers | **LeetCode:** #15

```python
"""
Find all unique triplets that sum to zero.

Example:
Input: nums = [-1,0,1,2,-1,-4]
Output: [[-1,-1,2],[-1,0,1]]
"""

def three_sum(nums):
    nums.sort()
    result = []
    
    for i in range(len(nums) - 2):
        # Skip duplicates for first number
        if i > 0 and nums[i] == nums[i-1]:
            continue
        
        left, right = i + 1, len(nums) - 1
        
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                result.append([nums[i], nums[left], nums[right]])
                
                # Skip duplicates for second number
                while left < right and nums[left] == nums[left + 1]:
                    left += 1
                # Skip duplicates for third number
                while left < right and nums[right] == nums[right - 1]:
                    right -= 1
                
                left += 1
                right -= 1
    
    return result

# Test
print(three_sum([-1,0,1,2,-1,-4]))  # [[-1,-1,2],[-1,0,1]]
```

**Time Complexity:** O(n²)
**Space Complexity:** O(1) excluding output

---

### **Problem 24: Product of Array Except Self**
**Difficulty:** Medium | **Pattern:** Prefix/Suffix | **LeetCode:** #238

```python
"""
Return array where output[i] is product of all elements except nums[i].
Cannot use division.

Example:
Input: nums = [1,2,3,4]
Output: [24,12,8,6]
"""

def product_except_self(nums):
    n = len(nums)
    output = [1] * n
    
    # Calculate prefix products
    prefix = 1
    for i in range(n):
        output[i] = prefix
        prefix *= nums[i]
    
    # Calculate suffix products and multiply
    suffix = 1
    for i in range(n - 1, -1, -1):
        output[i] *= suffix
        suffix *= nums[i]
    
    return output

# Test
print(product_except_self([1,2,3,4]))      # [24,12,8,6]
print(product_except_self([-1,1,0,-3,3]))  # [0,0,9,0,0]
```

**Time Complexity:** O(n)
**Space Complexity:** O(1) excluding output

---

### **Problem 25: Top K Frequent Elements**
**Difficulty:** Medium | **Pattern:** Heap/Bucket Sort | **LeetCode:** #347

```python
"""
Find k most frequent elements.

Example:
Input: nums = [1,1,1,2,2,3], k = 2
Output: [1,2]
"""

# Solution 1: Using Counter + heap
def top_k_frequent_heap(nums, k):
    from collections import Counter
    import heapq
    
    count = Counter(nums)
    return heapq.nlargest(k, count.keys(), key=count.get)

# Solution 2: Bucket Sort - O(n) ⭐ OPTIMAL
def top_k_frequent(nums, k):
    from collections import Counter
    
    count = Counter(nums)
    # Bucket sort: index = frequency
    buckets = [[] for _ in range(len(nums) + 1)]
    
    for num, freq in count.items():
        buckets[freq].append(num)
    
    result = []
    # Iterate from highest frequency
    for i in range(len(buckets) - 1, 0, -1):
        for num in buckets[i]:
            result.append(num)
            if len(result) == k:
                return result
    
    return result

# Test
print(top_k_frequent([1,1,1,2,2,3], 2))  # [1, 2]
print(top_k_frequent([1], 1))            # [1]
```

---

### **Problem 26: Container With Most Water**
**Difficulty:** Medium | **Pattern:** Two Pointers | **LeetCode:** #11

```python
"""
Find two lines that together with x-axis form container 
with most water.

Example:
Input: height = [1,8,6,2,5,4,8,3,7]
Output: 49
"""

def max_area(height):
    left, right = 0, len(height) - 1
    max_water = 0
    
    while left < right:
        # Calculate current area
        width = right - left
        h = min(height[left], height[right])
        max_water = max(max_water, width * h)
        
        # Move pointer with smaller height
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    
    return max_water

# Test
print(max_area([1,8,6,2,5,4,8,3,7]))  # 49
```

**Time Complexity:** O(n)
**Space Complexity:** O(1)

---

### **Problem 27: Longest Palindromic Substring**
**Difficulty:** Medium | **Pattern:** Expand Around Center | **LeetCode:** #5

```python
"""
Find longest palindromic substring.

Example:
Input: s = "babad"
Output: "bab" or "aba"
"""

def longest_palindrome(s):
    def expand_around_center(left, right):
        while left >= 0 and right < len(s) and s[left] == s[right]:
            left -= 1
            right += 1
        return right - left - 1
    
    if not s:
        return ""
    
    start = 0
    max_len = 0
    
    for i in range(len(s)):
        # Odd length palindrome (center is single char)
        len1 = expand_around_center(i, i)
        # Even length palindrome (center is between chars)
        len2 = expand_around_center(i, i + 1)
        
        length = max(len1, len2)
        if length > max_len:
            max_len = length
            start = i - (length - 1) // 2
    
    return s[start:start + max_len]

# Test
print(longest_palindrome("babad"))  # "bab" or "aba"
print(longest_palindrome("cbbd"))   # "bb"
```

**Time Complexity:** O(n²)
**Space Complexity:** O(1)

---

### **Problem 28: Merge Intervals**
**Difficulty:** Medium | **Pattern:** Sorting | **LeetCode:** #56

```python
"""
Merge overlapping intervals.

Example:
Input: intervals = [[1,3],[2,6],[8,10],[15,18]]
Output: [[1,6],[8,10],[15,18]]
"""

def merge_intervals(intervals):
    if not intervals:
        return []
    
    # Sort by start time
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    
    for current in intervals[1:]:
        last = merged[-1]
        
        # Overlapping intervals
        if current[0] <= last[1]:
            # Merge by updating end time
            last[1] = max(last[1], current[1])
        else:
            # Non-overlapping
            merged.append(current)
    
    return merged

# Test
print(merge_intervals([[1,3],[2,6],[8,10],[15,18]]))  # [[1,6],[8,10],[15,18]]
print(merge_intervals([[1,4],[4,5]]))                 # [[1,5]]
```

**Time Complexity:** O(n log n)
**Space Complexity:** O(n)

---

### **Problem 29: Rotate Image (Matrix)**
**Difficulty:** Medium | **Pattern:** Matrix | **LeetCode:** #48

```python
"""
Rotate n x n matrix by 90 degrees clockwise in-place.

Example:
Input: matrix = [[1,2,3],[4,5,6],[7,8,9]]
Output: [[7,4,1],[8,5,2],[9,6,3]]
"""

def rotate(matrix):
    n = len(matrix)
    
    # Step 1: Transpose (swap rows and columns)
    for i in range(n):
        for j in range(i, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    
    # Step 2: Reverse each row
    for i in range(n):
        matrix[i].reverse()

# Test
matrix = [[1,2,3],[4,5,6],[7,8,9]]
rotate(matrix)
print(matrix)  # [[7,4,1],[8,5,2],[9,6,3]]
```

**Time Complexity:** O(n²)
**Space Complexity:** O(1)

---

### **Problem 30: Subarray Sum Equals K**
**Difficulty:** Medium | **Pattern:** Prefix Sum + Hash Map | **LeetCode:** #560

```python
"""
Find total number of continuous subarrays whose sum equals k.

Example:
Input: nums = [1,1,1], k = 2
Output: 2
"""

def subarray_sum(nums, k):
    count = 0
    prefix_sum = 0
    sum_count = {0: 1}  # prefix_sum -> frequency
    
    for num in nums:
        prefix_sum += num
        
        # Check if (prefix_sum - k) exists
        if prefix_sum - k in sum_count:
            count += sum_count[prefix_sum - k]
        
        # Update prefix sum count
        sum_count[prefix_sum] = sum_count.get(prefix_sum, 0) + 1
    
    return count

# Test
print(subarray_sum([1,1,1], 2))      # 2
print(subarray_sum([1,2,3], 3))      # 2
```

**Key Insight:** 
- If prefix_sum[i] - prefix_sum[j] = k, then subarray from j+1 to i sums to k
- Use hash map to track prefix sums seen so far

**Time Complexity:** O(n)
**Space Complexity:** O(n)

---

---

### **Problem 31: Set Matrix Zeroes**
**Difficulty:** Medium | **Pattern:** Matrix | **LeetCode:** #73

```python
"""
Set entire row and column to 0 if element is 0.

Example:
Input: matrix = [[1,1,1],[1,0,1],[1,1,1]]
Output: [[1,0,1],[0,0,0],[1,0,1]]
"""

def set_zeroes(matrix):
    rows, cols = len(matrix), len(matrix[0])
    first_row_zero = False
    first_col_zero = False
    
    # Check if first row/col needs to be zero
    for j in range(cols):
        if matrix[0][j] == 0:
            first_row_zero = True
    
    for i in range(rows):
        if matrix[i][0] == 0:
            first_col_zero = True
    
    # Use first row/col as markers
    for i in range(1, rows):
        for j in range(1, cols):
            if matrix[i][j] == 0:
                matrix[i][0] = 0
                matrix[0][j] = 0
    
    # Set zeros based on markers
    for i in range(1, rows):
        for j in range(1, cols):
            if matrix[i][0] == 0 or matrix[0][j] == 0:
                matrix[i][j] = 0
    
    # Handle first row/col
    if first_row_zero:
        for j in range(cols):
            matrix[0][j] = 0
    
    if first_col_zero:
        for i in range(rows):
            matrix[i][0] = 0

# Test
matrix = [[1,1,1],[1,0,1],[1,1,1]]
set_zeroes(matrix)
print(matrix)  # [[1,0,1],[0,0,0],[1,0,1]]
```

**Time Complexity:** O(m * n)
**Space Complexity:** O(1)

---

### **Problem 32: Spiral Matrix**
**Difficulty:** Medium | **Pattern:** Matrix | **LeetCode:** #54

```python
"""
Return elements of matrix in spiral order.

Example:
Input: matrix = [[1,2,3],[4,5,6],[7,8,9]]
Output: [1,2,3,6,9,8,7,4,5]
"""

def spiral_order(matrix):
    if not matrix:
        return []
    
    result = []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    
    while top <= bottom and left <= right:
        # Traverse right
        for col in range(left, right + 1):
            result.append(matrix[top][col])
        top += 1
        
        # Traverse down
        for row in range(top, bottom + 1):
            result.append(matrix[row][right])
        right -= 1
        
        # Traverse left
        if top <= bottom:
            for col in range(right, left - 1, -1):
                result.append(matrix[bottom][col])
            bottom -= 1
        
        # Traverse up
        if left <= right:
            for row in range(bottom, top - 1, -1):
                result.append(matrix[row][left])
            left += 1
    
    return result

# Test
print(spiral_order([[1,2,3],[4,5,6],[7,8,9]]))  # [1,2,3,6,9,8,7,4,5]
```

---

### **Problem 33: Valid Sudoku**
**Difficulty:** Medium | **Pattern:** Hash Set | **LeetCode:** #36

```python
"""
Determine if a 9x9 Sudoku board is valid.

Example:
Input: board = [["5","3",".",".","7",".",".",".","."],...
Output: true
"""

def is_valid_sudoku(board):
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    
    for i in range(9):
        for j in range(9):
            num = board[i][j]
            if num == '.':
                continue
            
            # Check row
            if num in rows[i]:
                return False
            rows[i].add(num)
            
            # Check column
            if num in cols[j]:
                return False
            cols[j].add(num)
            
            # Check 3x3 box
            box_idx = (i // 3) * 3 + (j // 3)
            if num in boxes[box_idx]:
                return False
            boxes[box_idx].add(num)
    
    return True
```

---

### **Problem 34: Word Break**
**Difficulty:** Medium | **Pattern:** Dynamic Programming | **LeetCode:** #139

```python
"""
Determine if string can be segmented into dictionary words.

Example:
Input: s = "leetcode", wordDict = ["leet","code"]
Output: true
"""

def word_break(s, word_dict):
    word_set = set(word_dict)
    n = len(s)
    # dp[i] = True if s[:i] can be segmented
    dp = [False] * (n + 1)
    dp[0] = True  # Empty string
    
    for i in range(1, n + 1):
        for j in range(i):
            # Check if s[j:i] is a valid word
            if dp[j] and s[j:i] in word_set:
                dp[i] = True
                break
    
    return dp[n]

# Test
print(word_break("leetcode", ["leet","code"]))      # True
print(word_break("applepenapple", ["apple","pen"])) # True
print(word_break("catsandog", ["cats","dog","sand","and","cat"])) # False
```

---

### **Problem 35: Decode Ways**
**Difficulty:** Medium | **Pattern:** Dynamic Programming | **LeetCode:** #91

```python
"""
Decode digits to letters (1=A, 2=B, ..., 26=Z).
Count number of ways to decode.

Example:
Input: s = "12"
Output: 2
Explanation: "AB" (1 2) or "L" (12)
"""

def num_decodings(s):
    if not s or s[0] == '0':
        return 0
    
    n = len(s)
    dp = [0] * (n + 1)
    dp[0] = 1  # Empty string
    dp[1] = 1  # First character
    
    for i in range(2, n + 1):
        # Single digit
        if s[i-1] != '0':
            dp[i] += dp[i-1]
        
        # Two digits
        two_digit = int(s[i-2:i])
        if 10 <= two_digit <= 26:
            dp[i] += dp[i-2]
    
    return dp[n]

# Test
print(num_decodings("12"))   # 2
print(num_decodings("226"))  # 3
print(num_decodings("06"))   # 0
```

---

### **Problem 36: Permutations**
**Difficulty:** Medium | **Pattern:** Backtracking | **LeetCode:** #46

```python
"""
Generate all permutations of distinct integers.

Example:
Input: nums = [1,2,3]
Output: [[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]
"""

def permute(nums):
    result = []
    
    def backtrack(current, remaining):
        if not remaining:
            result.append(current[:])
            return
        
        for i in range(len(remaining)):
            # Choose
            current.append(remaining[i])
            # Explore
            backtrack(current, remaining[:i] + remaining[i+1:])
            # Unchoose
            current.pop()
    
    backtrack([], nums)
    return result

# Alternative: More efficient using swap
def permute_v2(nums):
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

### **Problem 37: Combination Sum**
**Difficulty:** Medium | **Pattern:** Backtracking | **LeetCode:** #39

```python
"""
Find all unique combinations that sum to target.
Same number can be used unlimited times.

Example:
Input: candidates = [2,3,6,7], target = 7
Output: [[2,2,3],[7]]
"""

def combination_sum(candidates, target):
    result = []
    
    def backtrack(start, current, remaining):
        if remaining == 0:
            result.append(current[:])
            return
        
        if remaining < 0:
            return
        
        for i in range(start, len(candidates)):
            current.append(candidates[i])
            # Can reuse same element, so start from i
            backtrack(i, current, remaining - candidates[i])
            current.pop()
    
    backtrack(0, [], target)
    return result

# Test
print(combination_sum([2,3,6,7], 7))  # [[2,2,3],[7]]
```

---

### **Problem 38: Letter Combinations of Phone Number**
**Difficulty:** Medium | **Pattern:** Backtracking | **LeetCode:** #17

```python
"""
Generate letter combinations from phone number digits.

Example:
Input: digits = "23"
Output: ["ad","ae","af","bd","be","bf","cd","ce","cf"]
"""

def letter_combinations(digits):
    if not digits:
        return []
    
    phone = {
        '2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',
        '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz'
    }
    
    result = []
    
    def backtrack(index, current):
        if index == len(digits):
            result.append(current)
            return
        
        for letter in phone[digits[index]]:
            backtrack(index + 1, current + letter)
    
    backtrack(0, "")
    return result

# Test
print(letter_combinations("23"))
```

---

### **Problem 39: Generate Parentheses**
**Difficulty:** Medium | **Pattern:** Backtracking | **LeetCode:** #22

```python
"""
Generate all valid parentheses combinations with n pairs.

Example:
Input: n = 3
Output: ["((()))","(()())","(())()","()(())","()()()"]
"""

def generate_parenthesis(n):
    result = []
    
    def backtrack(current, open_count, close_count):
        if len(current) == 2 * n:
            result.append(current)
            return
        
        # Add opening parenthesis
        if open_count < n:
            backtrack(current + '(', open_count + 1, close_count)
        
        # Add closing parenthesis
        if close_count < open_count:
            backtrack(current + ')', open_count, close_count + 1)
    
    backtrack("", 0, 0)
    return result

# Test
print(generate_parenthesis(3))
```

---

### **Problem 40: Longest Consecutive Sequence**
**Difficulty:** Medium | **Pattern:** Hash Set | **LeetCode:** #128

```python
"""
Find length of longest consecutive sequence in unsorted array.
Must be O(n) time.

Example:
Input: nums = [100,4,200,1,3,2]
Output: 4
Explanation: [1,2,3,4]
"""

def longest_consecutive(nums):
    if not nums:
        return 0
    
    num_set = set(nums)
    max_length = 0
    
    for num in num_set:
        # Only start counting from sequence start
        if num - 1 not in num_set:
            current = num
            length = 1
            
            # Count consecutive numbers
            while current + 1 in num_set:
                current += 1
                length += 1
            
            max_length = max(max_length, length)
    
    return max_length

# Test
print(longest_consecutive([100,4,200,1,3,2]))  # 4
print(longest_consecutive([0,3,7,2,5,8,4,6,0,1]))  # 9
```

---

## 🔴 LEVEL 3: HARD PROBLEMS (Advanced Concepts)

### **Problem 41: Median of Two Sorted Arrays**
**Difficulty:** Hard | **Pattern:** Binary Search | **LeetCode:** #4

```python
"""
Find median of two sorted arrays in O(log(min(m,n))) time.

Example:
Input: nums1 = [1,3], nums2 = [2]
Output: 2.0
"""

def find_median_sorted_arrays(nums1, nums2):
    # Ensure nums1 is smaller array
    if len(nums1) > len(nums2):
        nums1, nums2 = nums2, nums1
    
    m, n = len(nums1), len(nums2)
    left, right = 0, m
    
    while left <= right:
        partition1 = (left + right) // 2
        partition2 = (m + n + 1) // 2 - partition1
        
        # Get max of left and min of right for both arrays
        max_left1 = float('-inf') if partition1 == 0 else nums1[partition1 - 1]
        min_right1 = float('inf') if partition1 == m else nums1[partition1]
        
        max_left2 = float('-inf') if partition2 == 0 else nums2[partition2 - 1]
        min_right2 = float('inf') if partition2 == n else nums2[partition2]
        
        # Check if we found correct partition
        if max_left1 <= min_right2 and max_left2 <= min_right1:
            # Odd total length
            if (m + n) % 2 == 1:
                return max(max_left1, max_left2)
            # Even total length
            return (max(max_left1, max_left2) + min(min_right1, min_right2)) / 2
        elif max_left1 > min_right2:
            right = partition1 - 1
        else:
            left = partition1 + 1

# Test
print(find_median_sorted_arrays([1,3], [2]))  # 2.0
print(find_median_sorted_arrays([1,2], [3,4]))  # 2.5
```

---

### **Problem 42: Trapping Rain Water**
**Difficulty:** Hard | **Pattern:** Two Pointers | **LeetCode:** #42

```python
"""
Calculate how much water can be trapped after raining.

Example:
Input: height = [0,1,0,2,1,0,1,3,2,1,2,1]
Output: 6
"""

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
print(trap([0,1,0,2,1,0,1,3,2,1,2,1]))  # 6
```

---

### **Problem 43: Minimum Window Substring**
**Difficulty:** Hard | **Pattern:** Sliding Window | **LeetCode:** #76

```python
"""
Find minimum window substring containing all characters of t.

Example:
Input: s = "ADOBECODEBANC", t = "ABC"
Output: "BANC"
"""

def min_window(s, t):
    from collections import Counter
    
    if not s or not t:
        return ""
    
    # Count characters in t
    target_count = Counter(t)
    required = len(target_count)
    
    left = 0
    formed = 0
    window_count = {}
    
    # Result: (window_length, left, right)
    result = float('inf'), None, None
    
    for right in range(len(s)):
        char = s[right]
        window_count[char] = window_count.get(char, 0) + 1
        
        # Check if current char satisfies requirement
        if char in target_count and window_count[char] == target_count[char]:
            formed += 1
        
        # Try to shrink window
        while left <= right and formed == required:
            char = s[left]
            
            # Update result
            if right - left + 1 < result[0]:
                result = (right - left + 1, left, right)
            
            # Remove leftmost char
            window_count[char] -= 1
            if char in target_count and window_count[char] < target_count[char]:
                formed -= 1
            
            left += 1
    
    return "" if result[0] == float('inf') else s[result[1]:result[2] + 1]

# Test
print(min_window("ADOBECODEBANC", "ABC"))  # "BANC"
```

---

### **Problem 44: Regular Expression Matching**
**Difficulty:** Hard | **Pattern:** Dynamic Programming | **LeetCode:** #10

```python
"""
Implement regex matching with '.' and '*'.

Example:
Input: s = "aa", p = "a*"
Output: true
"""

def is_match(s, p):
    m, n = len(s), len(p)
    # dp[i][j] = True if s[:i] matches p[:j]
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    
    # Handle patterns like a*, a*b*, etc.
    for j in range(2, n + 1):
        if p[j-1] == '*':
            dp[0][j] = dp[0][j-2]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if p[j-1] == '*':
                # Zero occurrence of previous char
                dp[i][j] = dp[i][j-2]
                # One or more occurrences
                if p[j-2] == s[i-1] or p[j-2] == '.':
                    dp[i][j] = dp[i][j] or dp[i-1][j]
            elif p[j-1] == '.' or p[j-1] == s[i-1]:
                dp[i][j] = dp[i-1][j-1]
    
    return dp[m][n]

# Test
print(is_match("aa", "a"))     # False
print(is_match("aa", "a*"))    # True
print(is_match("ab", ".*"))    # True
```

---

### **Problem 45: Largest Rectangle in Histogram**
**Difficulty:** Hard | **Pattern:** Stack | **LeetCode:** #84

```python
"""
Find largest rectangle area in histogram.

Example:
Input: heights = [2,1,5,6,2,3]
Output: 10
"""

def largest_rectangle_area(heights):
    stack = []
    max_area = 0
    
    for i, h in enumerate(heights):
        # Pop bars taller than current
        while stack and heights[stack[-1]] > h:
            height_idx = stack.pop()
            height = heights[height_idx]
            # Width calculation
            width = i if not stack else i - stack[-1] - 1
            max_area = max(max_area, height * width)
        
        stack.append(i)
    
    # Process remaining bars
    while stack:
        height_idx = stack.pop()
        height = heights[height_idx]
        width = len(heights) if not stack else len(heights) - stack[-1] - 1
        max_area = max(max_area, height * width)
    
    return max_area

# Test
print(largest_rectangle_area([2,1,5,6,2,3]))  # 10
```

---

## 🟣 LEVEL 4: EXPERT PROBLEMS (Data Engineering Scenarios)

### **Problem 46: Process Large CSV File**
**Difficulty:** Expert | **Real-world DE Problem**

```python
"""
Process a 10GB CSV file with only 1GB RAM available.
Calculate aggregations without loading entire file.
"""

def process_large_csv(filename, chunk_size=10000):
    """
    Process large CSV in chunks
    Calculate: total rows, sum of numerical columns, unique values
    """
    import pandas as pd
    from collections import defaultdict
    
    stats = {
        'total_rows': 0,
        'column_sums': defaultdict(float),
        'unique_values': defaultdict(set)
    }
    
    # Process in chunks
    for chunk in pd.read_csv(filename, chunksize=chunk_size):
        stats['total_rows'] += len(chunk)
        
        # Sum numerical columns
        for col in chunk.select_dtypes(include=['number']).columns:
            stats['column_sums'][col] += chunk[col].sum()
        
        # Track unique values (with memory limit)
        for col in chunk.columns:
            # Only track if set size is reasonable
            if len(stats['unique_values'][col]) < 10000:
                stats['unique_values'][col].update(chunk[col].dropna().unique())
    
    return stats

# Alternative: Using generators for memory efficiency
def read_csv_generator(filename):
    """Generator to read CSV line by line"""
    with open(filename, 'r') as f:
        header = next(f).strip().split(',')
        for line in f:
            values = line.strip().split(',')
            yield dict(zip(header, values))

def process_with_generator(filename):
    from collections import Counter
    
    row_count = 0
    column_stats = Counter()
    
    for row in read_csv_generator(filename):
        row_count += 1
        # Process row
        for key, value in row.items():
            try:
                column_stats[key] += float(value)
            except:
                pass
    
    return row_count, column_stats
```

---

### **Problem 47: Deduplicate Records**
**Difficulty:** Expert | **Real-world DE Problem**

```python
"""
Deduplicate large dataset based on fuzzy matching.
Handle slight variations in names, addresses, etc.
"""

def deduplicate_records(records, threshold=0.8):
    """
    Deduplicate using similarity matching
    """
    from difflib import SequenceMatcher
    
    def similarity(a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    unique_records = []
    seen_keys = set()
    
    for record in records:
        # Create composite key
        key = f"{record.get('name', '')}_{record.get('email', '')}"
        
        # Check similarity with existing records
        is_duplicate = False
        for seen_key in seen_keys:
            if similarity(key, seen_key) >= threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_records.append(record)
            seen_keys.add(key)
    
    return unique_records

# Using pandas for larger datasets
def deduplicate_pandas(df):
    """
    Efficient deduplication using pandas
    """
    import pandas as pd
    
    # Method 1: Exact duplicates
    df_dedup = df.drop_duplicates(subset=['name', 'email'], keep='first')
    
    # Method 2: Case-insensitive
    df['name_lower'] = df['name'].str.lower()
    df['email_lower'] = df['email'].str.lower()
    df_dedup = df.drop_duplicates(subset=['name_lower', 'email_lower'], keep='first')
    df_dedup = df_dedup.drop(['name_lower', 'email_lower'], axis=1)
    
    return df_dedup
```

---

### **Problem 48: Implement Rate Limiter**
**Difficulty:** Expert | **Real-world DE Problem**

```python
"""
Implement rate limiter for API calls
Allow max N requests per T seconds per user
"""

from collections import defaultdict, deque
import time

class RateLimiter:
    def __init__(self, max_requests, time_window):
        """
        max_requests: Maximum number of requests allowed
        time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(deque)
    
    def is_allowed(self, user_id):
        """Check if request is allowed for user"""
        current_time = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests outside time window
        while user_requests and user_requests[0] < current_time - self.time_window:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) < self.max_requests:
            user_requests.append(current_time)
            return True
        
        return False

# Token Bucket Algorithm (more flexible)
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        """
        capacity: Maximum tokens
        refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens=1):
        """Try to consume tokens"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on time passed"""
        now = time.time()
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

# Test
limiter = RateLimiter(max_requests=5, time_window=60)
print(limiter.is_allowed("user1"))  # True
print(limiter.is_allowed("user1"))  # True
```

---

### **Problem 49: Design LRU Cache**
**Difficulty:** Expert | **Pattern:** Hash Map + Doubly Linked List | **LeetCode:** #146

```python
"""
Implement Least Recently Used (LRU) cache.
"""

class Node:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = {}  # key -> node
        # Dummy head and tail
        self.head = Node(0, 0)
        self.tail = Node(0, 0)
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def _remove(self, node):
        """Remove node from linked list"""
        prev_node = node.prev
        next_node = node.next
        prev_node.next = next_node
        next_node.prev = prev_node
    
    def _add_to_front(self, node):
        """Add node right after head"""
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node
    
    def get(self, key):
        if key in self.cache:
            node = self.cache[key]
            # Move to front (most recently used)
            self._remove(node)
            self._add_to_front(node)
            return node.value
        return -1
    
    def put(self, key, value):
        if key in self.cache:
            # Update existing
            self._remove(self.cache[key])
        
        node = Node(key, value)
        self.cache[key] = node
        self._add_to_front(node)
        
        # Check capacity
        if len(self.cache) > self.capacity:
            # Remove least recently used (before tail)
            lru = self.tail.prev
            self._remove(lru)
            del self.cache[lru.key]

# Test
cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
print(cache.get(1))    # 1
cache.put(3, 3)        # Evicts key 2
print(cache.get(2))    # -1 (not found)
```

---

### **Problem 50: Parallel File Processing**
**Difficulty:** Expert | **Real-world DE Problem**

```python
"""
Process multiple files in parallel using multiprocessing.
Aggregate results efficiently.
"""

from multiprocessing import Pool, Manager
import os

def process_single_file(filename):
    """Process single file and return stats"""
    word_count = 0
    line_count = 0
    
    with open(filename, 'r') as f:
        for line in f:
            line_count += 1
            word_count += len(line.split())
    
    return {
        'filename': filename,
        'lines': line_count,
        'words': word_count
    }

def parallel_file_processor(file_list, num_workers=4):
    """
    Process multiple files in parallel
    """
    with Pool(num_workers) as pool:
        results = pool.map(process_single_file, file_list)
    
    # Aggregate results
    total_stats = {
        'total_files': len(results),
        'total_lines': sum(r['lines'] for r in results),
        'total_words': sum(r['words'] for r in results),
        'files': results
    }
    
    return total_stats

# Alternative: Using concurrent.futures (more Pythonic)
from concurrent.futures import ProcessPoolExecutor, as_completed

def parallel_processor_v2(file_list, num_workers=4):
    results = []
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(process_single_file, f): f for f in file_list}
        
        # Process as they complete
        for future in as_completed(futures):
            filename = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"Processed: {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    return results
```

---

### **Problem 51: Stream Processing**
**Difficulty:** Expert | **Real-world DE Problem**

```python
"""
Process real-time data stream.
Calculate rolling statistics.
"""

from collections import deque
from datetime import datetime, timedelta

class StreamProcessor:
    def __init__(self, window_size_seconds=60):
        self.window_size = window_size_seconds
        self.data_window = deque()
        self.sum = 0
        self.count = 0
    
    def add_data_point(self, value, timestamp=None):
        """Add new data point to stream"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Add new point
        self.data_window.append((timestamp, value))
        self.sum += value
        self.count += 1
        
        # Remove old points outside window
        cutoff_time = timestamp - timedelta(seconds=self.window_size)
        while self.data_window and self.data_window[0][0] < cutoff_time:
            old_timestamp, old_value = self.data_window.popleft()
            self.sum -= old_value
            self.count -= 1
    
    def get_average(self):
        """Get average over current window"""
        return self.sum / self.count if self.count > 0 else 0
    
    def get_max(self):
        """Get max value in current window"""
        return max(value for _, value in self.data_window) if self.data_window else 0
    
    def get_min(self):
        """Get min value in current window"""
        return min(value for _, value in self.data_window) if self.data_window else 0

# Test
processor = StreamProcessor(window_size_seconds=5)
processor.add_data_point(10)
processor.add_data_point(20)
processor.add_data_point(30)
print(f"Average: {processor.get_average()}")  # 20.0
print(f"Max: {processor.get_max()}")          # 30
```

---

### **Problem 52: Data Quality Checks**
**Difficulty:** Expert | **Real-world DE Problem**

```python
"""
Implement comprehensive data quality framework.
"""

import pandas as pd
from typing import Dict, List

class DataQualityChecker:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.quality_report = {}
    
    def check_nulls(self):
        """Check for null values"""
        null_counts = self.df.isnull().sum()
        null_percentages = (null_counts / len(self.df)) * 100
        
        self.quality_report['nulls'] = {
            col: {
                'count': int(null_counts[col]),
                'percentage': float(null_percentages[col])
            }
            for col in self.df.columns
        }
    
    def check_duplicates(self):
        """Check for duplicate rows"""
        duplicate_count = self.df.duplicated().sum()
        
        self.quality_report['duplicates'] = {
            'count': int(duplicate_count),
            'percentage': float((duplicate_count / len(self.df)) * 100)
        }
    
    def check_data_types(self):
        """Verify expected data types"""
        self.quality_report['data_types'] = {
            col: str(dtype) for col, dtype in self.df.dtypes.items()
        }
    
    def check_value_ranges(self, range_rules: Dict[str, tuple]):
        """
        Check if numeric values are within expected ranges
        range_rules = {'age': (0, 120), 'price': (0, 10000)}
        """
        violations = {}
        
        for col, (min_val, max_val) in range_rules.items():
            if col in self.df.columns:
                out_of_range = self.df[
                    (self.df[col] < min_val) | (self.df[col] > max_val)
                ]
                
                if len(out_of_range) > 0:
                    violations[col] = {
                        'count': len(out_of_range),
                        'percentage': (len(out_of_range) / len(self.df)) * 100
                    }
        
        self.quality_report['range_violations'] = violations
    
    def check_uniqueness(self, unique_columns: List[str]):
        """Check if specified columns have unique values"""
        for col in unique_columns:
            if col in self.df.columns:
                duplicate_count = self.df[col].duplicated().sum()
                
                self.quality_report.setdefault('uniqueness_violations', {})[col] = {
                    'duplicate_count': int(duplicate_count),
                    'unique_count': int(self.df[col].nunique())
                }
    
    def generate_report(self):
        """Generate comprehensive quality report"""
        self.check_nulls()
        self.check_duplicates()
        self.check_data_types()
        
        return self.quality_report

# Test
df = pd.DataFrame({
    'id': [1, 2, 3, 3, 5],
    'name': ['A', 'B', None, 'D', 'E'],
    'age': [25, 30, 150, 40, -5]
})

checker = DataQualityChecker(df)
checker.check_value_ranges({'age': (0, 120)})
checker.check_uniqueness(['id'])
report = checker.generate_report()
print(report)
```

---

### **Problem 53: ETL Pipeline Implementation**
**Difficulty:** Expert | **Real-world DE Problem**

```python
"""
Build production-ready ETL pipeline.
"""

import logging
from datetime import datetime
from typing import Callable, List

class ETLPipeline:
    def __init__(self, name: str):
        self.name = name
        self.extract_fn = None
        self.transform_fns = []
        self.load_fn = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(name)
    
    def extract(self, extract_fn: Callable):
        """Register extract function"""
        self.extract_fn = extract_fn
        return self
    
    def transform(self, transform_fn: Callable):
        """Register transform function"""
        self.transform_fns.append(transform_fn)
        return self
    
    def load(self, load_fn: Callable):
        """Register load function"""
        self.load_fn = load_fn
        return self
    
    def run(self):
        """Execute ETL pipeline"""
        start_time = datetime.now()
        self.logger.info(f"Starting ETL pipeline: {self.name}")
        
        try:
            # Extract
            self.logger.info("Extracting data...")
            data = self.extract_fn()
            self.logger.info(f"Extracted {len(data)} records")
            
            # Transform
            for i, transform_fn in enumerate(self.transform_fns, 1):
                self.logger.info(f"Applying transformation {i}...")
                data = transform_fn(data)
                self.logger.info(f"After transformation {i}: {len(data)} records")
            
            # Load
            self.logger.info("Loading data...")
            result = self.load_fn(data)
            
            # Success
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"ETL completed successfully in {duration:.2f}s")
            
            return {
                'status': 'success',
                'duration': duration,
                'records_processed': len(data),
                'result': result
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"ETL failed: {str(e)}")
            
            return {
                'status': 'failed',
                'duration': duration,
                'error': str(e)
            }

# Example usage
def extract_from_csv():
    import pandas as pd
    return pd.read_csv('data.csv').to_dict('records')

def clean_data(data):
    # Remove nulls
    return [row for row in data if all(row.values())]

def enrich_data(data):
    # Add derived fields
    for row in data:
        row['full_name'] = f"{row.get('first_name', '')} {row.get('last_name', '')}"
    return data

def load_to_database(data):
    # Simulate database load
    print(f"Loading {len(data)} records to database")
    return len(data)

# Build and run pipeline
pipeline = (ETLPipeline("customer_pipeline")
    .extract(extract_from_csv)
    .transform(clean_data)
    .transform(enrich_data)
    .load(load_to_database))

# result = pipeline.run()
```

---

## 📝 PRACTICE SCHEDULE

### Week 1: Foundation (Easy Problems)
- **Day 1:** Problems 1-5 (Hash Map basics)
- **Day 2:** Problems 6-10 (Two Pointers, Math)
- **Day 3:** Problems 11-15 (Arrays, Bitwise)
- **Day 4:** Problems 16-20 (More arrays, algorithms)

### Week 2: Core Skills (Medium Problems)
- **Day 5:** Problems 21-25 (Hash Map, Sliding Window)
- **Day 6:** Problems 26-30 (Two Pointers, Intervals)
- **Day 7:** Review and practice weak areas
- **Day 8:** Timed practice (2-3 problems in 60 minutes)

### Week 3: Advanced (Hard + Expert)
- Focus on problems relevant to data engineering
- Practice with real datasets
- Mock interview scenarios

---

## 🎯 KEY PATTERNS FOR DATA ENGINEERS

1. **Hash Maps/Dictionaries** - Most common pattern
2. **Two Pointers** - Array manipulation
3. **Sliding Window** - Substring/subarray problems
4. **Prefix Sum** - Running totals
5. **Sorting** - Data organization

**Avoid spending time on:**
- Binary trees
- Linked lists
- Graph algorithms (unless specifically mentioned)

---

## 💡 INTERVIEW TIPS

1. **Always clarify requirements**
   - Ask about input size
   - Edge cases (empty, null, negatives)
   - Output format

2. **Explain your approach first**
   - Don't jump straight to coding
   - Discuss trade-offs

3. **Start with brute force**
   - Then optimize
   - Show your thinking process

4. **Test your code**
   - Use example inputs
   - Consider edge cases

5. **Analyze complexity**
   - Time and space complexity
   - Know Big O notation

---

**NEXT STEPS:**
Ready to start? Let's begin solving these problems one by one!
Which problem would you like to tackle first?
