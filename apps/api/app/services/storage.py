from pathlib import Path


class StorageService:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.originals_dir = self.root / "originals"
        self.outputs_dir = self.root / "outputs"
        self.tmp_dir = self.root / "tmp"
        self.ensure_directories()

    def ensure_directories(self) -> None:
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def original_path(self, job_id: str, suffix: str = ".mp4") -> Path:
        safe_suffix = suffix if suffix.startswith(".") and len(suffix) <= 8 else ".mp4"
        job_dir = self.originals_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir / f"input{safe_suffix.lower()}"

    def output_path(self, job_id: str) -> Path:
        output_dir = self.outputs_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / "output.mp4"

    def existing_output_path(self, job_id: str) -> Path | None:
        path = self.outputs_dir / job_id / "output.mp4"
        return path if path.exists() else None
