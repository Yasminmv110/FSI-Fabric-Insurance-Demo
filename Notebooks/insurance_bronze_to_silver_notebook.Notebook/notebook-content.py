# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "00000000-0000-0000-0000-000000000000",
# META       "default_lakehouse_name": "LH_Insurance",
# META       "default_lakehouse_workspace_id": "00000000-0000-0000-0000-000000000000",
# META       "known_lakehouses": [
# META         {
# META           "id": "00000000-0000-0000-0000-000000000000"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# ============================================================
# Fabric Notebook: Bronze to Silver Transformation
# Author   : Yasmin Udaipurwala
# Purpose  : Read raw CSVs from Bronze, clean, deduplicate,
#            enforce schema, and write to Silver Delta tables
# Lakehouse: LH_Insurance
# ============================================================

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StringType, IntegerType, DoubleType,
    BooleanType, DateType
)
from datetime import datetime

# 
# CONFIGURATION
# 

BRONZE_BASE_PATH = "Files/Bronze_Raw_Data"   # Relative to Lakehouse root
SILVER_SCHEMA    = "Silver"         # Silver schema/database name

# Table definitions:
#   table_name -> (csv_file_path, primary_key, date_col_for_dedup)
TABLE_CONFIG = {
    "offices": (
        f"{BRONZE_BASE_PATH}/offices.csv",
        "office_id",
        None
    ),
    "policyholders": (
        f"{BRONZE_BASE_PATH}/policyholders.csv",
        "policyholder_id",
        "date_of_birth"
    ),
    "insured_assets": (
        f"{BRONZE_BASE_PATH}/insured_assets.csv",
        "asset_id",
        "last_inspection_date"
    ),
    "adjusters": (
        f"{BRONZE_BASE_PATH}/adjusters.csv",
        "adjuster_id",
        "hire_date"
    ),
    "policies": (
        f"{BRONZE_BASE_PATH}/policies.csv",
        "policy_id",
        "effective_date"
    ),
    "claims": (
        f"{BRONZE_BASE_PATH}/claims.csv",
        "claim_id",
        "filed_date"
    ),
    "claim_events": (
        f"{BRONZE_BASE_PATH}/claim_events.csv",
        "claim_event_id",
        "created_at"
    ),
    "asset_inspections": (
        f"{BRONZE_BASE_PATH}/asset_inspections.csv",
        "inspection_id",
        "scheduled_date"
    ),
}

# Columns per table that must NOT be null (NOT NULL in schema)
NOT_NULL_COLUMNS = {
    "offices":           ["office_id", "name", "office_type", "address",
                          "city", "state", "zip_code", "latitude",
                          "longitude", "timezone"],
    "policyholders":     ["policyholder_id", "policyholder_number",
                          "full_name", "policyholder_type"],
    "insured_assets":    ["asset_id", "asset_number", "asset_type",
                          "asset_description", "year"],
    "adjusters":         ["adjuster_id", "employee_id", "first_name",
                          "last_name", "license_number", "license_state",
                          "status", "home_office_id"],
    "policies":          ["policy_id", "policy_number", "policyholder_id",
                          "asset_id", "policy_type", "status"],
    "claims":            ["claim_id", "claim_number", "policy_id",
                          "policyholder_id", "asset_id", "adjuster_id",
                          "office_id", "claim_type", "status"],
    "claim_events":      ["claim_event_id", "event_number", "claim_id",
                          "adjuster_id", "event_type", "status"],
    "asset_inspections": ["inspection_id", "asset_id", "office_id",
                          "inspection_type", "status"],
}

# Explicit column type casts per table (col_name -> spark type)
COLUMN_TYPES = {
    "offices": {
        "latitude":          DoubleType(),
        "longitude":         DoubleType(),
        "adjuster_capacity": IntegerType(),
        "has_siu_unit":      BooleanType(),
    },
    "policyholders": {
        "risk_score": IntegerType(),
    },
    "insured_assets": {
        "year":            IntegerType(),
        "estimated_value": DoubleType(),
    },
    "adjusters": {
        "max_active_claims": IntegerType(),
    },
    "policies": {
        "coverage_amount": DoubleType(),
        "deductible":      DoubleType(),
        "premium_annual":  DoubleType(),
    },
    "claims": {
        "estimated_loss":       DoubleType(),
        "approved_amount":      DoubleType(),
        "incident_latitude":    DoubleType(),
        "incident_longitude":   DoubleType(),
    },
    "claim_events": {
        "cost_usd": DoubleType(),
    },
    "asset_inspections": {
        "appraised_value": DoubleType(),
    },
}

# Date columns (string to DateType) per table
DATE_COLUMNS = {
    "policyholders":     ["date_of_birth"],
    "insured_assets":    ["last_inspection_date"],
    "adjusters":         ["hire_date"],
    "policies":          ["effective_date", "expiration_date"],
    "claims":            ["incident_date", "filed_date"],
    "claim_events":      ["created_at", "completed_at"],
    "asset_inspections": ["scheduled_date", "completed_date"],
}

# String columns where Title Case is meaningful
TITLE_CASE_COLUMNS = {
    "offices":           ["name", "city", "office_type", "timezone"],
    "policyholders":     ["full_name", "city", "state",
                          "policyholder_type"],
    "insured_assets":    ["asset_type", "make", "model", "city",
                          "state", "condition"],
    "adjusters":         ["first_name", "last_name", "specializations",
                          "status"],
    "policies":          ["policy_type", "status"],
    "claims":            ["claim_type", "status", "priority"],
    "claim_events":      ["event_type", "status"],
    "asset_inspections": ["inspection_type", "status", "condition_rating"],
}

# Numeric bounds validation  column -> (min, max)
NUMERIC_BOUNDS = {
    "policyholders":  {"risk_score":        (300,  900)},
    "offices":        {"latitude":          (24.0, 49.5),
                       "longitude":         (-125.0, -66.0),
                       "adjuster_capacity": (1, 500)},
    "claims":         {"incident_latitude":  (24.0, 49.5),
                       "incident_longitude": (-125.0, -66.0),
                       "estimated_loss":     (0, 10_000_000),
                       "approved_amount":    (0, 10_000_000)},
    "insured_assets": {"year":            (1900, 2026),
                       "estimated_value": (0, 50_000_000)},
    "policies":       {"coverage_amount": (0, 50_000_000),
                       "deductible":      (0, 500_000),
                       "premium_annual":  (0, 500_000)},
    "claim_events":   {"cost_usd": (0, 10_000_000)},
    "asset_inspections": {"appraised_value": (0, 50_000_000)},
}

# 
# UTILITY FUNCTIONS
# 

def log(msg: str):
    """Simple timestamped logger."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]  {msg}")


def read_bronze_csv(path: str) -> DataFrame:
    """Read a CSV file from the Bronze landing zone."""
    return (
        spark.read
             .option("header", "true")
             .option("inferSchema", "false")   # all strings; we cast explicitly
             .option("nullValue", "")
             .option("emptyValue", "")
             .csv(path)
    )


def replace_empty_with_null(df: DataFrame) -> DataFrame:
    """Convert empty strings / whitespace-only cells to null."""
    str_cols = [c for c, t in df.dtypes if t == "string"]
    for col in str_cols:
        df = df.withColumn(
            col,
            F.when(F.trim(F.col(col)) == "", None)
             .otherwise(F.trim(F.col(col)))
        )
    return df


def apply_title_case(df: DataFrame, cols: list) -> DataFrame:
    """Apply Title Case to specified string columns (if they exist)."""
    existing = [c for c in cols if c in df.columns]
    for col in existing:
        df = df.withColumn(col, F.initcap(F.col(col)))
    return df


def cast_column_types(df: DataFrame, type_map: dict) -> DataFrame:
    """Cast columns to their proper Spark types."""
    for col_name, spark_type in type_map.items():
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(spark_type))
    return df


def parse_date_columns(df: DataFrame, date_cols: list) -> DataFrame:
    """Parse string date columns (yyyy-MM-dd) to DateType."""
    for col in date_cols:
        if col in df.columns:
            df = df.withColumn(col, F.to_date(F.col(col), "yyyy-MM-dd"))
    return df


def clean_phone(df: DataFrame) -> DataFrame:
    """Standardise phone: keep digits only, null if < 7 digits."""
    if "phone" in df.columns:
        df = df.withColumn(
            "phone",
            F.when(
                F.length(F.regexp_replace(F.col("phone"), r"\D", "")) < 7,
                None
            ).otherwise(F.regexp_replace(F.col("phone"), r"[^\d\+\-\(\) ]", ""))
        )
    return df


def clean_zip_code(df: DataFrame) -> DataFrame:
    """Null out zip codes that are not 5-digit numeric."""
    if "zip_code" in df.columns:
        df = df.withColumn(
            "zip_code",
            F.when(
                F.col("zip_code").rlike(r"^\d{5}$"),
                F.col("zip_code")
            ).otherwise(None)
        )
    return df


def apply_numeric_bounds(df: DataFrame, bounds: dict) -> DataFrame:
    """Clip numeric columns to valid [min, max] range; out-of-range to null."""
    for col_name, (lo, hi) in bounds.items():
        if col_name in df.columns:
            df = df.withColumn(
                col_name,
                F.when(
                    (F.col(col_name) >= lo) & (F.col(col_name) <= hi),
                    F.col(col_name)
                ).otherwise(None)
            )
    return df


def deduplicate(df: DataFrame, primary_key: str,
                date_col: str = None) -> DataFrame:
    """
    1. Drop exact duplicate rows.
    2. For duplicate PKs, keep the row with the latest date_col value
       (or first occurrence if no date_col is available).
    """
    # Step 1  exact row dedup
    df = df.dropDuplicates()

    # Step 2  PK-level dedup
    if date_col and date_col in df.columns:
        from pyspark.sql.window import Window
        w = (Window.partitionBy(primary_key)
                   .orderBy(F.col(date_col).desc_nulls_last()))
        df = (df.withColumn("_row_num", F.row_number().over(w))
                .filter(F.col("_row_num") == 1)
                .drop("_row_num"))
    else:
        # No date col  keep first occurrence
        from pyspark.sql.window import Window
        w = Window.partitionBy(primary_key).orderBy(F.monotonically_increasing_id())
        df = (df.withColumn("_row_num", F.row_number().over(w))
                .filter(F.col("_row_num") == 1)
                .drop("_row_num"))
    return df


def add_silver_metadata(df: DataFrame, source_table: str,
                        not_null_cols: list) -> DataFrame:
    """
    Append Silver audit columns:
      _silver_processed_ts   when the record was processed
      _source                originating Bronze table name
      _is_valid              True when all NOT NULL fields are populated
    """
    # Build validity check: all required cols must be non-null
    validity_expr = F.lit(True)
    for col in not_null_cols:
        if col in df.columns:
            validity_expr = validity_expr & F.col(col).isNotNull()

    df = (df
          .withColumn("_silver_processed_ts", F.current_timestamp())
          .withColumn("_source", F.lit(source_table))
          .withColumn("_is_valid", validity_expr))
    return df


def write_silver_table(df: DataFrame, table_name: str,
                       schema: str = SILVER_SCHEMA):
    """Write DataFrame to Silver Delta table with schema evolution."""
    full_table_name = f"{schema}.{table_name}"
    (df.write
       .format("delta")
       .mode("overwrite")
       .option("mergeSchema", "true")
       .option("overwriteSchema", "true")
       .saveAsTable(full_table_name))
    log(f"  Written to Delta table: {full_table_name}")


# 
# MASTER TRANSFORMATION PIPELINE
# 

def transform_table(table_name: str):
    """Full Bronze to Silver pipeline for a single table."""
    csv_path, pk, date_col = TABLE_CONFIG[table_name]

    log(f"{''*60}")
    log(f"  Processing table: [{table_name}]")
    log(f"   Source : {csv_path}")
    log(f"   PK     : {pk}  |  Date col: {date_col}")

    #  1. Read 
    df = read_bronze_csv(csv_path)
    raw_count = df.count()
    log(f"   Bronze row count  : {raw_count:,}")

    #  2. Replace empty strings with null 
    df = replace_empty_with_null(df)

    #  3. Title-case cosmetic columns 
    df = apply_title_case(df, TITLE_CASE_COLUMNS.get(table_name, []))

    #  4. Cast to correct data types 
    df = cast_column_types(df, COLUMN_TYPES.get(table_name, {}))

    #  5. Parse date columns 
    df = parse_date_columns(df, DATE_COLUMNS.get(table_name, []))

    #  6. Phone & zip cleaning 
    df = clean_phone(df)
    df = clean_zip_code(df)

    #  7. Numeric bounds enforcement 
    df = apply_numeric_bounds(df, NUMERIC_BOUNDS.get(table_name, {}))

    #  8. Deduplication 
    df = deduplicate(df, pk, date_col)
    dedup_count = df.count()
    log(f"   Silver row count  : {dedup_count:,}  "
        f"(removed {raw_count - dedup_count:,} duplicates/invalids)")

    #  9. Silver metadata columns 
    df = add_silver_metadata(
        df,
        source_table=table_name,
        not_null_cols=NOT_NULL_COLUMNS.get(table_name, [])
    )

    valid_count = df.filter(F.col("_is_valid") == True).count()
    log(f"   Valid records     : {valid_count:,} / {dedup_count:,}")

    #  10. Write Silver Delta table 
    write_silver_table(df, table_name)

    return {
        "table":         table_name,
        "bronze_rows":   raw_count,
        "silver_rows":   dedup_count,
        "valid_rows":    valid_count,
        "removed_rows":  raw_count - dedup_count,
    }


# 
# ENTRY POINT  Run all tables
# 

def run_bronze_to_silver():
    """Orchestrate the full Bronze to Silver load."""
    log("=" * 60)
    log("  Fabric Bronze to Silver Transformation  START")
    log("=" * 60)

    # Ensure Silver schema exists
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER_SCHEMA}")
    log(f"Schema [{SILVER_SCHEMA}] ready.")

    summary = []
    for table_name in TABLE_CONFIG.keys():
        try:
            result = transform_table(table_name)
            summary.append(result)
        except Exception as e:
            log(f"  ERROR processing [{table_name}]: {e}")
            raise

    #  Print Summary Report 
    log("")
    log("=" * 60)
    log("  TRANSFORMATION SUMMARY")
    log("=" * 60)
    log(f"  {'Table':<25} {'Bronze':>10} {'Silver':>10} "
        f"{'Valid':>10} {'Removed':>10}")
    log(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    for r in summary:
        log(f"  {r['table']:<25} {r['bronze_rows']:>10,} "
            f"{r['silver_rows']:>10,} {r['valid_rows']:>10,} "
            f"{r['removed_rows']:>10,}")
    log("=" * 60)
    log("  Bronze to Silver Transformation  COMPLETE ")
    log("=" * 60)

    return summary


# 
# RUN
# 
summary = run_bronze_to_silver()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
