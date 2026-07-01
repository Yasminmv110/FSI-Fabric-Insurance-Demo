# FSI-Fabric-Medallion-Architecture-Insurance-Demo - Microsoft Fabric Insurance Jump Start

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
16. [Limitations and Notes](#16-limitations-and-notes)

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

> The repository is currently hosted at `https://github.com/<owner>/FSI-Fabric-Medallion-Architecture-Insurance-Demo`.

---

## 6. End-to-End Deployment Flow

The primary path does **not** require connecting the Fabric workspace to GitHub. Users download notebooks from this repository, import them into Fabric, and run them.

| Step | Action | Fabric item |
|---:|---|---|
| 1 | Download this repository as a ZIP from GitHub | Local browser/download |
| 2 | Import `Downloadable_Notebooks/00_provision_fabric_workspace_and_items.ipynb` into any Fabric workspace | Fabric notebook |
| 3 | Run the provision notebook with `RUN_REST_ITEM_DEPLOYMENT = True` | Creates workspace/items from repository ZIP |
| 4 | Run `01_upload_reference_data_to_lakehouse.ipynb` or the deployed upload notebook | Uploads/stages `Reference_Data` |
| 5 | Run `02_insurance_bronze_to_silver.ipynb` or the deployed medallion pipeline | Builds Silver tables |
| 6 | Run the deployed pipeline or stored procedure step | Loads Gold KPI tables |
| 7 | Review semantic models, report, ontology, and Data Agent assets | Fabric workspace items |

### Recommended no-Git deployment path

1. Download this repository as a ZIP.
2. In Fabric, create or open a bootstrap workspace.
3. Import `Downloadable_Notebooks/00_provision_fabric_workspace_and_items.ipynb`.
4. Set:
   - `CAPACITY_ID`
   - `RUN_REST_ITEM_DEPLOYMENT = True`
   - `SOURCE_MODE = "github_zip"` and `SOURCE_REPO_ZIP_URL` to your public repository archive URL, **or**
   - `SOURCE_MODE = "lakehouse_zip"` and `SOURCE_ZIP_FILE_PATH` after uploading the repository ZIP to Lakehouse Files.
5. Run all cells in the provision notebook.
6. Open the created target workspace and confirm the Fabric items were created.
7. Run the upload notebook and then the medallion pipeline.

### Optional Fabric Git path

Advanced users can still use Fabric Git integration by setting `RUN_GIT_SYNC = True` in `provision_fabric_workspace_and_items`, but it is not required for the jump-start path.

---

## 7. Manual Notebook Upload

Use the notebooks in `Downloadable_Notebooks/` when you want to import notebooks directly into Fabric without Git integration.

| Notebook | Purpose | Run order |
|---|---|---:|
| `00_provision_fabric_workspace_and_items.ipynb` | Creates or reuses the target workspace and deploys Fabric items through REST APIs | 1 |
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

Creates or reuses the `FSI-Fabric-Medallion-Architecture-Insurance-Demo` workspace and deploys the Fabric items from this repository.

Key configuration:

- `TARGET_WORKSPACE_DISPLAY_NAME`
- `CAPACITY_ID`
- `RUN_REST_ITEM_DEPLOYMENT`
- `SOURCE_MODE`
- `SOURCE_REPO_ZIP_URL`
- `SOURCE_ZIP_FILE_PATH`

Optional Git configuration:

- `RUN_GIT_SYNC`
- `GIT_PROVIDER_TYPE`
- `GIT_CONNECTION_ID`

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

## 16. Limitations and Notes

- This repository is intended to be safe for public sharing after replacing placeholder values with your own Fabric workspace, item, and Git provider settings.
- Fabric Git integration is optional. The recommended jump-start path is manual notebook import plus REST item deployment.
- If using `github_zip` mode with a private fork, store GitHub access tokens in Azure Key Vault. Do not paste secrets into notebooks.
- The upload notebook stages structured CSVs to `Files/Bronze_Raw_Data` because that is the path consumed by the Bronze-to-Silver notebook.
- The Warehouse contains only the six `gold_*` KPI tables. Deleted `Dim*` and `Fact*` objects are intentionally not referenced.
