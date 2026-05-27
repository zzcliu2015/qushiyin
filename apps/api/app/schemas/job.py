from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.link import Platform

JobStatus = Literal[
    "pending",
    "downloading",
    "analyzing",
    "processing",
    "uploading",
    "completed",
    "failed",
    "expired",
]


class CreateJobRequest(BaseModel):
    source_url: HttpUrl = Field(serialization_alias="sourceUrl", validation_alias="sourceUrl")
    confirmed_rights: bool = Field(
        serialization_alias="confirmedRights",
        validation_alias="confirmedRights",
    )
    watermark_mode: Literal["auto"] = Field(
        default="auto",
        serialization_alias="watermarkMode",
        validation_alias="watermarkMode",
    )


class JobResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(serialization_alias="jobId")
    source_url: str = Field(serialization_alias="sourceUrl")
    platform: Platform
    platform_label: str = Field(serialization_alias="platformLabel")
    status: JobStatus
    progress: int
    title: str | None = None
    output_url: str | None = Field(default=None, serialization_alias="outputUrl")
    error_message: str | None = Field(default=None, serialization_alias="errorMessage")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
