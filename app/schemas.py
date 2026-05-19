from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class URLRequest(BaseModel):
    url: str = Field(..., min_length=5)


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class TimeSegment(BaseModel):
    start: float
    end: float
    label: str | None = None
    text: str | None = None
    score: float | None = None


class AnalyzeResult(BaseModel):
    job_id: str
    meta: dict[str, Any]
    scenes: list[dict[str, Any]]
    transcript: list[dict[str, Any]]
    merged: list[dict[str, Any]]
