from __future__ import annotations

from pathlib import Path

from app.services.utils import run_command


def normalize_video(input_path: Path, output_path: Path) -> tuple[bool, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        "scale='min(854,iw)':-2:force_original_aspect_ratio=decrease",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "25",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(output_path),
    ]
    completed = run_command(cmd)
    if completed.returncode == 0:
        return True, "Конвертацію виконано успішно."

    fallback_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        "scale='min(854,iw)':-2:force_original_aspect_ratio=decrease",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "25",
        str(output_path),
    ]
    fallback = run_command(fallback_cmd)
    if fallback.returncode == 0:
        return True, "Конвертацію виконано без аудіодоріжки."

    return False, (completed.stderr or fallback.stderr or "FFmpeg conversion error").strip()
