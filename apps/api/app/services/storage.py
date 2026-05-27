from pathlib import Path

from fastapi import UploadFile


class StorageError(ValueError):
    pass


class StorageService:
    allowed_suffixes = {".mp4", ".mov", ".m4v", ".webm"}

    def __init__(self, root: Path, max_upload_mb: int) -> None:
        self.root = root
        self.max_upload_bytes = max_upload_mb * 1024 * 1024
        self.originals_dir = self.root / "originals"
        self.outputs_dir = self.root / "outputs"
        self.tmp_dir = self.root / "tmp"
        self.ensure_directories()

    def ensure_directories(self) -> None:
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, job_id: str, file: UploadFile) -> Path:
        filename = file.filename or "video.mp4"
        suffix = Path(filename).suffix.lower()
        if suffix not in self.allowed_suffixes:
            allowed = ", ".join(sorted(self.allowed_suffixes))
            raise StorageError(f"仅支持这些视频格式：{allowed}。")

        job_dir = self.originals_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        destination = job_dir / f"input{suffix}"

        total = 0
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > self.max_upload_bytes:
                    destination.unlink(missing_ok=True)
                    raise StorageError("上传视频超过大小限制。")
                output.write(chunk)

        if total == 0:
            destination.unlink(missing_ok=True)
            raise StorageError("上传文件为空。")

        return destination

    def output_path(self, job_id: str) -> Path:
        output_dir = self.outputs_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / "output.mp4"

    def existing_output_path(self, job_id: str) -> Path | None:
        path = self.outputs_dir / job_id / "output.mp4"
        return path if path.exists() else None

