"""
기술적 지표 계산 모듈
입력: OHLCV DataFrame (date, open, high, low, close, volume)
"""

import pandas as pd
import numpy as np


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()

def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()

def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(n).mean()
    loss  = (-delta.clip(upper=0)).rolling(n).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    hl  = df["high"] - df["low"]
    hc  = (df["high"] - df["close"].shift()).abs()
    lc  = (df["low"]  - df["close"].shift()).abs()
    tr  = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid  = sma(close, n)
    std  = close.rolling(n).std()
    return mid + k * std, mid, mid - k * std

def volume_ratio(volume: pd.Series, n: int = 20) -> pd.Series:
    return volume / volume.rolling(n).mean()

def highest_high(high: pd.Series, n: int = 252) -> pd.Series:
    return high.rolling(n).max()

def add_all(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    df["ma5"]    = sma(c, 5)
    df["ma10"]   = sma(c, 10)
    df["ma20"]   = sma(c, 20)
    df["ma60"]   = sma(c, 60)
    df["ma120"]  = sma(c, 120)
    df["rsi14"]  = rsi(c, 14)
    df["atr14"]  = atr(df, 14)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = bollinger(c, 20)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    df["vol_ratio20"] = volume_ratio(v, 20)
    df["vol_ratio5"]  = volume_ratio(v, 5)
    df["high_52w"]    = highest_high(h, 252)
    df["pct_from_52w_high"] = (c - df["high_52w"]) / df["high_52w"] * 100
    df["atr_ratio"]   = df["atr14"] / c * 100
    df["mom20"]  = c.pct_change(20) * 100
    df["mom60"]  = c.pct_change(60) * 100
    return df
