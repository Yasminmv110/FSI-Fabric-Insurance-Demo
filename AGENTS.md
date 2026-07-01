# FSI-Fabric-Medallion-Architecture-Insurance-Demo â€” Agent Instructions

> See [README.md](README.md) for the full architecture diagram and workspace component catalogue.

## What This Project Is

A Microsoft Fabric end-to-end insurance demo implementing **Medallion architecture** (Bronze â†’ Silver â†’ Gold) with PySpark notebooks, T-SQL stored procedures, DirectLake semantic models, a Power BI report, and a natural-language Data Agent.

---

## Medallion Layers

| Layer | Fabric Item | Schema | Source / Location |
|-------|------------|--------|------------------|
| **Bronze** | `LH_Insurance.Lakehouse` | *(files only)* | `Reference_Data/`, uploaded to `Files/Reference_Data/`, `Files/Bronze_Raw_Data/`, and `Files/Bronze_Unstructured_Data/` |
| **Silver** | `LH_Insurance.Lakehouse` | `Silver` (capital S) | Delta tables written by notebook |
| **Gold** | `WH_Insurance.Warehouse` | `gold` (lowercase) | `Fabric Data Stores/WH_Insurance.Warehouse/gold/` |

**Schema casing is intentional and load-bearing** â€” `Silver` â‰  `silver`. All cross-layer SQL references must use the exact casing above.

---

## Key Files

| Task | File |
|------|------|
| Workspace and item provisioning | [notebook-content.py](Notebooks/provision_fabric_workspace_and_items.Notebook/notebook-content.py) |
| Reference data upload | [notebook-content.py](Notebooks/upload_reference_data_to_lakehouse.Notebook/notebook-content.py) |
| Bronze â†’ Silver transform | [notebook-content.py](Notebooks/insurance_bronze_to_silver_notebook.Notebook/notebook-content.py) |
| Gold KPI table DDL | [gold/Tables/](Fabric%20Data%20Stores/WH_Insurance.Warehouse/gold/Tables/) |
| Silver â†’ Gold aggregation SP | [usp_Load_Silver_to_Gold.sql](Fabric%20Data%20Stores/WH_Insurance.Warehouse/gold/StoredProcedures/usp_Load_Silver_to_Gold.sql) |
| Gold schema creation | [gold.sql](Fabric%20Data%20Stores/WH_Insurance.Warehouse/gold/gold.sql) |
| Pipeline orchestration | [pipeline-content.json](Pipelines/Pl_Insurance_Medallion.DataPipeline/pipeline-content.json) |
| SM Gold â€” model / tables / relationships | [SM_Gold definition/](Semantic%20Models%20and%20PBI%20Reports/SM_Gold_InsuranceDemo.SemanticModel/definition/) |
| SM Silver â€” model / tables | [SM_Silver definition/](Semantic%20Models%20and%20PBI%20Reports/SM_Silver_InsuranceDemo.SemanticModel/definition/) |
| Snowflake mirror config | [mirroring.json](Mirrored%20Databases/INSURANCE.MirroredDatabase/mirroring.json) |
| Data Agent config | [data_agent.json](Data%20Agent/DA_InsuranceDemo.DataAgent/Files/Config/data_agent.json) |

---

## Non-Obvious Facts

### Stored procedure â€” Silver source references
[usp_Load_Silver_to_Gold.sql](Fabric%20Data%20Stores/WH_Insurance.Warehouse/gold/StoredProcedures/usp_Load_Silver_to_Gold.sql) uses dynamic SQL built from two variables declared at the top:

```sql
DECLARE @Lakehouse    sysname = N'LH_Insurance';
DECLARE @SilverSchema sysname = N'Silver';
```

Silver tables are referenced as `[LH_Insurance].[Silver].[table_name]` via the Lakehouse SQL analytics endpoint. When adding a new Gold table, follow this dynamic SQL pattern for all cross-layer `FROM` clauses.

### Gold load pattern
All six Gold tables use **DELETE then INSERT** (not MERGE/upsert). The `_gold_processed_ts` column is set to `SYSDATETIME()` at INSERT time.

### Metadata columns
Every **Silver** table has three audit columns appended by the notebook:

| Column | Type | Meaning |
|--------|------|---------|
| `_silver_processed_ts` | timestamp | When the row was written to Silver |
| `_source` | string | Originating Bronze CSV filename |
| `_is_valid` | boolean | `true` if all NOT NULL fields are populated |

Every **Gold** table has one audit column:

| Column | Type | Meaning |
|--------|------|---------|
| `_gold_processed_ts` | timestamp | `SYSDATETIME()` at load time |

### Notebook conventions
- The data upload notebook copies repository `Reference_Data/` into `LH_Insurance` Files:
  - full bundle: `Files/Reference_Data/`
  - structured CSV stage: `Files/Bronze_Raw_Data/`
  - unstructured file stage: `Files/Bronze_Unstructured_Data/`
- Bronze CSVs are read with `inferSchema=false` â€” all columns land as `StringType`.
- Explicit casts are applied afterwards via the `COLUMN_TYPES` config dict.
- Out-of-bounds numeric values are set to `null` (not clamped), per `NUMERIC_BOUNDS`.
- Deduplication order: exact-duplicate rows removed first, then PK-level duplicates resolved by keeping the row with the latest `date_col`.
- Delta tables written with schema evolution enabled (`mergeSchema=true`).

### Fraud scoring (`gold_fraud_flags`)
7 independent boolean flags with a composite score (0â€“100):

| Flag column | Points |
|------------|--------|
| `flag_high_loss_vs_coverage` (loss > 80% of coverage) | +20 |
| `flag_filed_before_incident` | +25 |
| `flag_multiple_claims_same_asset` | +15 |
| `flag_low_approval_ratio` (approved < 20% of estimated) | +10 |
| `flag_adjuster_high_volume` (active > 80% capacity) | +10 |
| `flag_new_policy_claim` (policy < 90 days old) | +10 |
| `flag_repeat_policyholder` (> 3 claims) | +10 |

Risk label thresholds: `Critical` â‰¥ 75 Â· `High` â‰¥ 50 Â· `Medium` â‰¥ 25 Â· `Low` < 25

### Semantic models â€” DirectLake
Both SM_Gold and SM_Silver use **DirectLake** mode. DDL changes to warehouse/lakehouse tables propagate automatically â€” no import refresh needed. Do not hardcode OneLake URLs; they live in `expressions.tmdl` and are workspace-specific.

SM_Gold surfaces **only the 6 `gold_*` KPI tables**. Older `Dim*` and `Fact*` warehouse tables were removed from the repository and are not expected to exist in deployed workspaces.

### Ontology definitions
Both top-level `definition.json` files are empty (`{}`), but the ontology folders contain populated entity and relationship definitions:
- `Ontology_Silver_Insurance`: 8 entity types and 11 relationship types
- `Ontology_Gold_Insurance`: 6 entity types and 4 relationship types

### Pipeline dependency
The pipeline has three sequential activities, each with a **12-hour timeout**:
1. `Notebook- Upload Reference Data` â€” uploads/stages repository reference data into `LH_Insurance` Files
2. `Notebook-Bronze_to_Silver` â€” runs the PySpark notebook; only runs if activity 1 succeeds
3. `SP-Silver to Gold` â€” calls `gold.usp_Load_Silver_to_Gold`; only runs if activity 2 succeeds

---

## Naming Conventions

| Element | Pattern | Examples |
|---------|---------|----------|
| Fabric items | `<Prefix>_<Domain>.<ItemType>` | `LH_Insurance.Lakehouse`, `WH_Insurance.Warehouse` |
| Gold KPI tables | `gold_<descriptor>` | `gold_claims_by_adjuster`, `gold_fraud_flags` |
| Silver tables | `<entity>` (lowercase plural) | `claims`, `adjusters`, `claim_events` |
| Columns | `snake_case` | `adjuster_id`, `avg_estimated_loss` |
| Metadata columns | `_<layer>_<field>` | `_silver_processed_ts`, `_gold_processed_ts` |
| Percentage columns | `<metric>_pct` or `<metric>_rate_pct` | `approval_rate_pct`, `utilization_rate_pct` |
| Fraud flag columns | `flag_<condition>` | `flag_high_loss_vs_coverage` |
| Stored procedures | `usp_<Action>_<Source>_to_<Target>` | `usp_Load_Silver_to_Gold` |
| Pipelines | `Pl_<Domain>_<Flow>` | `Pl_Insurance_Medallion` |

---

## Common Task Patterns

### Add a new Gold KPI table
1. Create DDL in [`Fabric Data Stores/WH_Insurance.Warehouse/gold/Tables/<table_name>.sql`](Fabric%20Data%20Stores/WH_Insurance.Warehouse/gold/Tables/)
2. Add a new DELETE + INSERT section to [`usp_Load_Silver_to_Gold.sql`](Fabric%20Data%20Stores/WH_Insurance.Warehouse/gold/StoredProcedures/usp_Load_Silver_to_Gold.sql) using the dynamic SQL pattern (`@Lakehouse`, `@SilverSchema`); include `_gold_processed_ts`
3. Add `ref table <table_name>` to [`SM_Gold model.tmdl`](Semantic%20Models%20and%20PBI%20Reports/SM_Gold_InsuranceDemo.SemanticModel/definition/model.tmdl)
4. Create [`SM_Gold definition/tables/<table_name>.tmdl`](Semantic%20Models%20and%20PBI%20Reports/SM_Gold_InsuranceDemo.SemanticModel/definition/tables/) following the column definition pattern in existing `.tmdl` files
5. Add relationships in [`relationships.tmdl`](Semantic%20Models%20and%20PBI%20Reports/SM_Gold_InsuranceDemo.SemanticModel/definition/relationships.tmdl) if needed

### Add a new Silver table
1. Add the Bronze CSV to `Reference_Data/bronze_structured_data/`
2. Update [`upload_reference_data_to_lakehouse` notebook-content.py](Notebooks/upload_reference_data_to_lakehouse.Notebook/notebook-content.py) if the file should be validated during upload
3. In [`insurance_bronze_to_silver_notebook` notebook-content.py](Notebooks/insurance_bronze_to_silver_notebook.Notebook/notebook-content.py), add entries to `TABLE_CONFIG`, `NOT_NULL_COLUMNS`, `COLUMN_TYPES`, `DATE_COLUMNS`, `TITLE_CASE_COLUMNS`, and `NUMERIC_BOUNDS` as applicable
3. Add `ref table <table_name>` to [`SM_Silver model.tmdl`](Semantic%20Models%20and%20PBI%20Reports/SM_Silver_InsuranceDemo.SemanticModel/definition/model.tmdl)
4. Create [`SM_Silver definition/tables/<table_name>.tmdl`](Semantic%20Models%20and%20PBI%20Reports/SM_Silver_InsuranceDemo.SemanticModel/definition/tables/) â€” include the three `_silver_*` metadata columns
