from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from app.schemas.job import JobResponse, JobStatus
from app.schemas.link import ParseLinkResponse, Platform


class JobStoreError(ValueError):
    pass


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobResponse] = {}
        self._lock = Lock()

    def create(self, source_url: str, parsed: ParseLinkResponse) -> JobResponse:
        now = datetime.now(UTC)
        job = JobResponse(
            job_id=str(uuid4()),
            source_url=source_url,
            platform=parsed.platform,
            platform_label=parsed.platform_label,
            status="pending",
            progress=0,
            title=parsed.title,
            output_url=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> JobResponse:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise JobStoreError("任务不存在或已过期。")
        return job

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus,
        progress: int,
        output_url: str | None = None,
        error_message: str | None = None,
    ) -> JobResponse:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobStoreError("任务不存在或已过期。")

            updated = job.model_copy(
                update={
                    "status": status,
                    "progress": max(0, min(100, progress)),
                    "output_url": output_url if output_url is not None else job.output_url,
                    "error_message": error_message,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._jobs[job_id] = updated
            return updated


async def run_link_video_processing(
    store: JobStore,
    job_id: str,
    source_service: object,
    downloader: object,
    storage: object,
    processor: object,
) -> None:
    try:
        job = store.get(job_id)
        store.update(job_id, status="downloading", progress=10)
        source_info = await source_service.resolve(platform=job.platform, source_url=job.source_url)
        input_path = storage.original_path(job_id)
        await downloader.download(download_url=source_info.download_url, destination=input_path)
        output_path = storage.output_path(job_id)
        store.update(job_id, status="analyzing", progress=34)
        store.update(job_id, status="processing", progress=35)
        await processor.process(input_path=str(input_path), output_path=str(output_path))
        store.update(job_id, status="uploading", progress=92)
        store.update(
            job_id,
            status="completed",
            progress=100,
            output_url=f"/api/jobs/{job_id}/download",
        )
    except Exception as exc:  # noqa: BLE001 - surface worker failures to the job record.
        store.update(job_id, status="failed", progress=100, error_message=str(exc))
