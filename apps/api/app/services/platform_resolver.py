from dataclasses import dataclass
import re
from urllib.parse import urlparse, urlunparse

from app.schemas.link import ParseLinkResponse, Platform


class UnsupportedPlatformError(ValueError):
    pass


@dataclass(frozen=True)
class PlatformRule:
    platform: Platform
    label: str
    domains: tuple[str, ...]


class PlatformResolver:
    url_pattern = re.compile(r"https?://[^\s]+")

    rules = (
        PlatformRule(
            platform="douyin",
            label="抖音",
            domains=("douyin.com", "iesdouyin.com", "amemv.com"),
        ),
        PlatformRule(
            platform="kuaishou",
            label="快手",
            domains=("kuaishou.com", "kuaishouapp.com", "gifshow.com"),
        ),
    )

    def parse(self, raw_url: str) -> ParseLinkResponse:
        normalized_url = self._normalize(raw_url)
        parsed = urlparse(normalized_url)
        hostname = (parsed.hostname or "").lower()

        rule = self._match_rule(hostname)
        if rule is None:
            raise UnsupportedPlatformError("当前仅支持抖音、快手公开视频链接。")

        return ParseLinkResponse(
            platform=rule.platform,
            platform_label=rule.label,
            normalized_url=normalized_url,
            title=None,
            cover_url=None,
            duration_ms=None,
            width=None,
            height=None,
            can_fetch_directly=False,
            requires_upload=False,
        )

    def _match_rule(self, hostname: str) -> PlatformRule | None:
        for rule in self.rules:
            if any(self._is_domain_or_subdomain(hostname, domain) for domain in rule.domains):
                return rule
        return None

    @staticmethod
    def _is_domain_or_subdomain(hostname: str, domain: str) -> bool:
        return hostname == domain or hostname.endswith(f".{domain}")

    @staticmethod
    def _normalize(raw_url: str) -> str:
        value = raw_url.strip()
        if not value:
            raise ValueError("请输入视频链接。")

        match = PlatformResolver.url_pattern.search(value)
        if match:
            value = match.group(0).rstrip("，,。.!！)）]")

        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("链接必须以 http:// 或 https:// 开头。")

        if not parsed.netloc:
            raise ValueError("链接缺少域名。")

        if parsed.username or parsed.password:
            raise ValueError("链接不能包含用户名或密码。")

        normalized = parsed._replace(fragment="")
        return urlunparse(normalized)
