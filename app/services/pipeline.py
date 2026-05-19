from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.config import INPUT_DIR, NORMALIZED_DIR, RESULT_DIR, settings
from app.db import get_job, update_job
from app.services.converter import normalize_video
from app.services.downloader import download_from_google_drive
from app.services.merger import merge_results
from app.services.scene_detector import detect_scenes
from app.services.speech_to_text import transcribe
from app.services.utils import ensure_dir, save_json
from app.services.video_probe import requires_normalization, summarize_video


def process_job(job_id: str) -> None:
    job = get_job(job_id)
    if not job:
        return

    try:
        update_job(job_id, status="downloading", message="Отримання відео з джерела.")

        input_dir = ensure_dir(INPUT_DIR / job_id)
        normalized_dir = ensure_dir(NORMALIZED_DIR / job_id)
        result_dir = ensure_dir(RESULT_DIR / job_id)

        source_value = job["source_value"]
        if job["source_type"] == "gdrive":
            input_path = download_from_google_drive(source_value, input_dir)
        else:
            input_path = Path(source_value)

        update_job(job_id, input_path=str(input_path), status="probing", message="Аналіз метаданих відео.")

        meta = summarize_video(input_path)
        normalized_path = input_path

        if requires_normalization(meta):
            update_job(job_id, status="normalizing", message="Конвертація у сумісний формат H.264 MP4.")
            normalized_path = normalized_dir / "normalized.mp4"
            ok, message = normalize_video(input_path, normalized_path)
            if not ok:
                raise RuntimeError(f"Помилка конвертації: {message}")
            meta = summarize_video(normalized_path)

        meta.pop("raw_probe", None)

        update_job(
            job_id,
            normalized_path=str(normalized_path),
            meta_json=meta,
            status="processing",
            message="Визначення сцен та розпізнавання мовлення (паралельно).",
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_scenes = executor.submit(
                detect_scenes,
                normalized_path,
                meta.get("duration", 0.0),
                settings.scene_threshold,
                settings.min_scene_length,
            )
            future_transcript = executor.submit(
                transcribe,
                normalized_path,
                meta.get("has_audio", False),
                settings.whisper_model,
                result_dir,
            )

            scene_result = future_scenes.result()
            update_job(job_id, status="transcription", message="Сцени визначено. Очікування транскрипції.")

            transcript_result = future_transcript.result()

        merged = merge_results(
            meta=meta,
            scenes=scene_result["scenes"],
            transcript_segments=transcript_result["segments"],
        )

        result_payload = {
            "job_id": job_id,
            "meta": {
                **meta,
                "scene_engine": scene_result["engine"],
                "speech_engine": transcript_result["engine"],
            },
            "merged": merged,
            "notes": {
                "transcription_message": transcript_result["message"],
                "normalization_applied": str(normalized_path) != str(input_path),
            },
        }

        result_path = result_dir / "result.json"
        save_json(result_path, result_payload)

        update_job(
            job_id,
            status="done",
            message="Обробку завершено успішно.",
            result_path=str(result_path),
            result_json=result_payload,
        )

    except Exception as exc:
        update_job(job_id, status="failed", message=f"{type(exc).__name__}: {exc}")