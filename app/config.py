from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Video Segmentation System"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    storage_dir: str = "storage"
    whisper_model: str = "small"
    scene_threshold: float = 0.45
    min_scene_length: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

ROOT_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = ROOT_DIR / settings.storage_dir
INPUT_DIR = STORAGE_DIR / "inputs"
NORMALIZED_DIR = STORAGE_DIR / "normalized"
RESULT_DIR = STORAGE_DIR / "results"
DB_PATH = STORAGE_DIR / "jobs.sqlite3"

for path in (STORAGE_DIR, INPUT_DIR, NORMALIZED_DIR, RESULT_DIR):
    path.mkdir(parents=True, exist_ok=True)
