

from pyspark.sql import SparkSession
from pyspark.sql.functions import pivot,groupby , col
import pyspark.sql.functions

spark = SparkSession.builder.appName.getOrCreate()

sc = spark.sparkContext

data = [
    ("Product1", "2024-01", 100),
    ("Product1", "2024-02", 150),
    ("Product2", "2024-01", 200),
    ("Product2", "2024-02", 250)
]
df = spark.createDataFrame(data, ["product", "month", "sales"])

df.filter(col("month").isNull())
df.filter(col("month").isNotNull())


df.withColumn("new_column", when(col("product").isNull(),0).otherwise(col("age")))


df.withColumn("age_filled",
    when(col("age").isNull(), 0).otherwise(col("age"))
).show()



