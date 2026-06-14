"""
현재 시점 기준 스킬 조건 만족 종목 스캔 → 다음 주 진입 후보
"""

import pandas as pd
from .indicators import add_all
from .skills import SKILL_REGISTRY

SKILL_KO = {
    "vcp":                 "VCP(변동성수축)",
    "sector_rotation":     "섹터로테이션",
    "flow_momentum":       "플로우모멘텀",
    "pre_surge":           "급등전징후",
    "contrarian_reversal": "역추세반전",
    "narrative_momentum":  "내러티브모멘텀",
    "value_chain":         "밸류체인",
    "best_of_best":        "베스트오브베스트",
}


def scan_current_signals(ohlcv_dict, name_map=None, market="KR"):
    """
    현재 시점(마지막 거래일) 기준으로 각 스킬 조건을 만족하는 종목 스캔
    반환: {skill: [{ticker, name, close, signal_date}]}
    """
    if name_map is None:
        name_map = {}

    results = {sk: [] for sk in SKILL_REGISTRY}

    for ticker, raw_df in ohlcv_dict.items():
        if raw_df.empty or len(raw_df) < 60:
            continue
        df = add_all(raw_df)
        last_date = df["date"].iloc[-1]
        name      = name_map.get(str(ticker), ticker)
        display   = f"{name}({ticker})" if name != ticker else ticker
        close     = df["close"].iloc[-1]

        for skill_name, skill_fn in SKILL_REGISTRY.items():
            try:
                signals = skill_fn(df)
                # 마지막 거래일 또는 최근 5거래일 내 신호 발생 종목
                recent_signals = [
                    s for s in signals
                    if (last_date - s).days <= 7
                ]
                if recent_signals:
                    results[skill_name].append({
                        "ticker":       ticker,
                        "name":         display,
                        "close":        int(close) if market == "KR" else round(close, 2),
                        "signal_date":  recent_signals[-1].strftime("%m/%d"),
                        "market":       market,
                    })
            except Exception as e:
                print(f"[WARN] scan {skill_name}/{ticker}: {e}")

    return results


def format_scan_results(kr_signals, us_signals=None):
    """
    스캔 결과를 HTML 렌더링용으로 포맷
    반환: {skill: {ko_name, kr: [...], us: [...]}}
    """
    out = {}
    for sk in SKILL_REGISTRY:
        kr = kr_signals.get(sk, [])
        us = us_signals.get(sk, []) if us_signals else []
        if kr or us:
            out[sk] = {
                "ko_name": SKILL_KO.get(sk, sk),
                "kr":      sorted(kr, key=lambda x: x["name"]),
                "us":      sorted(us, key=lambda x: x["name"]),
            }
    return out
