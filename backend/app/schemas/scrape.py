"""
Schémas Pydantic : requêtes de scraping.
"""
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ScrapeRequest(BaseModel):
    url: HttpUrl
    platform: Literal["taobao", "pinduoduo", "alibaba", "1688", "auto"] = "auto"
    fetch_reviews: bool = True
    max_reviews: int = Field(default=20, ge=0, le=200)


class ScrapeResult(BaseModel):
    success: bool
    product_id: str | None = None
    message: str
    data: dict | None = None
