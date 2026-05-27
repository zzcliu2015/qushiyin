from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse

from app.schemas.job import CreateJobRequest, JobResponse
from app.services.authorized_source_store import AuthorizedSourceStore
from app.services.job_store import JobStore, JobStoreError, run_link_video_processing
from app.services.platform_resolver import PlatformResolver, UnsupportedPlatformError
from app.services.source_fetcher import AuthorizedVideoSourceService, SourceVideoDownloader
from app.services.storage import StorageService
from app.services.video_processor import VideoProcessor
from app.core.config import settings

router = APIRouter()
resolver = PlatformResolver()
job_store = JobStore()
storage = StorageService(root=settings.storage_root)
video_processor = VideoProcessor()
source_service = AuthorizedVideoSourceService()
source_downloader = SourceVideoDownloader()
authorized_source_store = AuthorizedSourceStore()


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
    background_tasks.add_task(
        run_link_video_processing,
        job_store,
        job.job_id,
        authorized_source_store,
        source_service,
        source_downloader,
        storage,
        video_processor,
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
        content="未找到处理后的视频文件。\n",
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.job_id}.txt"'},
    )
