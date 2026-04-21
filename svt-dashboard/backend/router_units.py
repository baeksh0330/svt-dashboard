"""
router_units.py — 세븐틴 유닛 + 컴백 타임라인 API
===================================================
main.py에 추가:
  from router_units import units_router, timeline_router
  app.include_router(units_router)
  app.include_router(timeline_router)
"""

from fastapi import APIRouter, Query
from typing import Optional
from database import get_db, rows_to_list

units_router    = APIRouter(prefix="/units",    tags=["units"])
timeline_router = APIRouter(prefix="/timeline", tags=["timeline"])

# ─── 유닛 메타데이터 (하드코딩 — 공식 정보 기반) ────
UNIT_META = {
    # # 공식 유닛
    # "vocal": {
    #     "name_ko": "보컬팀",
    #     "name_en": "Vocal Unit",
    #     "type": "official",
    #     "color": "#6e9dc8",
    #     "members": ["정한", "조슈아", "우지", "도겸", "승관"],
    #     "description": "세븐틴 보컬 유닛. 감성적인 발라드와 R&B 계열 음악을 주로 선보임.",
    #     "debut": "2015-05-26",
    #     "keywords": ["vocal unit", "보컬팀", "vu"],
    # },
    # "performance": {
    #     "name_ko": "퍼포먼스팀",
    #     "name_en": "Performance Unit",
    #     "type": "official",
    #     "color": "#c8a96e",
    #     "members": ["호시", "준", "디에잇", "디노"],
    #     "description": "세븐틴 퍼포먼스 유닛. 강렬한 안무와 퍼포먼스 중심의 활동.",
    #     "debut": "2015-05-26",
    #     "keywords": ["performance unit", "퍼포먼스팀", "pu"],
    # },
    # "hiphop": {
    #     "name_ko": "힙합팀",
    #     "name_en": "Hip-hop Unit",
    #     "type": "official",
    #     "color": "#e8705a",
    #     "members": ["에스쿱스", "원우", "민규", "버논"],
    #     "description": "세븐틴 힙합 유닛. 랩과 프리스타일 중심의 활동.",
    #     "debut": "2015-05-26",
    #     "keywords": ["hip-hop unit", "hip hop unit", "힙합팀", "hu"],
    # },
    # 서브/프로젝트 유닛
        "Seventeen BSS": {
        "name_ko": "부석순",
        "name_en": "Hoshi x DK × Seungkwan (BSS)",
        "type": "sub",
        "color": "#7f0fc0",
        "members": ["호시", "도겸", "승관"],
        "description": "호시, 도겸, 승관의 서브 유닛.",
        "debut": "2018-03-21",
        "keywords": ["bss", "거침없이", "second wind", 'teleparty'],
    },
        
    "Seventeen JxW": {
        "name_ko": "정한x원우",
        "name_en": "Jeonghan × Wonwoo (JxW)",
        "type": "sub",
        "color": "#9d6ec8",
        "members": ["정한", "원우"],
        "description": "정한과 원우의 서브 유닛.",
        "debut": "2024-06-17",
        "keywords": ["jxw", "JEONGHAN X WONWOO", "정한 X 원우","this man", "last night", "어젯밤"],
    },
    "Seventeen HxW": {
        "name_ko": "호시×우지",
        "name_en": "Hoshi × Woozi (HxW)",
        "type": "sub",
        "color": "#6ec88a",
        "members": ["호시", "우지"],
        "description": "호시와 우지의 서브 유닛.",
        "debut": "2025-03-10",
        "keywords": ["hxw", "hoshi x woozi","96ers", "beam"],
    },
    "Seventeen CxM": {
        "name_ko": "에스쿱스×민규",
        "name_en": "S.coups × Mingyu (CxM)",
        "type": "sub",
        "color": "#c86e9d",
        "members": ["에스쿱스", "민규"],
        "description": "에스쿱스와 민규의 서브 유닛.",
        "debut": "2025-09-29",
        "keywords": ["cxm", "s.coups x mingyu", "hype vibes", 'double up'],
    },
    "Seventeen DxS": {
        "name_ko": "도겸×승관",
        "name_en": "The8 × Seungkwan (DxS)",
        "type": "sub",
        "color": "#c8c46e",
        "members": ["도겸", "승관"],
        "description": "도겸과 승관의 서브 유닛.",
        "debut": "2026-01-12",
        "keywords": ["dxs", "dk x seungkwan ","blue","소야곡"],
    },
}

# ─── 컴백 타임라인 데이터 (주요 앨범 기반) ──────────
COMEBACK_DATA = [
    {"date": "2015-05-29", "title": "17 CARAT",        "type": "comeback", "album_type": "미니",  "note": "데뷔 미니앨범"},
    {"date": "2015-10-19", "title": "Boys Be",          "type": "comeback", "album_type": "미니",  "note": "2nd 미니앨범"},
    {"date": "2016-04-25", "title": "Al1",              "type": "comeback", "album_type": "미니",  "note": "3rd 미니앨범"},
    {"date": "2016-10-04", "title": "Going Seventeen",  "type": "comeback", "album_type": "미니",  "note": "4th 미니앨범"},
    {"date": "2017-02-13", "title": "Al1 (재발매)",     "type": "comeback", "album_type": "리패키지", "note": ""},
    {"date": "2017-05-22", "title": "You Make My Dawn", "type": "comeback", "album_type": "미니",  "note": "5th 미니앨범"},
    {"date": "2018-04-09", "title": "You Make My Dawn", "type": "comeback", "album_type": "미니",  "note": "6th 미니앨범"},
    {"date": "2018-07-16", "title": "You Make My Dawn", "type": "comeback", "album_type": "리패키지", "note": ""},
    {"date": "2019-01-21", "title": "You Make My Dawn", "type": "comeback", "album_type": "미니",  "note": "7th 미니앨범"},
    {"date": "2019-09-16", "title": "An Ode",           "type": "comeback", "album_type": "정규",  "note": "3rd 정규앨범"},
    {"date": "2020-06-22", "title": "Heng:garæ",        "type": "comeback", "album_type": "미니",  "note": "8th 미니앨범"},
    {"date": "2021-04-05", "title": "Semicolon",        "type": "comeback", "album_type": "스페셜", "note": ""},
    {"date": "2021-06-18", "title": "Your Choice",      "type": "comeback", "album_type": "미니",  "note": "9th 미니앨범"},
    {"date": "2021-10-22", "title": "Attacca",          "type": "comeback", "album_type": "미니",  "note": "10th 미니앨범"},
    {"date": "2022-05-27", "title": "Face the Sun",     "type": "comeback", "album_type": "정규",  "note": "4th 정규앨범"},
    {"date": "2022-10-24", "title": "Sector 17",        "type": "comeback", "album_type": "리패키지", "note": ""},
    {"date": "2023-04-24", "title": "FML",              "type": "comeback", "album_type": "정규",  "note": "5th 정규앨범"},
    {"date": "2023-10-23", "title": "SPILL THE FEELS",  "type": "comeback", "album_type": "미니",  "note": "11th 미니앨범"},
    {"date": "2024-04-29", "title": "MAESTRO",          "type": "comeback", "album_type": "정규",  "note": "6th 정규앨범"},
    {"date": "2024-10-14", "title": "SPILL THE FEELS",  "type": "comeback", "album_type": "미니",  "note": "12th 미니앨범"},
]


# ══════════════════════════════════════════════
#  유닛 API
# ══════════════════════════════════════════════

@units_router.get("/")
def get_all_units():
    """모든 유닛 메타 + 관련 영상 수 요약"""
    conn = get_db()
    result = []

    for unit_id, meta in UNIT_META.items():
        # 키워드로 관련 영상 수 추출
        keyword_conditions = " OR ".join(
            [f"LOWER(title) LIKE '%{kw.lower()}%'" for kw in meta["keywords"]]
        )
        row = conn.execute(f"""
            SELECT
                COUNT(*)        AS video_count,
                SUM(view_count) AS total_views,
                MAX(published_date) AS latest_video
            FROM videos
            WHERE {keyword_conditions}
        """).fetchone()

        result.append({
            "unit_id":      unit_id,
            **meta,
            "video_count":  row["video_count"] if row else 0,
            "total_views":  row["total_views"]  if row else 0,
            "latest_video": row["latest_video"] if row else None,
        })

    conn.close()
    return result


@units_router.get("/{unit_id}/videos")
def get_unit_videos(
    unit_id: str,
    limit:   int = Query(20, le=100),
    sort_by: str = Query("published_date"),
    order:   str = Query("desc"),
):
    """유닛 관련 영상 목록"""
    if unit_id not in UNIT_META:
        from fastapi import HTTPException
        raise HTTPException(404, f"유닛 '{unit_id}' 없음")

    meta = UNIT_META[unit_id]
    order_sql = "DESC" if order == "desc" else "ASC"
    keyword_conditions = " OR ".join(
        [f"LOWER(title) LIKE '%{kw.lower()}%'" for kw in meta["keywords"]]
    )

    conn = get_db()
    rows = conn.execute(f"""
        SELECT video_id, title, video_type, published_date,
               view_count, like_count, comment_count, duration, thumbnail
        FROM videos
        WHERE {keyword_conditions}
        ORDER BY {sort_by} {order_sql}
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows_to_list(rows)


@units_router.get("/{unit_id}/stats")
def get_unit_stats(unit_id: str):
    """유닛 통계 — 연도별 조회수 추이"""
    if unit_id not in UNIT_META:
        from fastapi import HTTPException
        raise HTTPException(404, f"유닛 '{unit_id}' 없음")

    meta = UNIT_META[unit_id]
    keyword_conditions = " OR ".join(
        [f"LOWER(title) LIKE '%{kw.lower()}%'" for kw in meta["keywords"]]
    )

    conn = get_db()
    yearly = conn.execute(f"""
        SELECT
            published_year AS year,
            COUNT(*)        AS video_count,
            SUM(view_count) AS total_views,
            AVG(view_count) AS avg_views
        FROM videos
        WHERE {keyword_conditions}
        GROUP BY published_year
        ORDER BY published_year ASC
    """).fetchall()
    conn.close()

    return {
        "unit_id": unit_id,
        **UNIT_META[unit_id],
        "yearly": rows_to_list(yearly),
    }


# ══════════════════════════════════════════════
#  타임라인 API
# ══════════════════════════════════════════════

@timeline_router.get("/")
def get_timeline(
    type_filter: Optional[str] = Query(None, description="comeback | content | all"),
):
    """전체 활동 타임라인 — 컴백 + 자체 콘텐츠"""
    events = []

    # 컴백 이벤트 (하드코딩)
    for cb in COMEBACK_DATA:
        events.append({
            "date":       cb["date"],
            "year":       cb["date"][:4],
            "title":      cb["title"],
            "event_type": "comeback",
            "sub_type":   cb["album_type"],
            "note":       cb.get("note", ""),
            "view_count": None,
        })

    # 자체 콘텐츠 이벤트 (DB에서 주요 영상 추출) -> 제외 
    # conn = get_db()
    # content_rows = conn.execute("""
    #     SELECT
    #         published_date AS date,
    #         published_year AS year,
    #         title,
    #         video_type     AS sub_type,
    #         view_count,
    #         video_id,
    #         thumbnail
    #     FROM videos
    #     WHERE video_type IN ('고잉세븐틴','라이브','퍼포먼스')
    #       AND view_count > 1000000
    #     ORDER BY published_date ASC
    # """).fetchall()
    # conn.close()

    # for row in rows_to_list(content_rows):
    #     events.append({
    #         **row,
    #         "event_type": "content",
    #         "note": "",
    #     })

    # 날짜순 정렬
    events.sort(key=lambda x: x["date"])

    if type_filter and type_filter != "all":
        events = [e for e in events if e["event_type"] == type_filter]

    return events


@timeline_router.get("/years")
def get_timeline_years():
    """연도별 이벤트 수 요약"""
    conn = get_db()
    rows = conn.execute("""
        SELECT published_year AS year, COUNT(*) AS video_count,
               SUM(view_count) AS total_views
        FROM videos
        GROUP BY published_year
        ORDER BY published_year ASC
    """).fetchall()
    conn.close()

    year_data = {r["year"]: dict(r) for r in rows_to_list(rows)}

    comeback_by_year = {}
    for cb in COMEBACK_DATA:
        y = cb["date"][:4]
        comeback_by_year[y] = comeback_by_year.get(y, 0) + 1

    result = []
    all_years = sorted(set(list(year_data.keys()) + list(comeback_by_year.keys())))
    for y in all_years:
        result.append({
            "year":           y,
            "comeback_count": comeback_by_year.get(y, 0),
            "video_count":    year_data.get(y, {}).get("video_count", 0),
            "total_views":    year_data.get(y, {}).get("total_views", 0),
        })

    return result
