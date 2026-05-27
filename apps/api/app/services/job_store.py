import asyncio
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from app.schemas.job import JobResponse, JobStatus
from app.schemas.link import ParseLinkResponse, Platform
from app.schemas.watermark import WatermarkRegion


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

    def create_upload(self, *, original_filename: str, platform: Platform) -> JobResponse:
        now = datetime.now(UTC)
        platform_label = "抖音" if platform == "douyin" else "快手"
        job = JobResponse(
            job_id=str(uuid4()),
            source_url=f"upload://{original_filename}",
            platform=platform,
            platform_label=platform_label,
            status="pending",
            progress=0,
            title=original_filename,
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


async def run_mock_processing(store: JobStore, job_id: str) -> None:
    steps: tuple[tuple[JobStatus, int, float], ...] = (
        ("downloading", 18, 0.8),
        ("analyzing", 42, 0.9),
        ("processing", 74, 1.1),
        ("uploading", 92, 0.7),
        ("completed", 100, 0.2),
    )

    for status, progress, delay in steps:
        await asyncio.sleep(delay)
        output_url = f"/api/jobs/{job_id}/download" if status == "completed" else None
        store.update(job_id, status=status, progress=progress, output_url=output_url)


async def run_video_processing(
    store: JobStore,
    job_id: str,
    input_path: str,
    output_path: str,
    processor: object,
    regions: list[WatermarkRegion] | None = None,
) -> None:
    try:
        store.update(job_id, status="analyzing", progress=12)
        await asyncio.sleep(0.1)
        store.update(job_id, status="processing", progress=35)
        await processor.process(input_path=input_path, output_path=output_path, regions=regions)
        store.update(job_id, status="uploading", progress=92)
        await asyncio.sleep(0.1)
        store.update(
            job_id,
            status="completed",
            progress=100,
            output_url=f"/api/jobs/{job_id}/download",
        )
    except Exception as exc:  # noqa: BLE001 - surface worker failures to the job record.
        store.update(job_id, status="failed", progress=100, error_message=str(exc))
