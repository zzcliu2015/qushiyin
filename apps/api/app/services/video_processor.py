import asyncio
import os
import subprocess
from pathlib import Path
from typing import TypedDict

from app.core.config import settings


class BlurRegion(TypedDict):
    x: float
    y: float
    width: float
    height: float


class VideoProcessingError(RuntimeError):
    pass


class VideoProcessor:
    def __init__(self, ffmpeg_binary: str | None = None) -> None:
        self.ffmpeg_binary = ffmpeg_binary or settings.ffmpeg_binary

    async def process(self, *, input_path: str, output_path: str) -> None:
        await asyncio.to_thread(
            self._process_sync,
            Path(input_path),
            Path(output_path),
        )

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

    def _blur_filter(self) -> str:
        normalized_regions = self._default_regions()
        split_count = len(normalized_regions) + 1
        labels = "[base]" + "".join(f"[wm_src_{index}]" for index in range(len(normalized_regions)))
        parts = [f"[0:v]split={split_count}{labels};"]
        current_label = "base"

        for index, region in enumerate(normalized_regions):
            crop_w = self._dimension_expr("iw", region["width"])
            crop_h = self._dimension_expr("ih", region["height"])
            crop_x = self._position_expr("iw", region["x"])
            crop_y = self._position_expr("ih", region["y"])
            overlay_x = self._position_expr("main_w", region["x"])
            overlay_y = self._position_expr("main_h", region["y"])
            blur_label = f"wm_blur_{index}"
            next_label = "v" if index == len(normalized_regions) - 1 else f"tmp_{index}"

            parts.append(
                f"[wm_src_{index}]crop=w={crop_w}:h={crop_h}:x={crop_x}:y={crop_y},"
                f"boxblur=10:1[{blur_label}];"
            )
            parts.append(
                f"[{current_label}][{blur_label}]overlay=x={overlay_x}:y={overlay_y}[{next_label}]"
            )
            if index != len(normalized_regions) - 1:
                parts.append(";")
            current_label = next_label

        return "".join(parts)

    @staticmethod
    def _default_regions() -> list[BlurRegion]:
        return [
            {"x": 0, "y": 0, "width": 0.34, "height": 0.09},
            {"x": 0.64, "y": 0.90, "width": 0.36, "height": 0.08},
        ]

    @staticmethod
    def _dimension_expr(axis: str, ratio: float) -> str:
        return f"trunc({axis}*{ratio:.6f}/2)*2"

    @staticmethod
    def _position_expr(axis: str, ratio: float) -> str:
        return f"trunc({axis}*{ratio:.6f}/2)*2"
