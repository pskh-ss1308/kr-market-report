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
from skill_heatmap.scanner     import scan_current_signals, format_scan_results

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

    print(f"[START] {this_year}년 스킬 히트맵 생성")

    kis          = KisAPI()
    start        = f"{this_year - 1}0101"
    end          = today.strftime("%Y%m%d")
    name_map_kr  = kis._kr_names

    # ── KR 코스피 ─────────────────────────────────────────
    print("[1/3] KR 코스피 데이터 수집 중...")
    tickers_kospi = kis.get_ticker_list("KOSPI")
    ohlcv_kospi   = kis.batch_ohlcv(tickers_kospi, start, end, market="KR")
    print(f"  코스피 조회 완료: {len(ohlcv_kospi)}개 종목")
    heatmap_kospi = pivot_for_heatmap(run_skill_heatmap(ohlcv_kospi, year=this_year, name_map=name_map_kr))

    # ── KR 코스닥 ─────────────────────────────────────────
    print("[2/3] KR 코스닥 데이터 수집 중...")
    tickers_kosdaq = kis.get_ticker_list("KOSDAQ")
    ohlcv_kosdaq   = kis.batch_ohlcv(tickers_kosdaq, start, end, market="KR")
    print(f"  코스닥 조회 완료: {len(ohlcv_kosdaq)}개 종목")
    heatmap_kosdaq = pivot_for_heatmap(run_skill_heatmap(ohlcv_kosdaq, year=this_year, name_map=name_map_kr))

    # ── US ───────────────────────────────────────────────
    print("[3/3] US 데이터 수집 중...")
    tickers_us = kis.get_ticker_list("US")
    ohlcv_us   = kis.batch_ohlcv(tickers_us, start, end, market="US")
    print(f"  US 조회 완료: {len(ohlcv_us)}개 종목")
    heatmap_us = pivot_for_heatmap(run_skill_heatmap(ohlcv_us, year=this_year))

    # ── 인사이트 ──────────────────────────────────────────
    insights = generate_insights(heatmap_kospi, heatmap_us)
    print(f"  인사이트 {len(insights)}개 생성")

    # ── 진입 후보 스캔 ────────────────────────────────────
    print("  진입 후보 스캔 중...")
    ohlcv_all_kr = {**ohlcv_kospi, **ohlcv_kosdaq}
    kr_signals   = scan_current_signals(ohlcv_all_kr, name_map=name_map_kr, market="KR")
    us_signals   = scan_current_signals(ohlcv_us, market="US")
    scan_results = format_scan_results(kr_signals, us_signals)
    print(f"  스캔 완료")

    # ── HTML 렌더링 ───────────────────────────────────────
    render(
        heatmap_kospi  = heatmap_kospi,
        heatmap_kosdaq = heatmap_kosdaq,
        heatmap_us     = heatmap_us,
        output_path    = args.output,
        benchmark_kr   = BENCHMARK_KOSPI,
        insights       = insights,
        scan_results   = scan_results,
    )
    print(f"[DONE] {args.output}")


if __name__ == "__main__":
    main()
