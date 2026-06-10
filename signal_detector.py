"""
=============================================================
  V4.1 시그널 탐지기
  매일 장 마감 후 조건 충족 종목을 텔레그램으로 알림
  
  조건 (V4.1):
    1) 200일선 기울기 > 0 (우상향)
    2) 이격률 < 8% (수렴)
    3) 전일 종가 ≤ 20일선 → 당일 종가 > 20일선 (돌파)
    4) 당일 양봉
    5) 당일 거래량 > 20일 평균 거래량 × 1.2 (급증)
=============================================================
"""

import os
import time
import requests
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from io import StringIO

# ── 설정 ──────────────────────────────────
SMA_LONG     = 200
SMA_SHORT    = 20
GAP_PCT      = 8.0
SLOPE_WINDOW = 5
VOLUME_SURGE = 1.2
LOOKBACK     = 300   # 데이터 수집 기간 (거래일 기준 충분히 넉넉하게)

CORE_KEYWORDS = ["반도체", "전자부품", "디스플레이", "통신 및 방송 장비"]

# GitHub Secrets에서 자동으로 읽어옴
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
# ──────────────────────────────────────────


# ────────────────────────────────────────────────────────
#  1. 종목 리스트 수집 (KOSPI 반도체·IT 시총 상위)
# ────────────────────────────────────────────────────────
def get_tickers() -> list:
    base = datetime.today()
    for i in range(10):
        d = (base - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            url_desc = (f"https://raw.githubusercontent.com/FinanceData/"
                        f"fdr_krx_data_cache/refs/heads/master/data/listing/desc/{d}.csv")
            url_krx  = (f"https://raw.githubusercontent.com/FinanceData/"
                        f"fdr_krx_data_cache/refs/heads/master/data/listing/krx/{d}.csv")
            desc = pd.read_csv(StringIO(requests.get(url_desc, timeout=8).text), dtype={"Code": str})
            krx  = pd.read_csv(StringIO(requests.get(url_krx,  timeout=8).text), dtype={"Code": str})
            desc["Code"] = desc["Code"].str.zfill(6)
            krx["Code"]  = krx["Code"].str.zfill(6)
            merged = desc.merge(krx[["Code","Marcap"]], on="Code", how="left")
            mask = (
                merged["Market"] == "KOSPI") & (
                merged["Industry"].fillna("").apply(
                    lambda x: any(k in x for k in CORE_KEYWORDS))
            )
            it = merged[mask].copy()
            it["Marcap"] = pd.to_numeric(it["Marcap"], errors="coerce").fillna(0)
            tickers = it.sort_values("Marcap", ascending=False).head(30)
            names   = tickers.set_index("Code")["Name"].to_dict()
            print(f"  → KOSPI 반도체·IT {len(tickers)}개 ({d} 기준)")
            return tickers["Code"].tolist(), names
        except Exception:
            continue

    # 대체 하드코딩
    fallback = {
        "005930": "삼성전자",   "000660": "SK하이닉스",  "009150": "삼성전기",
        "066570": "LG전자",     "011070": "LG이노텍",    "000990": "DB하이텍",
        "034220": "LG디스플레이","108320": "LX세미콘",    "007660": "이수페타시스",
        "353200": "대덕전자",   "090460": "비에이치",     "248070": "솔루엠",
        "001820": "삼화콘덴서", "195870": "해성디에스",   "007810": "코리아써키트",
        "033240": "자화전자",   "005690": "파미셀",       "336370": "솔루스첨단소재",
        "020150": "롯데에너지머티리얼즈", "272210": "한화시스템",
    }
    print(f"  → 하드코딩 {len(fallback)}개 사용")
    return list(fallback.keys()), fallback


# ────────────────────────────────────────────────────────
#  2. OHLCV 수집
# ────────────────────────────────────────────────────────
def fetch_ohlcv(ticker: str) -> pd.DataFrame:
    end   = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=LOOKBACK * 2)).strftime("%Y-%m-%d")
    try:
        df = fdr.DataReader(ticker, start, end)
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [c.capitalize() for c in df.columns]
        needed = [c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
        df = df[needed].copy()
        df.index = pd.to_datetime(df.index)
        df = df[df["Close"] > 0].tail(LOOKBACK)
        return df
    except Exception:
        return pd.DataFrame()


# ────────────────────────────────────────────────────────
#  3. 시그널 판단 (오늘 조건 충족 여부)
# ────────────────────────────────────────────────────────
def check_signal(ticker: str, df: pd.DataFrame) -> dict | None:
    if len(df) < SMA_LONG + 5:
        return None

    df = df.copy()
    df["sma_long"]  = df["Close"].rolling(SMA_LONG).mean()
    df["sma_short"] = df["Close"].rolling(SMA_SHORT).mean()
    df["slope"]     = df["sma_long"] - df["sma_long"].shift(SLOPE_WINDOW)
    df["gap_pct"]   = (
        abs(df["sma_short"] - df["sma_long"])
        / df["sma_long"].clip(lower=0.0001) * 100
    )
    df["vol_ma20"]  = df["Volume"].rolling(20).mean()

    # 오늘(마지막 행) 기준
    today = df.iloc[-1]
    prev  = df.iloc[-2]

    cond_trend   = today["slope"] > 0
    cond_squeeze = today["gap_pct"] < GAP_PCT
    cond_cross   = (today["Close"] > today["sma_short"]) and \
                   (prev["Close"] <= prev["sma_short"])
    cond_bull    = today["Close"] > today["Open"]
    cond_volume  = today["Volume"] > today["vol_ma20"] * VOLUME_SURGE
    cond_valid   = pd.notna(today["sma_long"]) and pd.notna(today["vol_ma20"])

    if cond_valid and cond_trend and cond_squeeze and cond_cross and cond_bull and cond_volume:
        vol_ratio = today["Volume"] / today["vol_ma20"]
        return {
            "ticker":     ticker,
            "close":      int(today["Close"]),
            "sma200":     int(today["sma_long"]),
            "sma20":      int(today["sma_short"]),
            "gap_pct":    round(today["gap_pct"], 1),
            "vol_ratio":  round(vol_ratio, 1),
            "change_pct": round((today["Close"] - prev["Close"]) / prev["Close"] * 100, 2),
        }
    return None


# ────────────────────────────────────────────────────────
#  4. 텔레그램 메시지 발송
# ────────────────────────────────────────────────────────
def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  텔레그램 토큰/채팅ID 없음 — 콘솔 출력만")
        print(message)
        return

    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print("  ✅ 텔레그램 발송 완료")
        else:
            print(f"  ❌ 발송 실패: {r.status_code} {r.text}")
    except Exception as e:
        print(f"  ❌ 발송 오류: {e}")


# ────────────────────────────────────────────────────────
#  5. 메시지 포맷
# ────────────────────────────────────────────────────────
def format_message(signals: list, names: dict, today_str: str) -> str:
    if not signals:
        return (
            f"📊 <b>V4.1 시그널 탐지 결과</b>\n"
            f"📅 {today_str}\n\n"
            f"오늘 조건 충족 종목 없음\n\n"
            f"<i>※ 투자 판단은 본인 책임입니다</i>"
        )

    lines = [
        f"📊 <b>V4.1 시그널 탐지 결과</b>",
        f"📅 {today_str}",
        f"🎯 조건 충족 종목: <b>{len(signals)}개</b>\n",
    ]

    for s in signals:
        name = names.get(s["ticker"], s["ticker"])
        emoji = "🟢" if s["change_pct"] >= 0 else "🔴"
        lines += [
            f"{emoji} <b>{name}</b> ({s['ticker']})",
            f"   현재가: {s['close']:,}원  ({s['change_pct']:+.2f}%)",
            f"   200일선: {s['sma200']:,}원",
            f"   20일선:  {s['sma20']:,}원",
            f"   이격률:  {s['gap_pct']}%",
            f"   거래량:  평균의 {s['vol_ratio']}배",
            "",
        ]

    lines += [
        "─" * 25,
        "<i>※ 시그널은 참고용입니다</i>",
        "<i>※ 반드시 직접 차트 확인 후 판단하세요</i>",
        "<i>※ 투자 손익은 본인 책임입니다</i>",
    ]
    return "\n".join(lines)


# ────────────────────────────────────────────────────────
#  6. 메인 실행
# ────────────────────────────────────────────────────────
def main():
    today_str = datetime.today().strftime("%Y년 %m월 %d일")
    print(f"{'='*50}")
    print(f"  V4.1 시그널 탐지 시작: {today_str}")
    print(f"{'='*50}")

    # 종목 리스트
    print("\n[1/3] 종목 리스트 수집...")
    tickers, names = get_tickers()

    # 시그널 탐지
    print(f"\n[2/3] {len(tickers)}개 종목 시그널 탐지 중...")
    signals = []
    for idx, ticker in enumerate(tickers, 1):
        df = fetch_ohlcv(ticker)
        if df.empty:
            continue
        result = check_signal(ticker, df)
        if result:
            result["name"] = names.get(ticker, ticker)
            signals.append(result)
            print(f"  🎯 시그널 발생: {names.get(ticker, ticker)} ({ticker})")
        if idx % 5 == 0:
            print(f"  진행: {idx}/{len(tickers)}")
        time.sleep(0.3)

    print(f"\n  → 총 {len(signals)}개 시그널 발생")

    # 텔레그램 발송
    print("\n[3/3] 텔레그램 발송...")
    message = format_message(signals, names, today_str)
    send_telegram(message)

    print(f"\n✅ 완료")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
