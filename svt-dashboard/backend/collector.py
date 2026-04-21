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
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.environ.get("YOUTUBE_API_KEY") or "API_key_없음" # 제대로 받고 있음

if not API_KEY or API_KEY == "API_key_없음":
    print("[오류] YOUTUBE_API_KEY 환경변수가 설정되지 않았습니다.")
    sys.exit(1)

# MV는 HYBE 채널 공동업로드이므로 반드시 포함해야 집계됨
CHANNELS = {
    "seventeen_official": "UCfkXDY7vwkcJ8ddFGz8KusA",  # 세븐틴 공식
    "hybe_labels":        "UC3IZKseVpdzPSBaWxBxundA",  # HYBE Labels (MV 공동업로드)
    "seventeen_japan":    "UCpbTKp4B80rE2zHWvQvZpvA",  # 세븐틴 일본 공식
}

# HYBE 채널에서 세븐틴 관련 영상만 필터링
SVT_KEYWORDS = [
    "seventeen", "세븐틴", "svt",
    "s.coups", "jeonghan", "joshua", "jun", "hoshi",
    "wonwoo", "woozi", "the8", "mingyu", "dk", "seungkwan", "vernon", "dino",
]

BASE_DIR   = Path(__file__).parent
youtube = build("youtube", "v3", developerKey=API_KEY)


def classify_video_type(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["mv", "m/v", "music video"]):                return "MV"
    if any(k in t for k in ["live", "concert", "tour", "inside"]):       return "INSIDE SEVENTEEN"
    if any(k in t for k in ["performance", "choreography", "dance"]):    return "퍼포먼스"
    if any(k in t for k in ["going"]):                                   return "고잉세븐틴"
    if any(k in t for k in ["teaser", "highlight"]):                     return "티저"
    if any(k in t for k in ["record"]):                                  return "SVT Record"
    if any(k in t for k in ["브이로그", "하니왔쫑",
                            "위클리 호시", "every wonwoo"]):               return "브이로그"
    if any(k in t for k in ["snapshoot"]):                               return "SNAPSHOOT"
    if any(k in t for k in ["interview", "인터뷰"]):                      return "인터뷰"
    if any(k in t for k in ["cover", "원곡"]):                            return "커버"
    if any(k in t for k in ["s.coups", "jeonghan", "joshua",
                            "jun", "hoshi", "wonwoo", "woozi",
                            "the 8", "mingyu", 'dk',
                            'seungkwan', 'vernon', 'dino']):             return "솔로"
    if any(k in t for k in ["응원법"]):                                   return "응원법"
    if any(k in t for k in ["챌린지"]):                                   return "챌린지"
    return "기타(릴스)"


def parse_duration(s: str) -> float:
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    if not m: return 0
    return int(m.group(1) or 0)*60 + int(m.group(2) or 0) + int(m.group(3) or 0)/60


# 채널정보 가져오기 
def get_channel_info(channel_id: str) -> dict:
    res = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=channel_id
    ).execute()
    if not res.get("items"):
        return {}
    ch = res["items"][0]
    return {
        "title":               ch["snippet"]["title"],
        "subscriber_count":    int(ch["statistics"].get("subscriberCount", 0)),
        "video_count":         int(ch["statistics"].get("videoCount", 0)),
        "view_count":          int(ch["statistics"].get("viewCount", 0)),
        "uploads_playlist_id": ch["contentDetails"]["relatedPlaylists"]["uploads"],
        "collected_at":        datetime.now().isoformat(),
    }

def get_all_video_ids(playlist_id: str, max_videos: int = 3000): #수집 개수 
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


def get_video_details(video_ids: list, source_channel: str = "") -> list:
    records = []
    batches = [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]
    for batch in batches:
        res = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch)
        ).execute()
        for v in res["items"]:
            sn, st = v["snippet"], v.get("statistics", {})
            title  = sn["title"]
 
            # HYBE 채널은 세븐틴 관련 영상만 포함
            if source_channel == "hybe_labels":
                title_lower = title.lower()
                if not any(kw in title_lower for kw in SVT_KEYWORDS):
                    continue
 
            records.append({
                "video_id":       v["id"],
                "title":          title,
                "video_type":     classify_video_type(title),
                "source_channel": source_channel,          # 출처 채널 기록
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
    return records


if __name__ == "__main__":
    print(f"[수집 시작] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[대상 채널] {len(CHANNELS)}개 — 세븐틴 공식 + HYBE + 일본 공식\n")
 
    all_records = []
    main_meta   = None
 
    for ch_key, ch_id in CHANNELS.items():
        print(f"[{ch_key}] 채널 정보 수집 중...")
        meta = get_channel_info(ch_id)
        if not meta:
            print(f"  → 채널 정보 없음, 스킵")
            continue
 
        print(f"  채널명: {meta['title']}")
        print(f"  구독자: {meta['subscriber_count']:,}")
 
        # 메인 메타는 세븐틴 공식 채널 기준
        if ch_key == "seventeen_official":
            main_meta = meta
 
        ids = get_all_video_ids(meta["uploads_playlist_id"])
        print(f"  영상 ID: {len(ids)}개 수집")
 
        records = get_video_details(ids, source_channel=ch_key)
        print(f"  상세 수집: {len(records)}개 (SVT 필터 적용됨)\n")
        all_records.extend(records)
 
    # ── 중복 제거: 같은 video_id가 여러 채널에 있을 경우 첫 번째 유지
    df = pd.DataFrame(all_records)
    before = len(df)
    df = df.drop_duplicates(subset="video_id", keep="first")
    after = len(df)
    df = df.sort_values("published_date", ascending=False).reset_index(drop=True)
 
    print(f"[병합 완료] 전체 {before}개 → 중복 제거 후 {after}개")
    print(f"[채널별 영상 수]\n{df['source_channel'].value_counts().to_string()}\n")
    print(f"[영상 타입별 수]\n{df['video_type'].value_counts().to_string()}\n")
 
    # ── 저장
    df.to_csv(BASE_DIR / "seventeen_youtube.csv", index=False, encoding="utf-8-sig")
    print("저장: seventeen_youtube.csv")
 
    if main_meta:
        with open(BASE_DIR / "seventeen_youtube_meta.json", "w", encoding="utf-8") as f:
            json.dump(main_meta, f, ensure_ascii=False, indent=2)
        print("저장: seventeen_youtube_meta.json")
 
    print(f"\n[완료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("[다음 단계] python database.py 실행 → DB 업데이트")
    print("[다음 단계] uvicorn main:app --reload 로 서버 재시작")