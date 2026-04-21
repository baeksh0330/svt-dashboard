from fastapi import APIRouter, Query
from pathlib import Path
import json
import os
# print("현재 작업 디렉토리 : ", os.getcwd()) 파일 안 뜰때 이거 확인하기 
wordcloud_router = APIRouter(prefix="/wordcloud", tags=["wordcloud"])

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "going17_wordcloud.json"


def load_data():
    if not DATA_PATH.exists():
        return {"error": "no data"}
        # return None
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        # print('파일 있음.')
        return json.load(f)



def normalize_words(words):
    """value → normalized(0~100) 변환"""
    if not words:
        return []

    max_val = max(w["value"] for w in words) or 1

    return [
        {
            "text": w["text"],
            "value": w["value"],
            "normalized": round((w["value"] / max_val) * 100)
        }
        for w in words
    ]


# ─────────────────────────────
# 전체 워드클라우드
# ─────────────────────────────
@wordcloud_router.get("/all")
def get_all():
    data = load_data()
    if not data:
        return {"error": "no data"}

    word_map = {}

    for video in data.get("per_video", []):
        for w in video.get("words", []):
            word_map[w["text"]] = word_map.get(w["text"], 0) + w["value"]

    words = [{"text": k, "value": v} for k, v in word_map.items()]
    words = normalize_words(words)

    return {
        "total_comments": sum(w["value"] for w in words),
        "words": words
    }


# ─────────────────────────────
# 영상별 워드클라우드
# ─────────────────────────────
@wordcloud_router.get("/per-video")
def get_per_video(limit: int = Query(50, le=200)):
    data = load_data()
    if not data:
        return {"error": "no data"}

    result = []

    for v in data.get("per_video", [])[:limit]:
        words = normalize_words(v.get("words", []))

        result.append({
            "video_id": v.get("video_id"),
            "video_title": v.get("video_title"),
            "published_date": v.get("published_date"),
            "words": words
        })

    return result


# ─────────────────────────────
# 특정 영상 워드클라우드
# ─────────────────────────────
@wordcloud_router.get("/video/{video_id}")
def get_video(video_id: str):
    data = load_data()
    if not data:
        return {"error": "no data"}

    for v in data.get("per_video", []):
        if v.get("video_id") == video_id:
            return {
                "video_id": v.get("video_id"),
                "video_title": v.get("video_title"),
                "published_date": v.get("published_date"),
                "words": normalize_words(v.get("words", []))
            }

    return {"error": "not found"}