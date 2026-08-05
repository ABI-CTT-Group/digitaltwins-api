"""
Workflow Router.

This module provides endpoints to trigger Airflow DAG runs for assay processing.
"""
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from requests import Response

from sparc_me import Dataset

from .auth import validate_credentials
from .query import get_assay, querier
from digitaltwins.minio.uploader import Uploader

load_dotenv()

router = APIRouter()

# Airflow configs
AIRFLOW_ENABLED = os.getenv("AIRFLOW_ENABLED", "false").lower() == "true"
AIRFLOW_ENDPOINT = os.getenv("AIRFLOW_ENDPOINT", "http://airflow-apiserver:8080/airflow")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")

HOSTNAME = os.getenv("HOSTNAME")
AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", f"http://{HOSTNAME}/airflow")
JUPYTERHUB_PUBLIC_URL = os.getenv("JUPYTERHUB_PUBLIC_URL")
DEFAULT_BUCKET = "airflow-workspace"
WORKFLOW_TIMEZONE = os.getenv("WORKFLOW_TIMEZONE", os.getenv("TZ", "Pacific/Auckland"))


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
        print("Triggered DAG Run:", response.json())
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


def _fetch_assay_configs(assay_id: int) -> dict:
    assay_data = querier.get_assay(assay_id, get_configs=True)
    configs = assay_data.get("configs")
    if not configs:
        raise ValueError(f"No configs found for assay {assay_id}. Ensure the assay has been registered in Postgres.")
    
    return {
        "assay_id": assay_id,
        "workflow_seek_id": configs.get("workflow_seek_id"),
        "inputs": configs.get("inputs", []),
        "outputs": configs.get("outputs", []),
        "bucket": DEFAULT_BUCKET,
    }


def _discover_samples(configs: dict) -> list[dict]:
    inputs = configs.get("inputs", [])
    if not inputs:
        raise ValueError("No inputs found in assay configs.")

    samples_list = []
    seen = set()

    for inp in inputs:
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
        print(f"Warning: Failed to set dataset Name: {e}")

    try:
        subjects_meta = dataset.get_metadata("subjects")
        subjects_meta.clear_values("subject id")
        # Ensure unique subjects
        unique_subjects = list(set([s["subject_id"].replace("sub-", "") for s in samples]))
        subjects_meta.add_values("subject id", unique_subjects)
    except Exception as e:
        print(f"Warning: Failed to set subjects metadata: {e}")

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
        print(f"Warning: Failed to set samples metadata: {e}")

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
        print(f"Warning: Failed to set manifest metadata: {e}")

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
    uploader = Uploader()
    if not uploader.bucket_exists(DEFAULT_BUCKET):
        print(f"Bucket {DEFAULT_BUCKET} does not exist, upload may fail.")
        
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
        print(f"Warning: Failed to create empty S3 directories: {e}")

    return s3_prefix, output_mappings


@router.post("/assays/{assay_id}/run", tags=["assay"])
def run_assay(assay_id: int, username=Depends(validate_credentials)):
    """
    Trigger the assay processing.
    For script-based workflows, this handles fetching configs, discovering samples,
    creating SDS skeleton, uploading to MinIO, and triggering workflow DAG runs per sample.

    Args:
        assay_id (int): The ID of the assay to process.
        valid: Ensures valid credentials are provided.

    Returns:
        dict: Information about the triggered workflow runs.
    """
    if not AIRFLOW_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Airflow integration is disabled (AIRFLOW_ENABLED=false).",
        )

    assay = get_assay(assay_id, get_configs=False)
    tags = assay.get("assay").get("attributes").get("tags")

    if "script" in tags:
        try:
            configs = _fetch_assay_configs(assay_id)
            samples = _discover_samples(configs)
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


@router.get("/assays/{assay_id}/workspace/dataset/download", tags=["assay", "download"])
def download_workspace_dataset(
    assay_id: int,
    timestamp: Optional[str] = None,
    _valid: bool = Depends(validate_credentials),
) -> StreamingResponse:
    """Download the workspace dataset for an assay.

    Args:
        assay_id: The ID of the assay.
        timestamp: Optional timestamp to download a specific historical run. If omitted, the latest is used.

    Returns:
        A streaming ZIP archive containing the dataset files.
    """
    from digitaltwins.minio.downloader import Downloader as MinioDownloader
    
    downloader = MinioDownloader()
    prefix_base = f"assay_{assay_id}/"
    tmp_dir = tempfile.mkdtemp()
    
    try:
        resolved_timestamp = timestamp or downloader.get_latest_timestamp_folder(DEFAULT_BUCKET, prefix_base)
        target_prefix = f"{prefix_base}{resolved_timestamp}/"
        zip_path = os.path.join(tmp_dir, f"assay_{assay_id}_{resolved_timestamp}.zip")
        
        save_dir = os.path.join(tmp_dir, "data")
        
        # Download the specific folder
        downloader.download_folder(DEFAULT_BUCKET, target_prefix, save_dir)
        
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
        import traceback
        traceback.print_exc()
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
            "Content-Disposition": f'attachment; filename="assay_{assay_id}_{resolved_timestamp}.zip"',
        },
    )
