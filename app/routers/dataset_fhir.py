"""
FHIR annotation / push and file access for committed datasets.

UUIDs in annotations are server-owned: whatever a client sends is re-stamped
from ``dataset_mapping``. ``POST .../fhir/push`` queues the push job (first
push, retry and re-push alike); clients poll ``fhir_status`` via
``GET /datasets/{uuid}``. The file endpoint is what FHIR ``endpointUrl`` values
point at; it requires a token but no particular role.
"""
import json
import mimetypes

from botocore.exceptions import ClientError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from digitaltwins.measurements import jobs, pipeline
from digitaltwins.measurements.fhir_service import build_fhir_json, compute_endpoint_urls
from digitaltwins.measurements.tree import build_tree
from digitaltwins.minio.uploader import Uploader as MinioUploader

from .auth import require_upload_role, validate_credentials
from .dataset_uploads import AnnotationBody, get_conn

router = APIRouter(prefix="/datasets/{dataset_uuid}", tags=["dataset fhir"])


def _dataset_or_404(conn, dataset_uuid: str) -> dict:
    dataset = pipeline.get_dataset_row(conn, dataset_uuid)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


def _stamped(conn, dataset_uuid: str, descriptions: dict) -> dict:
    return pipeline.stamp_uuids(descriptions, dataset_uuid, pipeline.fetch_mapping(conn, dataset_uuid))


@router.get("/fhir/tree")
def get_tree(dataset_uuid: str, conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    """Prefilled descriptions carrying the dataset's real UUIDs."""
    dataset = _dataset_or_404(conn, dataset_uuid)
    tree = build_tree(pipeline.local_dataset(conn, dataset_uuid), dataset["dataset_name"] or "")
    tree["descriptions"] = _stamped(conn, dataset_uuid, tree["descriptions"])
    return tree


@router.get("/fhir/annotation")
def get_annotation(dataset_uuid: str, conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    _dataset_or_404(conn, dataset_uuid)
    descriptions = pipeline.load_annotation(conn, dataset_uuid)
    if descriptions is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No FHIR annotation for this dataset")
    return {"descriptions": descriptions}


@router.put("/fhir/annotation")
def put_annotation(
    dataset_uuid: str, body: AnnotationBody,
    conn=Depends(get_conn), _creds: dict = Depends(require_upload_role),
):
    _dataset_or_404(conn, dataset_uuid)
    try:
        pipeline.check_descriptions_match(body.descriptions, pipeline.local_dataset(conn, dataset_uuid))
        stamped = _stamped(conn, dataset_uuid, body.descriptions)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    pipeline.save_annotation(conn, dataset_uuid, stamped)
    return {"descriptions": stamped}


@router.post("/fhir/push", status_code=status.HTTP_202_ACCEPTED)
def push_fhir(
    dataset_uuid: str, background: BackgroundTasks,
    conn=Depends(get_conn), _creds: dict = Depends(require_upload_role),
):
    dataset = _dataset_or_404(conn, dataset_uuid)
    if dataset["fhir_status"] in ("pending", "pushing"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A FHIR push is already in progress")
    if pipeline.load_annotation(conn, dataset_uuid) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No FHIR annotation; PUT /datasets/{uuid}/fhir/annotation first.",
        )
    jobs.set_fhir_status(conn, dataset_uuid, "pending")
    background.add_task(jobs.run_fhir_push_job, dataset_uuid)
    return {"dataset_uuid": dataset_uuid, "fhir_status": "pending"}


@router.get("/fhir/preview")
def preview_fhir(dataset_uuid: str, conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    """The pushed fhir.json once completed; otherwise a dry-run build of the annotation."""
    dataset = _dataset_or_404(conn, dataset_uuid)
    if dataset["fhir_status"] == "completed":
        try:
            obj = MinioUploader().s3_client.get_object(Bucket=dataset["category"], Key=f"{dataset_uuid}/fhir.json")
            return json.load(obj["Body"])
        except ClientError:
            pass  # fall back to a rebuild
    descriptions = pipeline.load_annotation(conn, dataset_uuid)
    if descriptions is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No FHIR annotation for this dataset")
    descriptions = compute_endpoint_urls(descriptions, dataset_uuid, jobs.public_base())
    return build_fhir_json(pipeline.local_dataset(conn, dataset_uuid), descriptions)


@router.get("/files/{path:path}")
def get_file(dataset_uuid: str, path: str, conn=Depends(get_conn), _creds: dict = Depends(validate_credentials)):
    """Stream one object of the dataset from MinIO (the target of FHIR endpoint URLs)."""
    dataset = _dataset_or_404(conn, dataset_uuid)
    key = f"{dataset_uuid}/{path}"
    try:
        obj = MinioUploader().s3_client.get_object(Bucket=dataset["category"], Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {path}") from exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Storage unavailable") from exc

    headers = {"Cache-Control": "private, max-age=300"}
    if obj.get("ContentLength") is not None:
        headers["Content-Length"] = str(obj["ContentLength"])
    return StreamingResponse(
        obj["Body"].iter_chunks(chunk_size=64 * 1024),
        media_type=obj.get("ContentType") or mimetypes.guess_type(path)[0] or "application/octet-stream",
        headers=headers,
    )
