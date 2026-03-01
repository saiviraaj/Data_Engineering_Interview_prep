# 🐼 COMPLETE PANDAS GUIDE FOR DATA ENGINEERING
## Master Every Pandas Function, Pattern & Best Practice

**Purpose:** Exhaustive reference for Pandas operations in data engineering  
**Level:** Data Engineer / Data Analyst / Data Scientist  
**Coverage:** All functions, patterns, performance optimization, when to use what

---

## 📚 TABLE OF CONTENTS

1. **PATTERN RECOGNITION** - What operation for what task
2. **DATA STRUCTURES** - Series vs DataFrame
3. **READING & WRITING DATA** - All I/O operations
4. **DATA SELECTION** - Indexing, filtering, selecting
5. **DATA CLEANING** - Missing values, duplicates, types
6. **DATA TRANSFORMATION** - Apply, map, replace
7. **AGGREGATION & GROUPBY** - Grouping and summarizing
8. **MERGING & JOINING** - Combining DataFrames
9. **RESHAPING** - Pivot, melt, stack, unstack
10. **TIME SERIES** - DateTime operations
11. **STRING OPERATIONS** - Text processing
12. **WINDOW FUNCTIONS** - Rolling, expanding, ewm
13. **PERFORMANCE OPTIMIZATION** - Speed up operations
14. **BEST PRACTICES** - Production patterns

---

## 🎯 PART 1: PATTERN RECOGNITION FRAMEWORK

### **What Operation for What Task**

```
TASK → PANDAS OPERATION → KEY FUNCTIONS
```

| **Task** | **Operation** | **Function** | **Time** |
|----------|---------------|--------------|----------|
| Read CSV | I/O | `pd.read_csv()` | O(n) |
| Filter rows | Boolean indexing | `df[df['col'] > 5]` | O(n) |
| Select columns | Column selection | `df[['col1', 'col2']]` | O(1) |
| Remove nulls | Cleaning | `df.dropna()` or `df.fillna()` | O(n) |
| Remove duplicates | Cleaning | `df.drop_duplicates()` | O(n) |
| Sort | Ordering | `df.sort_values()` | O(n log n) |
| Group and aggregate | GroupBy | `df.groupby().agg()` | O(n) |
| Join tables | Merging | `pd.merge()` or `df.join()` | O(n+m) |
| Pivot table | Reshaping | `df.pivot_table()` | O(n) |
| Apply function | Transformation | `df.apply()` or `df.map()` | O(n) |
| Rolling window | Time series | `df.rolling()` | O(n*w) |
| String operations | Text | `df['col'].str.method()` | O(n) |

### **Decision Tree for Common Tasks**

```
NEED TO... → USE THIS
├─ Load data
│  ├─ From CSV → pd.read_csv()
│  ├─ From Excel → pd.read_excel()
│  ├─ From SQL → pd.read_sql()
│  └─ From JSON → pd.read_json()
│
├─ Clean data
│  ├─ Remove nulls → dropna() or fillna()
│  ├─ Remove duplicates → drop_duplicates()
│  ├─ Fix types → astype() or pd.to_datetime()
│  └─ Rename columns → rename()
│
├─ Transform data
│  ├─ Add column → df['new'] = expression
│  ├─ Apply function → apply(), map(), applymap()
│  ├─ Replace values → replace()
│  └─ Bin values → cut() or qcut()
│
├─ Filter/select
│  ├─ Filter rows → df[condition]
│  ├─ Select columns → df[['col1', 'col2']]
│  ├─ Sample rows → sample()
│  └─ Head/tail → head(), tail()
│
├─ Aggregate
│  ├─ Simple stats → sum(), mean(), count()
│  ├─ Group by → groupby().agg()
│  ├─ Pivot → pivot_table()
│  └─ Cross-tab → crosstab()
│
└─ Combine
   ├─ Concatenate → pd.concat()
   ├─ Join → merge() or join()
   └─ Append → pd.concat() with axis=0
```

---

## 📊 PART 2: DATA STRUCTURES

### **2.1 Series (1D)**

```python
import pandas as pd
import numpy as np

# ========== Creation ==========
# From list
s = pd.Series([1, 2, 3, 4, 5])

# With custom index
s = pd.Series([1, 2, 3], index=['a', 'b', 'c'])

# From dictionary
s = pd.Series({'a': 1, 'b': 2, 'c': 3})

# From scalar
s = pd.Series(5, index=range(5))  # [5, 5, 5, 5, 5]

# ========== Access ==========
# By position
s[0]
s[[0, 2, 4]]

# By label
s['a']
s[['a', 'c']]

# Slicing
s[1:4]
s['a':'c']  # Includes endpoint!

# ========== Operations ==========
# Arithmetic
s + 10
s * 2
s ** 2

# Statistical
s.sum()
s.mean()
s.std()
s.min()
s.max()
s.median()
s.quantile(0.75)

# Boolean operations
s > 2
s.between(2, 4)

# ========== Methods ==========
s.unique()          # Unique values
s.nunique()         # Count unique
s.value_counts()    # Frequency count
s.isnull()          # Check for nulls
s.isna()            # Same as isnull()
s.fillna(0)         # Fill nulls
s.dropna()          # Remove nulls
s.sort_values()     # Sort by values
s.sort_index()      # Sort by index
```

### **2.2 DataFrame (2D)**

```python
# ========== Creation ==========
# From dictionary
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'city': ['NYC', 'LA', 'SF']
})

# From list of dictionaries
data = [
    {'name': 'Alice', 'age': 25},
    {'name': 'Bob', 'age': 30}
]
df = pd.DataFrame(data)

# From 2D array
df = pd.DataFrame(
    [[1, 2, 3], [4, 5, 6]],
    columns=['A', 'B', 'C']
)

# From Series
s1 = pd.Series([1, 2, 3], name='col1')
s2 = pd.Series([4, 5, 6], name='col2')
df = pd.DataFrame([s1, s2]).T

# ========== Basic Info ==========
df.shape            # (rows, columns)
df.info()           # Column types, non-null counts
df.describe()       # Statistical summary
df.head(10)         # First 10 rows
df.tail(10)         # Last 10 rows
df.sample(5)        # Random 5 rows
df.columns          # Column names
df.index            # Index
df.dtypes           # Data types
df.memory_usage()   # Memory per column
```

---

## 📥 PART 3: READING & WRITING DATA

### **3.1 CSV Operations**

```python
# ========== Reading CSV ==========
# Basic read
df = pd.read_csv('data.csv')

# With options (PRODUCTION RECOMMENDED)
df = pd.read_csv(
    'data.csv',
    sep=',',                    # Delimiter
    header=0,                   # Row number of header
    names=['col1', 'col2'],     # Custom column names
    index_col='id',             # Set index column
    usecols=['col1', 'col2'],   # Read only these columns
    dtype={'col1': 'int64'},    # Specify types
    parse_dates=['date_col'],   # Parse as datetime
    na_values=['NA', 'NULL'],   # Additional null values
    encoding='utf-8',           # File encoding
    nrows=10000,                # Read first 10k rows
    skiprows=[0, 2],            # Skip these rows
    low_memory=False,           # Avoid mixed type warnings
    compression='gzip'          # For compressed files
)

# Read in chunks (for large files)
chunks = pd.read_csv('large_file.csv', chunksize=10000)
for chunk in chunks:
    process(chunk)

# Read with date parsing
df = pd.read_csv(
    'data.csv',
    parse_dates=['date'],
    date_parser=lambda x: pd.to_datetime(x, format='%Y-%m-%d')
)

# ========== Writing CSV ==========
df.to_csv('output.csv', index=False)

# With options
df.to_csv(
    'output.csv',
    sep=',',
    header=True,
    index=False,
    encoding='utf-8',
    compression='gzip',
    mode='w',  # 'w' for write, 'a' for append
    chunksize=10000
)
```

### **3.2 Excel Operations**

```python
# ========== Reading Excel ==========
df = pd.read_excel('data.xlsx')

# Specific sheet
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')

# Multiple sheets
dfs = pd.read_excel('data.xlsx', sheet_name=['Sheet1', 'Sheet2'])
# Returns dict: {'Sheet1': df1, 'Sheet2': df2}

# All sheets
dfs = pd.read_excel('data.xlsx', sheet_name=None)

# With options
df = pd.read_excel(
    'data.xlsx',
    sheet_name=0,           # First sheet
    header=0,
    usecols='A:C',          # Columns A through C
    skiprows=2,
    nrows=100,
    dtype={'col1': str}
)

# ========== Writing Excel ==========
df.to_excel('output.xlsx', index=False)

# Multiple sheets
with pd.ExcelWriter('output.xlsx') as writer:
    df1.to_excel(writer, sheet_name='Sheet1', index=False)
    df2.to_excel(writer, sheet_name='Sheet2', index=False)

# With formatting (requires openpyxl)
with pd.ExcelWriter('output.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Data', index=False)
    workbook = writer.book
    worksheet = writer.sheets['Data']
    # Apply formatting...
```

### **3.3 SQL Operations**

```python
from sqlalchemy import create_engine

# ========== Read from SQL ==========
# Using SQLAlchemy
engine = create_engine('postgresql://user:pass@host:5432/db')
df = pd.read_sql('SELECT * FROM table', engine)

# With query
query = """
    SELECT id, name, age
    FROM users
    WHERE age > 25
    ORDER BY age DESC
"""
df = pd.read_sql(query, engine)

# Read table directly
df = pd.read_sql_table('users', engine)

# ========== Write to SQL ==========
df.to_sql(
    'table_name',
    engine,
    if_exists='replace',  # 'fail', 'replace', 'append'
    index=False,
    chunksize=10000,
    method='multi'  # Faster bulk insert
)
```

### **3.4 Other Formats**

```python
# ========== JSON ==========
df = pd.read_json('data.json')
df = pd.read_json('data.json', orient='records')
df.to_json('output.json', orient='records', indent=2)

# ========== Parquet (BEST for big data) ==========
df = pd.read_parquet('data.parquet')
df.to_parquet('output.parquet', compression='snappy')

# ========== HDF5 ==========
df.to_hdf('data.h5', key='df', mode='w')
df = pd.read_hdf('data.h5', key='df')

# ========== Pickle (Python objects) ==========
df.to_pickle('data.pkl')
df = pd.read_pickle('data.pkl')

# ========== Clipboard ==========
df = pd.read_clipboard()
df.to_clipboard()
```

---

## 🎯 PART 4: DATA SELECTION & FILTERING

### **4.1 Column Selection**

```python
# ========== Select Single Column (returns Series) ==========
df['name']
df.name  # Only works for valid Python identifiers

# ========== Select Multiple Columns (returns DataFrame) ==========
df[['name', 'age']]

# Using list
cols = ['name', 'age', 'city']
df[cols]

# ========== Select by Type ==========
df.select_dtypes(include=['int64', 'float64'])
df.select_dtypes(exclude=['object'])

# All numeric columns
df.select_dtypes(include=[np.number])

# ========== Column Filtering ==========
# Columns containing substring
df.filter(like='date')
df.filter(regex='^user_')

# Columns by list
df.filter(items=['col1', 'col2'])
```

### **4.2 Row Selection**

```python
# ========== By Position (iloc) ==========
df.iloc[0]          # First row
df.iloc[[0, 2, 4]]  # Specific rows
df.iloc[0:5]        # First 5 rows
df.iloc[:, 0]       # First column
df.iloc[0:3, 0:2]   # Rows 0-2, Columns 0-1

# ========== By Label (loc) ==========
df.loc[0]           # Row with index 0
df.loc[[0, 2, 4]]   # Specific index labels
df.loc[0:5]         # Includes endpoint!
df.loc[:, 'name']   # All rows, name column
df.loc[0:3, ['name', 'age']]

# ========== Boolean Indexing (MOST COMMON) ==========
# Single condition
df[df['age'] > 25]
df[df['city'] == 'NYC']

# Multiple conditions (AND)
df[(df['age'] > 25) & (df['city'] == 'NYC')]

# Multiple conditions (OR)
df[(df['age'] > 25) | (df['city'] == 'NYC')]

# NOT
df[~(df['age'] > 25)]

# IN / NOT IN
df[df['city'].isin(['NYC', 'LA', 'SF'])]
df[~df['city'].isin(['NYC', 'LA'])]

# Between
df[df['age'].between(25, 35)]

# String contains
df[df['name'].str.contains('Alice')]

# Null/Not Null
df[df['email'].isnull()]
df[df['email'].notnull()]

# ========== Query Method (SQL-like) ==========
df.query('age > 25 and city == "NYC"')
df.query('age > @min_age')  # Use variables with @

# ========== Sample ==========
df.sample(n=10)              # Random 10 rows
df.sample(frac=0.1)          # Random 10%
df.sample(n=5, weights='age') # Weighted sampling
```

### **4.3 Advanced Indexing**

```python
# ========== Set Index ==========
df.set_index('id', inplace=True)
df.set_index(['country', 'city'], inplace=True)  # MultiIndex

# ========== Reset Index ==========
df.reset_index(inplace=True)
df.reset_index(drop=True, inplace=True)  # Don't keep old index

# ========== Sort Index ==========
df.sort_index()
df.sort_index(ascending=False)

# ========== MultiIndex Selection ==========
df = df.set_index(['country', 'city'])
df.loc['USA']                    # All cities in USA
df.loc[('USA', 'NYC')]          # Specific city
df.loc[('USA', 'NYC'), 'age']   # Specific value
```

---

## 🧹 PART 5: DATA CLEANING

### **5.1 Missing Values**

```python
# ========== Check Missing ==========
df.isnull()          # Boolean DataFrame
df.isna()            # Same as isnull()
df.isnull().sum()    # Count nulls per column
df.isnull().sum().sum()  # Total nulls

# Percentage of nulls
(df.isnull().sum() / len(df)) * 100

# ========== Drop Missing ==========
df.dropna()                      # Drop rows with any null
df.dropna(how='all')             # Drop rows where all are null
df.dropna(subset=['age', 'city']) # Drop if null in these columns
df.dropna(thresh=2)              # Keep rows with at least 2 non-nulls
df.dropna(axis=1)                # Drop columns with nulls

# ========== Fill Missing ==========
df.fillna(0)                     # Fill all with 0
df.fillna({'age': 0, 'city': 'Unknown'})  # Different values per column

# Forward fill
df.fillna(method='ffill')  # Fill with previous value
df['age'].fillna(method='ffill')

# Backward fill
df.fillna(method='bfill')

# Fill with mean/median
df['age'].fillna(df['age'].mean())
df['age'].fillna(df['age'].median())

# Fill with mode (most frequent)
df['city'].fillna(df['city'].mode()[0])

# Interpolate (for time series)
df['value'].interpolate()
df['value'].interpolate(method='linear')
```

### **5.2 Duplicates**

```python
# ========== Check Duplicates ==========
df.duplicated()              # Boolean Series
df.duplicated().sum()        # Count duplicates

# Based on specific columns
df.duplicated(subset=['email'])

# Keep parameter
df.duplicated(keep='first')  # Mark all but first as duplicate
df.duplicated(keep='last')   # Mark all but last as duplicate
df.duplicated(keep=False)    # Mark all duplicates

# ========== Drop Duplicates ==========
df.drop_duplicates()
df.drop_duplicates(subset=['email'])
df.drop_duplicates(subset=['email'], keep='first')
df.drop_duplicates(subset=['email'], keep='last')

# ========== Find Duplicate Rows ==========
duplicates = df[df.duplicated(keep=False)]
```

### **5.3 Data Types**

```python
# ========== Check Types ==========
df.dtypes
df.info()

# ========== Convert Types ==========
df['age'] = df['age'].astype(int)
df['price'] = df['price'].astype(float)
df['category'] = df['category'].astype('category')

# Convert to datetime
df['date'] = pd.to_datetime(df['date'])
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
df['date'] = pd.to_datetime(df['date'], errors='coerce')  # Invalid -> NaT

# Convert to numeric (coerce errors to NaN)
df['value'] = pd.to_numeric(df['value'], errors='coerce')

# ========== Category Type (Memory Efficient) ==========
df['category'] = df['category'].astype('category')

# Check memory savings
df['category'].memory_usage()  # Before
df['category'].astype('category').memory_usage()  # After
```

### **5.4 String Cleaning**

```python
# ========== Strip Whitespace ==========
df['name'] = df['name'].str.strip()
df['name'] = df['name'].str.lstrip()
df['name'] = df['name'].str.rstrip()

# ========== Case Conversion ==========
df['name'] = df['name'].str.lower()
df['name'] = df['name'].str.upper()
df['name'] = df['name'].str.title()

# ========== Replace ==========
df['text'] = df['text'].str.replace('old', 'new')
df['text'] = df['text'].str.replace(r'\d+', '', regex=True)

# ========== Remove Characters ==========
df['phone'] = df['phone'].str.replace(r'[^\d]', '', regex=True)  # Keep only digits
```

---

## 🔄 PART 6: DATA TRANSFORMATION

### **6.1 Apply Functions**

```python
# ========== Apply to Series ==========
# Element-wise operation
df['age_squared'] = df['age'].apply(lambda x: x ** 2)

# Custom function
def categorize_age(age):
    if age < 18:
        return 'Minor'
    elif age < 65:
        return 'Adult'
    else:
        return 'Senior'

df['age_group'] = df['age'].apply(categorize_age)

# ========== Apply to DataFrame ==========
# Column-wise (default axis=0)
df.apply(lambda col: col.sum())
df.apply(np.mean)

# Row-wise (axis=1)
df.apply(lambda row: row['age'] + row['salary'], axis=1)

# ========== Map (Series only, faster) ==========
# Dictionary mapping
mapping = {1: 'One', 2: 'Two', 3: 'Three'}
df['number_text'] = df['number'].map(mapping)

# Function mapping
df['age_doubled'] = df['age'].map(lambda x: x * 2)

# ========== Applymap (Element-wise on DataFrame) ==========
# Apply function to every element
df_numeric = df[['age', 'salary']].applymap(lambda x: x * 2)

# ========== Replace ==========
df['status'].replace('old', 'new')
df['status'].replace(['old1', 'old2'], ['new1', 'new2'])
df['status'].replace({'old1': 'new1', 'old2': 'new2'})

# ========== Vectorized Operations (FASTEST) ==========
# Use these instead of apply when possible
df['age_doubled'] = df['age'] * 2  # Much faster than apply
df['full_name'] = df['first'] + ' ' + df['last']
df['is_adult'] = df['age'] >= 18
```

### **6.2 Conditional Operations**

```python
# ========== np.where (if-else) ==========
df['category'] = np.where(df['age'] > 18, 'Adult', 'Minor')

# Nested conditions
df['category'] = np.where(
    df['age'] < 18, 'Minor',
    np.where(df['age'] < 65, 'Adult', 'Senior')
)

# ========== np.select (multiple conditions) ==========
conditions = [
    df['age'] < 18,
    df['age'] < 65,
    df['age'] >= 65
]
choices = ['Minor', 'Adult', 'Senior']
df['category'] = np.select(conditions, choices, default='Unknown')

# ========== DataFrame.where ==========
df['age_capped'] = df['age'].where(df['age'] <= 100, 100)
```

### **6.3 Binning**

```python
# ========== Cut (Equal-width bins) ==========
df['age_bin'] = pd.cut(df['age'], bins=3)  # 3 equal-width bins
df['age_bin'] = pd.cut(df['age'], bins=[0, 18, 65, 100])
df['age_bin'] = pd.cut(
    df['age'],
    bins=[0, 18, 65, 100],
    labels=['Minor', 'Adult', 'Senior']
)

# ========== Qcut (Equal-frequency bins) ==========
df['age_quartile'] = pd.qcut(df['age'], q=4)  # Quartiles
df['age_quartile'] = pd.qcut(df['age'], q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
```

---

## 📊 PART 7: AGGREGATION & GROUPBY

### **7.1 Basic Aggregation**

```python
# ========== Single Column ==========
df['age'].sum()
df['age'].mean()
df['age'].median()
df['age'].std()
df['age'].var()
df['age'].min()
df['age'].max()
df['age'].count()
df['age'].nunique()

# ========== Multiple Columns ==========
df[['age', 'salary']].mean()

# ========== Entire DataFrame ==========
df.sum()        # Sum each column
df.mean()       # Mean each column
df.describe()   # Statistical summary

# ========== Custom Aggregation ==========
df['age'].agg(['sum', 'mean', 'std'])
df[['age', 'salary']].agg(['min', 'max', 'mean'])
```

### **7.2 GroupBy Operations**

```python
# ========== Basic GroupBy ==========
df.groupby('city').size()                    # Count per group
df.groupby('city')['age'].mean()             # Mean age per city
df.groupby('city')['age'].sum()              # Sum age per city

# ========== Multiple Columns ==========
df.groupby(['city', 'gender'])['age'].mean()

# ========== Multiple Aggregations ==========
df.groupby('city').agg({
    'age': 'mean',
    'salary': 'sum',
    'name': 'count'
})

# Multiple aggregations per column
df.groupby('city').agg({
    'age': ['min', 'max', 'mean'],
    'salary': ['sum', 'mean']
})

# ========== Named Aggregations (Pandas 0.25+) ==========
df.groupby('city').agg(
    avg_age=('age', 'mean'),
    total_salary=('salary', 'sum'),
    count=('name', 'count')
)

# ========== Custom Aggregation Functions ==========
df.groupby('city').agg({
    'age': lambda x: x.max() - x.min(),
    'salary': lambda x: x.quantile(0.75)
})

# ========== Transform (keep original shape) ==========
# Add group mean as new column
df['age_group_mean'] = df.groupby('city')['age'].transform('mean')

# Normalize within groups
df['age_normalized'] = df.groupby('city')['age'].transform(
    lambda x: (x - x.mean()) / x.std()
)

# ========== Filter Groups ==========
# Keep groups with more than 10 members
df.groupby('city').filter(lambda x: len(x) > 10)

# Keep groups where mean age > 30
df.groupby('city').filter(lambda x: x['age'].mean() > 30)

# ========== Apply Custom Function ==========
def custom_stats(group):
    return pd.Series({
        'count': len(group),
        'mean_age': group['age'].mean(),
        'max_salary': group['salary'].max()
    })

df.groupby('city').apply(custom_stats)
```

### **7.3 Pivot Tables**

```python
# ========== Basic Pivot ==========
df.pivot_table(
    values='salary',
    index='city',
    columns='gender',
    aggfunc='mean'
)

# ========== Multiple Values ==========
df.pivot_table(
    values=['salary', 'age'],
    index='city',
    columns='gender',
    aggfunc='mean'
)

# ========== Multiple Aggregations ==========
df.pivot_table(
    values='salary',
    index='city',
    columns='gender',
    aggfunc=['mean', 'sum', 'count']
)

# ========== With Margins (totals) ==========
df.pivot_table(
    values='salary',
    index='city',
    columns='gender',
    aggfunc='mean',
    margins=True,
    margins_name='Total'
)

# ========== Fill Missing ==========
df.pivot_table(
    values='salary',
    index='city',
    columns='gender',
    aggfunc='mean',
    fill_value=0
)

# ========== Crosstab ==========
pd.crosstab(df['city'], df['gender'])
pd.crosstab(df['city'], df['gender'], normalize='all')  # Percentages
pd.crosstab(df['city'], df['gender'], values=df['salary'], aggfunc='mean')
```

---

## 🔗 PART 8: MERGING & JOINING

### **8.1 Merge (SQL-like joins)**

```python
# ========== Inner Join (default) ==========
pd.merge(df1, df2, on='key')
pd.merge(df1, df2, on=['key1', 'key2'])

# ========== Left Join ==========
pd.merge(df1, df2, on='key', how='left')

# ========== Right Join ==========
pd.merge(df1, df2, on='key', how='right')

# ========== Outer Join ==========
pd.merge(df1, df2, on='key', how='outer')

# ========== Different Column Names ==========
pd.merge(df1, df2, left_on='id', right_on='user_id')

# ========== Join on Index ==========
pd.merge(df1, df2, left_index=True, right_index=True)

# ========== Indicator (show merge type) ==========
pd.merge(df1, df2, on='key', how='outer', indicator=True)
# Adds '_merge' column: 'left_only', 'right_only', 'both'

# ========== Suffixes for Duplicate Columns ==========
pd.merge(df1, df2, on='key', suffixes=('_left', '_right'))
```

### **8.2 Join (Index-based)**

```python
# ========== DataFrame.join ==========
df1.join(df2, how='inner')
df1.join(df2, how='left')
df1.join(df2, on='key')  # Join on column from df1

# ========== Join Multiple DataFrames ==========
df1.join([df2, df3, df4])
```

### **8.3 Concat**

```python
# ========== Vertical Concatenation (stack rows) ==========
pd.concat([df1, df2])
pd.concat([df1, df2], ignore_index=True)  # Reset index

# ========== Horizontal Concatenation (add columns) ==========
pd.concat([df1, df2], axis=1)

# ========== With Keys (MultiIndex) ==========
pd.concat([df1, df2], keys=['first', 'second'])

# ========== Append (deprecated, use concat) ==========
# Old: df1.append(df2)
# New: pd.concat([df1, df2])
```

---

## 🔄 PART 9: RESHAPING DATA

### **9.1 Pivot & Melt**

```python
# ========== Pivot (Long to Wide) ==========
df_wide = df.pivot(
    index='date',
    columns='product',
    values='sales'
)

# ========== Melt (Wide to Long) ==========
df_long = pd.melt(
    df,
    id_vars=['date'],
    value_vars=['product_a', 'product_b'],
    var_name='product',
    value_name='sales'
)

# Melt all columns except id_vars
df_long = pd.melt(df, id_vars=['date', 'store'])
```

### **9.2 Stack & Unstack**

```python
# ========== Stack (Columns to Rows) ==========
df.stack()

# ========== Unstack (Rows to Columns) ==========
df.unstack()
df.unstack(level=0)  # Specific level of MultiIndex
df.unstack(fill_value=0)
```

### **9.3 Transpose**

```python
df.T  # Transpose
df.transpose()
```

---

## 📅 PART 10: TIME SERIES OPERATIONS

### **10.1 DateTime Creation**

```python
# ========== Convert to DateTime ==========
df['date'] = pd.to_datetime(df['date'])
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# ========== Date Range ==========
dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
dates = pd.date_range('2024-01-01', periods=365, freq='D')
dates = pd.date_range('2024-01-01', '2024-12-31', freq='M')  # Month end

# Frequencies: 'D' daily, 'W' weekly, 'M' month end, 'MS' month start, 'Y' year, 'H' hourly
```

### **10.2 DateTime Components**

```python
# ========== Extract Components ==========
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['day'] = df['date'].dt.day
df['dayofweek'] = df['date'].dt.dayofweek  # 0=Monday, 6=Sunday
df['dayofyear'] = df['date'].dt.dayofyear
df['quarter'] = df['date'].dt.quarter
df['week'] = df['date'].dt.isocalendar().week

# Time components
df['hour'] = df['datetime'].dt.hour
df['minute'] = df['datetime'].dt.minute
df['second'] = df['datetime'].dt.second

# ========== Date Properties ==========
df['is_month_end'] = df['date'].dt.is_month_end
df['is_month_start'] = df['date'].dt.is_month_start
df['is_quarter_end'] = df['date'].dt.is_quarter_end
df['days_in_month'] = df['date'].dt.days_in_month
```

### **10.3 Date Arithmetic**

```python
# ========== Add/Subtract Time ==========
df['next_week'] = df['date'] + pd.Timedelta(days=7)
df['last_month'] = df['date'] - pd.DateOffset(months=1)

# ========== Date Difference ==========
df['days_diff'] = (df['end_date'] - df['start_date']).dt.days

# ========== Resampling (Time-based GroupBy) ==========
df.set_index('date', inplace=True)

# Daily to monthly
df.resample('M').sum()
df.resample('M').mean()

# Upsampling (fill forward)
df.resample('D').ffill()

# ========== Shifting ==========
df['prev_day'] = df['value'].shift(1)
df['next_day'] = df['value'].shift(-1)
df['prev_week'] = df['value'].shift(7)
```

---

## 🪟 PART 11: WINDOW FUNCTIONS

### **11.1 Rolling Windows**

```python
# ========== Rolling Mean ==========
df['rolling_mean_7'] = df['value'].rolling(window=7).mean()

# ========== Rolling Sum ==========
df['rolling_sum_7'] = df['value'].rolling(window=7).sum()

# ========== Rolling Statistics ==========
df['rolling_std'] = df['value'].rolling(window=7).std()
df['rolling_min'] = df['value'].rolling(window=7).min()
df['rolling_max'] = df['value'].rolling(window=7).max()

# ========== Custom Rolling Function ==========
df['rolling_custom'] = df['value'].rolling(window=7).apply(
    lambda x: x.max() - x.min()
)

# ========== Rolling with min_periods ==========
df['rolling_mean'] = df['value'].rolling(window=7, min_periods=1).mean()
```

### **11.2 Expanding Windows**

```python
# ========== Expanding (Cumulative) ==========
df['expanding_mean'] = df['value'].expanding().mean()
df['expanding_sum'] = df['value'].expanding().sum()
df['expanding_max'] = df['value'].expanding().max()
```

### **11.3 Exponential Weighted Moving Average**

```python
# ========== EWMA ==========
df['ewma'] = df['value'].ewm(span=7).mean()
df['ewma'] = df['value'].ewm(alpha=0.3).mean()
```

---

## ⚡ PART 12: PERFORMANCE OPTIMIZATION

### **12.1 Memory Optimization**

```python
# ========== Check Memory Usage ==========
df.info(memory_usage='deep')
df.memory_usage(deep=True)

# ========== Reduce Memory ==========
# Use category for low-cardinality strings
df['category'] = df['category'].astype('category')

# Downcast numeric types
df['int_col'] = pd.to_numeric(df['int_col'], downcast='integer')
df['float_col'] = pd.to_numeric(df['float_col'], downcast='float')

# ========== Read CSV Efficiently ==========
df = pd.read_csv(
    'large_file.csv',
    dtype={'category': 'category'},
    parse_dates=['date'],
    usecols=['col1', 'col2'],  # Read only needed columns
    nrows=100000  # Limit rows
)
```

### **12.2 Vectorization (Fastest)**

```python
# ❌ SLOW: Loop
result = []
for val in df['age']:
    result.append(val * 2)
df['age_doubled'] = result

# ✅ FAST: Vectorized
df['age_doubled'] = df['age'] * 2

# ❌ SLOW: Apply
df['age_doubled'] = df['age'].apply(lambda x: x * 2)

# ✅ FAST: Vectorized operations
df['full_name'] = df['first_name'] + ' ' + df['last_name']
df['is_adult'] = df['age'] >= 18
df['category'] = np.where(df['age'] >= 18, 'Adult', 'Minor')
```

### **12.3 Query vs Boolean Indexing**

```python
# Sometimes query() is faster
df.query('age > 25 and city == "NYC"')

# Boolean indexing
df[(df['age'] > 25) & (df['city'] == 'NYC')]
```

### **12.4 Eval for Complex Expressions**

```python
# ✅ FAST for complex arithmetic
df.eval('result = (col_a + col_b) * col_c - col_d')

# Instead of
df['result'] = (df['col_a'] + df['col_b']) * df['col_c'] - df['col_d']
```

---

## 🎓 BEST PRACTICES

### **Production Patterns**

```python
# ========== 1. Read with Schema ==========
dtype_dict = {
    'user_id': 'int64',
    'category': 'category',
    'amount': 'float64'
}
df = pd.read_csv('data.csv', dtype=dtype_dict, parse_dates=['date'])

# ========== 2. Chain Operations ==========
df_clean = (df
    .drop_duplicates(subset=['user_id'])
    .dropna(subset=['email'])
    .assign(
        age_group=lambda x: pd.cut(x['age'], bins=[0, 18, 65, 100]),
        full_name=lambda x: x['first_name'] + ' ' + x['last_name']
    )
    .sort_values('date')
    .reset_index(drop=True)
)

# ========== 3. Error Handling ==========
try:
    df = pd.read_csv('data.csv')
except FileNotFoundError:
    print("File not found")
except pd.errors.EmptyDataError:
    print("File is empty")

# ========== 4. Validate Data ==========
assert df['age'].min() >= 0, "Age cannot be negative"
assert df['email'].notnull().all(), "Email cannot be null"
assert df.index.is_unique, "Index must be unique"
```

---

## 📋 QUICK REFERENCE

```
TASK → FUNCTION
├─ Read CSV → pd.read_csv()
├─ Filter rows → df[condition]
├─ Select columns → df[['col1', 'col2']]
├─ Drop nulls → df.dropna()
├─ Fill nulls → df.fillna()
├─ Remove duplicates → df.drop_duplicates()
├─ Sort → df.sort_values()
├─ Group & aggregate → df.groupby().agg()
├─ Merge → pd.merge()
├─ Pivot → df.pivot_table()
├─ Apply function → df.apply()
├─ Rolling mean → df.rolling().mean()
└─ To CSV → df.to_csv()
```

---

**STATUS:** Complete Pandas guide ready! 🐼

This covers ALL essential Pandas operations for data engineering!
