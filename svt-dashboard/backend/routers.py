"""
routers/videos.py — 영상 목록 + 필터 API
routers/stats.py  — 통계·트렌딩 API

(두 라우터를 한 파일에 작성 후, 폴더 분리 시 잘라내기)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from database import get_db, rows_to_list

# ══════════════════════════════════════════════
#  videos 라우터
# ══════════════════════════════════════════════
videos_router = APIRouter(prefix="/videos", tags=["videos"])


@videos_router.get("/")
def get_videos(
    category: Optional[str] = Query(None, description="MV | 퍼포먼스 | 고잉세븐틴 | 비하인드 | 티저 | 라이브 | 기타"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    sort_by:   str           = Query("view_count", description="view_count | published_date | like_count | comment_count"),
    order:     str           = Query("desc", description="asc | desc"),
    limit:     int           = Query(50, le=200),
    offset:    int           = Query(0, ge=0),
):
    """영상 목록 — 카테고리·기간 필터 + 정렬 지원"""

    allowed_sort = {"view_count", "published_date", "like_count", "comment_count", "duration"}
    if sort_by not in allowed_sort:
        raise HTTPException(400, f"sort_by는 {allowed_sort} 중 하나여야 합니다")
    order_sql = "DESC" if order.lower() == "desc" else "ASC"

    where, params = [], []
    if category:
        where.append("video_type = ?")
        params.append(category)
    if date_from:
        where.append("published_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("published_date <= ?")
        params.append(date_to)

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    cur = conn.cursor()

    total = cur.execute(
        f"SELECT COUNT(*) FROM videos {where_clause}", params
    ).fetchone()[0]

    rows = cur.execute(
        f"""
        SELECT video_id, title, video_type, published_date, published_year,
               published_month, view_count, like_count, comment_count, duration, thumbnail
        FROM videos {where_clause}
        ORDER BY {sort_by} {order_sql}
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()
    conn.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": rows_to_list(rows),
    }


@videos_router.get("/categories")
def get_categories():
    """사용 가능한 카테고리 목록 + 영상 수"""
    conn = get_db()
    rows = conn.execute("""
        SELECT video_type, COUNT(*) as count
        FROM videos
        GROUP BY video_type
        ORDER BY count DESC
    """).fetchall()
    conn.close()
    return rows_to_list(rows)


@videos_router.get("/{video_id}")
def get_video(video_id: str):
    """영상 상세 + 조회수 히스토리"""
    conn = get_db()
    video = conn.execute(
        "SELECT * FROM videos WHERE video_id=?", (video_id,)
    ).fetchone()
    if not video:
        raise HTTPException(404, "영상을 찾을 수 없습니다")

    history = conn.execute(
        """
        SELECT view_count, like_count, snapshot_at
        FROM view_snapshots WHERE video_id=?
        ORDER BY snapshot_at ASC
        """,
        (video_id,),
    ).fetchall()
    conn.close()

    return {
        **dict(video),
        "view_history": rows_to_list(history),
    }


# ══════════════════════════════════════════════
#  stats 라우터
# ══════════════════════════════════════════════
stats_router = APIRouter(prefix="/stats", tags=["stats"])


@stats_router.get("/summary")
def get_summary():
    """채널 전체 요약 통계"""
    conn = get_db()

    meta = conn.execute("SELECT * FROM channel_meta ORDER BY id DESC LIMIT 1").fetchone()
    row = conn.execute("""
        SELECT
            COUNT(*)                                        AS total_videos,
            SUM(view_count)                                 AS total_views,
            SUM(like_count)                                 AS total_likes,
            AVG(view_count)                                 AS avg_views,
            AVG(CAST(like_count AS REAL)/NULLIF(view_count,0)*100) AS avg_like_rate,
            MAX(published_date)                             AS latest_video_date
        FROM videos
    """).fetchone()
    conn.close()

    return {
        **(dict(meta) if meta else {}),
        **dict(row),
    }


@stats_router.get("/by-category")
def get_stats_by_category(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
):
    """카테고리별 집계 통계"""
    where, params = [], []
    if date_from:
        where.append("published_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("published_date <= ?")
        params.append(date_to)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    rows = conn.execute(f"""
        SELECT
            video_type,
            COUNT(*)        AS count,
            SUM(view_count) AS total_views,
            AVG(view_count) AS avg_views,
            AVG(like_count) AS avg_likes
        FROM videos {where_clause}
        GROUP BY video_type
        ORDER BY total_views DESC
    """, params).fetchall()
    conn.close()
    return rows_to_list(rows)


@stats_router.get("/monthly")
def get_monthly_stats(
    category: Optional[str] = Query(None),
):
    """월별 업로드 수 + 총 조회수"""
    where, params = [], []
    if category:
        where.append("video_type = ?")
        params.append(category)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    rows = conn.execute(f"""
        SELECT
            published_year || '-' || printf('%02d', CAST(published_month AS INT)) AS year_month,
            COUNT(*)        AS upload_count,
            SUM(view_count) AS total_views,
            AVG(view_count) AS avg_views
        FROM videos {where_clause}
        GROUP BY year_month
        ORDER BY year_month ASC
    """, params).fetchall()
    conn.close()
    return rows_to_list(rows)


@stats_router.get("/trending")
def get_trending(
    top_n: int = Query(10, le=50, description="상위 N개"),
    spike_threshold: float = Query(200.0, description="급상승 기준 성장률(%)"),
):
    """
    급상승 영상 탐지
    - view_snapshots 테이블에 이전 스냅샷이 있는 영상만 대상
    - 성장률 = (현재 - 이전) / 이전 * 100
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT
            v.video_id, v.title, v.video_type, v.published_date,
            v.view_count, v.thumbnail,
            s.view_count AS prev_view_count,
            ROUND(
                CAST(v.view_count - s.view_count AS REAL)
                / NULLIF(s.view_count, 0) * 100, 2
            ) AS growth_rate
        FROM videos v
        JOIN (
            SELECT video_id, view_count
            FROM view_snapshots
            WHERE snapshot_at = (
                SELECT MAX(snapshot_at) FROM view_snapshots vs2
                WHERE vs2.video_id = view_snapshots.video_id
            )
        ) s ON v.video_id = s.video_id
        WHERE s.view_count > 0
        ORDER BY growth_rate DESC
        LIMIT ?
    """, (top_n,)).fetchall()
    conn.close()

    result = []
    for row in rows_to_list(rows):
        row["is_spike"] = (row.get("growth_rate") or 0) >= spike_threshold
        result.append(row)
    return result


@stats_router.get("/top-videos")
def get_top_videos(
    category: Optional[str] = Query(None),
    metric:   str           = Query("view_count", description="view_count | like_count | comment_count"),
    limit:    int           = Query(10, le=50),
):
    """카테고리별 Top 영상"""
    allowed = {"view_count", "like_count", "comment_count"}
    if metric not in allowed:
        raise HTTPException(400, f"metric은 {allowed} 중 하나여야 합니다")

    where, params = [], []
    if category:
        where.append("video_type = ?")
        params.append(category)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    rows = conn.execute(f"""
        SELECT video_id, title, video_type, published_date,
               view_count, like_count, comment_count, thumbnail
        FROM videos {where_clause}
        ORDER BY {metric} DESC
        LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return rows_to_list(rows)
