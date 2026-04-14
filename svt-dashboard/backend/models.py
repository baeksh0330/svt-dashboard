"""
models.py — Pydantic 스키마 + DB 테이블 정의
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─── API 응답 스키마 ─────────────────────────────────

class VideoOut(BaseModel):
    video_id: str
    title: str
    video_type: str
    published_date: str
    published_year: str
    published_month: str
    view_count: int
    like_count: int
    comment_count: int
    duration: float
    thumbnail: Optional[str] = None

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total_videos: int
    total_views: int
    total_likes: int
    avg_views: float
    avg_like_rate: float        # 좋아요율 (%)
    latest_video_date: str
    subscriber_count: int


class CategoryStatsOut(BaseModel):
    video_type: str
    count: int
    total_views: int
    avg_views: float
    avg_likes: float


class TrendingOut(BaseModel):
    video_id: str
    title: str
    video_type: str
    published_date: str
    view_count: int
    prev_view_count: int        # 이전 수집 시점 조회수
    growth_rate: float          # 성장률 (%)
    is_spike: bool              # 급상승 여부 (200% 이상)
    thumbnail: Optional[str] = None


class MonthlyStatsOut(BaseModel):
    year_month: str             # "2024-03"
    upload_count: int
    total_views: int
    avg_views: float


class ChannelMetaOut(BaseModel):
    title: str
    subscriber_count: int
    video_count: int
    view_count: int
    collected_at: str


# ─── 필터 파라미터 ───────────────────────────────────

class VideoFilter(BaseModel):
    category: Optional[str] = None      # MV, 퍼포먼스, 고잉세븐틴, ...
    date_from: Optional[str] = None     # "2023-01-01"
    date_to: Optional[str] = None       # "2024-12-31"
    sort_by: str = "view_count"         # view_count | published_date | like_count
    order: str = "desc"                 # asc | desc
    limit: int = 50
    offset: int = 0
