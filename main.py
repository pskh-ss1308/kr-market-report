"""데일리 레포트 파이프라인 진입점.

SIMULATION_MODE=true  → 비용 0원. 데이터 수집·발송 파이프라인 검증.
SIMULATION_MODE=false → 실전. Claude AI 분석 레포트 생성.
"""
from __future__ import annotations
import sys
import datetime as dt

sys.path.insert(0, "src")

import config
from collect_market import collect_market
from collect_flows import collect_flows
from collect_sectors import collect_sectors
from collect_news import collect_news
from correlations import compute_correlations
from render import render
from deliver import send_email, send_slack


def _kospi_date(snapshot):
    for s in snapshot:
        if s["label"] == "KOSPI":
            return s.get("date")
    return None


def main(force: bool = False) -> int:
    mode_label = "🔵 시뮬레이션" if config.SIMULATION_MODE else "🟢 실전"
    print(f"[모드] {mode_label}")

    print("[1/6] 시장 데이터 수집…")
    market = collect_market()
    kospi_date = _kospi_date(market["snapshot"])
    today = dt.date.today().isoformat()

    if not force and kospi_date != today:
        print("오늘은 거래일이 아니거나 데이터 미반영 → 종료")
        return 0

    trade_date = (kospi_date or today).replace("-", "")

    print("[2/6] 수급 수집…")
    flows = collect_flows(trade_date)

    print("[3/6] 섹터·뉴스 수집…")
    sectors = collect_sectors(config.TOP_SECTORS)
    news = collect_news(config.NEWS_RSS_KR, config.NEWS_RSS_US, config.MAX_NEWS_PER_FEED)

    print("[4/6] 상관관계 산출…")
    corr = compute_correlations(market["closes"], config.CORR_LOOKBACK)

    bundle = {
        "snapshot": market["snapshot"],
        "supplementary": market["supplementary"],
        "flows": flows,
        "sectors": sectors,
        "news": news,
        "correlations": corr,
    }

    print("[5/6] 레포트 생성…")
    if config.SIMULATION_MODE:
        from simulate import generate_simulation
        report_md = generate_simulation(bundle)
        print("     └─ 시뮬레이션 템플릿 사용 (API 비용 없음)")
    else:
        if not config.ANTHROPIC_API_KEY:
            print("     └─ ❌ ANTHROPIC_API_KEY 미설정. SIMULATION_MODE=true 로 되돌립니다.")
            from simulate import generate_simulation
            report_md = generate_simulation(bundle)
        else:
            from analyze import generate_report
            report_md = generate_report(bundle)
            print("     └─ Claude AI 분석 완료")

    print("[6/6] 렌더링 & 발송…")
    out = render(report_md, bundle)
    print(f"  - {out['md_path']}\n  - {out['html_path']}")

    sim_tag = " [시뮬레이션]" if config.SIMULATION_MODE else ""
    subject = f"[국내증시 데일리{sim_tag}] {out['date']} 코스피·코스닥 분석 레포트"
    send_email(subject, out["html"])
    send_slack(f"*{subject}*\n\n{report_md[:2800]}")
    print(f"완료 ({mode_label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(force="--force" in sys.argv))
