"""
세븐틴 YouTube 데이터 수집 스크립트
=====================================
필요한 패키지: pip install google-api-python-client pandas

YouTube Data API v3 키 발급:
  1. https://console.cloud.google.com 접속
  2. 새 프로젝트 생성
  3. "YouTube Data API v3" 검색 후 활성화
  4. 사용자 인증 정보 → API 키 생성
"""

from googleapiclient.discovery import build
import pandas as pd
import json
import time
from datetime import datetime

# ─── 설정 ───────────────────────────────────────────
import os
from dotenv import load_dotenv
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
API_KEY = YOUTUBE_API_KEY

# 세븐틴 공식 채널 ID
SEVENTEEN_CHANNEL_ID = "UCfkXDY7vwkcJ8ddFGz8KusA"  # 세븐틴 공식 채널
HYBE_CHANNEL_ID = "UC3IZKseVpdzPSBaWxBxundA"     # 하이브 공식 채널

# 분석할 채널 선택
TARGET_CHANNEL_ID = SEVENTEEN_CHANNEL_ID

youtube = build("youtube", "v3", developerKey=API_KEY)


# ─── 1. 채널 기본 정보 ──────────────────────────────
def get_channel_info(channel_id=TARGET_CHANNEL_ID):
    res = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=channel_id
    ).execute()

    ch = res["items"][0]
    info = {
        "channel_id": channel_id,
        "title": ch["snippet"]["title"],
        "description": ch["snippet"]["description"][:200],
        "published_at": ch["snippet"]["publishedAt"],
        "subscriber_count": int(ch["statistics"].get("subscriberCount", 0)),
        "video_count": int(ch["statistics"].get("videoCount", 0)),
        "view_count": int(ch["statistics"].get("viewCount", 0)),
        "uploads_playlist_id": ch["contentDetails"]["relatedPlaylists"]["uploads"],
        "collected_at": datetime.now().isoformat(),
    }

    print(f"[채널] {info['title']}")
    print(f"  구독자: {info['subscriber_count']:,}")
    print(f"  총 영상 수: {info['video_count']:,}")
    print(f"  총 조회수: {info['view_count']:,}")
    return info


# ─── 2. 채널 내 전체 영상 ID 수집 ───────────────────
def get_all_video_ids(uploads_playlist_id, max_videos=500):
    video_ids = []
    next_page_token = None

    print(f"\n[영상 ID 수집 중...]")
    while len(video_ids) < max_videos:
        res = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        ).execute()

        for item in res["items"]:
            video_ids.append(item["contentDetails"]["videoId"])

        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break

        time.sleep(0.2)
        print(f"  수집된 영상 수: {len(video_ids)}", end="\r")

    print(f"  총 {len(video_ids)}개 영상 ID 수집 완료")
    return video_ids


# ─── 3. 영상 상세 정보 수집 (50개씩 배치) ───────────
def get_video_details(video_ids):
    all_videos = []

    # 50개씩 나눠서 요청 (API 제한)
    batches = [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]
    print(f"\n[영상 상세 정보 수집 중... {len(batches)}배치]")

    for i, batch in enumerate(batches):
        res = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch),
        ).execute()

        for video in res["items"]:
            snippet = video["snippet"]
            stats = video.get("statistics", {})
            duration_raw = video["contentDetails"]["duration"]  # ISO 8601

            # 영상 종류 분류 (제목 기반)
            title = snippet["title"]
            video_type = classify_video_type(title)

            all_videos.append({
                "video_id": video["id"],
                "title": title,
                "video_type": video_type,
                "published_at": snippet["publishedAt"],
                "published_date": snippet["publishedAt"][:10],
                "published_year": snippet["publishedAt"][:4],
                "published_month": snippet["publishedAt"][5:7],

                # 통계
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),

                # 메타데이터
                "duration": parse_duration(duration_raw),
                "duration_raw": duration_raw,
                "tags": ", ".join(snippet.get("tags", [])[:10]),
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                "description_preview": snippet.get("description", "")[:150],
            })

        print(f"  배치 {i+1}/{len(batches)} 완료", end="\r")
        time.sleep(0.1)

    df = pd.DataFrame(all_videos)
    df = df.sort_values("published_at", ascending=False)
    print(f"\n  총 {len(df)}개 영상 상세 정보 수집 완료")
    return df


# ─── 4. 영상 종류 분류 (제목 기반) ──────────────────
def classify_video_type(title):
    title_lower = title.lower()

    if any(k in title_lower for k in ["mv", "m/v", "music video"]):
        return "MV"
    elif any(k in title_lower for k in ["performance", "choreography", "dance"]):
        return "퍼포먼스"
    elif any(k in title_lower for k in ["going seventeen", "going svt"]):
        return "고잉세븐틴"
    elif any(k in title_lower for k in ["behind", "making", "비하인드"]):
        return "비하인드"
    elif any(k in title_lower for k in ["teaser", "highlight"]):
        return "티저"
    elif any(k in title_lower for k in ["live", "concert", "tour"]):
        return "라이브"
    elif any(k in title_lower for k in ["interview", "인터뷰"]):
        return "인터뷰"
    elif any(k in title_lower for k in ["cover", "reaction"]):
        return "커버"
    else:
        return "기타"


# ─── 5. ISO 8601 duration → 분 단위 변환 ────────────
def parse_duration(duration_str):
    import re
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return round(hours * 60 + minutes + seconds / 60, 2)


# ─── 6. 댓글 수집 (인기 영상 기준) ──────────────────
def get_comments(video_id, video_title, max_comments=100):
    comments = []
    try:
        res = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            order="relevance",
            textFormat="plainText",
        ).execute()

        for item in res["items"]:
            c = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "video_id": video_id,
                "video_title": video_title,
                "comment": c["textDisplay"],
                "like_count": c["likeCount"],
                "published_at": c["publishedAt"],
                "author": c["authorDisplayName"],
            })

        print(f"  댓글 {len(comments)}개 수집: {video_title[:40]}")
    except Exception as e:
        print(f"  댓글 수집 실패 ({video_title[:30]}): {e}")

    return comments


def get_top_video_comments(videos_df, top_n=10):
    top_videos = videos_df.nlargest(top_n, "view_count")
    all_comments = []

    print(f"\n[Top {top_n} 영상 댓글 수집 중...]")
    for _, video in top_videos.iterrows():
        comments = get_comments(video["video_id"], video["title"])
        all_comments.extend(comments)
        time.sleep(0.5)

    return pd.DataFrame(all_comments)


# ─── 7. 분석 요약 출력 ──────────────────────────────
def analyze_videos(videos_df):
    print("\n" + "="*55)
    print("세븐틴 YouTube 채널 분석 요약")
    print("="*55)

    print(f"\n총 영상 수: {len(videos_df):,}개")
    print(f"총 조회수 합계: {videos_df['view_count'].sum():,}")
    print(f"평균 조회수: {videos_df['view_count'].mean():,.0f}")
    print(f"최고 조회수: {videos_df['view_count'].max():,}")

    print("\n[영상 타입별 현황]")
    type_stats = videos_df.groupby("video_type").agg(
        영상수=("video_id", "count"),
        평균조회수=("view_count", "mean"),
        총조회수=("view_count", "sum"),
    ).sort_values("총조회수", ascending=False)
    type_stats["평균조회수"] = type_stats["평균조회수"].apply(lambda x: f"{x:,.0f}")
    type_stats["총조회수"] = type_stats["총조회수"].apply(lambda x: f"{x:,}")
    print(type_stats.to_string())

    print("\n[연도별 업로드 수]")
    year_counts = videos_df.groupby("published_year")["video_id"].count()
    print(year_counts.to_string())

    print("\n[조회수 Top 10 영상]")
    top10 = videos_df.nlargest(10, "view_count")[
        ["title", "view_count", "like_count", "video_type", "published_date"]
    ]
    for _, row in top10.iterrows():
        print(f"  {row['view_count']:>12,}회 | {row['title'][:45]}")


# ─── 메인 실행 ──────────────────────────────────────
if __name__ == "__main__":
    print("세븐틴 YouTube 데이터 수집 시작\n")

    # 1. 채널 정보
    channel_info = get_channel_info()

    # 2. 전체 영상 ID 수집
    video_ids = get_all_video_ids(channel_info["uploads_playlist_id"], max_videos=500)

    # 3. 영상 상세 정보
    videos_df = get_video_details(video_ids)
    videos_df.to_csv("seventeen_youtube.csv", index=False, encoding="utf-8-sig")
    print("저장: seventeen_youtube.csv")

    # 4. 댓글 수집 (Top 10 영상 기준, 선택사항)
    collect_comments = input("\n댓글도 수집할까요? (y/n): ").strip().lower()
    if collect_comments == "y":
        comments_df = get_top_video_comments(videos_df, top_n=10)
        comments_df.to_csv("seventeen_comments.csv", index=False, encoding="utf-8-sig")
        print("저장: seventeen_comments.csv")

    # 5. 채널 메타데이터 저장
    with open("seventeen_youtube_meta.json", "w", encoding="utf-8") as f:
        json.dump(channel_info, f, ensure_ascii=False, indent=2)
    print("저장: seventeen_youtube_meta.json")

    # 6. 분석 요약
    analyze_videos(videos_df)

    print("\n수집 완료! 다음 단계: visualize_youtube.py 로 시각화!")
