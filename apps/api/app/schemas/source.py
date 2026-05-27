from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.link import Platform


class AuthorizedSourceCreateRequest(BaseModel):
    source_url: str = Field(validation_alias="sourceUrl", min_length=8, max_length=2048)
    download_url: HttpUrl = Field(validation_alias="downloadUrl")
    title: str | None = Field(default=None, max_length=200)
    confirmed_rights: bool = Field(validation_alias="confirmedRights")


class AuthorizedSourceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    platform: Platform
    platform_label: str = Field(serialization_alias="platformLabel")
    source_url: str = Field(serialization_alias="sourceUrl")
    normalized_url: str = Field(serialization_alias="normalizedUrl")
    download_url: str = Field(serialization_alias="downloadUrl")
    title: str | None = None
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")

