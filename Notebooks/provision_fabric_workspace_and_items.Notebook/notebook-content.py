# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# ============================================================
# Fabric Notebook: Provision Workspace and Items
# Author   : Yasmin Udaipurwala
# Purpose  : Create the FSI-Fabric-Medallion-Architecture-Insurance-Demo Fabric workspace and
#            deploy the source-controlled Fabric items into it.
#
# Recommended path:
#   1. Set CAPACITY_ID.
#   2. Set RUN_GIT_SYNC = True.
#   3. Configure the Git provider block and GIT_CONNECTION_ID.
#   4. Run all cells.
#
# Fallback path:
#   Set RUN_REST_ITEM_DEPLOYMENT = True and SOURCE_REPO_ZIP_URL
#   to create/update supported item definitions directly with
#   Fabric REST item APIs.
# ============================================================

import base64
import json
import shutil
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

TARGET_WORKSPACE_DISPLAY_NAME = "FSI-Fabric-Medallion-Architecture-Insurance-Demo"
TARGET_WORKSPACE_DESCRIPTION = (
    "Insurance demo workspace provisioned from the FSI-Fabric-Medallion-Architecture-Insurance-Demo repository."
)

# Fabric Git update and most non-Power BI item creation require the workspace
# to be assigned to a Fabric capacity. Leave blank only if your tenant assigns
# capacity separately before Git sync or item creation.
CAPACITY_ID = ""
DOMAIN_ID = ""

# Preferred deployment path. This creates the workspace, connects it to the
# repository, initializes Git integration, and updates the workspace from Git.
RUN_GIT_SYNC = False
GIT_PROVIDER_TYPE = "GitHub"  # "GitHub" or "AzureDevOps"
GIT_BRANCH_NAME = "main"
GIT_DIRECTORY_NAME = ""       # Repo subdirectory that contains this Fabric project.

# GitHub settings. Required when GIT_PROVIDER_TYPE == "GitHub".
GITHUB_OWNER_NAME = ""
GITHUB_REPOSITORY_NAME = "FSI-Fabric-Medallion-Architecture-Insurance-Demo"
GITHUB_CUSTOM_DOMAIN_NAME = ""  # Optional, for supported GitHub Enterprise domains.

# Azure DevOps settings. Required when GIT_PROVIDER_TYPE == "AzureDevOps".
AZURE_DEVOPS_ORGANIZATION_NAME = ""
AZURE_DEVOPS_PROJECT_NAME = ""
AZURE_DEVOPS_REPOSITORY_NAME = ""

# For GitHub, Fabric Git connect requires a configured connection ID.
# Create/configure it in Fabric, then paste the connection object ID here.
GIT_CONNECTION_ID = ""

# REST fallback. This path creates items directly from the repo files where
# item definition APIs support the item type. It is useful for bootstrapping,
# but Git sync is the most complete deployment path for this source tree.
RUN_REST_ITEM_DEPLOYMENT = False
SOURCE_REPO_ZIP_URL = ""       # Example: https://github.com/owner/repo/archive/refs/heads/main.zip

# Optional GitHub token for private SOURCE_REPO_ZIP_URL downloads. Store it in
# Key Vault and set both values below. Do not paste tokens into this notebook.
GITHUB_TOKEN_KEY_VAULT_URL = ""
GITHUB_TOKEN_SECRET_NAME = ""

UPDATE_EXISTING_DEFINITIONS = True
ALLOW_EMPTY_ITEM_FALLBACK = True


# ------------------------------------------------------------
# FABRIC REST CLIENT
# ------------------------------------------------------------

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"


class FabricApiError(RuntimeError):
    def __init__(self, method: str, url: str, status_code: int, response_text: str):
        self.method = method
        self.url = url
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(f"{method} {url} failed with HTTP {status_code}: {response_text}")

    @property
    def error_code(self) -> str:
        try:
            return str(json.loads(self.response_text).get("errorCode", ""))
        except Exception:
            return ""


def _get_notebookutils():
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


def fabric_token() -> str:
    return _get_notebookutils().credentials.getToken("pbi")


def fabric_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {fabric_token()}",
        "Content-Type": "application/json",
    }


def fabric_request(
    method: str,
    path_or_url: str,
    *,
    expected_status: Iterable[int] = (200,),
    json_body: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = 120,
) -> requests.Response:
    url = (
        path_or_url
        if path_or_url.startswith("https://")
        else f"{FABRIC_API_BASE}{path_or_url}"
    )

    while True:
        response = requests.request(
            method,
            url,
            headers=fabric_headers(),
            json=json_body,
            timeout=timeout_seconds,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "30"))
            print(f"Rate limited by Fabric API. Retrying in {retry_after} seconds.")
            time.sleep(retry_after)
            continue

        if response.status_code not in set(expected_status):
            raise FabricApiError(method, url, response.status_code, response.text)

        return response


def response_json(response: requests.Response) -> Dict[str, Any]:
    return response.json() if response.text else {}


def wait_for_operation(response: requests.Response, *, timeout_minutes: int = 60) -> Dict[str, Any]:
    operation_id = response.headers.get("x-ms-operation-id")
    if response.status_code != 202 or not operation_id:
        return response_json(response)

    deadline = time.time() + timeout_minutes * 60
    while time.time() < deadline:
        state_response = fabric_request(
            "GET",
            f"/operations/{operation_id}",
            expected_status=(200,),
        )
        state = response_json(state_response)
        status = state.get("status")

        if status == "Succeeded":
            try:
                result_response = fabric_request(
                    "GET",
                    f"/operations/{operation_id}/result",
                    expected_status=(200,),
                )
                return response_json(result_response)
            except FabricApiError as exc:
                if exc.status_code == 404:
                    return state
                raise

        if status == "Failed":
            raise RuntimeError(f"Fabric long-running operation failed: {json.dumps(state)}")

        retry_after = int(state_response.headers.get("Retry-After", "20"))
        print(f"Operation {operation_id} is {status}. Checking again in {retry_after} seconds.")
        time.sleep(retry_after)

    raise TimeoutError(f"Fabric operation {operation_id} did not finish within {timeout_minutes} minutes.")


# ------------------------------------------------------------
# WORKSPACE CREATION
# ------------------------------------------------------------

def list_workspaces() -> List[Dict[str, Any]]:
    workspaces: List[Dict[str, Any]] = []
    path = "/workspaces"

    while path:
        payload = response_json(fabric_request("GET", path, expected_status=(200,)))
        workspaces.extend(payload.get("value", []))

        continuation = payload.get("continuationToken")
        path = f"/workspaces?continuationToken={continuation}" if continuation else ""

    return workspaces


def get_workspace_by_name(display_name: str) -> Optional[Dict[str, Any]]:
    matches = [
        workspace
        for workspace in list_workspaces()
        if workspace.get("displayName") == display_name
    ]
    if len(matches) > 1:
        raise RuntimeError(f"Multiple workspaces named {display_name!r} were found.")
    return matches[0] if matches else None


def create_or_get_workspace() -> Dict[str, Any]:
    existing = get_workspace_by_name(TARGET_WORKSPACE_DISPLAY_NAME)
    if existing:
        print(f"Using existing workspace: {existing['displayName']} ({existing['id']})")
        return existing

    body: Dict[str, Any] = {
        "displayName": TARGET_WORKSPACE_DISPLAY_NAME,
        "description": TARGET_WORKSPACE_DESCRIPTION,
    }
    if CAPACITY_ID:
        body["capacityId"] = CAPACITY_ID
    if DOMAIN_ID:
        body["domainId"] = DOMAIN_ID

    response = fabric_request("POST", "/workspaces", expected_status=(201,), json_body=body)
    workspace = response_json(response)
    print(f"Created workspace: {workspace['displayName']} ({workspace['id']})")
    return workspace


# ------------------------------------------------------------
# PREFERRED PATH: FABRIC GIT SYNC
# ------------------------------------------------------------

def git_provider_details() -> Dict[str, Any]:
    if GIT_PROVIDER_TYPE == "GitHub":
        if not GITHUB_OWNER_NAME or not GITHUB_REPOSITORY_NAME:
            raise ValueError("Set GITHUB_OWNER_NAME and GITHUB_REPOSITORY_NAME for GitHub sync.")

        details: Dict[str, Any] = {
            "gitProviderType": "GitHub",
            "ownerName": GITHUB_OWNER_NAME,
            "repositoryName": GITHUB_REPOSITORY_NAME,
            "branchName": GIT_BRANCH_NAME,
            "directoryName": GIT_DIRECTORY_NAME,
        }
        if GITHUB_CUSTOM_DOMAIN_NAME:
            details["customDomainName"] = GITHUB_CUSTOM_DOMAIN_NAME
        return details

    if GIT_PROVIDER_TYPE == "AzureDevOps":
        required = [
            AZURE_DEVOPS_ORGANIZATION_NAME,
            AZURE_DEVOPS_PROJECT_NAME,
            AZURE_DEVOPS_REPOSITORY_NAME,
        ]
        if not all(required):
            raise ValueError(
                "Set AZURE_DEVOPS_ORGANIZATION_NAME, AZURE_DEVOPS_PROJECT_NAME, "
                "and AZURE_DEVOPS_REPOSITORY_NAME for Azure DevOps sync."
            )
        return {
            "gitProviderType": "AzureDevOps",
            "organizationName": AZURE_DEVOPS_ORGANIZATION_NAME,
            "projectName": AZURE_DEVOPS_PROJECT_NAME,
            "repositoryName": AZURE_DEVOPS_REPOSITORY_NAME,
            "branchName": GIT_BRANCH_NAME,
            "directoryName": GIT_DIRECTORY_NAME,
        }

    raise ValueError("GIT_PROVIDER_TYPE must be 'GitHub' or 'AzureDevOps'.")


def git_credentials() -> Dict[str, Any]:
    if GIT_CONNECTION_ID:
        return {
            "source": "ConfiguredConnection",
            "connectionId": GIT_CONNECTION_ID,
        }

    if GIT_PROVIDER_TYPE == "GitHub":
        raise ValueError("GitHub sync requires GIT_CONNECTION_ID.")

    return {"source": "Automatic"}


def connect_workspace_to_git(workspace_id: str) -> None:
    body = {
        "gitProviderDetails": git_provider_details(),
        "myGitCredentials": git_credentials(),
    }

    try:
        fabric_request(
            "POST",
            f"/workspaces/{workspace_id}/git/connect",
            expected_status=(200,),
            json_body=body,
        )
        print("Connected workspace to Git.")
    except FabricApiError as exc:
        if exc.error_code == "WorkspaceAlreadyConnectedToGit":
            print("Workspace is already connected to Git.")
            return
        raise


def initialize_git_connection(workspace_id: str) -> Dict[str, Any]:
    response = fabric_request(
        "POST",
        f"/workspaces/{workspace_id}/git/initializeConnection",
        expected_status=(200, 202),
        json_body={"initializationStrategy": "PreferRemote"},
    )
    result = wait_for_operation(response)
    print(f"Git initialization requiredAction: {result.get('requiredAction')}")
    return result


def update_workspace_from_git(workspace_id: str, init_result: Dict[str, Any]) -> None:
    if init_result.get("requiredAction") in (None, "None"):
        print("Workspace is already synchronized with Git.")
        return

    if init_result.get("requiredAction") != "UpdateFromGit":
        raise RuntimeError(f"Unsupported Git requiredAction: {init_result.get('requiredAction')}")

    body = {
        "workspaceHead": init_result.get("workspaceHead"),
        "remoteCommitHash": init_result["remoteCommitHash"],
        "conflictResolution": {
            "conflictResolutionType": "Workspace",
            "conflictResolutionPolicy": "PreferRemote",
        },
        "options": {
            "allowOverrideItems": True,
        },
    }

    response = fabric_request(
        "POST",
        f"/workspaces/{workspace_id}/git/updateFromGit",
        expected_status=(200, 202),
        json_body=body,
    )
    wait_for_operation(response, timeout_minutes=90)
    print("Workspace updated from Git.")


def deploy_from_git(workspace_id: str) -> None:
    connect_workspace_to_git(workspace_id)
    init_result = initialize_git_connection(workspace_id)
    update_workspace_from_git(workspace_id, init_result)


# ------------------------------------------------------------
# FALLBACK PATH: ITEM DEFINITIONS FROM REPO FILES
# ------------------------------------------------------------

@dataclass(frozen=True)
class FabricItemSource:
    item_dir: Path
    item_type: str
    display_name: str
    description: str
    logical_id: str


ITEM_TYPE_ORDER = {
    "Lakehouse": 10,
    "Warehouse": 20,
    "MirroredDatabase": 30,
    "Notebook": 40,
    "DataPipeline": 50,
    "SemanticModel": 60,
    "Report": 70,
    "Ontology": 80,
    "DataAgent": 90,
}


DEFINITION_NOT_SUPPORTED_CODES = {
    "OperationNotSupportedForItem",
    "ItemDefinitionNotSupported",
    "UnsupportedItemDefinition",
}


def get_secret_from_key_vault(vault_url: str, secret_name: str) -> str:
    return _get_notebookutils().credentials.getSecret(vault_url, secret_name)


def download_repo_zip() -> Path:
    if not SOURCE_REPO_ZIP_URL:
        raise ValueError("Set SOURCE_REPO_ZIP_URL before running REST item deployment.")

    headers = {}
    if GITHUB_TOKEN_KEY_VAULT_URL and GITHUB_TOKEN_SECRET_NAME:
        token = get_secret_from_key_vault(
            GITHUB_TOKEN_KEY_VAULT_URL,
            GITHUB_TOKEN_SECRET_NAME,
        )
        headers["Authorization"] = f"Bearer {token}"

    work_dir = Path("/tmp/ws_insurance_demo_repo")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    zip_path = work_dir / "repo.zip"
    response = requests.get(SOURCE_REPO_ZIP_URL, headers=headers, timeout=300)
    response.raise_for_status()
    zip_path.write_bytes(response.content)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(work_dir)

    roots = [path for path in work_dir.iterdir() if path.is_dir()]
    if len(roots) == 1:
        return roots[0]
    return work_dir


def discover_local_repo_root() -> Optional[Path]:
    current = Path.cwd()
    candidates = [current, *current.parents]
    for candidate in candidates:
        if (candidate / "README.md").exists() and list(candidate.rglob(".platform")):
            return candidate
    return None


def repo_root_for_rest_deployment() -> Path:
    local_root = discover_local_repo_root()
    if local_root:
        print(f"Using local repository root: {local_root}")
        return local_root

    downloaded_root = download_repo_zip()
    print(f"Using downloaded repository root: {downloaded_root}")
    return downloaded_root


def read_platform(platform_path: Path) -> FabricItemSource:
    platform = json.loads(platform_path.read_text(encoding="utf-8"))
    metadata = platform["metadata"]
    config = platform.get("config", {})
    return FabricItemSource(
        item_dir=platform_path.parent,
        item_type=metadata["type"],
        display_name=metadata["displayName"],
        description=metadata.get("description", ""),
        logical_id=config.get("logicalId", ""),
    )


def discover_items(repo_root: Path) -> List[FabricItemSource]:
    items = [
        read_platform(platform_path)
        for platform_path in repo_root.rglob(".platform")
        if ".git" not in platform_path.parts
    ]
    return sorted(
        items,
        key=lambda item: (
            ITEM_TYPE_ORDER.get(item.item_type, 999),
            item.display_name.lower(),
        ),
    )


def encode_item_definition(item_dir: Path) -> Dict[str, Any]:
    parts: List[Dict[str, str]] = []
    for file_path in sorted(path for path in item_dir.rglob("*") if path.is_file()):
        relative_path = file_path.relative_to(item_dir).as_posix()
        payload = base64.b64encode(file_path.read_bytes()).decode("ascii")
        parts.append(
            {
                "path": relative_path,
                "payload": payload,
                "payloadType": "InlineBase64",
            }
        )
    return {"parts": parts}


def list_workspace_items(workspace_id: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    path = f"/workspaces/{workspace_id}/items"

    while path:
        payload = response_json(fabric_request("GET", path, expected_status=(200,)))
        items.extend(payload.get("value", []))

        continuation = payload.get("continuationToken")
        path = (
            f"/workspaces/{workspace_id}/items?continuationToken={continuation}"
            if continuation
            else ""
        )

    return items


def find_workspace_item(
    workspace_items: List[Dict[str, Any]],
    source_item: FabricItemSource,
) -> Optional[Dict[str, Any]]:
    matches = [
        item
        for item in workspace_items
        if item.get("displayName") == source_item.display_name
        and item.get("type") == source_item.item_type
    ]
    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple {source_item.item_type} items named {source_item.display_name!r} were found."
        )
    return matches[0] if matches else None


def definition_not_supported(exc: FabricApiError) -> bool:
    response_text = exc.response_text.lower()
    return (
        exc.error_code in DEFINITION_NOT_SUPPORTED_CODES
        or ("definition" in response_text and "not supported" in response_text)
    )


def create_empty_item(workspace_id: str, source_item: FabricItemSource) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "displayName": source_item.display_name,
        "type": source_item.item_type,
    }
    if source_item.description:
        body["description"] = source_item.description[:256]

    response = fabric_request(
        "POST",
        f"/workspaces/{workspace_id}/items",
        expected_status=(201, 202),
        json_body=body,
    )
    result = wait_for_operation(response)
    print(f"Created empty {source_item.item_type}: {source_item.display_name}")
    return result


def create_item_with_definition(workspace_id: str, source_item: FabricItemSource) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "displayName": source_item.display_name,
        "type": source_item.item_type,
        "definition": encode_item_definition(source_item.item_dir),
    }
    if source_item.description:
        body["description"] = source_item.description[:256]

    response = fabric_request(
        "POST",
        f"/workspaces/{workspace_id}/items",
        expected_status=(201, 202),
        json_body=body,
    )
    result = wait_for_operation(response)
    print(f"Created {source_item.item_type}: {source_item.display_name}")
    return result


def update_item_definition(
    workspace_id: str,
    item_id: str,
    source_item: FabricItemSource,
) -> None:
    body = {"definition": encode_item_definition(source_item.item_dir)}
    response = fabric_request(
        "POST",
        f"/workspaces/{workspace_id}/items/{item_id}/updateDefinition?updateMetadata=True",
        expected_status=(200, 202),
        json_body=body,
    )
    wait_for_operation(response)
    print(f"Updated {source_item.item_type}: {source_item.display_name}")


def deploy_item_from_repo(
    workspace_id: str,
    workspace_items: List[Dict[str, Any]],
    source_item: FabricItemSource,
) -> None:
    existing_item = find_workspace_item(workspace_items, source_item)

    if existing_item:
        if not UPDATE_EXISTING_DEFINITIONS:
            print(f"Skipping existing {source_item.item_type}: {source_item.display_name}")
            return
        try:
            update_item_definition(workspace_id, existing_item["id"], source_item)
        except FabricApiError as exc:
            if definition_not_supported(exc) and ALLOW_EMPTY_ITEM_FALLBACK:
                print(
                    f"Definition update is not supported for {source_item.item_type} "
                    f"{source_item.display_name}; existing item left unchanged."
                )
                return
            raise
        return

    try:
        created = create_item_with_definition(workspace_id, source_item)
        if created.get("id"):
            workspace_items.append(created)
    except FabricApiError as exc:
        if definition_not_supported(exc) and ALLOW_EMPTY_ITEM_FALLBACK:
            created = create_empty_item(workspace_id, source_item)
            if created.get("id"):
                workspace_items.append(created)
            print(
                f"{source_item.item_type} {source_item.display_name} was created without "
                "a definition because this item type does not support definition deployment "
                "through the generic item API in this tenant."
            )
            return
        raise


def deploy_items_from_repo(workspace_id: str) -> None:
    repo_root = repo_root_for_rest_deployment()
    source_items = discover_items(repo_root)

    print("Discovered Fabric items:")
    for source_item in source_items:
        print(f"  - {source_item.item_type}: {source_item.display_name}")

    workspace_items = list_workspace_items(workspace_id)
    for source_item in source_items:
        deploy_item_from_repo(workspace_id, workspace_items, source_item)


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------

if not RUN_GIT_SYNC and not RUN_REST_ITEM_DEPLOYMENT:
    raise ValueError(
        "Set RUN_GIT_SYNC = True for the recommended Git deployment path, "
        "or RUN_REST_ITEM_DEPLOYMENT = True for direct REST item deployment."
    )

workspace = create_or_get_workspace()
workspace_id = workspace["id"]

if RUN_GIT_SYNC:
    deploy_from_git(workspace_id)

if RUN_REST_ITEM_DEPLOYMENT:
    deploy_items_from_repo(workspace_id)

print(f"Provisioning complete for workspace {TARGET_WORKSPACE_DISPLAY_NAME} ({workspace_id}).")
