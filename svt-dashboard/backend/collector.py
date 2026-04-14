"""
collector.py — GitHub Actions용 수집 스크립트
================================================
로컬: API_KEY를 직접 입력하거나 .env 파일 사용
배포: GitHub Secrets → 환경변수 YOUTUBE_API_KEY 자동 주입
"""

import os
import sys
import time
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from googleapiclient.discovery import build

# ─── API 키: 환경변수 우선, 없으면 직접 입력 ────────
API_KEY = os.environ.get("YOUTUBE_API_KEY") or "여기에_API_KEY_입력"

if not API_KEY or API_KEY == "여기에_API_KEY_입력":
    print("[오류] YOUTUBE_API_KEY 환경변수가 설정되지 않았습니다.")
    sys.exit(1)

CHANNEL_ID = "UC-dkYN_rjr48s0xNg8a6EXg"  # 세븐틴 공식
BASE_DIR   = Path(__file__).parent

youtube = build("youtube", "v3", developerKey=API_KEY)


def classify_video_type(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["mv", "m/v", "music video"]):           return "MV"
    if any(k in t for k in ["performance", "choreography", "dance"]): return "퍼포먼스"
    if any(k in t for k in ["going seventeen", "going svt"]):         return "고잉세븐틴"
    if any(k in t for k in ["behind", "making", "비하인드"]):          return "비하인드"
    if any(k in t for k in ["teaser", "highlight"]):                  return "티저"
    if any(k in t for k in ["live", "concert", "tour"]):              return "라이브"
    if any(k in t for k in ["interview", "인터뷰"]):                   return "인터뷰"
    if any(k in t for k in ["cover", "reaction"]):                    return "커버"
    return "기타"


def parse_duration(s: str) -> float:
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    if not m: return 0
    return int(m.group(1) or 0)*60 + int(m.group(2) or 0) + int(m.group(3) or 0)/60


def get_channel_info():
    res = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=CHANNEL_ID
    ).execute()
    ch = res["items"][0]
    return {
        "title":            ch["snippet"]["title"],
        "subscriber_count": int(ch["statistics"].get("subscriberCount", 0)),
        "video_count":      int(ch["statistics"].get("videoCount", 0)),
        "view_count":       int(ch["statistics"].get("viewCount", 0)),
        "uploads_playlist_id": ch["contentDetails"]["relatedPlaylists"]["uploads"],
        "collected_at":     datetime.now().isoformat(),
    }


def get_all_video_ids(playlist_id: str, max_videos: int = 500):
    ids, token = [], None
    while len(ids) < max_videos:
        res = youtube.playlistItems().list(
            part="contentDetails", playlistId=playlist_id,
            maxResults=50, pageToken=token
        ).execute()
        ids += [i["contentDetails"]["videoId"] for i in res["items"]]
        token = res.get("nextPageToken")
        if not token: break
        time.sleep(0.2)
    return ids


def get_video_details(video_ids: list):
    records = []
    for batch in [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]:
        res = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch)
        ).execute()
        for v in res["items"]:
            sn, st = v["snippet"], v.get("statistics", {})
            records.append({
                "video_id":       v["id"],
                "title":          sn["title"],
                "video_type":     classify_video_type(sn["title"]),
                "published_at":   sn["publishedAt"],
                "published_date": sn["publishedAt"][:10],
                "published_year": sn["publishedAt"][:4],
                "published_month":sn["publishedAt"][5:7],
                "view_count":     int(st.get("viewCount", 0)),
                "like_count":     int(st.get("likeCount", 0)),
                "comment_count":  int(st.get("commentCount", 0)),
                "duration":       parse_duration(v["contentDetails"]["duration"]),
                "thumbnail":      sn["thumbnails"].get("high", {}).get("url", ""),
            })
        time.sleep(0.1)
    return pd.DataFrame(records)


if __name__ == "__main__":
    print(f"[수집 시작] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    meta = get_channel_info()
    print(f"[채널] {meta['title']} — 구독자 {meta['subscriber_count']:,}")

    ids = get_all_video_ids(meta["uploads_playlist_id"])
    print(f"[영상 ID] {len(ids)}개")

    df = get_video_details(ids)
    print(f"[상세 수집] {len(df)}개")

    df.to_csv(BASE_DIR / "seventeen_youtube.csv", index=False, encoding="utf-8-sig")
    with open(BASE_DIR / "seventeen_youtube_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[완료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
