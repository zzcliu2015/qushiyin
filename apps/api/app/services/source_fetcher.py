import ipaddress
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.schemas.link import Platform


class SourceFetchError(RuntimeError):
    pass


class SourceVideoInfo:
    def __init__(self, *, download_url: str, title: str | None = None) -> None:
        self.download_url = download_url
        self.title = title


class AuthorizedVideoSourceService:
    async def resolve(self, *, platform: Platform, source_url: str) -> SourceVideoInfo:
        if not settings.auth_source_api_base_url:
            raise SourceFetchError(
                "未配置授权视频源服务。请配置 AUTH_SOURCE_API_BASE_URL 和 AUTH_SOURCE_API_TOKEN，"
                "由授权服务返回可下载的视频源地址。"
            )

        endpoint = settings.auth_source_api_base_url.rstrip("/") + "/resolve"
        headers = {}
        if settings.auth_source_api_token:
            headers["Authorization"] = f"Bearer {settings.auth_source_api_token}"

        async with httpx.AsyncClient(timeout=settings.auth_source_timeout_seconds) as client:
            response = await client.post(
                endpoint,
                json={"platform": platform, "sourceUrl": source_url},
                headers=headers,
            )

        if response.status_code >= 400:
            raise SourceFetchError(f"授权视频源服务返回错误：HTTP {response.status_code}。")

        payload = response.json()
        download_url = payload.get("downloadUrl")
        if not isinstance(download_url, str) or not download_url:
            raise SourceFetchError("授权视频源服务未返回 downloadUrl。")

        self._validate_download_url(download_url)
        title = payload.get("title") if isinstance(payload.get("title"), str) else None
        return SourceVideoInfo(download_url=download_url, title=title)

    @staticmethod
    def _validate_download_url(download_url: str) -> None:
        parsed = urlparse(download_url)
        if parsed.scheme not in {"http", "https"}:
            raise SourceFetchError("授权视频源地址必须是 HTTP 或 HTTPS。")
        if not parsed.hostname:
            raise SourceFetchError("授权视频源地址缺少域名。")


class SourceVideoDownloader:
    allowed_content_types = {
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "application/octet-stream",
    }

    async def download(self, *, download_url: str, destination: Path) -> None:
        self._validate_public_url(download_url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        max_bytes = settings.max_source_video_mb * 1024 * 1024
        total = 0

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.auth_source_timeout_seconds, read=120)
        ) as client:
            async with client.stream("GET", download_url, follow_redirects=True) as response:
                if response.status_code >= 400:
                    raise SourceFetchError(f"视频源下载失败：HTTP {response.status_code}。")

                content_type = response.headers.get("content-type", "").split(";")[0].lower()
                if content_type and content_type not in self.allowed_content_types:
                    raise SourceFetchError(f"视频源类型不受支持：{content_type}。")

                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    raise SourceFetchError("视频源文件超过大小限制。")

                with destination.open("wb") as output:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > max_bytes:
                            destination.unlink(missing_ok=True)
                            raise SourceFetchError("视频源文件超过大小限制。")
                        output.write(chunk)

        if total == 0:
            destination.unlink(missing_ok=True)
            raise SourceFetchError("下载到的视频源为空。")

    @staticmethod
    def _validate_public_url(download_url: str) -> None:
        if settings.allow_private_source_urls:
            return

        parsed = urlparse(download_url)
        hostname = parsed.hostname
        if not hostname:
            raise SourceFetchError("视频源地址缺少域名。")

        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            return

        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise SourceFetchError("视频源地址不能指向内网、回环或保留地址。")

