# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Classification Data Ingestion Pipeline
# MAGIC 
# MAGIC **Detective Databricks Case #1: Data Lake Foundation**
# MAGIC 
# MAGIC This notebook ingests classification results from JSON files into a Delta Lake for scalable analytics.
# MAGIC 
# MAGIC ## Pipeline Stages:
# MAGIC 1. **Bronze Layer**: Raw JSON ingestion
# MAGIC 2. **Schema Enforcement**: Validate data structure
# MAGIC 3. **Delta Lake Storage**: ACID-compliant data lake
# MAGIC 4. **Learning Database Migration**: Convert learning_database.json to Delta

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
from delta.tables import DeltaTable
import json

# Define paths
BRONZE_PATH = "/mnt/classification-data/bronze/results"
SILVER_PATH = "/mnt/classification-data/silver/results"
LEARNING_DB_PATH = "/mnt/classification-data/delta/learning_database"

# GitHub repo data path (adjust based on your clone location)
SOURCE_DATA_PATH = "/Workspace/Repos/your-username/TAMU-Datathon/backend/results"

print(f"Bronze Path: {BRONZE_PATH}")
print(f"Silver Path: {SILVER_PATH}")
print(f"Learning DB Path: {LEARNING_DB_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Define Classification Result Schema

# COMMAND ----------

# Define comprehensive schema for classification results
classification_schema = StructType([
    StructField("document_id", StringType(), False),
    StructField("filename", StringType(), False),
    StructField("classification", StringType(), False),
    StructField("confidence", DoubleType(), False),
    StructField("summary", StringType(), True),
    StructField("reasoning", StringType(), True),
    StructField("secondary_labels", ArrayType(StringType()), True),
    StructField("additional_labels", ArrayType(StringType()), True),
    StructField("label_confidence", MapType(StringType(), DoubleType()), True),
    
    # Evidence array
    StructField("evidence", ArrayType(StructType([
        StructField("page", IntegerType(), True),
        StructField("region", StringType(), True),
        StructField("quote", StringType(), True),
        StructField("reasoning", StringType(), True),
        StructField("image_index", IntegerType(), True),
        StructField("sensitivity_level", StringType(), True),
        StructField("keywords", ArrayType(StringType()), True)
    ])), True),
    
    # Safety check
    StructField("safety_check", StructType([
        StructField("is_safe", BooleanType(), True),
        StructField("flags", ArrayType(StringType()), True),
        StructField("details", StringType(), True),
        StructField("confidence", DoubleType(), True)
    ]), True),
    
    # Metadata
    StructField("page_count", IntegerType(), True),
    StructField("image_count", IntegerType(), True),
    StructField("processing_time", DoubleType(), True),
    StructField("timestamp", StringType(), True),
    StructField("requires_review", BooleanType(), True),
    StructField("review_reason", StringType(), True),
    
    # Text segments
    StructField("text_segments", ArrayType(StructType([
        StructField("text", StringType(), True),
        StructField("classification", StringType(), True),
        StructField("confidence", DoubleType(), True),
        StructField("page", IntegerType(), True),
        StructField("keywords", ArrayType(StringType()), True)
    ])), True),
    
    # Image analysis
    StructField("image_analysis", ArrayType(StructType([
        StructField("image_index", IntegerType(), True),
        StructField("analysis", StringType(), True),
        StructField("classification", StringType(), True),
        StructField("confidence", DoubleType(), True)
    ])), True)
])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Bronze Layer: Ingest Raw Classification Results

# COMMAND ----------

# Read all classification result JSON files
# Using permissive mode to handle any schema variations
bronze_df = spark.read \
    .option("multiLine", True) \
    .option("mode", "PERMISSIVE") \
    .schema(classification_schema) \
    .json(f"{SOURCE_DATA_PATH}/*.json")

# Add metadata columns
bronze_df = bronze_df \
    .withColumn("ingestion_timestamp", F.current_timestamp()) \
    .withColumn("source_file", F.input_file_name()) \
    .withColumn("data_quality_flag", 
                F.when(F.col("document_id").isNull(), "INVALID")
                 .otherwise("VALID"))

# Display sample
display(bronze_df.limit(5))

print(f"Total records ingested: {bronze_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Write to Bronze Delta Table

# COMMAND ----------

# Write to Bronze layer with Delta Lake
bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", True) \
    .partitionBy("classification") \
    .save(BRONZE_PATH)

# Create Delta table
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS classification_bronze
    USING DELTA
    LOCATION '{BRONZE_PATH}'
""")

print(f"✅ Bronze table created: classification_bronze")
print(f"   Records: {spark.read.format('delta').load(BRONZE_PATH).count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Data Quality Checks

# COMMAND ----------

# Quality checks on Bronze data
bronze_quality = spark.read.format("delta").load(BRONZE_PATH)

quality_metrics = bronze_quality.agg(
    F.count("*").alias("total_records"),
    F.countDistinct("document_id").alias("unique_documents"),
    F.count(F.when(F.col("confidence").isNull(), True)).alias("null_confidence"),
    F.count(F.when(F.col("classification").isNull(), True)).alias("null_classification"),
    F.avg("confidence").alias("avg_confidence"),
    F.avg("processing_time").alias("avg_processing_time"),
    F.min("processing_time").alias("min_processing_time"),
    F.max("processing_time").alias("max_processing_time")
).collect()[0]

print("📊 Data Quality Metrics:")
print(f"   Total Records: {quality_metrics['total_records']}")
print(f"   Unique Documents: {quality_metrics['unique_documents']}")
print(f"   Null Confidence: {quality_metrics['null_confidence']}")
print(f"   Null Classification: {quality_metrics['null_classification']}")
print(f"   Avg Confidence: {quality_metrics['avg_confidence']:.4f}")
print(f"   Avg Processing Time: {quality_metrics['avg_processing_time']:.2f}s")
print(f"   Min/Max Processing Time: {quality_metrics['min_processing_time']:.2f}s / {quality_metrics['max_processing_time']:.2f}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Learning Database Migration

# COMMAND ----------

# Define schema for learning database
learning_schema = StructType([
    StructField("version", StringType(), True),
    StructField("created_at", StringType(), True),
    StructField("total_feedback_count", IntegerType(), True),
    StructField("learning_entries", ArrayType(StructType([
        StructField("document_id", StringType(), True),
        StructField("reviewer_id", StringType(), True),
        StructField("approved", BooleanType(), True),
        StructField("corrected_classification", StringType(), True),
        StructField("original_classification", StringType(), True),
        StructField("feedback_notes", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("document_context", StructType([
            StructField("filename", StringType(), True),
            StructField("page_count", IntegerType(), True),
            StructField("image_count", IntegerType(), True),
            StructField("summary", StringType(), True),
            StructField("original_classification", StringType(), True),
            StructField("confidence", DoubleType(), True),
            StructField("key_evidence", ArrayType(StructType([
                StructField("quote", StringType(), True),
                StructField("reasoning", StringType(), True)
            ])), True),
            StructField("keywords", ArrayType(StringType()), True)
        ]), True)
    ])), True)
])

# Read learning database JSON
learning_raw_df = spark.read \
    .schema(learning_schema) \
    .json(f"{SOURCE_DATA_PATH}/learning_database.json")

# Explode learning entries into individual rows
learning_df = learning_raw_df.select(
    F.col("version"),
    F.col("created_at"),
    F.explode("learning_entries").alias("entry")
).select(
    "version",
    "created_at",
    "entry.document_id",
    "entry.reviewer_id",
    "entry.approved",
    "entry.corrected_classification",
    "entry.original_classification",
    "entry.feedback_notes",
    F.to_timestamp("entry.timestamp").alias("feedback_timestamp"),
    "entry.document_context.*"
)

# Add derived columns
learning_df = learning_df \
    .withColumn("is_correction", F.col("approved") == False) \
    .withColumn("feedback_date", F.to_date("feedback_timestamp")) \
    .withColumn("ingestion_timestamp", F.current_timestamp())

display(learning_df.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Write Learning Database to Delta

# COMMAND ----------

# Write to Delta with partitioning
learning_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", True) \
    .partitionBy("corrected_classification", "feedback_date") \
    .save(LEARNING_DB_PATH)

# Create table
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS learning_database
    USING DELTA
    LOCATION '{LEARNING_DB_PATH}'
""")

print(f"✅ Learning database migrated to Delta Lake")
print(f"   Total feedback entries: {learning_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Enable Delta Lake Features

# COMMAND ----------

# Enable Change Data Feed for learning database
spark.sql(f"""
    ALTER TABLE learning_database
    SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

# Enable automatic optimization
spark.sql(f"""
    ALTER TABLE learning_database
    SET TBLPROPERTIES (
        delta.autoOptimize.optimizeWrite = true,
        delta.autoOptimize.autoCompact = true
    )
""")

# Enable for classification_bronze as well
spark.sql(f"""
    ALTER TABLE classification_bronze
    SET TBLPROPERTIES (
        delta.enableChangeDataFeed = true,
        delta.autoOptimize.optimizeWrite = true,
        delta.autoOptimize.autoCompact = true
    )
""")

print("✅ Delta Lake features enabled:")
print("   - Change Data Feed")
print("   - Auto Optimize Write")
print("   - Auto Compact")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Learning Database Analytics

# COMMAND ----------

# Analyze learning patterns
learning_stats = spark.sql("""
    SELECT 
        corrected_classification,
        COUNT(*) as total_feedback,
        SUM(CASE WHEN is_correction THEN 1 ELSE 0 END) as corrections,
        SUM(CASE WHEN NOT is_correction THEN 1 ELSE 0 END) as approvals,
        ROUND(SUM(CASE WHEN is_correction THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as correction_rate_pct,
        AVG(confidence) as avg_original_confidence
    FROM learning_database
    GROUP BY corrected_classification
    ORDER BY correction_rate_pct DESC
""")

display(learning_stats)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Time Travel Demo

# COMMAND ----------

# Show Delta Lake history
learning_history = spark.sql("""
    DESCRIBE HISTORY learning_database
    LIMIT 10
""")

display(learning_history)

# Example: Query previous version
# previous_version = spark.read.format("delta").option("versionAsOf", 0).load(LEARNING_DB_PATH)
# display(previous_version.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Summary Statistics

# COMMAND ----------

# Classification distribution
classification_dist = spark.sql("""
    SELECT 
        classification,
        COUNT(*) as count,
        ROUND(AVG(confidence), 4) as avg_confidence,
        ROUND(AVG(processing_time), 2) as avg_processing_time,
        SUM(CASE WHEN requires_review THEN 1 ELSE 0 END) as review_count,
        ROUND(SUM(CASE WHEN requires_review THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as review_rate_pct
    FROM classification_bronze
    WHERE data_quality_flag = 'VALID'
    GROUP BY classification
    ORDER BY count DESC
""")

display(classification_dist)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Bronze Layer Complete!
# MAGIC 
# MAGIC **Next Steps:**
# MAGIC 1. Run notebook `02_data_transformation.py` to build Silver layer
# MAGIC 2. Set up scheduled jobs for continuous ingestion
# MAGIC 3. Configure alerts for data quality issues
# MAGIC 
# MAGIC **Key Achievements:**
# MAGIC - ✅ Migrated 10+ JSON files to unified Delta Lake
# MAGIC - ✅ Learning database now supports ACID transactions
# MAGIC - ✅ Enabled time travel for audit trails
# MAGIC - ✅ Partitioned by classification for optimal queries
# MAGIC - ✅ Data quality checks in place
