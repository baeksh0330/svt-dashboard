"""
main.py — FastAPI 앱 진입점 (v2)
===================================
실행: uvicorn main:app --reload
API 문서: http://localhost:8000/docs

다음 단계:
  → frontend/ 폴더에서 python -m http.server 3000
  → 브라우저에서 http://localhost:3000/dashboard.html
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import init_db, load_csv_to_db
from routers import videos_router, stats_router
from router_wordcloud import wordcloud_router
from router_units import units_router, timeline_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[시작] DB 초기화 중...")
    init_db()
    load_csv_to_db()
    print("[시작] 준비 완료!")
    print("[중요] 폴더 위치 확인")
    yield

app = FastAPI(
    title="세븐틴 YouTube 분석 API",
    description="세븐틴 공식 유튜브 채널 데이터 분석 API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos_router)
app.include_router(stats_router)
app.include_router(wordcloud_router)
app.include_router(units_router)
app.include_router(timeline_router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}

# debug
# for route in app.routes:
#     print("route path : ",route.path)