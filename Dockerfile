# Базовий образ: Python 3.11 (сумісний з torch, faster-whisper, TransNet V2)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # кеш моделей (Hugging Face / faster-whisper / torch) виносимо в окремий том
    HF_HOME=/models/hf \
    TORCH_HOME=/models/torch \
    XDG_CACHE_HOME=/models/cache

# Системні залежності: FFmpeg (разом з ffprobe) і бібліотеки для OpenCV/аудіо
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Спочатку CPU-версія PyTorch: стандартний пакет з PyPI тягне CUDA-збірку на кілька гігабайт
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Залежності встановлюємо окремим шаром, щоб кеш Docker працював при зміні коду
COPY requirements.txt .
RUN pip install -r requirements.txt

# Код застосунку
COPY app ./app
COPY run_local.py .

# Непривілейований користувач, каталоги для файлів і моделей
RUN useradd --create-home appuser \
    && mkdir -p /app/storage /models \
    && chown -R appuser:appuser /app /models
USER appuser

VOLUME ["/app/storage", "/models"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

# Без --reload: це продакшн-запуск, слухаємо на всіх інтерфейсах контейнера
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
