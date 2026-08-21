"""Pydantic models for assay-related requests."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AssayInputModel(BaseModel):
    name: str = ""
    category: str = ""
    dataset_uuid: str = ""
    sample_type: str = ""


class AssayOutputModel(BaseModel):
    name: str = ""
    category: str = ""
    dataset_name: str = ""
    sample_name: str = ""


class AssayDataModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    assay_uuid: Optional[str] = ""
    assay_seek_id: int
    workflow_seek_id: int
    cohort: List[str]
    ready: bool
    inputs: Optional[List[AssayInputModel]] = []
    outputs: Optional[List[AssayOutputModel]] = []
