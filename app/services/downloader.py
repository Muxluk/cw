from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.services.utils import sanitize_filename


def _extract_google_drive_file_id(url: str) -> str | None:
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "id" in query:
        return query["id"][0]
    return None


def download_from_google_drive(url: str, target_dir: Path) -> Path:
    import requests
    target_dir.mkdir(parents=True, exist_ok=True)
    file_id = _extract_google_drive_file_id(url)
    if not file_id:
        raise ValueError("Неможливо визначити ідентифікатор файлу Google Drive.")
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    session = requests.Session()
    response = session.get(direct_url, stream=True, timeout=60)
    token = None
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            token = value
            break
    if token:
        response = session.get(direct_url, params={"confirm": token, "id": file_id}, stream=True, timeout=60)
    response.raise_for_status()
    filename = response.headers.get("Content-Disposition", "")
    name_match = re.search(r'filename="?([^"]+)"?', filename)
    filename = sanitize_filename(name_match.group(1) if name_match else f"{file_id}.mp4")
    out_path = target_dir / filename
    with open(out_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 512):
            if chunk:
                f.write(chunk)
    return out_path


def save_uploaded_file(upload_bytes: bytes, original_name: str, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(original_name)
    out_path = target_dir / safe_name
    out_path.write_bytes(upload_bytes)
    return out_path