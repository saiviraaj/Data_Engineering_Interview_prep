# 🐍 COMPLETE PYTHON INTERVIEW PATTERNS & CONCEPTS
## Every Real-World Pattern for Data Engineering Interviews

**CRITICAL:** Covers CDC, snapshot comparison, data reconciliation, and production patterns  
**Level:** Senior Data Engineer / Python Developer interviews  
**Focus:** Real interview questions with complete solutions

---

## 📚 TABLE OF CONTENTS

1. **CDC & SNAPSHOT COMPARISON** - Change data capture, reconciliation
2. **DATA STRUCTURE COMPARISONS** - Dict/list diffing, deep comparison
3. **HASH MAP PATTERNS** - Frequency, grouping, two-sum variations
4. **TWO POINTERS** - Array/string problems
5. **SLIDING WINDOW** - Subarray/substring problems
6. **STRING MANIPULATION** - Parsing, transformation, validation
7. **DATE/TIME OPERATIONS** - Business days, intervals, parsing
8. **FILE PROCESSING** - CSV, JSON, chunking, streaming
9. **DATA VALIDATION** - Schema validation, type checking
10. **ERROR HANDLING** - Retry logic, exception handling
11. **GENERATORS & ITERATORS** - Memory-efficient processing
12. **FUNCTIONAL PROGRAMMING** - map, filter, reduce patterns
13. **CONCURRENCY** - Threading, multiprocessing, async
14. **TESTING PATTERNS** - Unit tests, mocking, fixtures
15. **PRODUCTION PATTERNS** - Logging, configuration, best practices

---

## 🔄 PART 1: CDC & SNAPSHOT COMPARISON

### **1.1 The Pattern - Snapshot Reconciliation**

**When to use:**
- Compare two snapshots and find changes
- Data reconciliation
- Audit trail generation
- Merge/sync operations

### **1.2 Complete CDC Solution**

```python
"""
Problem: Compare two snapshots and identify inserted, deleted, updated records

Input:
snapshot_a = [
    {"id": 1, "name": "Alice", "city": "Calgary"},
    {"id": 2, "name": "Bob", "city": "Toronto"},
    {"id": 3, "name": "Charlie", "city": "Vancouver"}
]

snapshot_b = [
    {"id": 1, "name": "Alice", "city": "Edmonton"},    # Updated
    {"id": 3, "name": "Charlie", "city": "Vancouver"}, # Unchanged
    {"id": 4, "name": "David", "city": "Montreal"}     # Inserted
]
# id=2 is deleted

Output:
{
    "inserted": [{"id": 4, "name": "David", "city": "Montreal"}],
    "deleted": [{"id": 2, "name": "Bob", "city": "Toronto"}],
    "updated": [{
        "id": 1,
        "old": {"id": 1, "name": "Alice", "city": "Calgary"},
        "new": {"id": 1, "name": "Alice", "city": "Edmonton"}
    }]
}
"""

def compare_snapshots(snapshot_a, snapshot_b, key_field="id"):
    """
    Compare two snapshots and identify changes
    
    Args:
        snapshot_a: List of dicts (old snapshot)
        snapshot_b: List of dicts (new snapshot)
        key_field: Field to use as unique identifier
    
    Returns:
        Dict with 'inserted', 'deleted', 'updated' lists
    """
    # Convert to dictionaries keyed by ID
    dict_a = {record[key_field]: record for record in snapshot_a}
    dict_b = {record[key_field]: record for record in snapshot_b}
    
    # Get key sets
    keys_a = set(dict_a.keys())
    keys_b = set(dict_b.keys())
    
    # Find inserted (in B but not in A)
    inserted_keys = keys_b - keys_a
    inserted = [dict_b[key] for key in inserted_keys]
    
    # Find deleted (in A but not in B)
    deleted_keys = keys_a - keys_b
    deleted = [dict_a[key] for key in deleted_keys]
    
    # Find updated (in both but different)
    common_keys = keys_a & keys_b
    updated = []
    
    for key in common_keys:
        old_record = dict_a[key]
        new_record = dict_b[key]
        
        # Check if any field changed
        if old_record != new_record:
            updated.append({
                key_field: key,
                "old": old_record,
                "new": new_record
            })
    
    return {
        "inserted": inserted,
        "deleted": deleted,
        "updated": updated
    }

# Test
snapshot_a = [
    {"id": 1, "name": "Alice", "city": "Calgary"},
    {"id": 2, "name": "Bob", "city": "Toronto"},
    {"id": 3, "name": "Charlie", "city": "Vancouver"}
]

snapshot_b = [
    {"id": 1, "name": "Alice", "city": "Edmonton"},
    {"id": 3, "name": "Charlie", "city": "Vancouver"},
    {"id": 4, "name": "David", "city": "Montreal"}
]

result = compare_snapshots(snapshot_a, snapshot_b)

print("INSERTED:", result["inserted"])
print("DELETED:", result["deleted"])
print("UPDATED:", result["updated"])
```

### **1.3 Advanced: Field-Level Change Tracking**

```python
def compare_with_field_changes(snapshot_a, snapshot_b, key_field="id", exclude_fields=None):
    """
    Track which specific fields changed
    
    Returns detailed field-level changes
    """
    exclude_fields = exclude_fields or []
    
    dict_a = {record[key_field]: record for record in snapshot_a}
    dict_b = {record[key_field]: record for record in snapshot_b}
    
    keys_a = set(dict_a.keys())
    keys_b = set(dict_b.keys())
    
    # Inserted and deleted (same as before)
    inserted = [dict_b[key] for key in keys_b - keys_a]
    deleted = [dict_a[key] for key in keys_a - keys_b]
    
    # Updated with field-level tracking
    updated = []
    common_keys = keys_a & keys_b
    
    for key in common_keys:
        old_record = dict_a[key]
        new_record = dict_b[key]
        
        # Find changed fields
        changed_fields = {}
        
        # Check all fields in both records
        all_fields = set(old_record.keys()) | set(new_record.keys())
        
        for field in all_fields:
            if field in exclude_fields or field == key_field:
                continue
            
            old_value = old_record.get(field)
            new_value = new_record.get(field)
            
            if old_value != new_value:
                changed_fields[field] = {
                    "old": old_value,
                    "new": new_value
                }
        
        if changed_fields:
            updated.append({
                key_field: key,
                "changes": changed_fields
            })
    
    return {
        "inserted": inserted,
        "deleted": deleted,
        "updated": updated
    }

# Usage
result = compare_with_field_changes(snapshot_a, snapshot_b)

# Output for updated:
# [
#     {
#         "id": 1,
#         "changes": {
#             "city": {"old": "Calgary", "new": "Edmonton"}
#         }
#     }
# ]
```

### **1.4 Production-Ready CDC with Validation**

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class SnapshotComparator:
    """
    Production-ready CDC comparator with validation and logging
    """
    
    def __init__(self, key_field: str = "id"):
        self.key_field = key_field
        self.comparison_timestamp = datetime.now()
    
    def validate_snapshot(self, snapshot: List[Dict]) -> bool:
        """Validate snapshot structure"""
        if not snapshot:
            return True
        
        if not isinstance(snapshot, list):
            raise ValueError("Snapshot must be a list")
        
        for record in snapshot:
            if not isinstance(record, dict):
                raise ValueError("Each record must be a dictionary")
            if self.key_field not in record:
                raise ValueError(f"Key field '{self.key_field}' not found in record")
        
        return True
    
    def compare(self, 
                snapshot_old: List[Dict], 
                snapshot_new: List[Dict],
                ignore_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compare snapshots with full validation
        """
        # Validate
        self.validate_snapshot(snapshot_old)
        self.validate_snapshot(snapshot_new)
        
        ignore_fields = ignore_fields or []
        
        # Convert to dicts
        dict_old = {r[self.key_field]: r for r in snapshot_old}
        dict_new = {r[self.key_field]: r for r in snapshot_new}
        
        keys_old = set(dict_old.keys())
        keys_new = set(dict_new.keys())
        
        # Find changes
        inserted_keys = keys_new - keys_old
        deleted_keys = keys_old - keys_new
        common_keys = keys_old & keys_new
        
        inserted = [dict_new[k] for k in inserted_keys]
        deleted = [dict_old[k] for k in deleted_keys]
        
        # Find updated with field comparison
        updated = []
        for key in common_keys:
            old_rec = {k: v for k, v in dict_old[key].items() if k not in ignore_fields}
            new_rec = {k: v for k, v in dict_new[key].items() if k not in ignore_fields}
            
            if old_rec != new_rec:
                updated.append({
                    self.key_field: key,
                    "old": dict_old[key],
                    "new": dict_new[key]
                })
        
        # Summary statistics
        summary = {
            "total_old": len(snapshot_old),
            "total_new": len(snapshot_new),
            "inserted_count": len(inserted),
            "deleted_count": len(deleted),
            "updated_count": len(updated),
            "unchanged_count": len(common_keys) - len(updated),
            "comparison_timestamp": self.comparison_timestamp.isoformat()
        }
        
        return {
            "inserted": inserted,
            "deleted": deleted,
            "updated": updated,
            "summary": summary
        }
    
    def to_json(self, result: Dict) -> str:
        """Export comparison result as JSON"""
        return json.dumps(result, indent=2, default=str)
    
    def generate_sql_statements(self, result: Dict, table_name: str) -> List[str]:
        """
        Generate SQL statements for the changes
        """
        statements = []
        
        # Inserts
        for record in result["inserted"]:
            cols = ", ".join(record.keys())
            vals = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) 
                             for v in record.values()])
            statements.append(f"INSERT INTO {table_name} ({cols}) VALUES ({vals});")
        
        # Deletes
        for record in result["deleted"]:
            key_val = record[self.key_field]
            statements.append(
                f"DELETE FROM {table_name} WHERE {self.key_field} = '{key_val}';"
            )
        
        # Updates
        for change in result["updated"]:
            key_val = change[self.key_field]
            new_rec = change["new"]
            set_clause = ", ".join([
                f"{k} = '{v}'" if isinstance(v, str) else f"{k} = {v}"
                for k, v in new_rec.items() if k != self.key_field
            ])
            statements.append(
                f"UPDATE {table_name} SET {set_clause} WHERE {self.key_field} = '{key_val}';"
            )
        
        return statements

# Usage
comparator = SnapshotComparator(key_field="id")
result = comparator.compare(snapshot_a, snapshot_b)

print("Summary:", result["summary"])
print("\nSQL Statements:")
for stmt in comparator.generate_sql_statements(result, "users"):
    print(stmt)
```

---

## 📊 PART 2: DATA STRUCTURE COMPARISONS

### **2.1 Deep Comparison of Nested Structures**

```python
def deep_compare(obj1, obj2, path="root"):
    """
    Deep comparison of nested dicts/lists
    Returns list of differences
    """
    differences = []
    
    # Type mismatch
    if type(obj1) != type(obj2):
        differences.append({
            "path": path,
            "type": "type_mismatch",
            "old": type(obj1).__name__,
            "new": type(obj2).__name__
        })
        return differences
    
    # Compare dicts
    if isinstance(obj1, dict):
        all_keys = set(obj1.keys()) | set(obj2.keys())
        
        for key in all_keys:
            key_path = f"{path}.{key}"
            
            if key not in obj1:
                differences.append({
                    "path": key_path,
                    "type": "added",
                    "value": obj2[key]
                })
            elif key not in obj2:
                differences.append({
                    "path": key_path,
                    "type": "removed",
                    "value": obj1[key]
                })
            else:
                # Recursively compare values
                differences.extend(deep_compare(obj1[key], obj2[key], key_path))
    
    # Compare lists
    elif isinstance(obj1, list):
        if len(obj1) != len(obj2):
            differences.append({
                "path": path,
                "type": "length_mismatch",
                "old_length": len(obj1),
                "new_length": len(obj2)
            })
        
        for i, (item1, item2) in enumerate(zip(obj1, obj2)):
            differences.extend(deep_compare(item1, item2, f"{path}[{i}]"))
    
    # Compare primitives
    else:
        if obj1 != obj2:
            differences.append({
                "path": path,
                "type": "value_changed",
                "old": obj1,
                "new": obj2
            })
    
    return differences

# Example
old_data = {
    "user": {
        "name": "Alice",
        "addresses": [
            {"city": "Calgary", "zip": "T2P"},
            {"city": "Toronto", "zip": "M5H"}
        ]
    }
}

new_data = {
    "user": {
        "name": "Alice",
        "addresses": [
            {"city": "Edmonton", "zip": "T5J"},  # Changed
            {"city": "Toronto", "zip": "M5H"}
        ],
        "phone": "123-456-7890"  # Added
    }
}

diffs = deep_compare(old_data, new_data)
for diff in diffs:
    print(diff)
```

### **2.2 List of Dicts Reconciliation**

```python
def reconcile_lists(old_list, new_list, key_func=lambda x: x.get('id')):
    """
    Reconcile two lists of dicts based on key function
    
    Args:
        old_list: Original list
        new_list: Updated list
        key_func: Function to extract unique key from dict
    
    Returns:
        Dict with added, removed, modified, unchanged
    """
    old_dict = {key_func(item): item for item in old_list}
    new_dict = {key_func(item): item for item in new_list}
    
    old_keys = set(old_dict.keys())
    new_keys = set(new_dict.keys())
    
    result = {
        "added": [new_dict[k] for k in new_keys - old_keys],
        "removed": [old_dict[k] for k in old_keys - new_keys],
        "modified": [],
        "unchanged": []
    }
    
    # Check common keys for modifications
    for key in old_keys & new_keys:
        if old_dict[key] != new_dict[key]:
            result["modified"].append({
                "key": key,
                "old": old_dict[key],
                "new": new_dict[key]
            })
        else:
            result["unchanged"].append(new_dict[key])
    
    return result
```

---

## 🗂️ PART 3: HASH MAP PATTERNS

### **3.1 Frequency Counter**

```python
from collections import Counter, defaultdict

# Method 1: Using Counter
def count_frequency(items):
    return Counter(items)

# Method 2: Manual with defaultdict
def count_frequency_manual(items):
    freq = defaultdict(int)
    for item in items:
        freq[item] += 1
    return dict(freq)

# Method 3: Plain dict
def count_frequency_plain(items):
    freq = {}
    for item in items:
        freq[item] = freq.get(item, 0) + 1
    return freq

# Find top K frequent elements
def top_k_frequent(nums, k):
    """
    Find k most frequent elements
    Time: O(n log k)
    """
    from collections import Counter
    import heapq
    
    counter = Counter(nums)
    return heapq.nlargest(k, counter.keys(), key=counter.get)

# Alternative: O(n) using bucket sort
def top_k_frequent_linear(nums, k):
    counter = Counter(nums)
    buckets = [[] for _ in range(len(nums) + 1)]
    
    for num, freq in counter.items():
        buckets[freq].append(num)
    
    result = []
    for i in range(len(buckets) - 1, -1, -1):
        result.extend(buckets[i])
        if len(result) >= k:
            return result[:k]
    
    return result
```

### **3.2 Group By Pattern**

```python
from collections import defaultdict

def group_by(items, key_func):
    """
    Group items by key function result
    
    Args:
        items: List of items
        key_func: Function to extract grouping key
    
    Returns:
        Dict mapping keys to lists of items
    """
    groups = defaultdict(list)
    for item in items:
        key = key_func(item)
        groups[key].append(item)
    return dict(groups)

# Example: Group users by city
users = [
    {"name": "Alice", "city": "Calgary"},
    {"name": "Bob", "city": "Toronto"},
    {"name": "Charlie", "city": "Calgary"}
]

by_city = group_by(users, lambda u: u["city"])
# {"Calgary": [{"name": "Alice", ...}, {"name": "Charlie", ...}], ...}

# Example: Group by multiple keys
def group_by_multi(items, *key_funcs):
    """Group by multiple keys (nested grouping)"""
    if not key_funcs:
        return items
    
    first_key = key_funcs[0]
    remaining_keys = key_funcs[1:]
    
    groups = defaultdict(list)
    for item in items:
        groups[first_key(item)].append(item)
    
    if remaining_keys:
        return {
            k: group_by_multi(v, *remaining_keys)
            for k, v in groups.items()
        }
    
    return dict(groups)

# Group by city then by age group
by_city_age = group_by_multi(
    users,
    lambda u: u["city"],
    lambda u: "adult" if u.get("age", 0) >= 18 else "minor"
)
```

---

## 🔢 PART 4: TWO POINTERS PATTERN

### **4.1 Opposite Direction Pointers**

```python
def two_sum_sorted(nums, target):
    """
    Find two numbers that sum to target in sorted array
    Time: O(n), Space: O(1)
    """
    left, right = 0, len(nums) - 1
    
    while left < right:
        current_sum = nums[left] + nums[right]
        
        if current_sum == target:
            return [left, right]
        elif current_sum < target:
            left += 1
        else:
            right -= 1
    
    return []

def is_palindrome(s):
    """
    Check if string is palindrome (ignoring non-alphanumeric)
    Time: O(n), Space: O(1)
    """
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
```

### **4.2 Same Direction Pointers (Fast & Slow)**

```python
def remove_duplicates(nums):
    """
    Remove duplicates in-place from sorted array
    Time: O(n), Space: O(1)
    """
    if not nums:
        return 0
    
    slow = 0
    for fast in range(1, len(nums)):
        if nums[fast] != nums[slow]:
            slow += 1
            nums[slow] = nums[fast]
    
    return slow + 1

def move_zeroes(nums):
    """
    Move all zeros to end while maintaining order
    Time: O(n), Space: O(1)
    """
    slow = 0
    
    for fast in range(len(nums)):
        if nums[fast] != 0:
            nums[slow], nums[fast] = nums[fast], nums[slow]
            slow += 1
```

---

## 🪟 PART 5: SLIDING WINDOW PATTERN

### **5.1 Fixed Size Window**

```python
def max_sum_subarray(nums, k):
    """
    Maximum sum of subarray of size k
    Time: O(n), Space: O(1)
    """
    if len(nums) < k:
        return 0
    
    # Initial window
    window_sum = sum(nums[:k])
    max_sum = window_sum
    
    # Slide window
    for i in range(k, len(nums)):
        window_sum = window_sum - nums[i - k] + nums[i]
        max_sum = max(max_sum, window_sum)
    
    return max_sum

def average_of_subarrays(nums, k):
    """
    Calculate average of all subarrays of size k
    """
    result = []
    window_sum = sum(nums[:k])
    result.append(window_sum / k)
    
    for i in range(k, len(nums)):
        window_sum = window_sum - nums[i - k] + nums[i]
        result.append(window_sum / k)
    
    return result
```

### **5.2 Variable Size Window**

```python
def longest_substring_k_distinct(s, k):
    """
    Longest substring with at most k distinct characters
    Time: O(n), Space: O(k)
    """
    from collections import defaultdict
    
    char_count = defaultdict(int)
    left = 0
    max_length = 0
    
    for right in range(len(s)):
        char_count[s[right]] += 1
        
        # Shrink window while too many distinct chars
        while len(char_count) > k:
            char_count[s[left]] -= 1
            if char_count[s[left]] == 0:
                del char_count[s[left]]
            left += 1
        
        max_length = max(max_length, right - left + 1)
    
    return max_length

def min_window_substring(s, t):
    """
    Minimum window substring containing all chars from t
    Time: O(s + t), Space: O(t)
    """
    from collections import Counter
    
    if not s or not t:
        return ""
    
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

---

## 🎯 QUICK PATTERN REFERENCE

```
PROBLEM TYPE → PATTERN → KEY APPROACH
├─ Snapshot comparison → CDC pattern → Set operations + dict comparison
├─ Two elements sum → Hash map → seen = {}; check target - num
├─ Pair in sorted array → Two pointers → left/right from ends
├─ Subarray size k → Fixed window → Slide and update sum
├─ Longest substring → Variable window → Expand right, shrink left
├─ Remove duplicates → Fast/slow pointers → slow tracks unique position
├─ Group by key → defaultdict → groups[key(item)].append(item)
└─ Deep comparison → Recursion → Check type, recurse on nested
```

---

**STATUS:** Complete Python patterns with CDC, snapshot comparison, and all data engineering essentials! 🐍

Now creating practice problems...
