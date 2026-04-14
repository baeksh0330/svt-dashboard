"""
comment_collector.py — 댓글 수집 + 감성 분석
================================================
필요한 패키지:
  pip install google-api-python-client pandas transformers torch
  pip install vaderSentiment  # 영어 감성 (보조용)

감성 분석 전략:
  1차: snunlp/KR-FinBert-SC (한국어 BERT, 가장 정확)
  2차: 키워드 사전 기반 (빠른 폴백)
"""

import os
import time
import json
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from googleapiclient.discovery import build

API_KEY  = os.environ.get("YOUTUBE_API_KEY") or "여기에_API_KEY_입력"
BASE_DIR = Path(__file__).parent
youtube  = build("youtube", "v3", developerKey=API_KEY)

# ─── 한국어 감성 키워드 사전 (BERT 없을 때 폴백) ────
POS_KEYWORDS = [
    "좋아", "최고", "사랑", "대박", "완벽", "감동", "멋있", "예쁘",
    "잘생", "천재", "신기", "행복", "설레", "소름", "귀엽", "짱",
    "good", "love", "amazing", "perfect", "beautiful", "great", "wow",
]
NEG_KEYWORDS = [
    "싫어", "별로", "실망", "최악", "불만", "아쉬", "못생", "노잼",
    "bad", "hate", "boring", "disappointing", "worst",
]


# ─── 1. 키워드 기반 감성 점수 ───────────────────────
def keyword_sentiment(text: str) -> dict:
    text_lower = text.lower()
    pos = sum(1 for k in POS_KEYWORDS if k in text_lower)
    neg = sum(1 for k in NEG_KEYWORDS if k in text_lower)
    total = pos + neg

    if total == 0:
        label, score = "neutral", 0.0
    elif pos > neg:
        label = "positive"
        score = pos / total
    else:
        label = "negative"
        score = -(neg / total)

    return {"label": label, "score": round(score, 3)}


# ─── 2. KoBERT 감성 분석 (설치된 경우) ─────────────
def load_bert_model():
    try:
        from transformers import pipeline
        classifier = pipeline(
            "text-classification",
            model="snunlp/KR-FinBert-SC",
            device=-1,  # CPU 사용 (-1), GPU 있으면 0
        )
        print("[BERT] 모델 로드 완료")
        return classifier
    except Exception as e:
        print(f"[BERT] 로드 실패, 키워드 방식으로 대체: {e}")
        return None


def bert_sentiment(classifier, text: str) -> dict:
    try:
        # BERT 입력 길이 제한 (512 토큰)
        text = text[:300]
        result = classifier(text)[0]
        label_map = {"positive": "positive", "negative": "negative", "neutral": "neutral"}
        label = label_map.get(result["label"].lower(), "neutral")
        score = result["score"] if label == "positive" else -result["score"] if label == "negative" else 0.0
        return {"label": label, "score": round(score, 3)}
    except Exception:
        return keyword_sentiment(text)


# ─── 3. 댓글 수집 ───────────────────────────────────
def get_comments(video_id: str, video_title: str, max_comments: int = 100) -> list:
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
                "video_id":    video_id,
                "video_title": video_title,
                "comment":     c["textDisplay"],
                "like_count":  c["likeCount"],
                "published_at":c["publishedAt"],
                "author":      c["authorDisplayName"],
            })
    except Exception as e:
        # 댓글 비활성화된 영상은 스킵
        print(f"  [스킵] {video_title[:30]}: {e}")

    return comments


# ─── 4. 전체 수집 실행 ──────────────────────────────
def collect_comments(videos_csv: Path, top_n: int = 30) -> pd.DataFrame:
    """조회수 상위 N개 영상의 댓글 수집"""
    videos = pd.read_csv(videos_csv)
    top_videos = videos.nlargest(top_n, "view_count")

    all_comments = []
    print(f"\n[댓글 수집] 상위 {top_n}개 영상 대상")

    for i, (_, video) in enumerate(top_videos.iterrows(), 1):
        print(f"  ({i}/{top_n}) {video['title'][:45]}")
        comments = get_comments(video["video_id"], video["title"])
        all_comments.extend(comments)
        time.sleep(0.5)  # API rate limit

    df = pd.DataFrame(all_comments)
    print(f"\n[댓글 수집 완료] 총 {len(df)}개")
    return df


# ─── 5. 감성 분석 실행 ──────────────────────────────
def analyze_sentiment(comments_df: pd.DataFrame) -> pd.DataFrame:
    print("\n[감성 분석 시작]")
    classifier = load_bert_model()

    sentiments = []
    for i, row in comments_df.iterrows():
        text = str(row["comment"])
        if classifier:
            result = bert_sentiment(classifier, text)
        else:
            result = keyword_sentiment(text)
        sentiments.append(result)

        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(comments_df)} 완료")

    comments_df["sentiment_label"] = [s["label"] for s in sentiments]
    comments_df["sentiment_score"] = [s["score"] for s in sentiments]
    return comments_df


# ─── 6. 영상별 감성 집계 ────────────────────────────
def aggregate_by_video(comments_df: pd.DataFrame) -> pd.DataFrame:
    agg = comments_df.groupby(["video_id", "video_title"]).agg(
        total_comments   = ("comment", "count"),
        positive_count   = ("sentiment_label", lambda x: (x == "positive").sum()),
        negative_count   = ("sentiment_label", lambda x: (x == "negative").sum()),
        neutral_count    = ("sentiment_label", lambda x: (x == "neutral").sum()),
        avg_score        = ("sentiment_score", "mean"),
        avg_comment_likes= ("like_count", "mean"),
    ).reset_index()

    agg["positive_rate"] = (agg["positive_count"] / agg["total_comments"] * 100).round(1)
    agg["negative_rate"] = (agg["negative_count"] / agg["total_comments"] * 100).round(1)
    agg["avg_score"]     = agg["avg_score"].round(3)

    return agg.sort_values("avg_score", ascending=False)


# ─── 7. 재시청 지수 계산 ────────────────────────────
def calc_rewatch_index(videos_csv: Path) -> pd.DataFrame:
    """
    재시청 가능성 Proxy Metric
    = (좋아요율 × 댓글수) / (영상길이 × 0.1 + 1)

    해석:
    - 짧고 반응(좋아요+댓글)이 폭발적인 영상 = 재시청 가능성 높음
    - 긴 영상은 패널티 적용
    """
    df = pd.read_csv(videos_csv)
    df = df[df["view_count"] > 0].copy()

    df["like_rate"]      = df["like_count"] / df["view_count"]
    df["rewatch_index"]  = (
        (df["like_rate"] * df["comment_count"])
        / (df["duration"] * 0.1 + 1)
    ).round(4)

    # 0~100 정규화
    min_r, max_r = df["rewatch_index"].min(), df["rewatch_index"].max()
    df["rewatch_score"] = (
        (df["rewatch_index"] - min_r) / (max_r - min_r) * 100
    ).round(1)

    cols = ["video_id", "title", "video_type", "published_date",
            "view_count", "like_count", "comment_count",
            "duration", "like_rate", "rewatch_score", "thumbnail"]
    return df[cols].sort_values("rewatch_score", ascending=False)


# ─── 메인 ───────────────────────────────────────────
if __name__ == "__main__":
    videos_csv = BASE_DIR / "seventeen_youtube.csv"

    # 재시청 지수
    print("=" * 50)
    print("재시청 콘텐츠 Top 10")
    print("=" * 50)
    rewatch_df = calc_rewatch_index(videos_csv)
    print(rewatch_df.head(10)[["title", "video_type", "rewatch_score", "duration"]].to_string(index=False))
    rewatch_df.to_csv(BASE_DIR / "seventeen_rewatch.csv", index=False, encoding="utf-8-sig")
    print("저장: seventeen_rewatch.csv")

    # 댓글 수집
    print("\n" + "=" * 50)
    comments_df = collect_comments(videos_csv, top_n=30)

    # 감성 분석
    comments_df = analyze_sentiment(comments_df)
    comments_df.to_csv(BASE_DIR / "seventeen_comments.csv", index=False, encoding="utf-8-sig")
    print("저장: seventeen_comments.csv")

    # 영상별 집계
    video_sentiment = aggregate_by_video(comments_df)
    video_sentiment.to_csv(BASE_DIR / "seventeen_sentiment.csv", index=False, encoding="utf-8-sig")
    print("저장: seventeen_sentiment.csv")

    print("\n[요약]")
    print(f"  긍정 댓글: {(comments_df['sentiment_label']=='positive').sum()}개")
    print(f"  중립 댓글: {(comments_df['sentiment_label']=='neutral').sum()}개")
    print(f"  부정 댓글: {(comments_df['sentiment_label']=='negative').sum()}개")
    print("\n완료! 다음: python database.py 로 DB 반영")
