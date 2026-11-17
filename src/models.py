from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class CreateLinkRequest(BaseModel):
    url: HttpUrl = Field(..., description="HTTP or HTTPS URL to shorten")


class LinkResponse(BaseModel):
    short_code: str
    original_url: str
    short_url: str
    created_at: datetime
    click_count: int


class AnalyticsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int
