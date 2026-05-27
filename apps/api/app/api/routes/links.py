from fastapi import APIRouter, HTTPException, status

from app.schemas.link import ParseLinkRequest, ParseLinkResponse
from app.services.platform_resolver import PlatformResolver, UnsupportedPlatformError

router = APIRouter()
resolver = PlatformResolver()


@router.post("/parse", response_model=ParseLinkResponse, response_model_by_alias=True)
def parse_link(payload: ParseLinkRequest) -> ParseLinkResponse:
    try:
        return resolver.parse(payload.url)
    except UnsupportedPlatformError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
