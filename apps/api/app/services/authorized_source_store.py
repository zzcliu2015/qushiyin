import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.core.config import settings
from app.schemas.link import Platform
from app.schemas.source import AuthorizedSourceResponse
from app.services.platform_resolver import PlatformResolver
from app.services.source_fetcher import SourceVideoInfo


class AuthorizedSourceError(ValueError):
    pass


class AuthorizedSourceStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (settings.storage_root / "authorized-sources.json")
        self._lock = Lock()
        self._resolver = PlatformResolver()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(
        self,
        *,
        source_url: str,
        download_url: str,
        title: str | None,
    ) -> AuthorizedSourceResponse:
        parsed = self._resolver.parse(source_url)
        now = datetime.now(UTC)
        records = self._read_records()
        existing = next(
            (item for item in records if item["normalized_url"] == parsed.normalized_url),
            None,
        )

        if existing:
            existing.update(
                {
                    "download_url": download_url,
                    "title": title,
                    "updated_at": now.isoformat(),
                }
            )
            record = existing
        else:
            record = {
                "id": str(uuid4()),
                "platform": parsed.platform,
                "platform_label": parsed.platform_label,
                "source_url": source_url,
                "normalized_url": parsed.normalized_url,
                "download_url": download_url,
                "title": title,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            records.append(record)

        self._write_records(records)
        return self._to_response(record)

    def list(self) -> list[AuthorizedSourceResponse]:
        return [self._to_response(item) for item in self._read_records()]

    def resolve(self, *, platform: Platform, source_url: str) -> SourceVideoInfo | None:
        parsed = self._resolver.parse(source_url)
        if parsed.platform != platform:
            raise AuthorizedSourceError("链接平台和任务平台不一致。")

        for record in self._read_records():
            if record["normalized_url"] == parsed.normalized_url:
                return SourceVideoInfo(
                    download_url=record["download_url"],
                    title=record.get("title"),
                )

        return None

    def _read_records(self) -> list[dict[str, object]]:
        with self._lock:
            if not self.path.exists():
                return []
            text = self.path.read_text(encoding="utf-8")
            if not text.strip():
                return []
            data = json.loads(text)
            if not isinstance(data, list):
                raise AuthorizedSourceError("授权源登记文件格式错误。")
            return data

    def _write_records(self, records: list[dict[str, object]]) -> None:
        with self._lock:
            self.path.write_text(
                json.dumps(records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    @staticmethod
    def _to_response(record: dict[str, object]) -> AuthorizedSourceResponse:
        return AuthorizedSourceResponse(
            id=str(record["id"]),
            platform=record["platform"],
            platform_label=str(record["platform_label"]),
            source_url=str(record["source_url"]),
            normalized_url=str(record["normalized_url"]),
            download_url=str(record["download_url"]),
            title=str(record["title"]) if record.get("title") else None,
            created_at=datetime.fromisoformat(str(record["created_at"])),
            updated_at=datetime.fromisoformat(str(record["updated_at"])),
        )

