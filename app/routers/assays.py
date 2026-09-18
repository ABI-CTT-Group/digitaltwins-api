"""
Assay Router.

Consolidates all assay endpoints: list, get, configure, run assay workflows,
and workspace dataset upload/download.
"""

import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from requests import Response

from sparc_me import Dataset

from digitaltwins import Querier, Uploader
from digitaltwins.minio.uploader import Uploader as MinioUploader
from .auth import validate_credentials
from .dependencies import get_querier, get_uploader
from ..schemas.assay import AssayDataModel

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()

# Airflow configs
AIRFLOW_ENABLED = os.getenv("AIRFLOW_ENABLED", "false").lower() == "true"
AIRFLOW_ENDPOINT = os.getenv("AIRFLOW_ENDPOINT", "http://airflow-apiserver:8080/airflow")

HOSTNAME = os.getenv("HOSTNAME")
AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", f"http://{HOSTNAME}/airflow")# JupyterHub configs
JUPYTERHUB_PUBLIC_URL = os.getenv("JUPYTERHUB_PUBLIC_URL", "http://localhost/jupyter")
JUPYTERHUB_INTERNAL_URL = os.getenv("JUPYTERHUB_INTERNAL_URL", "http://digitaltwins-platform-jupyterhub:8000/jupyter")
DEFAULT_BUCKET = "airflow-workspace"
WORKFLOW_TIMEZONE = os.getenv("WORKFLOW_TIMEZONE", os.getenv("TZ", "Pacific/Auckland"))
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")

# assay_input.category value marking an input as a model dataset.
MODEL_INPUT_CATEGORY = "models"


# ── Private helpers (workflow orchestration) ──────────────────────────


def _workflow_local_timestamp() -> str:
    try:
        tz = ZoneInfo(WORKFLOW_TIMEZONE)
    except ZoneInfoNotFoundError:
        tz = timezone.utc
    return datetime.now(tz).strftime("%Y%m%d_%H%M%S")


def _get_api_token():
    url = f"{AIRFLOW_ENDPOINT}/auth/token"
    headers = {"Content-Type": "application/json"}
    payload = {
        "username": AIRFLOW_USERNAME,
        "password": AIRFLOW_PASSWORD
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        access_token = response.json().get("access_token")
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to reach Airflow auth endpoint: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Airflow returned a non-JSON token response.",
        ) from exc
    return access_token


def _trigger_dag(dag_id: str, conf: dict) -> Response:
    """Trigger an Airflow DAG run via the Airflow REST API v2 (Airflow 3)."""
    url = f"{AIRFLOW_ENDPOINT}/api/v2/dags/{dag_id}/dagRuns"
    api_token = _get_api_token()
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    logical_date = datetime.now(timezone.utc).isoformat()

    payload = {
        "logical_date": logical_date,  # required
        "conf": conf
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Triggered DAG Run: %s", response.json())
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Airflow API Error: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Airflow returned a non-JSON DAG run response.",
        ) from exc

    return response


def _fetch_assay_configs(querier: Querier, assay_id: int) -> dict:
    assay_data = querier.get_assay(assay_id, get_configs=True)
    configs = assay_data.get("configs")
    if not configs:
        raise ValueError(f"No configs found for assay {assay_id}. Ensure the assay has been registered in Postgres.")
    
    return {
        "assay_id": assay_id,
        "workflow_seek_id": configs.get("workflow_seek_id"),
        "cohort": configs.get("cohort"),
        "inputs": configs.get("inputs", []),
        "outputs": configs.get("outputs", []),
        "bucket": DEFAULT_BUCKET,
    }


def _model_conf_overrides(inputs: list[dict]) -> dict[str, str]:
    """Map model-category assay inputs to their ``{name}_dataset_uuid`` DAG conf keys."""
    overrides: dict[str, str] = {}
    for inp in inputs:
        if inp.get("category") != MODEL_INPUT_CATEGORY:
            continue
        name = inp.get("name") or ""
        dataset_uuid = inp.get("dataset_uuid") or ""
        if not name:
            raise ValueError("A model assay input is missing its name.")
        if not dataset_uuid:
            raise ValueError(f"Model input '{name}' has no dataset_uuid.")
        overrides[f"{name}_dataset_uuid"] = dataset_uuid
    return overrides


def _normalise_subject(value: str) -> str:
    """Strip the SDS ``sub-`` prefix so cohort indices and subject ids compare equal."""
    return str(value).strip().removeprefix("sub-")


def _discover_samples(querier: Querier, configs: dict) -> list[dict]:
    inputs = configs.get("inputs", [])
    if not inputs:
        raise ValueError("No inputs found in assay configs.")

    # assay.cohort holds the indices of the subjects to run; empty means all of them.
    cohort = {_normalise_subject(c) for c in (configs.get("cohort") or [])}
    matched = set()

    samples_list = []
    seen = set()

    for inp in inputs:
        if inp.get("category") == MODEL_INPUT_CATEGORY:
            continue
        dataset_uuid = inp.get("dataset_uuid")
        sample_type = inp.get("sample_type")
        input_name = inp.get("name", "input")

        if not dataset_uuid:
            continue

        resp = querier.get_dataset_samples(dataset_uuid, sample_type)
        # querier.get_dataset_samples returns a list of dictionaries with sample details
        for row in resp:
            subject_id = row.get("subject_id")
            sample_id = row.get("sample_id")
            
            if subject_id and sample_id:
                subject_key = _normalise_subject(subject_id)
                if cohort:
                    if subject_key not in cohort:
                        continue
                    matched.add(subject_key)

                key = (subject_id, sample_id)
                if key not in seen:
                    seen.add(key)
                    samples_list.append({
                        "subject_id": subject_id,
                        "sample_id": sample_id,
                        "dataset_uuid": dataset_uuid,
                        "sample_type": sample_type,
                        "input_name": input_name,
                    })

    unmatched = cohort - matched
    if unmatched:
        raise ValueError(
            "No samples found for cohort subjects: "
            + ", ".join(f"sub-{s}" for s in sorted(unmatched))
        )

    if not samples_list:
        raise ValueError("No samples found for the given inputs.")

    return samples_list


def _build_output_name_by_sample_type(outputs: list[dict]) -> dict[str, str]:
    """Map sample type labels (e.g. nifti/nrrd) to assay output names."""
    output_name_by_sample_type: dict[str, str] = {}
    for output in outputs:
        out_name = str(output.get("name", "")).strip()
        sample_name = str(output.get("sample_name", "")).strip().lower()
        if out_name and sample_name and sample_name not in output_name_by_sample_type:
            output_name_by_sample_type[sample_name] = out_name
    return output_name_by_sample_type


def _create_sds_output(
    configs: dict, samples: list[dict], temp_dir: str
) -> tuple[str, dict[tuple[str, str], dict[str, str]]]:
    assay_id = configs.get("assay_id")
    dataset_name = "output_dataset"
    outputs = configs.get("outputs", [])
    if outputs and len(outputs) > 0 and outputs[0].get("dataset_name"):
        dataset_name = outputs[0].get("dataset_name")

    timestamp = _workflow_local_timestamp()
    s3_prefix = f"assay_{assay_id}/{timestamp}/{dataset_name}"

    # init sparc-me dataset
    dataset = Dataset()
    dataset.create_empty_dataset(version="2.0.0")
    
    try:
        meta = dataset.get_metadata("dataset_description")
        meta.clear_values("Name")
        meta.add_values("Name", dataset_name)
    except Exception as e:
        logger.warning("Failed to set dataset Name: %s", e)

    try:
        subjects_meta = dataset.get_metadata("subjects")
        subjects_meta.clear_values("subject id")
        # Ensure unique subjects
        unique_subjects = list(set([s["subject_id"].replace("sub-", "") for s in samples]))
        subjects_meta.add_values("subject id", unique_subjects)
    except Exception as e:
        logger.warning("Failed to set subjects metadata: %s", e)

    output_mappings: dict[tuple[str, str], dict[str, str]] = {}

    try:
        samples_meta = dataset.get_metadata("samples")
        samples_meta.clear_values("subject id")
        samples_meta.clear_values("sample id")
        samples_meta.clear_values("sample type")
        
        subject_ids = []
        sample_ids = []
        sample_types = []
        
        subject_sample_counter: dict[str, int] = {}
        
        for sample in samples:
            subject_key = sample["subject_id"]
            sample_key = sample["sample_id"]
            sub_id = sample["subject_id"].replace("sub-", "")
            
            if sub_id not in subject_sample_counter:
                subject_sample_counter[sub_id] = 1
                
            output_mappings[(subject_key, sample_key)] = {}
            
            for out in outputs:
                out_name = out.get("name", "")
                sample_type = out.get("sample_name", "unknown")
                
                new_sam_id = str(subject_sample_counter[sub_id])
                output_mappings[(subject_key, sample_key)][out_name] = new_sam_id
                subject_sample_counter[sub_id] += 1
                
                subject_ids.append(sub_id)
                sample_ids.append(new_sam_id)
                sample_types.append(sample_type)

        samples_meta.add_values("subject id", subject_ids)
        samples_meta.add_values("sample id", sample_ids)
        samples_meta.add_values("sample type", sample_types)
    except Exception as e:
        logger.warning("Failed to set samples metadata: %s", e)

    try:
        manifest_meta = dataset.get_metadata("manifest")
        filenames = []
        timestamps = []
        descriptions = []
        file_types = []
        
        now = datetime.now(timezone.utc).isoformat()
        
        for sample in samples:
            subject_key = sample["subject_id"]
            sample_key = sample["sample_id"]
            sub_id = sample["subject_id"].replace("sub-", "")
            
            for out in outputs:
                out_name = out.get("name", "")
                sample_type = out.get("sample_name", "")
                new_sam_id = output_mappings[(subject_key, sample_key)][out_name]
                
                base_dir = f"sub-{sub_id}/sam-{new_sam_id}"
                
                if "nifti" in sample_type.lower():
                    fname = f"{base_dir}/breast_mri_rai.nii.gz"
                elif "nrrd" in sample_type.lower():
                    fname = f"{base_dir}/image.nrrd"
                else:
                    fname = f"{base_dir}/output_{sample_type}.ext"
                    
                filenames.append(fname)
                timestamps.append(now)
                descriptions.append(f"Generated output {sample_type}")
                file_types.append("image")
        
        if filenames:
            manifest_meta.clear_values("filename")
            manifest_meta.clear_values("timestamp")
            manifest_meta.clear_values("description")
            manifest_meta.clear_values("file type")
            
            manifest_meta.add_values("filename", filenames)
            manifest_meta.add_values("timestamp", timestamps)
            manifest_meta.add_values("description", descriptions)
            manifest_meta.add_values("file type", file_types)
    except Exception as e:
        logger.warning("Failed to set manifest metadata: %s", e)

    dataset.save(save_dir=temp_dir)
    
    # create sample subdirectories in primary
    primary_dir = os.path.join(temp_dir, "primary")
    for sample in samples:
        subject_key = sample["subject_id"]
        sample_key = sample["sample_id"]
        sub_id = sample["subject_id"].replace("sub-", "")
        
        for out_name, new_sam_id in output_mappings[(subject_key, sample_key)].items():
            sample_dir = os.path.join(primary_dir, f"sub-{sub_id}", f"sam-{new_sam_id}")
            os.makedirs(sample_dir, exist_ok=True)

    # Upload to MinIO
    uploader = MinioUploader()
    if not uploader.bucket_exists(DEFAULT_BUCKET):
        logger.warning("Bucket %s does not exist, upload may fail.", DEFAULT_BUCKET)
        
    uploader.upload_folder(temp_dir, DEFAULT_BUCKET, prefix=s3_prefix, overwrite=True)

    # Explicitly create empty directories for SPARC folders in MinIO
    try:
        empty_dirs = [
            "primary/", "derivative/", "docs/", "code/", "protocol/", "source/"
        ]
        for sample in samples:
            subject_key = sample["subject_id"]
            sample_key = sample["sample_id"]
            sub_id = sample["subject_id"].replace("sub-", "")
            
            for out_name, new_sam_id in output_mappings[(subject_key, sample_key)].items():
                empty_dirs.append(f"primary/sub-{sub_id}/sam-{new_sam_id}/")
            
        for d in empty_dirs:
            key = f"{s3_prefix}/{d}"
            uploader.s3_client.put_object(Bucket=DEFAULT_BUCKET, Key=key, Body=b"")
    except Exception as e:
        logger.warning("Failed to create empty S3 directories: %s", e)

    return s3_prefix, output_mappings


# ── Query endpoints ───────────────────────────────────────────────────


@router.get("/assays", tags=["assays"])
def get_assays(get_details: bool = False, querier: Querier = Depends(get_querier)):
    """
    Retrieve a list of assays.

    Args:
        get_details (bool, optional): If True, returns detailed information about each assay. Defaults to False.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the list of assays under the 'assays' key.
    """
    assays = querier.get_assays(get_details=get_details)
    return {"assays": assays}


@router.get("/assays/{assay_id}", tags=["assays"])
def get_assay(assay_id: int, get_configs: bool = False, querier: Querier = Depends(get_querier)):
    """
    Retrieve a specific assay by its ID, with optional parameters.

    Args:
        assay_id (int): The ID of the assay to retrieve.
        get_configs (bool, optional): If True, retrieves additional parameters related to the assay. Defaults to False.
        querier (Querier): Per-request querier authenticated as the calling user.

    Returns:
        dict: A dictionary containing the assay details under the 'assay' key.
    """
    assay = querier.get_assay(assay_id, get_configs=get_configs)
    return {"assay": assay}


# ── Configure endpoint ────────────────────────────────────────────────


@router.post("/assays", tags=["assays"])
async def configure_assay(
    assay_data: AssayDataModel,
    uploader: Uploader = Depends(get_uploader),
    _valid: bool = Depends(validate_credentials),
) -> dict[str, Any]:
    """Configure an assay through PostgreSQL.
    
    Accepts an AssayDataModel JSON payload containing the assay configuration
    as well as inputs and outputs mapping. Directly invokes
    `uploader.configure_assay(assay_data.model_dump())` to persist the 
    configuration in the PostgreSQL database.
    """
    try:
        # Convert Pydantic payload to dictionary string exactly as the DB layer expects
        payload = assay_data.model_dump()
        assay_uuid = uploader.configure_assay(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Failed to configure assay")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure assay: {exc}",
        ) from exc

    return {
        "message": "Assay configured successfully.",
        "assay_uuid": assay_uuid,
    }


# ── Run endpoint ──────────────────────────────────────────────────────


@router.post("/assays/{assay_id}/run", tags=["assays"])
def run_assay(assay_id: int, credentials: dict = Depends(validate_credentials), querier: Querier = Depends(get_querier)):
    """
    Trigger the assay processing.
    For script-based workflows, this handles fetching configs, discovering samples,
    creating SDS skeleton, uploading to MinIO, and triggering workflow DAG runs per sample.

    Args:
        assay_id (int): The ID of the assay to process.
        credentials: Authenticated user credentials.
        querier: Per-request querier authenticated as the calling user.

    Returns:
        dict: Information about the triggered workflow runs.
    """
    username = credentials["username"]
    if not AIRFLOW_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Airflow integration is disabled (AIRFLOW_ENABLED=false).",
        )

    assay = querier.get_assay(assay_id, get_configs=False)
    tags = assay.get("attributes").get("tags")

    if "script" in tags:
        try:
            configs = _fetch_assay_configs(querier, assay_id)
            samples = _discover_samples(querier, configs)
            model_conf = _model_conf_overrides(configs.get("inputs", []))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to prepare assay: {str(e)}",
            )
        
        workflow_seek_id = configs.get("workflow_seek_id")
        if not workflow_seek_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="workflow_seek_id missing from configs.",
            )
        output_name_by_sample_type = _build_output_name_by_sample_type(configs.get("outputs", []))

        dag_id = f"workflow_{workflow_seek_id}"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            s3_prefix, output_mappings = _create_sds_output(configs, samples, temp_dir)
        
        # Trigger per-sample
        results = []
        for idx, sample in enumerate(samples):
            subject_id = sample["subject_id"]
            sample_id = sample["sample_id"]
            
            output_prefixes = {}
            if (subject_id, sample_id) in output_mappings:
                for out_name, new_sam_id in output_mappings[(subject_id, sample_id)].items():
                    output_prefixes[out_name] = f"{s3_prefix}/primary/{subject_id}/sam-{new_sam_id}"
            
            run_id = f"{dag_id}/run_{idx}"
            
            payload_conf = {
                "bucket": DEFAULT_BUCKET,
                "subject_id": subject_id,
                "sample_id": sample_id,
                "dataset_uuid": sample["dataset_uuid"],
                "sample_type": sample.get("sample_type", ""),
                "input_name": sample.get("input_name", "input"),
                "output_prefixes": output_prefixes,
                "output_name_by_sample_type": output_name_by_sample_type,
                "run_id": run_id,
                "run_index": idx,
                **model_conf,
            }
            
            try:
                response = _trigger_dag(dag_id, payload_conf)
                results.append({
                    "subject_id": subject_id,
                    "sample_id": sample_id,
                    "dag_run": response.json(),
                })
            except Exception as e:
                results.append({
                    "subject_id": subject_id,
                    "sample_id": sample_id,
                    "error": str(e)
                })

        monitor_base_url = AIRFLOW_BASE_URL
        monitor_url = f"{monitor_base_url}/dags/workflow_{workflow_seek_id}"

        return {"dag_runs": results, "monitor_url": monitor_url}
        
    elif "notebook" in tags:
        monitor_base_url = JUPYTERHUB_PUBLIC_URL
        monitor_url = f"{monitor_base_url}/user/{username}/lab/tree/assay_{assay_id}"
        return {"url": monitor_url}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assay must have either 'script' or 'notebook' tag to determine workflow.",
        )


# ── Workspace dataset endpoints ───────────────────────────────────────


@router.get("/assays/{assay_id}/workspace/dataset/download", tags=["assays"])
def download_workspace_dataset(
    assay_id: int,
    timestamp: Optional[str] = None,
    querier: Querier = Depends(get_querier),
    credentials: dict = Depends(validate_credentials),
) -> StreamingResponse:
    """Download the workspace dataset for an assay.

    Args:
        assay_id: The ID of the assay.
        timestamp: Optional timestamp to download a specific historical run. If omitted, the latest is used.

    Returns:
        A streaming ZIP archive containing the dataset files.
    """
    from digitaltwins.minio.downloader import Downloader as MinioDownloader
    
    assay_data = querier.get_assay(assay_id, get_configs=False)
    tags = assay_data.get("attributes", {}).get("tags", []) or []
    is_jupyter = "notebook" in tags

    tmp_dir = tempfile.mkdtemp()
    
    try:
        save_dir = os.path.join(tmp_dir, "data")
        
        if is_jupyter:
            username = credentials["username"]
            remote_path = f"assay_{assay_id}/outputs/datasets"
            _download_jupyter_folder(username, remote_path, save_dir)
            resolved_timestamp = None
        else:
            downloader = MinioDownloader()
            prefix_base = f"assay_{assay_id}/"
            resolved_timestamp = timestamp or downloader.get_latest_timestamp_folder(DEFAULT_BUCKET, prefix_base)
            target_prefix = f"{prefix_base}{resolved_timestamp}/"
            # Download the specific folder
            downloader.download_folder(DEFAULT_BUCKET, target_prefix, save_dir)
        
        filename_base = f"assay_{assay_id}_results_{resolved_timestamp}" if resolved_timestamp else f"assay_{assay_id}_results"
        zip_path = os.path.join(tmp_dir, f"{filename_base}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(save_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, save_dir)
                    zf.write(file_path, arcname)
                    
    except FileNotFoundError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage backend unavailable: {exc}",
        ) from exc
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.exception("Unexpected error while downloading workspace dataset")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error while downloading dataset: {exc}",
        ) from exc

    def _stream_and_cleanup():
        try:
            with open(zip_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return StreamingResponse(
        _stream_and_cleanup(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename_base}.zip"',
        },
    )


def _download_jupyter_folder(username: str, remote_path: str, local_dir: str):
    """Recursively download a folder from Jupyter Server."""
    api_token = os.getenv("JUPYTERHUB_API_TOKEN", "digitaltwins-api-secret-token")
    headers = {"Authorization": f"token {api_token}"}
    api_url = f"{JUPYTERHUB_INTERNAL_URL}/user/{username}/api/contents/{remote_path}"
    
    response = requests.get(api_url, headers=headers)
    if response.status_code == 404:
        raise FileNotFoundError(f"Folder not found in Jupyter workspace: {remote_path}")
    response.raise_for_status()
    data = response.json()
    
    if data.get("type") == "directory":
        os.makedirs(local_dir, exist_ok=True)
        for item in data.get("content", []):
            item_path = item["path"]
            item_name = item["name"]
            item_type = item["type"]
            local_item_path = os.path.join(local_dir, item_name)
            
            if item_type == "directory":
                _download_jupyter_folder(username, item_path, local_item_path)
            elif item_type == "file":
                file_url = f"{JUPYTERHUB_INTERNAL_URL}/user/{username}/files/{item_path}"
                file_resp = requests.get(file_url, headers=headers, stream=True)
                file_resp.raise_for_status()
                with open(local_item_path, 'wb') as f:
                    for chunk in file_resp.iter_content(chunk_size=8192):
                        f.write(chunk)


@router.post("/assays/{assay_id}/workspace/dataset/upload", tags=["assays"])
async def upload_workspace_datasets(
    assay_id: int,
    timestamp: Optional[str] = None,
    uploader: Uploader = Depends(get_uploader),
    querier: Querier = Depends(get_querier),
    credentials: dict = Depends(validate_credentials),
) -> dict[str, Any]:
    """Upload datasets from the workspace bucket to the platform.

    Args:
        assay_id: The ID of the assay.
        timestamp: Optional timestamp to specify a historical run. If omitted, the latest is used.
    
    Returns:
        A dictionary containing the uploaded dataset UUIDs.
    """

    tmp_dir = None
    try:
        # 1. Fetch assay configs to get category mapping
        assay_data = querier.get_assay(assay_id, get_configs=True)
        configs = assay_data.get("configs", {})
        outputs = configs.get("outputs", [])
        tags = assay_data.get("attributes", {}).get("tags", []) or []
        is_jupyter = "notebook" in tags
        
        category_map = {}
        for out in outputs:
            ds_name = out.get("dataset_name")
            cat = out.get("category", "workflows")
            if ds_name:
                category_map[ds_name] = cat
                
        tmp_dir = tempfile.mkdtemp()
        save_dir = os.path.join(tmp_dir, "data")
        
        if is_jupyter:
            # Jupyter / Notebook flow
            username = credentials["username"]
            remote_path = f"assay_{assay_id}/outputs/datasets"
            _download_jupyter_folder(username, remote_path, save_dir)
        else:
            # Airflow / MinIO flow
            from digitaltwins.minio.downloader import Downloader as MinioDownloader
            minio_downloader = MinioDownloader()
            prefix_base = f"assay_{assay_id}/"
            
            if not timestamp:
                timestamp = minio_downloader.get_latest_timestamp_folder(DEFAULT_BUCKET, prefix_base)
                
            target_prefix = f"{prefix_base}{timestamp}/"
            minio_downloader.download_folder(DEFAULT_BUCKET, target_prefix, save_dir)
        
        
        # 4. Iterate subdirectories and upload each
        uploaded_datasets = []
        
        for item in os.listdir(save_dir):
            item_path = os.path.join(save_dir, item)
            if os.path.isdir(item_path):
                # determine category
                category = category_map.get(item, "workflows")
                
                # upload
                dataset_uuid = uploader.upload_dataset(
                    dataset_path=item_path,
                    category=category,
                )
                uploaded_datasets.append({
                    "dataset_name": item,
                    "dataset_uuid": dataset_uuid,
                    "category": category
                })
                
    except FileNotFoundError as exc:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage backend unavailable: {exc}",
        ) from exc
    except Exception as exc:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.exception("Unexpected error while uploading workspace datasets")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error while uploading datasets: {exc}",
        ) from exc
        
    # Cleanup
    if tmp_dir:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "message": f"Successfully uploaded {len(uploaded_datasets)} datasets.",
        "datasets": uploaded_datasets,
    }
