"""
메인 실행 스크립트
usage: python main.py [--year 2025] [--market KOSPI]
"""

import argparse
import datetime
from skill_heatmap.kis_api     import KisAPI
from skill_heatmap.heatmap     import run_skill_heatmap, pivot_for_heatmap
from skill_heatmap.render_html import render

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
    parser.add_argument("--year",   type=int, default=datetime.date.today().year)
    parser.add_argument("--market", type=str, default="KOSPI")
    parser.add_argument("--output", type=str, default="output/heatmap.html")
    args = parser.parse_args()

    print(f"[START] {args.market} {args.year}년 스킬 히트맵 생성")

    kis     = KisAPI()
    tickers = kis.get_ticker_list(args.market)
    print(f"  대상 종목 수: {len(tickers)}")

    start = f"{args.year - 1}0101"
    end   = f"{args.year}1231"
    print(f"  데이터 조회 기간: {start} ~ {end}")
    ohlcv_dict = kis.batch_ohlcv(tickers, start, end)
    print(f"  조회 완료: {len(ohlcv_dict)}개 종목")

    result_df    = run_skill_heatmap(ohlcv_dict, year=args.year)
    print(f"  신호 집계 완료: {len(result_df)}행")

    heatmap_data = pivot_for_heatmap(result_df)
    render(
        heatmap_data,
        output_path=args.output,
        benchmark=BENCHMARK_KOSPI,
    )
    print(f"[DONE] {args.output}")


if __name__ == "__main__":
    main()
