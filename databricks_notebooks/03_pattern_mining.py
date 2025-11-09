# Databricks notebook source
# MAGIC %md
# MAGIC # 🔬 Classification Pattern Mining
# MAGIC 
# MAGIC **Detective Databricks Case #3: Uncovering Hidden Patterns**
# MAGIC 
# MAGIC This notebook uses Spark MLlib to discover patterns in misclassifications and auto-generate training examples.
# MAGIC 
# MAGIC ## Analysis Pipeline:
# MAGIC 1. **Misclassification Analysis**: Identify common errors
# MAGIC 2. **Feature Extraction**: TF-IDF on feedback notes
# MAGIC 3. **Clustering**: Group similar misclassifications
# MAGIC 4. **Pattern Discovery**: Extract actionable insights
# MAGIC 5. **Training Data Generation**: Auto-generate examples

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.ml.feature import Tokenizer, HashingTF, IDF, StopWordsRemover
from pyspark.ml.clustering import KMeans
from pyspark.ml import Pipeline
import matplotlib.pyplot as plt
import seaborn as sns

# Paths
LEARNING_DB_PATH = "/mnt/classification-data/delta/learning_database"
CLASSIFICATION_PATH = "/mnt/classification-data/bronze/results"
PATTERNS_OUTPUT_PATH = "/mnt/classification-data/gold/patterns"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load Learning Database

# COMMAND ----------

# Load learning database
learning_df = spark.read.format("delta").load(LEARNING_DB_PATH)

# Filter for corrections only (where AI was wrong)
corrections_df = learning_df.filter(F.col("is_correction") == True)

print(f"Total feedback entries: {learning_df.count()}")
print(f"Corrections: {corrections_df.count()}")
print(f"Correction rate: {corrections_df.count() / learning_df.count() * 100:.2f}%")

display(corrections_df.select("document_id", "filename", "original_classification", 
                             "corrected_classification", "feedback_notes").limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Misclassification Matrix

# COMMAND ----------

# Create confusion matrix for misclassifications
confusion_matrix = corrections_df.groupBy("original_classification", "corrected_classification") \
    .agg(F.count("*").alias("count")) \
    .orderBy(F.desc("count"))

display(confusion_matrix)

# Calculate most common misclassification patterns
top_patterns = confusion_matrix.limit(5).collect()

print("\n📊 Top 5 Misclassification Patterns:")
for i, row in enumerate(top_patterns, 1):
    print(f"{i}. {row['original_classification']} → {row['corrected_classification']}: {row['count']} cases")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Text Feature Extraction from Feedback

# COMMAND ----------

# Prepare text data - combine feedback notes with filename for context
text_df = corrections_df.select(
    "document_id",
    "filename",
    "original_classification",
    "corrected_classification",
    F.concat_ws(" ", F.col("feedback_notes"), F.col("filename")).alias("feedback_text"),
    "confidence"
)

# Text processing pipeline
tokenizer = Tokenizer(inputCol="feedback_text", outputCol="words")
remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")
hashingTF = HashingTF(inputCol="filtered_words", outputCol="raw_features", numFeatures=1000)
idf = IDF(inputCol="raw_features", outputCol="features")

# Build and fit pipeline
pipeline = Pipeline(stages=[tokenizer, remover, hashingTF, idf])
pipeline_model = pipeline.fit(text_df)
features_df = pipeline_model.transform(text_df)

display(features_df.select("document_id", "feedback_text", "features").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. K-Means Clustering to Find Pattern Groups

# COMMAND ----------

# Optimal number of clusters (try different k values)
k_values = [3, 5, 7]
silhouette_scores = []

from pyspark.ml.evaluation import ClusteringEvaluator

for k in k_values:
    kmeans = KMeans(k=k, seed=42, featuresCol="features", predictionCol=f"cluster_{k}")
    model = kmeans.fit(features_df)
    predictions = model.transform(features_df)
    
    evaluator = ClusteringEvaluator()
    score = evaluator.evaluate(predictions)
    silhouette_scores.append(score)
    
    print(f"K={k}: Silhouette Score = {score:.4f}")

# Use k=5 as default (good balance)
optimal_k = 5
kmeans = KMeans(k=optimal_k, seed=42, featuresCol="features", predictionCol="cluster")
kmeans_model = kmeans.fit(features_df)
clustered_df = kmeans_model.transform(features_df)

display(clustered_df.select("document_id", "feedback_text", "original_classification", 
                           "corrected_classification", "cluster").limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Analyze Cluster Patterns

# COMMAND ----------

# Analyze each cluster
cluster_analysis = clustered_df.groupBy("cluster", "original_classification", "corrected_classification") \
    .agg(
        F.count("*").alias("count"),
        F.collect_list("filename").alias("example_files"),
        F.collect_list("feedback_text").alias("feedback_examples")
    ) \
    .orderBy("cluster", F.desc("count"))

display(cluster_analysis)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Extract Top Keywords per Cluster

# COMMAND ----------

# Extract top words from each cluster
from pyspark.sql.window import Window

# Explode words for each cluster
cluster_words = clustered_df.select(
    "cluster",
    F.explode("filtered_words").alias("word")
)

# Count word frequency per cluster
word_freq = cluster_words.groupBy("cluster", "word") \
    .agg(F.count("*").alias("frequency")) \
    .orderBy("cluster", F.desc("frequency"))

# Get top 10 words per cluster
window_spec = Window.partitionBy("cluster").orderBy(F.desc("frequency"))
top_words_per_cluster = word_freq.withColumn("rank", F.row_number().over(window_spec)) \
    .filter(F.col("rank") <= 10) \
    .groupBy("cluster") \
    .agg(F.collect_list(F.struct("word", "frequency")).alias("top_words"))

display(top_words_per_cluster)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Pattern Insights & Recommendations

# COMMAND ----------

# Generate pattern insights
pattern_insights = spark.sql("""
    SELECT 
        cluster,
        original_classification,
        corrected_classification,
        COUNT(*) as error_count,
        ROUND(AVG(confidence), 4) as avg_confidence_when_wrong,
        COLLECT_LIST(STRUCT(filename, feedback_text)) as examples
    FROM (
        SELECT * FROM clustered_df_temp
    )
    GROUP BY cluster, original_classification, corrected_classification
    HAVING error_count >= 1
    ORDER BY error_count DESC
""")

# Register temp view for SQL
clustered_df.createOrReplaceTempView("clustered_df_temp")

pattern_insights = spark.sql("""
    SELECT 
        cluster,
        original_classification,
        corrected_classification,
        COUNT(*) as error_count,
        ROUND(AVG(confidence), 4) as avg_confidence_when_wrong
    FROM clustered_df_temp
    GROUP BY cluster, original_classification, corrected_classification
    HAVING error_count >= 1
    ORDER BY error_count DESC
""")

display(pattern_insights)

print("\n🎯 Key Insights:")
insights = pattern_insights.collect()
for i, insight in enumerate(insights[:5], 1):
    print(f"{i}. Cluster {insight['cluster']}: {insight['original_classification']} → {insight['corrected_classification']}")
    print(f"   Occurred {insight['error_count']} times with avg confidence {insight['avg_confidence_when_wrong']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Auto-Generate Training Examples

# COMMAND ----------

# Generate high-quality training examples from patterns
training_examples = clustered_df.select(
    "document_id",
    "filename",
    "original_classification",
    "corrected_classification",
    "feedback_notes",
    "confidence",
    "cluster",
    
    # Generate training instruction
    F.concat(
        F.lit("When you see a document like '"),
        F.col("filename"),
        F.lit("', classify it as '"),
        F.col("corrected_classification"),
        F.lit("' not '"),
        F.col("original_classification"),
        F.lit("'. Reason: "),
        F.col("feedback_notes")
    ).alias("training_instruction"),
    
    # Calculate training weight (higher confidence errors = better examples)
    (F.col("confidence") * 10).alias("training_weight")
).filter(
    # Only use high-confidence errors as training examples
    F.col("confidence") > 0.7
)

print(f"\n✅ Generated {training_examples.count()} high-quality training examples")
display(training_examples.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Save Training Examples

# COMMAND ----------

# Write training examples to Delta table
training_examples.write \
    .format("delta") \
    .mode("overwrite") \
    .save(f"{PATTERNS_OUTPUT_PATH}/training_examples")

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS training_examples
    USING DELTA
    LOCATION '{PATTERNS_OUTPUT_PATH}/training_examples'
""")

print(f"✅ Training examples saved to Delta table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Pattern Summary Report

# COMMAND ----------

# Create comprehensive pattern report
pattern_report = spark.sql("""
    SELECT 
        'Total Corrections' as metric,
        CAST(COUNT(*) AS STRING) as value
    FROM clustered_df_temp
    
    UNION ALL
    
    SELECT 
        'Unique Patterns' as metric,
        CAST(COUNT(DISTINCT CONCAT(original_classification, '->', corrected_classification)) AS STRING) as value
    FROM clustered_df_temp
    
    UNION ALL
    
    SELECT 
        'Pattern Clusters' as metric,
        CAST(COUNT(DISTINCT cluster) AS STRING) as value
    FROM clustered_df_temp
    
    UNION ALL
    
    SELECT 
        'High-Confidence Errors (>0.8)' as metric,
        CAST(SUM(CASE WHEN confidence > 0.8 THEN 1 ELSE 0 END) AS STRING) as value
    FROM clustered_df_temp
    
    UNION ALL
    
    SELECT 
        'Most Common Error' as metric,
        CONCAT(original_classification, ' → ', corrected_classification, ' (', CAST(count AS STRING), ' times)')
    FROM (
        SELECT original_classification, corrected_classification, COUNT(*) as count
        FROM clustered_df_temp
        GROUP BY original_classification, corrected_classification
        ORDER BY count DESC
        LIMIT 1
    )
""")

display(pattern_report)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Export Insights for Prompt Library

# COMMAND ----------

# Generate prompt enhancement suggestions
prompt_enhancements = clustered_df.groupBy("cluster", "corrected_classification") \
    .agg(
        F.count("*").alias("pattern_count"),
        F.concat_ws("; ", F.collect_list("feedback_notes")).alias("combined_feedback"),
        F.collect_list("filename").alias("example_files")
    ) \
    .withColumn(
        "prompt_enhancement",
        F.concat(
            F.lit("For "),
            F.col("corrected_classification"),
            F.lit(" classification, pay special attention to: "),
            F.col("combined_feedback")
        )
    )

display(prompt_enhancements.select("corrected_classification", "pattern_count", "prompt_enhancement"))

# Save to Delta
prompt_enhancements.write \
    .format("delta") \
    .mode("overwrite") \
    .save(f"{PATTERNS_OUTPUT_PATH}/prompt_enhancements")

print("✅ Prompt enhancements saved")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Pattern Analysis Complete!
# MAGIC 
# MAGIC **Key Achievements:**
# MAGIC - ✅ Identified {optimal_k} distinct misclassification pattern groups
# MAGIC - ✅ Generated training examples from high-confidence errors
# MAGIC - ✅ Extracted keywords driving misclassifications
# MAGIC - ✅ Created prompt enhancement suggestions
# MAGIC - ✅ Built reusable pattern detection pipeline
# MAGIC 
# MAGIC **Next Steps:**
# MAGIC 1. Integrate training examples into prompt library
# MAGIC 2. Update classifier with discovered patterns
# MAGIC 3. Set up automated pattern detection workflow
# MAGIC 4. Monitor improvement in accuracy

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🎯 Impact Summary
# MAGIC 
# MAGIC This pattern mining approach enables:
# MAGIC - **Automated Learning**: System learns from mistakes without manual analysis
# MAGIC - **Scalable Improvement**: Handles 1000s of corrections efficiently
# MAGIC - **Data-Driven Prompts**: Enhance prompts based on real patterns
# MAGIC - **Continuous Evolution**: Pattern detection runs automatically
