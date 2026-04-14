"""
database_update.py — 새 테이블 추가 마이그레이션
===================================================
기존 database.py에 아래 내용을 추가하거나,
이 파일을 한 번만 실행해서 테이블을 추가하세요.

실행: python database_update.py
"""

import pandas as pd
from pathlib import Path
from database import get_db

BASE_DIR = Path(__file__).parent


# ─── 새 테이블 생성 ──────────────────────────────────
def migrate():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS rewatch (
        video_id        TEXT PRIMARY KEY,
        like_rate       REAL,
        rewatch_index   REAL,
        rewatch_score   REAL,
        updated_at      TEXT,
        FOREIGN KEY (video_id) REFERENCES videos(video_id)
    );

    CREATE TABLE IF NOT EXISTS comments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id        TEXT,
        video_title     TEXT,
        comment         TEXT,
        like_count      INTEGER DEFAULT 0,
        published_at    TEXT,
        author          TEXT,
        sentiment_label TEXT,
        sentiment_score REAL,
        FOREIGN KEY (video_id) REFERENCES videos(video_id)
    );

    CREATE TABLE IF NOT EXISTS video_sentiment (
        video_id         TEXT PRIMARY KEY,
        total_comments   INTEGER,
        positive_count   INTEGER,
        negative_count   INTEGER,
        neutral_count    INTEGER,
        positive_rate    REAL,
        negative_rate    REAL,
        avg_score        REAL,
        avg_comment_likes REAL,
        FOREIGN KEY (video_id) REFERENCES videos(video_id)
    );

    CREATE INDEX IF NOT EXISTS idx_comments_vid  ON comments(video_id);
    CREATE INDEX IF NOT EXISTS idx_comments_sent ON comments(sentiment_label);
    CREATE INDEX IF NOT EXISTS idx_comments_date ON comments(published_at);
    """)
    conn.commit()
    conn.close()
    print("[마이그레이션] 테이블 추가 완료")


# ─── CSV → rewatch 테이블 적재 ──────────────────────
def load_rewatch():
    csv_path = BASE_DIR / "seventeen_rewatch.csv"
    if not csv_path.exists():
        print("[rewatch] CSV 없음 — comment_collector.py 먼저 실행하세요")
        return

    from datetime import datetime
    df = pd.read_csv(csv_path).fillna(0)
    conn = get_db()
    now = datetime.now().isoformat()

    for _, row in df.iterrows():
        conn.execute("""
            INSERT OR REPLACE INTO rewatch
                (video_id, like_rate, rewatch_index, rewatch_score, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            row["video_id"],
            float(row.get("like_rate", 0)),
            float(row.get("rewatch_index", 0)) if "rewatch_index" in row else 0,
            float(row.get("rewatch_score", 0)),
            now,
        ))

    conn.commit()
    conn.close()
    print(f"[rewatch] {len(df)}개 적재 완료")


# ─── CSV → comments + video_sentiment 적재 ──────────
def load_comments():
    comments_path  = BASE_DIR / "seventeen_comments.csv"
    sentiment_path = BASE_DIR / "seventeen_sentiment.csv"

    if not comments_path.exists():
        print("[comments] CSV 없음 — comment_collector.py 먼저 실행하세요")
        return

    conn = get_db()

    # 댓글 적재
    df = pd.read_csv(comments_path).fillna("")
    conn.execute("DELETE FROM comments")  # 전체 갱신
    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO comments
                (video_id, video_title, comment, like_count,
                 published_at, author, sentiment_label, sentiment_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["video_id"], row["video_title"],
            row["comment"],  int(row.get("like_count", 0)),
            row["published_at"], row["author"],
            row.get("sentiment_label", "neutral"),
            float(row.get("sentiment_score", 0)),
        ))
    print(f"[comments] {len(df)}개 적재 완료")

    # 영상별 감성 집계 적재
    if sentiment_path.exists():
        sf = pd.read_csv(sentiment_path).fillna(0)
        conn.execute("DELETE FROM video_sentiment")
        for _, row in sf.iterrows():
            conn.execute("""
                INSERT INTO video_sentiment
                    (video_id, total_comments, positive_count, negative_count,
                     neutral_count, positive_rate, negative_rate,
                     avg_score, avg_comment_likes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["video_id"],
                int(row.get("total_comments", 0)),
                int(row.get("positive_count", 0)),
                int(row.get("negative_count", 0)),
                int(row.get("neutral_count",  0)),
                float(row.get("positive_rate", 0)),
                float(row.get("negative_rate", 0)),
                float(row.get("avg_score",     0)),
                float(row.get("avg_comment_likes", 0)),
            ))
        print(f"[video_sentiment] {len(sf)}개 적재 완료")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
    load_rewatch()
    load_comments()
    print("\n완료! uvicorn main:app --reload 로 서버 재시작하세요.")
