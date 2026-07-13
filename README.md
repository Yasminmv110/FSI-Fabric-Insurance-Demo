# FSI-Fabric-Medallion-Architecture-Insurance-Demo

> End-to-end Microsoft Fabric jump-start solution for deploying an insurance analytics workspace with Lakehouse, Warehouse, notebooks, pipeline orchestration, semantic models, Power BI report, ontologies, Data Agent configuration, and bundled reference data.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Business Scenario](#2-business-scenario)
3. [Architecture Overview](#3-architecture-overview)
4. [Repository Structure](#4-repository-structure)
5. [Prerequisites](#5-prerequisites)
6. [End-to-End Deployment Flow](#6-end-to-end-deployment-flow)
7. [Manual Notebook Upload](#7-manual-notebook-upload)
8. [Reference Data Upload](#8-reference-data-upload)
9. [Workspace Components](#9-workspace-components)
10. [Notebooks](#10-notebooks)
11. [Pipeline Orchestration](#11-pipeline-orchestration)
12. [Lakehouse and Warehouse Layers](#12-lakehouse-and-warehouse-layers)
13. [Semantic Models and Report](#13-semantic-models-and-report)
14. [Ontologies and Data Agent](#14-ontologies-and-data-agent)
15. [Validation Checklist](#15-validation-checklist)

---

## 1. Overview

`FSI-Fabric-Medallion-Architecture-Insurance-Demo` is a source-controlled Microsoft Fabric workspace project for a property and casualty insurance demo. It is designed to help you quickly deploy a complete Fabric workspace and run a Bronze-to-Silver-to-Gold analytics flow.

With this solution, you can:

- Create or reuse a Fabric workspace named `FSI-Fabric-Medallion-Architecture-Insurance-Demo`.
- Deploy Fabric source-controlled items from this repository.
- Upload bundled reference data into the `LH_Insurance` Lakehouse Files area.
- Transform raw Bronze CSVs into cleaned Silver Delta tables.
- Aggregate Silver tables into Gold KPI tables in `WH_Insurance`.
- Analyze the data through Direct Lake semantic models and a Power BI report.
- Use ontology and Data Agent assets for relationship-aware, natural-language exploration.

---

## 2. Business Scenario

This demo models an insurance claims operation across offices, policyholders, insured assets, adjusters, policies, claims, claim events, and asset inspections.

The solution answers questions such as:

- Which offices process the most claims?
- Which adjusters have the highest active claim volume?
- Which claim types have the highest average estimated or approved losses?
- Which claims show fraud risk indicators?
- Which policyholders have elevated risk profiles?

The data model reflects the lifecycle from raw operational insurance records to curated analytics-ready KPI tables.

---

## 3. Architecture Overview

```text
Reference_Data in repository
        |
        v
Notebook: upload_reference_data_to_lakehouse
        |
        v
LH_Insurance Lakehouse Files
  - Files/Reference_Data/
  - Files/bronze_structured_data/
  - Files/bronze_unstructured_data/
        |
        v
Notebook: insurance_bronze_to_silver_notebook
        |
        v
LH_Insurance Silver Delta tables
        |
        v
Warehouse stored procedure: gold.usp_Load_Silver_to_Gold
        |
        v
WH_Insurance gold KPI tables
        |
        +-----------------------------+
        |                             |
        v                             v
SM_Silver_InsuranceDemo       SM_Gold_InsuranceDemo
Direct Lake semantic model    Direct Lake semantic model
                                      |
                                      v
                             Insurance_Demo_Report
                                      |
                                      v
                               DA_InsuranceDemo
```

The full data processing flow is orchestrated by `Pl_Insurance_Medallion`.

---

## 4. Repository Structure

```text
FSI-Fabric-Medallion-Architecture-Insurance-Demo/
|-- AGENTS.md
|-- Downloadable_Notebooks/
|   |-- 00_provision_fabric_workspace_and_items.ipynb
|   |-- 01_upload_reference_data_to_lakehouse.ipynb
|   `-- 02_insurance_bronze_to_silver.ipynb
|-- README.md
|-- Reference_Data/
|   |-- bronze_structured_data/
|   |   |-- adjusters.csv
|   |   |-- asset_inspections.csv
|   |   |-- claim_events.csv
|   |   |-- claims.csv
|   |   |-- insured_assets.csv
|   |   |-- offices.csv
|   |   |-- policies.csv
|   |   `-- policyholders.csv
|   `-- bronze_unstructured_data/
|       |-- *.txt
|       `-- *.png
|-- Data Agent/
|   `-- DA_InsuranceDemo.DataAgent/
|-- Fabric Data Stores/
|   |-- LH_Insurance.Lakehouse/
|   `-- WH_Insurance.Warehouse/
|       `-- gold/
|           |-- gold.sql
|           |-- StoredProcedures/
|           |   `-- usp_Load_Silver_to_Gold.sql
|           `-- Tables/
|               `-- gold_*.sql
|-- Mirrored Databases/
|   `-- INSURANCE.MirroredDatabase/
|-- Notebooks/
|   |-- provision_fabric_workspace_and_items.Notebook/
|   |-- upload_reference_data_to_lakehouse.Notebook/
|   `-- insurance_bronze_to_silver_notebook.Notebook/
|-- Ontology/
|   |-- Ontology_Silver_Insurance.Ontology/
|   `-- Ontology_Gold_Insurance.Ontology/
|-- Pipelines/
|   `-- Pl_Insurance_Medallion.DataPipeline/
`-- Semantic Models and PBI Reports/
    |-- SM_Silver_InsuranceDemo.SemanticModel/
    |-- SM_Gold_InsuranceDemo.SemanticModel/
    `-- Insurance_Demo_Report.Report/
```

---

## 5. Prerequisites

Before deploying, confirm that you have:

- A Microsoft Fabric tenant.
- Permission to create a Fabric workspace, or access to an existing workspace.
- Access to a Fabric capacity for the target workspace.
- Contributor or Admin access to the target Fabric workspace.
- Ability to import `.ipynb` notebooks into a Fabric workspace.
- Required preview features enabled as needed for Ontology and Data Agent.

>`.

---

## 6. End-to-End Deployment Flow

The primary path does **not** require connecting the Fabric workspace to GitHub. The provision notebook creates only the **data stores** (workspace, Lakehouse, Warehouse) programmatically and idempotently. Loading data is done through a few explicit manual steps afterward.

| Step | Action | Fabric item |
|---:|---|---|
| 1 | Download this repository as a ZIP from GitHub | Local browser/download |
| 2 | Import `Downloadable_Notebooks/00_provision_fabric_workspace_and_items.ipynb` into any Fabric workspace | Fabric notebook |
| 3 | Run the provision notebook (Run all) to create the workspace, `LH_Insurance`, and `WH_Insurance`, and print both SQL endpoints | Workspace, Lakehouse, Warehouse |
| 4 | **Manually upload the reference data** from this GitHub repo into `LH_Insurance` | Lakehouse Files |
| 5 | **Manually run** `02_insurance_bronze_to_silver` to build the Silver Delta tables | Silver tables |
| 6 | **Create** the `gold` schema, KPI tables, and `usp_Load_Silver_to_Gold` procedure in `WH_Insurance` | Warehouse objects |
| 7 | **Manually run** the stored procedure `gold.usp_Load_Silver_to_Gold` to load the Gold KPI tables | Gold tables |
| 8 | Review semantic models, report, ontology, and Data Agent assets | Fabric workspace items |

### Recommended deployment path

1. Download this repository as a ZIP.
2. In Fabric, create or open a bootstrap workspace.
3. Import `Downloadable_Notebooks/00_provision_fabric_workspace_and_items.ipynb`.
4. In the notebook **Configuration** cell, set:
   - `WORKSPACE_ID` (to provision into an existing workspace), **or** leave it blank and set `CAPACITY_ID` to create/reuse the workspace named `TARGET_WORKSPACE_DISPLAY_NAME`.
5. Run all cells. The notebook creates `LH_Insurance` and `WH_Insurance` (idempotent) and prints the Lakehouse and Warehouse SQL endpoint connection strings.
6. Open the target workspace and confirm the Lakehouse and Warehouse exist.
7. Complete the manual data-load steps in sections 6.1–6.4 below.

### 6.1. Manually upload the reference data from GitHub

Load the bundled Bronze CSVs from this GitHub repository into `LH_Insurance`. Use either option:

- **Option A — run the upload notebook**: import and run `Downloadable_Notebooks/01_upload_reference_data_to_lakehouse.ipynb` (with `LH_Insurance` attached as its default lakehouse). It downloads the repo archive and stages the files automatically.
- **Option B — upload by hand**: from the GitHub repo, download the `Reference_Data/bronze_structured_data/*.csv` files, then in the Fabric portal open `LH_Insurance` and upload them into **`Files/Bronze_Raw_Data/`** (the path the Bronze-to-Silver notebook reads). Optionally also stage `Reference_Data/bronze_unstructured_data/*` into `Files/Bronze_Unstructured_Data/`.

Confirm the eight structured CSVs are present under `Files/Bronze_Raw_Data/` before continuing.

### 6.2. Manually run the Bronze-to-Silver notebook

Import and run `Downloadable_Notebooks/02_insurance_bronze_to_silver.ipynb` with `LH_Insurance` attached as the default lakehouse. It reads `Files/Bronze_Raw_Data/*.csv`, then cleans, casts, deduplicates, and validates the data into the eight Silver Delta tables under the `Silver` schema in `LH_Insurance`.

### 6.3. Create the Silver-to-Gold stored procedure in `WH_Insurance`

Before the Gold load can run, the `gold` schema, the six `gold_*` KPI tables, and the `gold.usp_Load_Silver_to_Gold` stored procedure must exist in `WH_Insurance`. The DDL for all of these is source-controlled under `Fabric Data Stores/WH_Insurance.Warehouse/gold/`:

| Object | Repository source |
|---|---|
| `gold` schema | `gold/gold.sql` |
| Six `gold_*` KPI tables | `gold/Tables/gold_*.sql` |
| `gold.usp_Load_Silver_to_Gold` | `gold/StoredProcedures/usp_Load_Silver_to_Gold.sql` |

To create them:

1. Connect to `WH_Insurance` using the Warehouse SQL endpoint printed by the provision notebook (Fabric SQL editor, SSMS, or Azure Data Studio).
2. Run `gold/gold.sql` (creates the `gold` schema), then each file in `gold/Tables/` (creates the six KPI tables).
3. Run `gold/StoredProcedures/usp_Load_Silver_to_Gold.sql` to create the procedure:

   ```sql
   CREATE PROCEDURE gold.usp_Load_Silver_to_Gold
   AS
   -- Loads all six gold.* KPI tables from LH_Insurance.Silver.* via
   -- cross-database (3-part naming) reads against the Lakehouse SQL endpoint.
   ...
   ```

   Run the file's full contents as-is from the repository (the snippet above is only the header). If you are re-deploying, change `CREATE PROCEDURE` to `CREATE OR ALTER PROCEDURE` to make it idempotent.

> If your Fabric workspace is connected to Git, syncing the repository deploys these `WH_Insurance` objects automatically and you can skip the manual DDL.

### 6.4. Manually run the Silver-to-Gold stored procedure

With the procedure created (section 6.3) and the Silver tables loaded (section 6.2), load the Gold KPI tables:

1. Connect to `WH_Insurance` using the Warehouse SQL endpoint.
2. Execute the stored procedure:

   ```sql
   EXEC gold.usp_Load_Silver_to_Gold;
   ```

The procedure reads the Silver tables from the Lakehouse SQL analytics endpoint via 3-part naming (`LH_Insurance.Silver.<table>`) and loads all six Gold KPI tables — no shortcuts required.

### Optional Fabric Git path

Advanced users can still connect the Fabric workspace to Git to sync the full item definitions (notebooks, semantic models, report, ontologies, pipeline). This is not required for the jump-start path.

---

## 7. Manual Notebook Upload

Use the notebooks in `Downloadable_Notebooks/` when you want to import notebooks directly into Fabric without Git integration.

| Notebook | Purpose | Run order |
|---|---|---:|
| `00_provision_fabric_workspace_and_items.ipynb` | Creates or reuses the target workspace, Lakehouse, and Warehouse via REST APIs | 1 |
| `01_upload_reference_data_to_lakehouse.ipynb` | Uploads/stages repository reference data into `LH_Insurance` Files | 2 |
| `02_insurance_bronze_to_silver.ipynb` | Builds Silver Delta tables from structured Bronze CSVs | 3 |

Manual import steps:

1. In Fabric, open the workspace where you want to run the notebook.
2. Select **New** > **Import notebook**.
3. Choose the `.ipynb` file from `Downloadable_Notebooks/`.
4. Attach/select the required Lakehouse when prompted. For upload and Bronze-to-Silver notebooks, use `LH_Insurance`.
5. Review the configuration cell at the top of the notebook.
6. Run the notebook cells.

The `Notebooks/*.Notebook/` folders are the Fabric source-control item definitions. The `Downloadable_Notebooks/*.ipynb` files are provided for manual import.

---

## 8. Reference Data Upload

The first data step is to upload the bundled repository data into `LH_Insurance`.

### Source folders in this repository

```text
Reference_Data/
|-- bronze_structured_data/
`-- bronze_unstructured_data/
```

### Lakehouse destinations

The upload notebook writes to these Lakehouse Files locations:

| Source | Lakehouse destination | Purpose |
|---|---|---|
| `Reference_Data/bronze_structured_data/*` | `Files/Reference_Data/bronze_structured_data/*` | Preserve original structured reference bundle |
| `Reference_Data/bronze_unstructured_data/*` | `Files/Reference_Data/bronze_unstructured_data/*` | Preserve original unstructured reference bundle |
| `Reference_Data/bronze_structured_data/*.csv` | `Files/Bronze_Raw_Data/*.csv` | Input path consumed by Bronze-to-Silver notebook |
| `Reference_Data/bronze_unstructured_data/*` | `Files/Bronze_Unstructured_Data/*` | Staged unstructured Bronze files |

### Running the upload notebook

Use `Notebooks/upload_reference_data_to_lakehouse.Notebook/notebook-content.py`.

Supported source modes:

| Mode | When to use | Configuration |
|---|---|---|
| `github_zip` | Download the repository archive from GitHub | Set `SOURCE_REPO_ZIP_URL`; for a private repo, set `GITHUB_TOKEN_KEY_VAULT_URL` and `GITHUB_TOKEN_SECRET_NAME` |
| `lakehouse_zip` | Upload a repo zip manually to Lakehouse Files first | Set `SOURCE_ZIP_FILE_PATH` |

The notebook validates that all expected structured CSVs and unstructured demo files exist before copying data.

---

## 9. Workspace Components

| Category | Fabric item | Description |
|---|---|---|
| Lakehouse | `LH_Insurance` | Stores reference files, Bronze files, and Silver Delta tables |
| Warehouse | `WH_Insurance` | Stores six Gold KPI tables and the Silver-to-Gold stored procedure |
| Notebook | `provision_fabric_workspace_and_items` | Creates/deploys the Fabric workspace and items |
| Notebook | `upload_reference_data_to_lakehouse` | Uploads repository reference data into Lakehouse Files |
| Notebook | `insurance_bronze_to_silver_notebook` | Cleans, casts, deduplicates, validates, and writes Silver Delta tables |
| Pipeline | `Pl_Insurance_Medallion` | Orchestrates upload, Bronze-to-Silver, and Silver-to-Gold |
| Semantic Model | `SM_Silver_InsuranceDemo` | Direct Lake model over Silver Lakehouse tables |
| Semantic Model | `SM_Gold_InsuranceDemo` | Direct Lake model over Gold Warehouse KPI tables |
| Report | `Insurance_Demo_Report` | Power BI report over `SM_Gold_InsuranceDemo` |
| Ontology | `Ontology_Silver_Insurance` | Relationship model over Silver-layer entities |
| Ontology | `Ontology_Gold_Insurance` | Relationship model over Gold-layer KPIs |
| Data Agent | `DA_InsuranceDemo` | Natural-language Q&A configuration |
| Mirrored Database | `INSURANCE` | Mirrored source item scaffold/configuration |

---

## 10. Notebooks

### `provision_fabric_workspace_and_items`

Creates or reuses the `FSI-Fabric-Medallion-Architecture-Insurance-Demo` workspace and provisions the core data stores (`LH_Insurance` Lakehouse and `WH_Insurance` Warehouse) via the Fabric REST API. It is idempotent and also prints the Lakehouse and Warehouse SQL endpoint connection strings. It does **not** load data — the reference-data upload, Bronze-to-Silver notebook, and Silver-to-Gold stored procedure are run manually (see section 6).

Key configuration:

- `WORKSPACE_ID` (provision into an existing workspace), or leave blank to create/reuse by name
- `TARGET_WORKSPACE_DISPLAY_NAME`
- `CAPACITY_ID`
- `LAKEHOUSE_NAME`
- `WAREHOUSE_NAME`

### `upload_reference_data_to_lakehouse`

Uploads the repository `Reference_Data` bundle into `LH_Insurance` Files.

Expected structured files:

`adjusters.csv`, `asset_inspections.csv`, `claim_events.csv`, `claims.csv`, `insured_assets.csv`, `offices.csv`, `policies.csv`, `policyholders.csv`

### `insurance_bronze_to_silver_notebook`

Reads structured CSVs from:

```text
Files/Bronze_Raw_Data
```

It writes Silver Delta tables using schema name `Silver`:

`offices`, `policyholders`, `insured_assets`, `adjusters`, `policies`, `claims`, `claim_events`, `asset_inspections`

Important conventions:

- Bronze CSVs are read with `inferSchema=false`.
- Explicit casts are applied in the notebook.
- Invalid numeric ranges are set to null.
- Each Silver table includes `_silver_processed_ts`, `_source`, and `_is_valid`.
- The Silver schema uses capital `S`: `Silver`.

---

## 11. Pipeline Orchestration

`Pl_Insurance_Medallion` runs three activities in order:

| Order | Activity | Type | Depends on |
|---:|---|---|---|
| 1 | `Notebook- Upload Reference Data` | Notebook | None |
| 2 | `Notebook- Bronze_to_Silver` | Notebook | Upload Reference Data succeeded |
| 3 | `SP- Silver to Gold` | Warehouse stored procedure | Bronze-to-Silver succeeded |

The stored procedure activity executes:

```sql
[gold].[usp_Load_Silver_to_Gold]
```

---

## 12. Lakehouse and Warehouse Layers

### Bronze

Bronze files are stored in `LH_Insurance` under:

- `Files/Reference_Data/`
- `Files/Bronze_Raw_Data/`
- `Files/Bronze_Unstructured_Data/`

### Silver

Silver tables are Delta tables in `LH_Insurance` under schema `Silver`.

| Table | Description |
|---|---|
| `offices` | Branch and regional office details |
| `policyholders` | Policyholder master records |
| `insured_assets` | Insured property, vehicle, or asset records |
| `adjusters` | Claims adjuster records |
| `policies` | Insurance policy records |
| `claims` | Claim header records |
| `claim_events` | Claim lifecycle event records |
| `asset_inspections` | Inspection and appraisal records |

### Gold

Gold tables are stored in `WH_Insurance` under schema `gold`.

| Table | Description |
|---|---|
| `gold_claims_by_adjuster` | Claim counts, approval rates, and loss metrics by adjuster |
| `gold_claims_summary_by_office` | Claim volume and financial rollups by office |
| `gold_adjuster_performance` | Adjuster workload and efficiency KPIs |
| `gold_avg_loss_by_claim_type` | Average estimated and approved loss by claim type |
| `gold_fraud_flags` | Fraud indicator flags and risk labels |
| `gold_policyholder_risk_profile` | Policyholder-level risk profile metrics |


---

## 13. Semantic Models and Report

### `SM_Silver_InsuranceDemo`

Direct Lake semantic model over the eight Silver Lakehouse tables. Use this model for exploratory analysis over cleaned entity-level records.

### `SM_Gold_InsuranceDemo`

Direct Lake semantic model over the six Gold Warehouse KPI tables. This model powers the Power BI report.

### `Insurance_Demo_Report`

Power BI report connected to `SM_Gold_InsuranceDemo`.

---

## 14. Ontologies and Data Agent

### Ontologies

| Ontology | Layer | Purpose |
|---|---|---|
| `Ontology_Silver_Insurance` | Silver | Entity relationship model over detailed insurance records |
| `Ontology_Gold_Insurance` | Gold | Relationship model over curated KPI outputs |

### Data Agent

`DA_InsuranceDemo` provides Data Agent configuration for natural-language Q&A over the insurance data. Use it for business-friendly questions about claims, policies, policyholders, adjusters, offices, assets, inspections, and claim events.

Example prompts:

- Show the highest-risk policyholders.
- Which adjusters have the most active claims?
- Which offices have the highest estimated losses?
- Which claims have fraud risk indicators?
- Show claims by claim type and status.

---

## 15. Validation Checklist

After deployment, verify:

1. `FSI-Fabric-Medallion-Architecture-Insurance-Demo` workspace exists and is assigned to Fabric capacity.
2. `LH_Insurance` Lakehouse exists.
3. `WH_Insurance` Warehouse exists.
4. `Reference_Data` was uploaded to `Files/Reference_Data`.
5. Structured CSVs exist in `Files/Bronze_Raw_Data`.
6. Unstructured files exist in `Files/Bronze_Unstructured_Data`.
7. `insurance_bronze_to_silver_notebook` created all eight Silver tables.
8. `gold.usp_Load_Silver_to_Gold` loaded all six Gold tables.
9. `SM_Silver_InsuranceDemo` and `SM_Gold_InsuranceDemo` open successfully.
10. `Insurance_Demo_Report` is connected to `SM_Gold_InsuranceDemo`.
11. `Pl_Insurance_Medallion` completes successfully.

---

