"""
메인 실행 스크립트
usage: python main_heatmap.py [--output docs/heatmap.html]
"""

import argparse
import datetime
from skill_heatmap.kis_api     import KisAPI
from skill_heatmap.heatmap     import run_skill_heatmap, pivot_for_heatmap
from skill_heatmap.render_html import render
from skill_heatmap.insight     import generate_insights

BENCHMARK_KOSPI = {
    "W06": -0.3, "W07": +2.3, "W08": -1.0,
    "W09":-12.1, "W10": -6.0, "W11": -2.7,
    "W12": -6.5, "W13": -4.5, "W14": -1.6,
    "W15": -0.9, "W16": -0.0, "W17": -1.4,
    "W18": +0.1, "W19": -6.1, "W20": -3.3,
    "W21": -0.5, "W22": -5.5, "W23": -8.3,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="docs/heatmap.html")
    args = parser.parse_args()

    today     = datetime.date.today()
    this_year = today.year
    last_year = today.year - 1

    print(f"[START] {last_year}~{this_year}년 스킬 히트맵 생성")

    kis   = KisAPI()
    start = f"{last_year - 1}0101"   # 지표 계산용 여유 데이터
    end   = today.strftime("%Y%m%d") # 오늘까지

    # ── KR ───────────────────────────────────────────────
    print("[1/2] KR 데이터 수집 중...")
    tickers_kr = kis.get_ticker_list("KOSPI")
    ohlcv_kr   = kis.batch_ohlcv(tickers_kr, start, end, market="KR")
    print(f"  KR 조회 완료: {len(ohlcv_kr)}개 종목")

    # 2025 + 2026 각각 집계 후 합치기
    result_kr_25 = run_skill_heatmap(ohlcv_kr, year=last_year)
    result_kr_26 = run_skill_heatmap(ohlcv_kr, year=this_year)

    import pandas as pd
    result_kr  = pd.concat([result_kr_25, result_kr_26], ignore_index=True)
    heatmap_kr = pivot_for_heatmap(result_kr)
    print(f"  KR 신호 집계 완료: {len(result_kr)}행")

    # ── US ───────────────────────────────────────────────
    print("[2/2] US 데이터 수집 중...")
    tickers_us = kis.get_ticker_list("US")
    ohlcv_us   = kis.batch_ohlcv(tickers_us, start, end, market="US")
    print(f"  US 조회 완료: {len(ohlcv_us)}개 종목")

    result_us_25 = run_skill_heatmap(ohlcv_us, year=last_year)
    result_us_26 = run_skill_heatmap(ohlcv_us, year=this_year)
    result_us    = pd.concat([result_us_25, result_us_26], ignore_index=True)
    heatmap_us   = pivot_for_heatmap(result_us)
    print(f"  US 신호 집계 완료: {len(result_us)}행")

    # ── 인사이트 생성 ─────────────────────────────────────
    insights = generate_insights(heatmap_kr, heatmap_us)
    print(f"  인사이트 {len(insights)}개 생성")

    # ── HTML 렌더링 ───────────────────────────────────────
    render(
        heatmap_kr   = heatmap_kr,
        output_path  = args.output,
        benchmark_kr = BENCHMARK_KOSPI,
        heatmap_us   = heatmap_us if ohlcv_us else None,
        insights     = insights,
    )
    print(f"[DONE] {args.output}")


if __name__ == "__main__":
    main()
