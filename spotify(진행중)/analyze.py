import pandas as pd
import os

FILE = "data/tracks.csv"

# ── 파일 존재 체크
if not os.path.exists(FILE):
    raise FileNotFoundError("tracks.csv 없음 → collect.py 먼저 실행")

df = pd.read_csv(FILE)

# ── 데이터 없을 때 처리
if df.empty:
    print("데이터 없음")
    exit()

# ── 숫자 컬럼 강제 변환 (깨짐 방지)
num_cols = ["danceability", "energy", "valence", "tempo", "loudness"]

for col in num_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["energy", "valence", "tempo"])

print("\n=== BASIC INFO ===")
print("rows:", len(df))
print("columns:", len(df.columns))

# ── 기본 통계
print("\n=== DESCRIBE ===")
print(df[num_cols].describe())

# ── 에너지 Top 5
if "energy" in df.columns:
    print("\n=== ENERGY TOP 5 ===")
    print(
        df.sort_values("energy", ascending=False)[["track", "energy"]].head(5)
    )

# ── 밝기 Top 5
if "valence" in df.columns:
    print("\n=== VALENCE TOP 5 ===")
    print(
        df.sort_values("valence", ascending=False)[["track", "valence"]].head(5)
    )

# ── 평균 BPM
if "tempo" in df.columns:
    print("\n=== AVG TEMPO ===")
    print(round(df["tempo"].mean(), 2))