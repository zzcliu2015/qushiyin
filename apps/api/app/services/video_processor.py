import asyncio
import os
import subprocess
from pathlib import Path

from app.core.config import settings


class VideoProcessingError(RuntimeError):
    pass


class VideoProcessor:
    def __init__(self, ffmpeg_binary: str | None = None) -> None:
        self.ffmpeg_binary = ffmpeg_binary or settings.ffmpeg_binary

    async def process(self, *, input_path: str, output_path: str) -> None:
        await asyncio.to_thread(self._process_sync, Path(input_path), Path(output_path))

    def _process_sync(self, input_path: Path, output_path: Path) -> None:
        if not input_path.exists():
            raise VideoProcessingError("原视频文件不存在。")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = self._resolve_ffmpeg()
        filter_complex = self._blur_filter()

        command = [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )

        if result.returncode != 0:
            message = result.stderr[-1200:] if result.stderr else "FFmpeg 处理失败。"
            raise VideoProcessingError(message.strip())

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise VideoProcessingError("FFmpeg 未生成有效输出文件。")

    def _resolve_ffmpeg(self) -> str:
        if self.ffmpeg_binary:
            return self.ffmpeg_binary

        path_ffmpeg = self._which("ffmpeg")
        if path_ffmpeg:
            return path_ffmpeg

        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:  # noqa: BLE001 - users need a clear setup error.
            raise VideoProcessingError("未找到 FFmpeg，请安装 FFmpeg 或配置 FFMPEG_BINARY。") from exc

    @staticmethod
    def _which(name: str) -> str | None:
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(directory) / name
            if candidate.exists():
                return str(candidate)

            exe_candidate = Path(directory) / f"{name}.exe"
            if exe_candidate.exists():
                return str(exe_candidate)

        return None

    @staticmethod
    def _blur_filter() -> str:
        top_w = "trunc(iw*0.34/2)*2"
        top_h = "trunc(ih*0.09/2)*2"
        bottom_w = "trunc(iw*0.36/2)*2"
        bottom_h = "trunc(ih*0.08/2)*2"
        bottom_x = "trunc(iw*0.64/2)*2"
        bottom_y = "trunc(ih*0.90/2)*2"
        overlay_x = "trunc(main_w*0.64/2)*2"
        overlay_y = "trunc(main_h*0.90/2)*2"

        return (
            f"[0:v]split=3[base][top_src][bottom_src];"
            f"[top_src]crop=w={top_w}:h={top_h}:x=0:y=0,boxblur=10:1[top_blur];"
            f"[bottom_src]crop=w={bottom_w}:h={bottom_h}:x={bottom_x}:y={bottom_y},"
            f"boxblur=10:1[bottom_blur];"
            f"[base][top_blur]overlay=0:0[tmp];"
            f"[tmp][bottom_blur]overlay=x={overlay_x}:y={overlay_y}[v]"
        )
