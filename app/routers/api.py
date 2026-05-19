from __future__ import annotations

import threading

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import INPUT_DIR
from app.db import create_job, get_job
from app.schemas import JobResponse, URLRequest
from app.services.downloader import save_uploaded_file
from app.services.pipeline import process_job
from app.services.utils import ensure_dir, generate_job_id

router = APIRouter(prefix="/api", tags=["api"])


def _run_background(job_id: str) -> None:
    thread = threading.Thread(target=process_job, args=(job_id,), daemon=True)
    thread.start()


@router.post("/analyze/upload", response_model=JobResponse)
async def analyze_uploaded_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не вибрано.")
    job_id = generate_job_id()
    target_dir = ensure_dir(INPUT_DIR / job_id)
    data = await file.read()
    saved_path = save_uploaded_file(data, file.filename, target_dir)

    create_job({
        "id": job_id,
        "source_type": "upload",
        "source_value": str(saved_path),
        "status": "queued",
        "message": "Задачу поставлено в чергу.",
        "input_path": str(saved_path),
    })
    _run_background(job_id)
    return JobResponse(job_id=job_id, status="queued", message="Файл прийнято на обробку.")



@router.post("/analyze/gdrive", response_model=JobResponse)
async def analyze_google_drive_video(payload: URLRequest):
    job_id = generate_job_id()
    create_job({
        "id": job_id,
        "source_type": "gdrive",
        "source_value": payload.url,
        "status": "queued",
        "message": "Задачу поставлено в чергу.",
    })
    _run_background(job_id)
    return JobResponse(job_id=job_id, status="queued", message="Google Drive-посилання прийнято.")


@router.get("/jobs/{job_id}")
async def read_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задачу не знайдено.")
    return {
        "job_id": job["id"],
        "status": job["status"],
        "message": job["message"],
        "meta": job["meta_json"],
        "result_exists": bool(job["result_json"]),
    }


@router.get("/results/{job_id}")
async def read_result(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задачу не знайдено.")
    if not job["result_json"]:
        raise HTTPException(status_code=409, detail="Результат ще не готовий.")
    return job["result_json"]
