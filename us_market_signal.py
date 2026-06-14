"""
us_market_signal.py
────────────────────────────────────────────────────────
미국 주식 매수 후보 + SOX 반도체 지수 → 텔레그램 알림
기존 kr-market-report 레포에 추가하는 스크립트

필요 환경변수 (GitHub Secrets):
  TELEGRAM_TOKEN  - 기존 봇 토큰 그대로 사용
  TELEGRAM_CHAT_ID    - 기존 채팅 ID 그대로 사용

필요 라이브러리:
  pip install yfinance requests
────────────────────────────────────────────────────────
"""

import os
import requests
import yfinance as yf
from datetime import datetime, timezone, timedelta


# ── 설정 ──────────────────────────────────────────────

# 매수 후보 종목 (원하는 종목 자유롭게 추가/변경)
US_CANDIDATES = ["NVDA", "AMZN"]

# SOX 지수 티커 (Yahoo Finance 기준)
SOX_TICKER = "^SOX"

# 텔레그램
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# 한국 시간 기준
KST = timezone(timedelta(hours=9))


# ── 데이터 수집 ───────────────────────────────────────

def get_price_info(ticker: str) -> dict:
    """종목/지수의 전일 종가, 등락률, 거래량 반환"""
    tk = yf.Ticker(ticker)
    hist = tk.history(period="5d")

    if hist.empty or len(hist) < 2:
        return {"error": True}

    last_close = hist["Close"].iloc[-1]
    prev_close = hist["Close"].iloc[-2]
    change_pct = (last_close - prev_close) / prev_close * 100

    result = {
        "ticker": ticker,
        "close": last_close,
        "change_pct": change_pct,
        "error": False,
    }

    # 종목은 거래량 및 52주 고저 추가
    if ticker != SOX_TICKER:
        volume = hist["Volume"].iloc[-1]
        avg_volume = hist["Volume"].mean()
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

        info = tk.info
        week52_high = info.get("fiftyTwoWeekHigh", 0)
        week52_low = info.get("fiftyTwoWeekLow", 0)
        near_high = (
            (last_close / week52_high >= 0.90) if week52_high > 0 else False
        )

        result.update({
            "volume_ratio": volume_ratio,
            "near_52w_high": near_high,
            "week52_high": week52_high,
        })

    return result


def get_sox_signal(sox_data: dict) -> tuple[str, str]:
    """SOX 등락률 → 환경 판단 문자열 반환"""
    if sox_data.get("error"):
        return "확인불가", "⚪"

    chg = sox_data["change_pct"]
    if chg >= 1.5:
        return "강세", "🟢"
    elif chg >= -1.0:
        return "보합", "🟡"
    else:
        return "약세", "🔴"


def build_stock_line(data: dict, sox_weak: bool) -> str:
    """종목 1개의 알림 라인 생성"""
    if data.get("error"):
        return f"  • {data['ticker']}: 데이터 조회 실패"

    ticker = data["ticker"]
    close = data["close"]
    chg = data["change_pct"]
    vol_ratio = data.get("volume_ratio", 1.0)
    near_high = data.get("near_52w_high", False)

    # SOX 약세이고 NVDA 등 반도체 종목이면 주의 태그
    SOX_RELATED = ["NVDA", "AMD", "INTC", "MU", "AMAT", "KLAC", "LRCX", "AVGO"]
    caution = " ⚠️반도체약세" if (sox_weak and ticker in SOX_RELATED) else ""

    tags = []
    if vol_ratio >= 1.5:
        tags.append(f"거래량 {vol_ratio:.1f}배")
    if near_high:
        tags.append("52주고점근처")
    tag_str = " | ".join(tags) if tags else "신호대기"

    chg_sign = "+" if chg >= 0 else ""
    return (
        f"  • {ticker}: ${close:,.2f} ({chg_sign}{chg:.2f}%)"
        f"  [{tag_str}]{caution}"
    )


# ── 텔레그램 전송 ──────────────────────────────────────

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    print("텔레그램 전송 완료")


# ── 메인 ──────────────────────────────────────────────

def main():
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    # 1. SOX 지수 조회
    sox_data = get_price_info(SOX_TICKER)
    sox_signal, sox_icon = get_sox_signal(sox_data)
    sox_weak = (sox_signal == "약세")

    if not sox_data.get("error"):
        sox_chg_sign = "+" if sox_data["change_pct"] >= 0 else ""
        sox_line = (
            f"{sox_icon} SOX 반도체지수: "
            f"{sox_data['close']:,.0f} "
            f"({sox_chg_sign}{sox_data['change_pct']:.2f}%) "
            f"→ {sox_signal}"
        )
    else:
        sox_line = "⚪ SOX 반도체지수: 조회 실패"

    # 2. 종목 조회
    stock_lines = []
    for ticker in US_CANDIDATES:
        data = get_price_info(ticker)
        stock_lines.append(build_stock_line(data, sox_weak))

    stocks_str = "\n".join(stock_lines)

    # 3. 시장 환경 판단 (SOX 기반 간단 로직)
    if sox_weak:
        market_env = "🔴 관망 (반도체 약세 — 신규 매수 주의)"
    elif sox_signal == "강세":
        market_env = "🟢 매수 가능 (반도체 강세)"
    else:
        market_env = "🟡 선별 매수 (보합 — 종목별 판단)"

    # 4. 메시지 조립
    message = f"""🇺🇸 <b>미국 시장 신호</b> | {now_kst}

{sox_line}

📈 <b>매수 후보</b>
{stocks_str}

⚠️ <b>오늘 시장 환경</b>
{market_env}

─────────────────
💡 SOX 약세 시 반도체 종목 매수 주의
📌 최종 판단은 본인이 직접 확인 후 결정"""

    print(message)
    send_telegram(message)


if __name__ == "__main__":
    main()
