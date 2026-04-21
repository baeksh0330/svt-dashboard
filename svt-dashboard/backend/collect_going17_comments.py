"""
collect_going17_comments.py — Going Seventeen 영상 댓글 수집
=============================================================
필요한 패키지: pip install google-api-python-client pandas

출력:
  going17_comments.csv  ← 댓글 원본
  going17_wordcloud.json ← 워드클라우드용 단어 빈도
"""

import os, re, time, json
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter
from googleapiclient.discovery import build


# 왜 너만 키를 못 받아옴? 
from dotenv import load_dotenv # 이 부분이 빠져서 API를 못 받아옴 -> 해결 
load_dotenv()

API_KEY = os.environ.get("YOUTUBE_API_KEY") or "API_key_없음"
BASE_DIR = Path(__file__).parent
youtube  = build("youtube", "v3", developerKey=API_KEY)
# print(API_KEY)



STOPWORDS = {
    # 영어
    "the", "a", "an", "is", "it", "in", "of", "to", "and", "for",
    "this", "that", "so", "my", "me", "i", "you", "we", "they",
    "he", "she", "be", "was", "are", "have", "has", "do", "did",
    "with", "at", "on", "from", "by", "as", "but", "or", "not",
    "s", "t", "re", "ll", "ve", "just", "like", "also", "very",
    "im", "its", "their", "there", "what", "when", "how", "who",
    # 한국어 (조사/어미 등)
    "이", "가", "은", "는", "을", "를", "의", "에", "도", "와", "과",
    "로", "으로", "에서", "이다", "있다", "하다", "ㅋ", "ㅠ", "ㅜ",
    # 노이즈
    "세븐틴", "seventeen", "svt", "going", "고잉",
    "https", "http", "www", "com", 
    # "s.coups", "jeonghan", "joshua",
    # "jun", "hoshi", "wonwoo", "woozi",
    # "the 8", "mingyu", 'dk',
    # 'seungkwan', 'vernon', 'dino',  -> 유의미한 stopword인지 확인할 것 
}


def get_going17_videos(videos_csv: Path) -> pd.DataFrame:
    """CSV에서 고잉세븐틴 카테고리 영상 추출 —지금 인기순으로 되어있음 """
    df = pd.read_csv(videos_csv) 
    
            # """조회수 상위 N개 영상의 댓글 수집"""

    going = df[
        (df["video_type"] == "고잉세븐틴") &
        (df["title"].str.contains(r"\[GOING SEVENTEEN\]", na=False))
    ].copy() # str.contains 를 써야하지 in을 쓰면 값이 df안에 몇 개 있는지를 물어보는거임 
    going = going.sort_values("published_at", ascending=False) # 최신순 : published_at/인기순: view_count 으로 변경하면 됨
    print(f"[고잉세븐틴] 총 {len(going)}개 영상 발견")
    return going


def get_comments_for_video(video_id: str, video_title: str, max_pages: int = 3) -> list:
    """영상 한 개의 댓글 수집 (최대 300개)"""
    comments = []
    token = None


    for _ in range(max_pages):
            try:
                res = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=100,
                    order="relevance",
                    textFormat="plainText",
                    pageToken=token,
                ).execute()

                for item in res["items"]:
                    c = item["snippet"]["topLevelComment"]["snippet"]
                    comments.append({
                        "video_id":     video_id,
                        "video_title":  video_title,
                        "published_date": video_title,  # 나중에 merge로 채움
                        "comment":      c["textDisplay"],
                        "like_count":   c["likeCount"],
                        "comment_date": c["publishedAt"][:10],
                    })

                token = res.get("nextPageToken")
                if not token:
                    break
                time.sleep(0.2)

            except Exception as e:
                print(f"  [스킵] {video_title[:30]}: {e}")
                break

    return comments


def collect_all_comments(going_df: pd.DataFrame, max_videos: int = 50) -> pd.DataFrame:
    """최신 영상부터 최대 max_videos개 댓글 수집"""
    all_comments = []
    target = going_df.head(max_videos)


    print(f"\n[댓글 수집 시작] 최신 순 {len(target)}개 영상 대상")
    for i, (_, row) in enumerate(target.iterrows(), 1):
        print(f"  ({i}/{len(target)}) {row['title'][:50]}")
        comments = get_comments_for_video(row["video_id"], row["title"])

        # 발매일 채우기
        for c in comments:
            c["published_date"] = row["published_date"]

        print(f"    → {len(comments)}개 댓글")
        all_comments.extend(comments)
        time.sleep(0.5)

    df = pd.DataFrame(all_comments)
    print(f"\n[수집 완료] 총 {len(df)}개 댓글")
    return df


def build_wordcloud_data(comments_df: pd.DataFrame, top_n: int = 150) -> list:
    """
    댓글 텍스트 → 단어 빈도 계산
    반환: [{"text": "단어", "value": 빈도, "video": "최근 영상 제목"}, ...]
    """
    all_tokens = []

    for _, row in comments_df.iterrows():
        text = str(row["comment"])
        # 특수문자 제거
        text = re.sub(r"[^\w\s가-힣]", " ", text)
        tokens = text.lower().split()
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) >= 2]
        all_tokens.extend(tokens)

    counter = Counter(all_tokens)
    top_words = counter.most_common(top_n)

    # 최대값 기준 정규화 (워드클라우드 크기 조정용)
    max_val = top_words[0][1] if top_words else 1
    result = [
        {"text": word, "value": count, "normalized": round(count / max_val * 100, 1)}
        for word, count in top_words
    ]
    return result


def build_per_video_words(comments_df: pd.DataFrame, top_n: int = 30) -> list:
    """
    영상별 Top 단어 — 최신순 정렬
    대시보드에서 영상 선택 시 해당 영상 워드클라우드 표시용
    """
    result = []
    # published_date 기준 최신순
    videos = (
        comments_df[["video_id", "video_title", "published_date"]]
        .drop_duplicates("video_id")
        .sort_values("published_date", ascending=False)
    )

    for _, vrow in videos.iterrows():
        vid_comments = comments_df[comments_df["video_id"] == vrow["video_id"]]
        tokens = []
        for _, crow in vid_comments.iterrows():
            text = re.sub(r"[^\w\s가-힣]", " ", str(crow["comment"])).lower()
            tokens += [t for t in text.split() if t not in STOPWORDS and len(t) >= 2]

        counter = Counter(tokens)
        top = counter.most_common(top_n)
        if not top:
            continue
        max_val = top[0][1]
        result.append({
            "video_id":    vrow["video_id"],
            "video_title": vrow["video_title"],
            "published_date": vrow["published_date"],
            "words": [
                {"text": w, "value": c, "normalized": round(c / max_val * 100, 1)}
                for w, c in top
            ],
        })

    return result


if __name__ == "__main__":
    
    if API_KEY == 'API_key_없음':
        print("API 못받아옴")
        exit(1)
        
    videos_csv = BASE_DIR / "seventeen_youtube.csv"

    # 1. 고잉세븐틴 영상 목록
    going_df = get_going17_videos(videos_csv)

    # 2. 댓글 수집 (최신 50개 영상)
    comments_df = collect_all_comments(going_df, max_videos=50)
    comments_df.to_csv(BASE_DIR / "going17_comments.csv", index=False, encoding="utf-8-sig")
    print("저장: going17_comments.csv")

    # 3. 전체 워드클라우드 데이터
    wc_all = build_wordcloud_data(comments_df, top_n=150)

    # 4. 영상별 워드클라우드 데이터
    wc_per_video = build_per_video_words(comments_df, top_n=30)

    # 5. JSON 저장 (API 서빙용)
    output = {
        "generated_at":   datetime.now().isoformat(),
        "total_comments": len(comments_df),
        "total_videos":   len(going_df),
        "all_words":      wc_all,
        "per_video":      wc_per_video,
    }
    with open(BASE_DIR / "going17_wordcloud.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("저장: going17_wordcloud.json")

    print(f"\n상위 20개 단어:")
    for item in wc_all[:20]:
        print(f"  {item['text']:15s} {item['value']:>5}회")

    print("\n완료! 다음: python database_update.py → uvicorn main:app --reload")
