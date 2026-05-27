from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

Platform = Literal["douyin", "kuaishou"]


class ParseLinkRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class ParseLinkResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    platform: Platform
    platform_label: str = Field(serialization_alias="platformLabel")
    normalized_url: str = Field(serialization_alias="normalizedUrl")
    title: str | None = None
    cover_url: HttpUrl | None = Field(default=None, serialization_alias="coverUrl")
    duration_ms: int | None = Field(default=None, serialization_alias="durationMs")
    width: int | None = None
    height: int | None = None
    can_fetch_directly: bool = Field(serialization_alias="canFetchDirectly")
    requires_upload: bool = Field(serialization_alias="requiresUpload")

