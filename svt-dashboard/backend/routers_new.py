"""
routers_new.py — 재시청 지수 + 감성 분석 API
기존 routers.py 하단에 붙여넣기 하세요.
"""

from fastapi import APIRouter, Query
from typing import Optional
from database import get_db, rows_to_list

rewatch_router  = APIRouter(prefix="/rewatch",   tags=["rewatch"])
sentiment_router = APIRouter(prefix="/sentiment", tags=["sentiment"])


# ══════════════════════════════════════════════
#  재시청 지수 API
# ══════════════════════════════════════════════

@rewatch_router.get("/top")
def get_rewatch_top(
    limit:    int           = Query(10, le=50),
    category: Optional[str] = Query(None),
):
    """재시청 가능성 Top N 영상"""
    where, params = [], []
    if category:
        where.append("video_type = ?")
        params.append(category)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    rows = conn.execute(f"""
        SELECT
            v.video_id, v.title, v.video_type, v.published_date,
            v.view_count, v.like_count, v.comment_count,
            v.duration, v.thumbnail,
            r.rewatch_score, r.like_rate
        FROM videos v
        JOIN rewatch r ON v.video_id = r.video_id
        {where_clause}
        ORDER BY r.rewatch_score DESC
        LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return rows_to_list(rows)


# ══════════════════════════════════════════════
#  감성 분석 API
# ══════════════════════════════════════════════

@sentiment_router.get("/summary")
def get_sentiment_summary():
    """전체 댓글 감성 분포 요약"""
    conn = get_db()
    row = conn.execute("""
        SELECT
            COUNT(*)                                          AS total_comments,
            SUM(CASE WHEN sentiment_label='positive' THEN 1 ELSE 0 END) AS positive,
            SUM(CASE WHEN sentiment_label='negative' THEN 1 ELSE 0 END) AS negative,
            SUM(CASE WHEN sentiment_label='neutral'  THEN 1 ELSE 0 END) AS neutral,
            ROUND(AVG(sentiment_score), 3)                   AS avg_score
        FROM comments
    """).fetchone()
    conn.close()
    if not row:
        return {"message": "댓글 데이터 없음. comment_collector.py 먼저 실행하세요."}
    return dict(row)


@sentiment_router.get("/by-video")
def get_sentiment_by_video(
    limit:    int           = Query(10, le=50),
    order:    str           = Query("desc", description="desc=긍정순, asc=부정순"),
    category: Optional[str] = Query(None),
):
    """영상별 감성 집계 — 긍정률 기준 정렬"""
    order_sql = "DESC" if order == "desc" else "ASC"

    where, params = [], []
    if category:
        where.append("v.video_type = ?")
        params.append(category)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    rows = conn.execute(f"""
        SELECT
            s.video_id,
            v.title,
            v.video_type,
            v.thumbnail,
            s.total_comments,
            s.positive_count,
            s.negative_count,
            s.neutral_count,
            s.positive_rate,
            s.negative_rate,
            s.avg_score
        FROM video_sentiment s
        JOIN videos v ON s.video_id = v.video_id
        {where_clause}
        ORDER BY s.avg_score {order_sql}
        LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return rows_to_list(rows)


@sentiment_router.get("/timeline")
def get_sentiment_timeline(
    video_id: Optional[str] = Query(None, description="특정 영상 ID"),
):
    """댓글 감성 시계열 — 날짜별 평균 감성 점수"""
    where, params = [], []
    if video_id:
        where.append("video_id = ?")
        params.append(video_id)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    rows = conn.execute(f"""
        SELECT
            substr(published_at, 1, 10) AS date,
            COUNT(*)                    AS comment_count,
            ROUND(AVG(sentiment_score), 3) AS avg_score,
            SUM(CASE WHEN sentiment_label='positive' THEN 1 ELSE 0 END) AS positive,
            SUM(CASE WHEN sentiment_label='negative' THEN 1 ELSE 0 END) AS negative
        FROM comments
        {where_clause}
        GROUP BY date
        ORDER BY date ASC
    """, params).fetchall()
    conn.close()
    return rows_to_list(rows)
