"""
database.py — SQLite 연결 + CSV → DB 초기 적재
"""

import sqlite3
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "svt.db"
CSV_VIDEOS = Path(__file__).parent / "seventeen_youtube.csv"
CSV_META   = Path(__file__).parent / "seventeen_youtube_meta.json"


# ─── DB 연결 ────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict처럼 접근 가능
    return conn


# ─── 테이블 생성 ─────────────────────────────────────
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS channel_meta (
        id              INTEGER PRIMARY KEY,
        title           TEXT,
        subscriber_count INTEGER,
        video_count     INTEGER,
        view_count      INTEGER,
        collected_at    TEXT
    );

    CREATE TABLE IF NOT EXISTS videos (
        video_id        TEXT PRIMARY KEY,
        title           TEXT NOT NULL,
        video_type      TEXT,
        published_at    TEXT,
        published_date  TEXT,
        published_year  TEXT,
        published_month TEXT,
        view_count      INTEGER DEFAULT 0,
        like_count      INTEGER DEFAULT 0,
        comment_count   INTEGER DEFAULT 0,
        duration        REAL,
        thumbnail       TEXT,
        updated_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS view_snapshots (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id        TEXT,
        view_count      INTEGER,
        like_count      INTEGER,
        snapshot_at     TEXT,
        FOREIGN KEY (video_id) REFERENCES videos(video_id)
    );

    CREATE INDEX IF NOT EXISTS idx_videos_type ON videos(video_type);
    CREATE INDEX IF NOT EXISTS idx_videos_date ON videos(published_date);
    CREATE INDEX IF NOT EXISTS idx_snapshots_vid ON view_snapshots(video_id);
    """)

    conn.commit()
    conn.close()
    print("[DB] 테이블 초기화 완료")


# ─── CSV → DB 적재 ───────────────────────────────────
def load_csv_to_db():
    if not CSV_VIDEOS.exists():
        print(f"[DB] CSV 없음: {CSV_VIDEOS}")
        return

    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()

    # 채널 메타 적재
    if CSV_META.exists():
        with open(CSV_META, encoding="utf-8") as f:
            meta = json.load(f)
        cur.execute("DELETE FROM channel_meta")
        cur.execute("""
            INSERT INTO channel_meta (title, subscriber_count, video_count, view_count, collected_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            meta.get("title", "SEVENTEEN"),
            meta.get("subscriber_count", 0),
            meta.get("video_count", 0),
            meta.get("view_count", 0),
            meta.get("collected_at", now),
        ))
        print(f"[DB] 채널 메타 적재 완료")

    # 영상 데이터 적재
    df = pd.read_csv(CSV_VIDEOS)
    df = df.fillna("")

    inserted, updated = 0, 0
    for _, row in df.iterrows():
        exists = cur.execute(
            "SELECT 1 FROM videos WHERE video_id=?", (row["video_id"],)
        ).fetchone()

        if exists:
            # 조회수 스냅샷 저장 (기존 영상이 업데이트될 때)
            old = cur.execute(
                "SELECT view_count, like_count FROM videos WHERE video_id=?",
                (row["video_id"],)
            ).fetchone()
            if old and old["view_count"] != int(row.get("view_count", 0)):
                cur.execute("""
                    INSERT INTO view_snapshots (video_id, view_count, like_count, snapshot_at)
                    VALUES (?, ?, ?, ?)
                """, (row["video_id"], old["view_count"], old["like_count"], now))

            cur.execute("""
                UPDATE videos SET
                    view_count=?, like_count=?, comment_count=?, updated_at=?
                WHERE video_id=?
            """, (
                int(row.get("view_count", 0)),
                int(row.get("like_count", 0)),
                int(row.get("comment_count", 0)),
                now,
                row["video_id"],
            ))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO videos
                    (video_id, title, video_type, published_at, published_date,
                     published_year, published_month, view_count, like_count,
                     comment_count, duration, thumbnail, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row["video_id"],
                row.get("title", ""),
                row.get("video_type", "기타"),
                row.get("published_at", ""),
                row.get("published_date", ""),
                str(row.get("published_year", ""))[:4],
                str(row.get("published_month", ""))[:2],
                int(row.get("view_count", 0)),
                int(row.get("like_count", 0)),
                int(row.get("comment_count", 0)),
                float(row.get("duration", 0)),
                row.get("thumbnail", ""),
                now,
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"[DB] 영상 적재 완료 — 신규: {inserted}개, 업데이트: {updated}개")


# ─── 유틸: 쿼리 결과 → dict 리스트 ──────────────────
def rows_to_list(rows):
    return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()
    load_csv_to_db()
