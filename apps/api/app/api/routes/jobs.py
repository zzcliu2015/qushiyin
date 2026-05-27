import json

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import ValidationError

from app.schemas.job import CreateJobRequest, JobResponse
from app.schemas.watermark import WatermarkRegion
from app.services.job_store import JobStore, JobStoreError, run_mock_processing, run_video_processing
from app.services.platform_resolver import PlatformResolver, UnsupportedPlatformError
from app.services.storage import StorageError, StorageService
from app.services.video_processor import VideoProcessor
from app.core.config import settings

router = APIRouter()
resolver = PlatformResolver()
job_store = JobStore()
storage = StorageService(root=settings.storage_root, max_upload_mb=settings.max_upload_mb)
video_processor = VideoProcessor()


@router.post(
    "",
    response_model=JobResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def create_job(payload: CreateJobRequest, background_tasks: BackgroundTasks) -> JobResponse:
    if not payload.confirmed_rights:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先确认该视频为本人所有、已获授权，或平台允许下载和二次处理。",
        )

    try:
        parsed = resolver.parse(str(payload.source_url))
    except UnsupportedPlatformError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    job = job_store.create(source_url=parsed.normalized_url, parsed=parsed)
    background_tasks.add_task(run_mock_processing, job_store, job.job_id)
    return job


@router.post(
    "/upload",
    response_model=JobResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    platform: str = Form(...),
    confirmed_rights: bool = Form(...),
    watermark_regions: str | None = Form(default=None),
) -> JobResponse:
    if platform not in {"douyin", "kuaishou"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="平台仅支持抖音或快手。")

    if not confirmed_rights:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先确认该视频为本人所有、已获授权，或平台允许下载和二次处理。",
        )

    job = job_store.create_upload(original_filename=file.filename or "video.mp4", platform=platform)

    try:
        regions = parse_watermark_regions(watermark_regions)
        input_path = await storage.save_upload(job.job_id, file)
    except StorageError as exc:
        job_store.update(job.job_id, status="failed", progress=100, error_message=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        job_store.update(job.job_id, status="failed", progress=100, error_message=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    output_path = storage.output_path(job.job_id)
    background_tasks.add_task(
        run_video_processing,
        job_store,
        job.job_id,
        str(input_path),
        str(output_path),
        video_processor,
        regions,
    )
    return job


@router.get("/{job_id}", response_model=JobResponse, response_model_by_alias=True)
def get_job(job_id: str) -> JobResponse:
    try:
        return job_store.get(job_id)
    except JobStoreError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{job_id}/download", response_model=None)
def download_job(job_id: str) -> FileResponse | PlainTextResponse:
    try:
        job = job_store.get(job_id)
    except JobStoreError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if job.status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="任务尚未完成。")

    output_path = storage.existing_output_path(job_id)
    if output_path is not None:
        return FileResponse(
            output_path,
            media_type="video/mp4",
            filename=f"{job_id}.mp4",
        )

    return PlainTextResponse(
        content="链接任务当前仍为占位结果；真实链接下载将在授权获取模块接入后启用。\n",
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.job_id}.txt"'},
    )


def parse_watermark_regions(raw_regions: str | None) -> list[WatermarkRegion] | None:
    if not raw_regions:
        return None

    try:
        payload = json.loads(raw_regions)
    except json.JSONDecodeError as exc:
        raise ValueError("水印区域参数不是有效 JSON。") from exc

    if not isinstance(payload, list):
        raise ValueError("水印区域参数必须是数组。")

    if len(payload) > 5:
        raise ValueError("最多支持 5 个水印区域。")

    try:
        regions = [WatermarkRegion.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError("水印区域参数不合法。") from exc

    return regions or None
