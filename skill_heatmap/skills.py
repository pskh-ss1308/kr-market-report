"""
스킬별 매수 신호 로직
각 함수는 DataFrame을 받아 신호 발생일 날짜 목록을 반환
"""

import pandas as pd
import numpy as np
from .indicators import add_all
from collections import Counter


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    if "ma20" not in df.columns:
        df = add_all(df)
    return df

def _has_min_bars(df: pd.DataFrame, n: int = 120) -> bool:
    return len(df) >= n


def vcp(df: pd.DataFrame) -> list:
    if not _has_min_bars(df, 120):
        return []
    df = _prep(df)
    signals = []
    for i in range(60, len(df)):
        row    = df.iloc[i]
        row_60 = df.iloc[i - 60]
        if pd.isna(row["ma60"]) or pd.isna(row["atr_ratio"]):
            continue
        cond1 = row["pct_from_52w_high"] >= -25
        cond2 = row["atr_ratio"] < row_60["atr_ratio"] * 0.6
        cond3 = row["vol_ratio20"] < 1.0
        cond4 = row["close"] > row["ma60"]
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def sector_rotation(df: pd.DataFrame) -> list:
    if not _has_min_bars(df, 80):
        return []
    df = _prep(df)
    signals = []
    for i in range(60, len(df)):
        row = df.iloc[i]
        if pd.isna(row["mom60"]):
            continue
        cond1 = row["mom20"] > 5
        cond2 = row["mom60"] > 10
        cond3 = row["vol_ratio20"] > 1.2
        cond4 = row["close"] > row["ma20"] > row["ma60"]
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def flow_momentum(df: pd.DataFrame) -> list:
    if not _has_min_bars(df, 30):
        return []
    df = _prep(df)
    signals = []
    for i in range(20, len(df)):
        row  = df.iloc[i]
        prev = df.iloc[i - 1]
        if pd.isna(row["rsi14"]):
            continue
        cond1 = row["vol_ratio20"] > 2.5
        cond2 = row["close"] > prev["close"]
        cond3 = row["close"] > row["ma20"]
        cond4 = 40 <= row["rsi14"] <= 70
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def pre_surge(df: pd.DataFrame) -> list:
    if not _has_min_bars(df, 80):
        return []
    df = _prep(df)
    signals = []
    for i in range(60, len(df)):
        row    = df.iloc[i]
        window = df["bb_width"].iloc[i-60:i]
        if pd.isna(row["bb_width"]) or pd.isna(row["rsi14"]):
            continue
        bb_pct = (row["bb_width"] - window.min()) / (window.max() - window.min() + 1e-9)
        cond1 = bb_pct < 0.15
        cond2 = row["vol_ratio5"] < 0.7
        cond3 = row["close"] > row["bb_mid"]
        cond4 = 45 <= row["rsi14"] <= 62
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def contrarian_reversal(df: pd.DataFrame) -> list:
    if not _has_min_bars(df, 30):
        return []
    df = _prep(df)
    signals = []
    for i in range(20, len(df)):
        row  = df.iloc[i]
        prev = df.iloc[i - 1]
        if pd.isna(row["rsi14"]):
            continue
        cond1 = row["rsi14"] < 30
        cond2 = row["close"] > row["open"]
        cond3 = row["close"] > prev["low"]
        cond4 = row["vol_ratio20"] > 1.0
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def narrative_momentum(df: pd.DataFrame) -> list:
    if not _has_min_bars(df, 120):
        return []
    df = _prep(df)
    signals = []
    for i in range(60, len(df)):
        row = df.iloc[i]
        if pd.isna(row["ma60"]):
            continue
        cond1 = row["high"] >= row["high_52w"] * 0.998
        cond2 = row["mom20"] > 8
        cond3 = row["vol_ratio20"] > 1.5
        cond4 = row["ma5"] > row["ma20"] > row["ma60"]
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def value_chain(df: pd.DataFrame) -> list:
    if not _has_min_bars(df, 80):
        return []
    df = _prep(df)
    signals = []
    for i in range(60, len(df)):
        row       = df.iloc[i]
        ma20_prev = df["ma20"].iloc[i - 5]
        if pd.isna(row["mom60"]) or pd.isna(row["rsi14"]):
            continue
        cond1 = row["mom60"] > 15
        cond2 = row["ma20"] > ma20_prev
        cond3 = 1.0 < row["vol_ratio20"] < 2.0
        cond4 = 50 <= row["rsi14"] <= 65
        if cond1 and cond2 and cond3 and cond4:
            signals.append(row["date"])
    return signals


def best_of_best(df: pd.DataFrame) -> list:
    skill_funcs = [vcp, sector_rotation, flow_momentum, pre_surge, narrative_momentum]
    all_signals = []
    for fn in skill_funcs:
        all_signals.extend(fn(df))
    counts = Counter(all_signals)
    return [date for date, cnt in counts.items() if cnt >= 2]


SKILL_REGISTRY = {
    "vcp":                 vcp,
    "sector_rotation":     sector_rotation,
    "flow_momentum":       flow_momentum,
    "pre_surge":           pre_surge,
    "contrarian_reversal": contrarian_reversal,
    "narrative_momentum":  narrative_momentum,
    "value_chain":         value_chain,
    "best_of_best":        best_of_best,
}
