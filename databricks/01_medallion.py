# Databricks notebook source
# Run on compute supporting Unity Catalog and Delta Lake.
# Install the project wheel on compute before running this notebook.
from career_ai.core import skills
from pyspark.sql import functions as F, types as T

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("schema", "career_dev")
dbutils.widgets.text("input_path", "")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
input_path = dbutils.widgets.get("input_path")
import re
for name in (catalog, schema):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Provide valid catalog/schema identifiers")
if not input_path.startswith("/Volumes/"):
    raise ValueError("Upload sample_jobs.json to a Unity Catalog Volume and provide its /Volumes/ path")
namespace = f"`{catalog}`.`{schema}`"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {namespace}")
raw_schema = T.StructType([T.StructField(k, T.StringType()) for k in
                          ("title", "company", "description", "source_url")])
raw = spark.read.schema(raw_schema).option("multiLine", True).json(input_path)
bronze = raw.withColumn("ingested_at", F.current_timestamp()).withColumn("source_file", F.lit(input_path))
# v0.1 rebuilds a complete batch snapshot; use a development schema only.
bronze.write.format("delta").mode("overwrite").saveAsTable(f"{namespace}.bronze_jobs")
clean = bronze
for column in ("title", "company", "description"):
    clean = clean.withColumn(column, F.trim(F.regexp_replace(F.col(column), r"\s+", " ")))
valid = F.lit(True)
for column in ("title", "company", "description"):
    valid = valid & F.col(column).isNotNull() & (F.length(F.col(column)) > 0)
clean.filter(~valid).write.format("delta").mode("overwrite").saveAsTable(f"{namespace}.quarantine_jobs")
extract = F.udf(skills, T.ArrayType(T.StringType()))
silver = (clean.filter(valid)
          .withColumn("job_id", F.sha2(F.to_json(F.struct("company", "title", "description")), 256))
          .dropDuplicates(["job_id"])
          .withColumn("skills", extract("description")))
silver.write.format("delta").mode("overwrite").saveAsTable(f"{namespace}.silver_jobs")
gold = silver.select(F.explode("skills").alias("skill")).groupBy("skill").count()
gold.write.format("delta").mode("overwrite").saveAsTable(f"{namespace}.gold_skill_demand")
display(gold.orderBy(F.desc("count")))
