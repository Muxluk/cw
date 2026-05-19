from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routers.api import router as api_router
from app.routers.pages import router as pages_router

app = FastAPI(title=settings.app_name)

init_db()
app.include_router(pages_router)
app.include_router(api_router)
