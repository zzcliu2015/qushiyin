from fastapi import APIRouter, HTTPException, status

from app.schemas.source import AuthorizedSourceCreateRequest, AuthorizedSourceResponse
from app.services.authorized_source_store import AuthorizedSourceError, AuthorizedSourceStore

router = APIRouter()
source_store = AuthorizedSourceStore()


@router.get("", response_model=list[AuthorizedSourceResponse], response_model_by_alias=True)
def list_authorized_sources() -> list[AuthorizedSourceResponse]:
    return source_store.list()


@router.post(
    "",
    response_model=AuthorizedSourceResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def create_authorized_source(
    payload: AuthorizedSourceCreateRequest,
) -> AuthorizedSourceResponse:
    if not payload.confirmed_rights:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先确认该源视频为本人所有、已获授权，或平台允许下载和二次处理。",
        )

    try:
        return source_store.add(
            source_url=payload.source_url,
            download_url=str(payload.download_url),
            title=payload.title,
        )
    except (AuthorizedSourceError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

