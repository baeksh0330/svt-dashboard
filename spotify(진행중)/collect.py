import os
import requests
import base64
import pandas as pd
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# ── 설정
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

ARTIST_ID = "7nqOGRxlXj7N2JYbgNEjYH"

# ── 토큰 발급
def get_token():
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    res = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"}
    )

    data = res.json()
    return data.get("access_token")


token = get_token()
headers = {"Authorization": f"Bearer {token}"}


# ── 1. 아티스트 정보 (절대 안 죽게)
def get_artist():
    res = requests.get(
        f"https://api.spotify.com/v1/artists/{ARTIST_ID}",
        headers=headers
    ).json()

    return {
        "name": res.get("name"),
        "followers": res.get("followers", {}).get("total", 0),
        "popularity": res.get("popularity", 0),
        "genres": res.get("genres", []),
        "id": res.get("id"),
        "collected_at": datetime.now().isoformat()
    }


# ── 2. 앨범 수집
def get_albums():
    url = f"https://api.spotify.com/v1/artists/{ARTIST_ID}/albums?limit=50"
    albums = []

    while url:
        res = requests.get(url, headers=headers).json()

        for a in res.get("items", []):
            albums.append({
                "id": a.get("id"),
                "name": a.get("name"),
                "release_date": a.get("release_date"),
                "total_tracks": a.get("total_tracks", 0)
            })

        url = res.get("next")

    return pd.DataFrame(albums)


# ── 3. 트랙 + audio features
def get_tracks(album_df):
    all_tracks = []

    for _, row in album_df.iterrows():
        album_id = row["id"]

        res = requests.get(
            f"https://api.spotify.com/v1/albums/{album_id}/tracks",
            headers=headers
        ).json()

        track_items = res.get("items", [])
        track_ids = [t.get("id") for t in track_items if t.get("id")]

        if not track_ids:
            continue

        feat_res = requests.get(
            "https://api.spotify.com/v1/audio-features",
            headers=headers,
            params={"ids": ",".join(track_ids[:100])}
        ).json()

        features = feat_res.get("audio_features", [])

        for t, f in zip(track_items, features):
            if not t or not f:
                continue

            all_tracks.append({
                "track": t.get("name"),
                "album": row["name"],
                "danceability": f.get("danceability"),
                "energy": f.get("energy"),
                "valence": f.get("valence"),
                "tempo": f.get("tempo"),
                "loudness": f.get("loudness"),
            })

        time.sleep(0.1)

    return pd.DataFrame(all_tracks)


# ── 실행
if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    print("collect start")

    artist = get_artist()
    pd.DataFrame([artist]).to_csv("data/artist.csv", index=False, encoding="utf-8-sig")

    albums = get_albums()
    albums.to_csv("data/albums.csv", index=False, encoding="utf-8-sig")

    tracks = get_tracks(albums)
    tracks.to_csv("data/tracks.csv", index=False, encoding="utf-8-sig")

    print("done")
    print("files saved → data/")
    print(pd.read_csv('data/tracks.csv'))