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
# Fabric Notebook: Upload Reference Data to LH_Insurance
# Author   : Yasmin Udaipurwala
# Purpose  : Upload the repository Reference_Data bundle into
#            the default LH_Insurance Lakehouse Files area.
#
# Outputs:
#   Files/Reference_Data/bronze_structured_data/*
#   Files/Reference_Data/bronze_unstructured_data/*
#   Files/Bronze_Raw_Data/*.csv
#   Files/Bronze_Unstructured_Data/*
#
# The Bronze -> Silver notebook reads Files/Bronze_Raw_Data,
# so this notebook stages the structured CSVs there in addition
# to preserving the original Reference_Data folder layout.
# ============================================================

import shutil
import time
import zipfile
from pathlib import Path
from typing import Iterable, List, Tuple

import requests


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

SOURCE_MODE = "github_zip"  # "github_zip" or "lakehouse_zip"

# GitHub archive for the repository. For private forks, set
# GITHUB_TOKEN_KEY_VAULT_URL and GITHUB_TOKEN_SECRET_NAME before running, or
# switch SOURCE_MODE to "lakehouse_zip" and upload the repository zip manually.
SOURCE_REPO_ZIP_URL = (
    "https://github.com/<owner>/FSI-Fabric-Medallion-Architecture-Insurance-Demo/archive/refs/heads/main.zip"
)
GITHUB_TOKEN_KEY_VAULT_URL = ""
GITHUB_TOKEN_SECRET_NAME = ""

# Alternative source when SOURCE_MODE = "lakehouse_zip". Upload a repository
# zip to this Lakehouse path first, for example with the Fabric Files UI.
SOURCE_ZIP_FILE_PATH = "Files/Reference_Data_Source/FSI-Fabric-Medallion-Architecture-Insurance-Demo-main.zip"

REFERENCE_DATA_REPO_PATH = "Reference_Data"
BRONZE_STRUCTURED_FOLDER = "bronze_structured_data"
BRONZE_UNSTRUCTURED_FOLDER = "bronze_unstructured_data"

DEST_REFERENCE_DATA_PATH = "Files/Reference_Data"
DEST_BRONZE_STRUCTURED_PATH = "Files/Bronze_Raw_Data"
DEST_BRONZE_UNSTRUCTURED_PATH = "Files/Bronze_Unstructured_Data"

OVERWRITE_EXISTING = True

EXPECTED_STRUCTURED_FILES = [
    "adjusters.csv",
    "asset_inspections.csv",
    "claim_events.csv",
    "claims.csv",
    "insured_assets.csv",
    "offices.csv",
    "policies.csv",
    "policyholders.csv",
]

EXPECTED_UNSTRUCTURED_FILES = [
    "adjuster_call_notes_ADJ00000001.txt",
    "claim_form_scan_CLM00000001.png",
    "claim_photos_manifest_CLM00000001.txt",
    "damage_photo_CLM00000001.png",
    "fraud_risk_dashboard_CLM00000002.png",
    "office_map_OFF00000001.png",
    "underwriter_memo_POL00000001.txt",
]


# ------------------------------------------------------------
# NOTEBOOK UTILITIES
# ------------------------------------------------------------

def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")


def get_notebookutils():
    try:
        return notebookutils  # type: ignore[name-defined]
    except NameError:
        try:
            import notebookutils as imported_notebookutils  # type: ignore
            return imported_notebookutils
        except ImportError as exc:
            raise RuntimeError(
                "This notebook must run in Microsoft Fabric, where notebookutils is available."
            ) from exc


def get_github_token() -> str:
    if not GITHUB_TOKEN_KEY_VAULT_URL and not GITHUB_TOKEN_SECRET_NAME:
        return ""

    if not GITHUB_TOKEN_KEY_VAULT_URL or not GITHUB_TOKEN_SECRET_NAME:
        raise ValueError(
            "Set both GITHUB_TOKEN_KEY_VAULT_URL and GITHUB_TOKEN_SECRET_NAME, "
            "or leave both blank."
        )

    return get_notebookutils().credentials.getSecret(
        GITHUB_TOKEN_KEY_VAULT_URL,
        GITHUB_TOKEN_SECRET_NAME,
    )


def lakehouse_path_exists(path: str) -> bool:
    fs = get_notebookutils().fs
    if hasattr(fs, "exists"):
        return bool(fs.exists(path))

    parent = "/".join(path.rstrip("/").split("/")[:-1]) or "."
    name = path.rstrip("/").split("/")[-1]
    return any(item.name.rstrip("/") == name for item in fs.ls(parent))


def reset_lakehouse_dir(path: str) -> None:
    fs = get_notebookutils().fs
    if OVERWRITE_EXISTING and lakehouse_path_exists(path):
        log(f"Removing existing {path}")
        fs.rm(path, True)
    fs.mkdirs(path)


def local_file_uri(path: Path) -> str:
    return "file:" + path.resolve().as_posix()


def copy_local_file_to_lakehouse(source_file: Path, destination_file: str) -> None:
    destination_dir = "/".join(destination_file.split("/")[:-1])
    get_notebookutils().fs.mkdirs(destination_dir)
    get_notebookutils().fs.cp(local_file_uri(source_file), destination_file)


# ------------------------------------------------------------
# SOURCE ACQUISITION
# ------------------------------------------------------------

def download_repo_zip(work_dir: Path) -> Path:
    headers = {}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    zip_path = work_dir / "repo.zip"
    response = requests.get(SOURCE_REPO_ZIP_URL, headers=headers, timeout=300)
    if response.status_code in (401, 403, 404) and not token:
        raise RuntimeError(
            "Could not download the private GitHub repository archive. "
            "Set GITHUB_TOKEN_KEY_VAULT_URL and GITHUB_TOKEN_SECRET_NAME, "
            "or use SOURCE_MODE = 'lakehouse_zip'."
        )
    response.raise_for_status()
    zip_path.write_bytes(response.content)
    return zip_path


def copy_lakehouse_zip_to_local(work_dir: Path) -> Path:
    if not SOURCE_ZIP_FILE_PATH:
        raise ValueError("Set SOURCE_ZIP_FILE_PATH when SOURCE_MODE = 'lakehouse_zip'.")

    zip_path = work_dir / "repo.zip"
    get_notebookutils().fs.cp(SOURCE_ZIP_FILE_PATH, local_file_uri(zip_path))
    return zip_path


def extract_zip(zip_path: Path, work_dir: Path) -> Path:
    extract_dir = work_dir / "extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)

    children = [path for path in extract_dir.iterdir() if path.is_dir()]
    if len(children) == 1 and (children[0] / REFERENCE_DATA_REPO_PATH).exists():
        return children[0]
    return extract_dir


def get_repo_root() -> Path:
    work_dir = Path("/tmp/ws_insurance_reference_data_upload")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    if SOURCE_MODE == "github_zip":
        log("Downloading repository archive from GitHub.")
        zip_path = download_repo_zip(work_dir)
    elif SOURCE_MODE == "lakehouse_zip":
        log("Copying repository archive from Lakehouse Files.")
        zip_path = copy_lakehouse_zip_to_local(work_dir)
    else:
        raise ValueError("SOURCE_MODE must be 'github_zip' or 'lakehouse_zip'.")

    return extract_zip(zip_path, work_dir)


# ------------------------------------------------------------
# VALIDATION AND UPLOAD
# ------------------------------------------------------------

def require_files(directory: Path, expected_files: Iterable[str]) -> None:
    missing = [name for name in expected_files if not (directory / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing expected files in {directory}: {', '.join(missing)}"
        )


def iter_files(directory: Path) -> List[Path]:
    return sorted(path for path in directory.rglob("*") if path.is_file())


def upload_directory(source_dir: Path, destination_dir: str) -> Tuple[int, int]:
    reset_lakehouse_dir(destination_dir)

    files = iter_files(source_dir)
    total_bytes = 0
    for source_file in files:
        relative_path = source_file.relative_to(source_dir).as_posix()
        destination_file = f"{destination_dir.rstrip('/')}/{relative_path}"
        copy_local_file_to_lakehouse(source_file, destination_file)
        total_bytes += source_file.stat().st_size

    return len(files), total_bytes


repo_root = get_repo_root()
reference_data_dir = repo_root / REFERENCE_DATA_REPO_PATH
structured_dir = reference_data_dir / BRONZE_STRUCTURED_FOLDER
unstructured_dir = reference_data_dir / BRONZE_UNSTRUCTURED_FOLDER

if not reference_data_dir.is_dir():
    raise FileNotFoundError(f"Reference_Data folder not found at {reference_data_dir}.")
if not structured_dir.is_dir():
    raise FileNotFoundError(f"Structured Bronze folder not found at {structured_dir}.")
if not unstructured_dir.is_dir():
    raise FileNotFoundError(f"Unstructured Bronze folder not found at {unstructured_dir}.")

require_files(structured_dir, EXPECTED_STRUCTURED_FILES)
require_files(unstructured_dir, EXPECTED_UNSTRUCTURED_FILES)

log(f"Uploading full Reference_Data folder to {DEST_REFERENCE_DATA_PATH}.")
reference_count, reference_bytes = upload_directory(
    reference_data_dir,
    DEST_REFERENCE_DATA_PATH,
)

log(f"Staging structured Bronze CSVs to {DEST_BRONZE_STRUCTURED_PATH}.")
structured_count, structured_bytes = upload_directory(
    structured_dir,
    DEST_BRONZE_STRUCTURED_PATH,
)

log(f"Staging unstructured Bronze files to {DEST_BRONZE_UNSTRUCTURED_PATH}.")
unstructured_count, unstructured_bytes = upload_directory(
    unstructured_dir,
    DEST_BRONZE_UNSTRUCTURED_PATH,
)

print("Upload complete.")
print(f"Reference_Data: {reference_count} files, {reference_bytes} bytes")
print(f"Bronze_Raw_Data: {structured_count} files, {structured_bytes} bytes")
print(f"Bronze_Unstructured_Data: {unstructured_count} files, {unstructured_bytes} bytes")
