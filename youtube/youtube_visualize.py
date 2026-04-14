"""
세븐틴 YouTube 데이터 시각화 스크립트
========================================
필요한 패키지: pip install pandas plotly

youtube_seventeen.py 실행 후 생성된 CSV 파일이 있어야 합니다.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

# ─── 데이터 로드 ────────────────────────────────────
videos = pd.read_csv("seventeen_youtube.csv")
with open("seventeen_youtube_meta.json", encoding="utf-8") as f:
    meta = json.load(f)

videos["published_at"] = pd.to_datetime(videos["published_at"])
videos["published_year"] = videos["published_year"].astype(str)

TYPE_COLORS = {
    "MV":       "#8B5CF6",
    "퍼포먼스": "#06B6D4",
    "고잉세븐틴": "#F59E0B",
    "비하인드": "#10B981",
    "티저":     "#F43F5E",
    "라이브":   "#3B82F6",
    "인터뷰":   "#EC4899",
    "커버":     "#84CC16",
    "기타":     "#6B7280",
}


# ─── 차트 1: 조회수 Top 20 가로 바차트 ──────────────
def top_videos_chart():
    top20 = videos.nlargest(20, "view_count").sort_values("view_count")

    fig = go.Figure(go.Bar(
        x=top20["view_count"],
        y=top20["title"].str[:40],
        orientation="h",
        marker_color=[TYPE_COLORS.get(t, "#6B7280") for t in top20["video_type"]],
        text=top20["view_count"].apply(lambda x: f"{x/1e6:.1f}M"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>조회수: %{x:,}<extra></extra>",
    ))
    fig.update_layout(
        title="조회수 Top 20 영상",
        xaxis_title="조회수",
        template="plotly_dark",
        height=650,
        margin=dict(l=320),
    )
    fig.write_html("yt_viz_top20.html")
    fig.show()
    print("저장: yt_viz_top20.html")


# ─── 차트 2: 월별 업로드 수 + 총 조회수 시계열 ───────
def monthly_upload_timeline():
    videos["ym"] = videos["published_at"].dt.to_period("M").astype(str)
    monthly = videos.groupby("ym").agg(
        upload_count=("video_id", "count"),
        total_views=("view_count", "sum"),
        avg_views=("view_count", "mean"),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=monthly["ym"],
        y=monthly["upload_count"],
        name="업로드 수",
        marker_color="#8B5CF6",
        opacity=0.7,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=monthly["ym"],
        y=monthly["total_views"],
        name="총 조회수",
        line=dict(color="#F59E0B", width=2),
        mode="lines+markers",
        marker=dict(size=4),
    ), secondary_y=True)

    fig.update_layout(
        title="월별 업로드 수 & 총 조회수 추이",
        template="plotly_dark",
        height=450,
        xaxis=dict(tickangle=45),
        legend=dict(orientation="h", y=1.1),
    )
    fig.update_yaxes(title_text="업로드 수", secondary_y=False)
    fig.update_yaxes(title_text="총 조회수", secondary_y=True)
    fig.write_html("yt_viz_timeline.html")
    fig.show()
    print("저장: yt_viz_timeline.html")


# ─── 차트 3: 영상 타입별 성과 비교 ──────────────────
def video_type_comparison():
    type_stats = videos.groupby("video_type").agg(
        count=("video_id", "count"),
        avg_views=("view_count", "mean"),
        avg_likes=("like_count", "mean"),
        total_views=("view_count", "sum"),
    ).reset_index()
    type_stats = type_stats[type_stats["count"] >= 3]  # 최소 3개 이상

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["타입별 평균 조회수", "타입별 영상 수 & 총 조회수"],
    )

    # 평균 조회수 바차트
    type_stats_sorted = type_stats.sort_values("avg_views", ascending=True)
    fig.add_trace(go.Bar(
        x=type_stats_sorted["avg_views"],
        y=type_stats_sorted["video_type"],
        orientation="h",
        marker_color=[TYPE_COLORS.get(t, "#6B7280") for t in type_stats_sorted["video_type"]],
        text=type_stats_sorted["avg_views"].apply(lambda x: f"{x/1e6:.2f}M"),
        textposition="outside",
        showlegend=False,
    ), row=1, col=1)

    # 버블차트: 영상 수 vs 총 조회수
    fig.add_trace(go.Scatter(
        x=type_stats["count"],
        y=type_stats["total_views"],
        mode="markers+text",
        marker=dict(
            size=type_stats["avg_views"] / type_stats["avg_views"].max() * 60 + 10,
            color=[TYPE_COLORS.get(t, "#6B7280") for t in type_stats["video_type"]],
            opacity=0.7,
        ),
        text=type_stats["video_type"],
        textposition="top center",
        showlegend=False,
    ), row=1, col=2)

    fig.update_layout(
        title="영상 타입별 성과 분석",
        template="plotly_dark",
        height=450,
    )
    fig.update_xaxes(title_text="영상 수", row=1, col=2)
    fig.update_yaxes(title_text="총 조회수", row=1, col=2)
    fig.write_html("yt_viz_type.html")
    fig.show()
    print("저장: yt_viz_type.html")


# ─── 차트 4: 조회수 vs 좋아요 산점도 ────────────────
def views_vs_likes_scatter():
    df = videos[videos["view_count"] > 0].copy()
    df["like_rate"] = (df["like_count"] / df["view_count"] * 100).round(3)

    fig = px.scatter(
        df,
        x="view_count",
        y="like_count",
        color="video_type",
        size="comment_count",
        hover_name="title",
        hover_data={"like_rate": ":.2f", "published_date": True},
        color_discrete_map=TYPE_COLORS,
        labels={
            "view_count": "조회수",
            "like_count": "좋아요 수",
            "video_type": "영상 타입",
            "comment_count": "댓글 수",
        },
        title="조회수 vs 좋아요 수 (버블 크기 = 댓글 수)",
        template="plotly_dark",
        log_x=True,
        log_y=True,
        height=550,
    )
    fig.write_html("yt_viz_scatter.html")
    fig.show()
    print("저장: yt_viz_scatter.html")


# ─── 차트 5: 연도별 평균 조회수 추이 ────────────────
def yearly_performance():
    yearly = videos.groupby(["published_year", "video_type"]).agg(
        avg_views=("view_count", "mean"),
        count=("video_id", "count"),
    ).reset_index()

    # 주요 타입만 선택
    main_types = ["MV", "퍼포먼스", "고잉세븐틴", "비하인드", "티저"]
    yearly_filtered = yearly[yearly["video_type"].isin(main_types)]

    fig = px.line(
        yearly_filtered,
        x="published_year",
        y="avg_views",
        color="video_type",
        markers=True,
        color_discrete_map=TYPE_COLORS,
        labels={
            "published_year": "연도",
            "avg_views": "평균 조회수",
            "video_type": "영상 타입",
        },
        title="연도별 영상 타입별 평균 조회수 추이",
        template="plotly_dark",
        height=450,
    )
    fig.write_html("yt_viz_yearly.html")
    fig.show()
    print("저장: yt_viz_yearly.html")


# ─── 차트 6: 통합 대시보드 ──────────────────────────
def full_dashboard():
    type_stats = videos.groupby("video_type").agg(
        count=("video_id", "count"),
        avg_views=("view_count", "mean"),
        total_views=("view_count", "sum"),
    ).reset_index().sort_values("total_views", ascending=False)

    yearly_uploads = videos.groupby("published_year")["video_id"].count().reset_index()
    top10 = videos.nlargest(10, "view_count")

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[
            "타입별 총 조회수",
            "연도별 업로드 수",
            "조회수 Top 10",
            "조회수 분포",
            "타입별 영상 비율",
            "좋아요율 분포",
        ],
        specs=[
            [{"type": "bar"}, {"type": "bar"}, {"type": "bar"}],
            [{"type": "histogram"}, {"type": "pie"}, {"type": "histogram"}],
        ]
    )

    # 1. 타입별 총 조회수
    fig.add_trace(go.Bar(
        x=type_stats["video_type"],
        y=type_stats["total_views"],
        marker_color=[TYPE_COLORS.get(t, "#6B7280") for t in type_stats["video_type"]],
        showlegend=False,
    ), row=1, col=1)

    # 2. 연도별 업로드 수
    fig.add_trace(go.Bar(
        x=yearly_uploads["published_year"],
        y=yearly_uploads["video_id"],
        marker_color="#06B6D4",
        showlegend=False,
    ), row=1, col=2)

    # 3. 조회수 Top 10
    top10_sorted = top10.sort_values("view_count")
    fig.add_trace(go.Bar(
        x=top10_sorted["view_count"],
        y=top10_sorted["title"].str[:25] + "...",
        orientation="h",
        marker_color="#F59E0B",
        showlegend=False,
    ), row=1, col=3)

    # 4. 조회수 분포
    fig.add_trace(go.Histogram(
        x=videos[videos["view_count"] < videos["view_count"].quantile(0.95)]["view_count"],
        nbinsx=30,
        marker_color="#8B5CF6",
        showlegend=False,
    ), row=2, col=1)

    # 5. 타입 비율 파이차트
    fig.add_trace(go.Pie(
        labels=type_stats["video_type"],
        values=type_stats["count"],
        marker_colors=[TYPE_COLORS.get(t, "#6B7280") for t in type_stats["video_type"]],
        showlegend=True,
    ), row=2, col=2)

    # 6. 좋아요율 분포
    like_rate = (videos["like_count"] / videos["view_count"].replace(0, 1) * 100)
    fig.add_trace(go.Histogram(
        x=like_rate[like_rate < like_rate.quantile(0.95)],
        nbinsx=25,
        marker_color="#10B981",
        showlegend=False,
    ), row=2, col=3)

    fig.update_layout(
        title=f"세븐틴 YouTube 분석 대시보드 — 구독자 {meta.get('subscriber_count', 0):,}명",
        template="plotly_dark",
        height=750,
        showlegend=True,
    )
    fig.write_html("yt_viz_dashboard.html")
    fig.show()
    print("저장: yt_viz_dashboard.html")


# ─── 메인 실행 ──────────────────────────────────────
if __name__ == "__main__":
    print("세븐틴 YouTube 시각화 시작\n")

    print("1/6 Top 20 영상 차트 생성 중...")
    top_videos_chart()

    print("2/6 월별 타임라인 생성 중...")
    monthly_upload_timeline()

    print("3/6 영상 타입 비교 생성 중...")
    video_type_comparison()

    print("4/6 조회수×좋아요 산점도 생성 중...")
    views_vs_likes_scatter()

    print("5/6 연도별 성과 추이 생성 중...")
    yearly_performance()

    print("6/6 통합 대시보드 생성 중...")
    full_dashboard()

    print("\n완료! 생성된 시각화 파일:")
    print("  - yt_viz_top20.html      (조회수 Top 20)")
    print("  - yt_viz_timeline.html   (월별 업로드 & 조회수 추이)")
    print("  - yt_viz_type.html       (영상 타입별 성과)")
    print("  - yt_viz_scatter.html    (조회수 vs 좋아요 산점도)")
    print("  - yt_viz_yearly.html     (연도별 타입별 추이)")
    print("  - yt_viz_dashboard.html  (통합 대시보드)")
