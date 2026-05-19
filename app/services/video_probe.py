from __future__ import annotations

import json
from pathlib import Path

import cv2

from app.services.utils import run_command


def ffprobe_streams(video_path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(video_path),
    ]
    completed = run_command(cmd)
    if completed.returncode != 0:
        return {"streams": [], "format": {}, "probe_error": completed.stderr.strip()}
    return json.loads(completed.stdout or "{}")


def can_open_with_opencv(video_path: Path) -> bool:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False
    ok, _frame = cap.read()
    cap.release()
    return bool(ok)

def _parse_fps(raw: str) -> float:
    try:
        num, den = raw.split("/")
        return float(num) / float(den) if float(den) else 0.0
    except Exception:
        return 0.0

def summarize_video(video_path: Path) -> dict:
    probe = ffprobe_streams(video_path)
    video_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    format_info = probe.get("format", {})
    return {
        "path": str(video_path),
        "container": format_info.get("format_name"),
        "duration": float(format_info.get("duration", 0.0) or 0.0),
        "size_bytes": int(format_info.get("size", 0) or 0),
        "video_codec": video_stream.get("codec_name"),
        "width": int(video_stream.get("width", 0) or 0),
        "height": int(video_stream.get("height", 0) or 0),
        "fps": _parse_fps(video_stream.get("avg_frame_rate", "0/0")),
        "has_audio": audio_stream is not None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "opencv_readable": can_open_with_opencv(video_path),
        "raw_probe": probe,
    }


def requires_normalization(meta: dict) -> bool:
    if not meta.get("opencv_readable"):
        return True
    if meta.get("video_codec") != "h264":
        return True
    if not str(meta.get("container", "")).startswith("mov,mp4") and "mp4" not in str(meta.get("container", "")):
        return True
    return False
