"""
main.py — FastAPI 앱 진입점
============================
실행: uvicorn main:app --reload
API 문서: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import init_db, load_csv_to_db
from routers import videos_router, stats_router


# ─── 앱 시작 시 DB 초기화 ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[시작] DB 초기화 중...")
    init_db()
    load_csv_to_db()
    print("[시작] 준비 완료!")
    yield

app = FastAPI(
    title="세븐틴 YouTube 분석 API",
    description="세븐틴 공식 유튜브 채널 데이터 분석 API",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS (프론트와 통신 위해 필수) ─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # Next.js 개발 서버
        "https://*.vercel.app",     # 배포 후 Vercel 도메인
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 라우터 등록 ─────────────────────────────────────
app.include_router(videos_router)
app.include_router(stats_router)


# ─── 헬스체크 ────────────────────────────────────────
@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "세븐틴 YouTube 분석 API"}

@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
