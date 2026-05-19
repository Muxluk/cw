from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.utils import run_command


def extract_audio(video_path: Path, wav_path: Path) -> tuple[bool, str]:
    cmd = [
    "ffmpeg", "-y", "-i", str(video_path),
    "-vn", "-ac", "1", "-ar", "16000",
    "-compression_level", "0",
    str(wav_path),
]
    completed = run_command(cmd)
    if completed.returncode == 0:
        return True, "audio extracted"
    return False, completed.stderr.strip()


def _transcribe_with_faster_whisper(audio_path: Path, model_name: str) -> list[dict[str, Any]] | None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(str(audio_path))
        return [
            {
                "start": round(s.start, 3),
                "end": round(s.end, 3),
                "text": s.text.strip(),
                "engine": "faster-whisper",
            }
            for s in segments
        ]
    except Exception:
        return None


def _transcribe_with_openai_whisper(audio_path: Path, model_name: str) -> list[dict[str, Any]] | None:
    try:
        import whisper
        model = whisper.load_model(model_name)
        result = model.transcribe(str(audio_path))
        return [
            {
                "start": round(seg["start"], 3),
                "end": round(seg["end"], 3),
                "text": seg["text"].strip(),
                "engine": "openai-whisper",
            }
            for seg in result.get("segments", [])
        ]
    except Exception:
        return None


def transcribe(video_path: Path, has_audio: bool, model_name: str, work_dir: Path) -> dict[str, Any]:
    if not has_audio:
        return {"engine": "none", "segments": [], "skipped": True, "message": "У відео не виявлено аудіодоріжку."}

    wav_path = work_dir / "audio.wav"
    ok, message = extract_audio(video_path, wav_path)
    if not ok:
        return {"engine": "none", "segments": [], "skipped": True, "message": f"Не вдалося витягти аудіо: {message}"}

    result = _transcribe_with_faster_whisper(wav_path, model_name)
    if result is not None:
        return {"engine": "faster-whisper", "segments": result, "skipped": False, "message": "Транскрипцію виконано."}

    result = _transcribe_with_openai_whisper(wav_path, model_name)
    if result is not None:
        return {"engine": "openai-whisper", "segments": result, "skipped": False, "message": "Транскрипцію виконано."}

    return {
        "engine": "unavailable",
        "segments": [],
        "skipped": True,
        "message": "Whisper-модуль не знайдено або модель не вдалося ініціалізувати.",
    }
