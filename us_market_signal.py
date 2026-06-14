"""
us_market_signal.py
────────────────────────────────────────────────────────
미국 + 한국 시장 신호 → 텔레그램 알림
매일 아침 6:00 KST 자동 실행

필요 환경변수 (GitHub Secrets):
  TELEGRAM_TOKEN   - 텔레그램 봇 토큰
  TELEGRAM_CHAT_ID - 채팅 ID
  KIS_APP_KEY      - 한국투자증권 API 키 (외국인/기관 순매수용)
  KIS_APP_SECRET   - 한국투자증권 API 시크릿
────────────────────────────────────────────────────────
"""

import os
import requests
import yfinance as yf
from datetime import datetime, timezone, timedelta

# ── 설정 ──────────────────────────────────────────────

# 미국 매수 후보 종목
US_CANDIDATES = ["NVDA", "AMZN"]

# 한국 대형주 (종목코드: 이름)
KR_CANDIDATES = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "005380": "현대차",
    "051910": "LG화학",
    "035420": "NAVER",
}

# 한국 반도체 소부장 (장비 + 소재)
KR_SOBUJANG = {
    "042700": "한미반도체",
    "240810": "원익IPS",
    "036930": "주성엔지니어링",
    "319660": "피에스케이",
    "031980": "피에스케이홀딩스",
    "058470": "리노공업",
    "084370": "유진테크",
    "067310": "하나마이크론",
}

# 한국 장 예측 지표
KR_PREDICTORS = {
    "NQ=F":  "나스닥 선물",
    "KORU":   "KORU ETF (한국 대형주 3배)",
    "^SOX":   "SOX 반도체지수",
    "KRW=X":  "달러/원 환율",
}

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
KIS_APP_KEY      = os.environ.get("KIS_APP_KEY", "")
KIS_APP_SECRET   = os.environ.get("KIS_APP_SECRET", "")

KST = timezone(timedelta(hours=9))


# ── KIS API — 접근토큰 발급 ───────────────────────────

def get_kis_token() -> str:
    if not KIS_APP_KEY or not KIS_APP_SECRET:
        return ""
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
    }
    try:
        resp = requests.post(url, json=body, timeout=10)
        return resp.json().get("access_token", "")
    except Exception:
        return ""


# ── KIS API — 외국인/기관 순매수 ─────────────────────

def get_kr_price_returns(code: str) -> dict:
    """KRX 종목 1주/1개월 수익률 반환 (yfinance .KS/.KQ)"""
    for suffix in [".KS", ".KQ"]:
        try:
            tk = yf.Ticker(code + suffix)
            hist = tk.history(period="1mo")
            if hist.empty or len(hist) < 2:
                continue
            last  = hist["Close"].iloc[-1]
            w_idx = -6 if len(hist) >= 6 else 0
            ret_1w = (last - hist["Close"].iloc[w_idx]) / hist["Close"].iloc[w_idx] * 100
            ret_1m = (last - hist["Close"].iloc[0])  / hist["Close"].iloc[0]  * 100
            return {"ret_1w": ret_1w, "ret_1m": ret_1m, "error": False}
        except Exception:
            continue
    return {"error": True}


def get_kr_investor_flow(code: str, token: str) -> dict:
    """외국인 + 기관 순매수 금액(억원) 반환"""
    if not token:
        return {"error": True}
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-investor"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST01010900",
        "content-type": "application/json; charset=utf-8",
    }
    params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        raw = resp.json()
        print(f"[KIS DEBUG {code}] rt_cd={raw.get('rt_cd')} msg={raw.get('msg1')} output={str(raw.get('output',''))[:200]}")
        output = raw.get("output", [])
        # output이 리스트면 첫번째, 딕셔너리면 그대로
        data = output[0] if isinstance(output, list) and output else output if isinstance(output, dict) else {}

        # 금액(만원) 필드 우선, 없으면 수량*가격으로 계산
        def to_bil(amt_str, qty_str, price_str):
            amt = float(amt_str or 0)
            if amt != 0:
                return round(amt / 1e4, 1)  # 만원 → 억원
            qty   = int(qty_str or 0)
            price = float(price_str or 0)
            return round(qty * price / 1e8, 1)

        foreign_bil = to_bil(
            data.get("frgn_ntby_amt", 0),
            data.get("frgn_ntby_qty", 0),
            data.get("stck_prpr", 0)
        )
        inst_bil = to_bil(
            data.get("orgn_ntby_amt", 0),
            data.get("orgn_ntby_qty", 0),
            data.get("stck_prpr", 0)
        )
        return {
            "foreign": foreign_bil,
            "institution": inst_bil,
            "both_buying": foreign_bil > 0 and inst_bil > 0,
            "error": False,
        }
    except Exception:
        return {"error": True}


# ── Yahoo Finance — 미국 지표 ─────────────────────────

def get_price_info(ticker: str) -> dict:
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d")
        if hist.empty or len(hist) < 2:
            return {"error": True}
        last  = hist["Close"].iloc[-1]
        prev  = hist["Close"].iloc[-2]
        chg   = (last - prev) / prev * 100

        # 1주 / 1개월 수익률
        try:
            hist_1m = tk.history(period="1mo")
            week_ago_idx = -6 if len(hist_1m) >= 6 else 0
            price_1w_ago = hist_1m["Close"].iloc[week_ago_idx]
            price_1m_ago = hist_1m["Close"].iloc[0]
            ret_1w = (last - price_1w_ago) / price_1w_ago * 100
            ret_1m = (last - price_1m_ago) / price_1m_ago * 100
        except Exception:
            ret_1w, ret_1m = None, None

        result = {
            "ticker": ticker, "close": last, "change_pct": chg,
            "ret_1w": ret_1w, "ret_1m": ret_1m, "error": False
        }

        # 미국 개별 종목만 추가 정보
        if ticker in US_CANDIDATES:
            vol       = hist["Volume"].iloc[-1]
            avg_vol   = hist["Volume"].mean()
            vol_ratio = vol / avg_vol if avg_vol > 0 else 1.0
            info      = tk.info
            w52_high  = info.get("fiftyTwoWeekHigh", 0)
            near_high = (last / w52_high >= 0.90) if w52_high > 0 else False
            result.update({"volume_ratio": vol_ratio, "near_52w_high": near_high})

        return result
    except Exception:
        return {"error": True}


# ── 신호 판단 ─────────────────────────────────────────

def sox_signal(chg: float) -> tuple[str, str]:
    if chg >= 1.5:  return "강세", "🟢"
    if chg >= -1.0: return "보합", "🟡"
    return "약세", "🔴"

def krw_signal(close: float) -> tuple[str, str]:
    """환율 1,380 기준 — 높으면 외국인 이탈 우려"""
    if close < 1340:   return "원화강세 (외국인 유입 우호적)", "🟢"
    if close < 1390:   return "보통", "🟡"
    return "원화약세 (외국인 이탈 주의)", "🔴"

def korea_outlook(predictors: dict) -> tuple[str, str]:
    """한국 장 전망 종합 판단"""
    score = 0
    nq  = predictors.get("NQ=F", {})
    koru = predictors.get("KORU", {})
    sox  = predictors.get("^SOX", {})
    krw  = predictors.get("KRW=X", {})

    if not nq.get("error")   and nq["change_pct"] > 0:    score += 2
    if not koru.get("error") and koru["change_pct"] > 0:  score += 3  # 한국 직접 반영
    if not sox.get("error")  and sox["change_pct"] > 1.5: score += 1
    if not krw.get("error")  and krw["close"] < 1390:     score += 1

    if score >= 5: return "매수 우호적", "🟢"
    if score >= 3: return "중립 — 종목별 판단", "🟡"
    return "관망 권장", "🔴"


# ── 메시지 조립 ───────────────────────────────────────

def build_message(
    sox_data, us_stocks, kr_predictors_data, kr_stocks, kis_token, kr_sobujang
) -> str:
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    # ─ 미국 섹션 ─
    if not sox_data.get("error"):
        sig, icon = sox_signal(sox_data["change_pct"])
        chg_str = f"{sox_data['change_pct']:+.2f}%"
        sox_line = f"{icon} SOX 반도체지수: {sox_data['close']:,.0f} ({chg_str}) → {sig}"
    else:
        sox_line = "⚪ SOX: 조회 실패"

    us_lines = []
    for d in us_stocks:
        if d.get("error"):
            us_lines.append(f"  • {d['ticker']}: 조회 실패")
            continue
        tags = []
        if d.get("volume_ratio", 0) >= 1.5: tags.append(f"거래량 {d['volume_ratio']:.1f}배")
        if d.get("near_52w_high"):           tags.append("52주 고점 근처")
        tag_str = " | ".join(tags) if tags else "신호 없음"
        sox_weak = not sox_data.get("error") and sox_data["change_pct"] < -1.0
        caution  = " ⚠️반도체약세" if sox_weak and d["ticker"] in ["NVDA","AMD"] else ""
        ret_str = ""
        if d.get("ret_1w") is not None:
            ret_str = "\n      📈 1주 {:+.1f}% | 1개월 {:+.1f}%".format(d['ret_1w'], d['ret_1m'])
        us_lines.append(
            f"  • {d['ticker']}: ${d['close']:,.2f} ({d['change_pct']:+.2f}%)  [{tag_str}]{caution}{ret_str}"
        )

    # ─ 한국 예측 섹션 ─
    pred_lines = []
    for ticker, name in KR_PREDICTORS.items():
        d = kr_predictors_data.get(ticker, {"error": True})
        if d.get("error"):
            pred_lines.append(f"  • {name}: 조회 실패")
            continue
        chg = d["change_pct"]
        if ticker == "KRW=X":
            sig, icon = krw_signal(d["close"])
            pred_lines.append(f"  {icon} {name}: {d['close']:,.0f}원  → {sig}")
        else:
            icon = "🟢" if chg > 0 else "🔴"
            ret_str = ""
            if d.get("ret_1w") is not None:
                ret_str = f"  (1주 {d['ret_1w']:+.1f}% | 1개월 {d['ret_1m']:+.1f}%)"
            pred_lines.append(f"  {icon} {name}: {chg:+.2f}%{ret_str}")

    outlook, out_icon = korea_outlook(kr_predictors_data)

    # ─ 한국 대형주 섹션 ─
    kr_lines = []
    if kis_token:
        for code, name in KR_CANDIDATES.items():
            flow = get_kr_investor_flow(code, kis_token)
            ret  = get_kr_price_returns(code)
            if flow.get("error"):
                kr_lines.append(f"  • {name}: 조회 실패")
                continue
            f_str = f"외국인 {flow['foreign']:+.0f}억"
            i_str = f"기관 {flow['institution']:+.0f}억"
            mark  = " ✅" if flow["both_buying"] else ""
            ret_str = ""
            if not ret.get("error"):
                ret_str = "\n      📈 1주 {:+.1f}% | 1개월 {:+.1f}%".format(ret['ret_1w'], ret['ret_1m'])
            kr_lines.append(f"  • {name}: {f_str} | {i_str}{mark}{ret_str}")
    else:
        kr_lines.append("  • KIS API 미설정 — 외국인/기관 데이터 없음")

    # 소부장 섹션
    sb_lines = []
    if kr_sobujang:
        for code, (name, flow) in kr_sobujang.items():
            if flow.get("error"):
                sb_lines.append(f"  • {name}: 조회 실패")
                continue
            f_str = f"외국인 {flow['foreign']:+.0f}억"
            i_str = f"기관 {flow['institution']:+.0f}억"
            mark  = " ✅" if flow["both_buying"] else ""
            ret   = get_kr_price_returns(code)
            ret_str = ""
            if not ret.get("error"):
                ret_str = "\n      📈 1주 {:+.1f}% | 1개월 {:+.1f}%".format(ret['ret_1w'], ret['ret_1m'])
            sb_lines.append(f"  • {name}: {f_str} | {i_str}{mark}{ret_str}")
    else:
        sb_lines.append("  • KIS API 미설정")

    us_str       = "\n".join(us_lines)
    pred_str     = "\n".join(pred_lines)
    kr_str       = "\n".join(kr_lines)
    sobujang_str = "\n".join(sb_lines)

    return f"""🌏 <b>시장 신호</b> | {now}

━━━━━━━━━━━━━━━━━━━
🇺🇸 <b>미국 시장</b>
{sox_line}

📈 <b>매수 후보</b>
{us_str}

━━━━━━━━━━━━━━━━━━━
🇰🇷 <b>한국 장 예측</b>
{pred_str}

{out_icon} <b>오늘 한국 장 전망: {outlook}</b>

📊 <b>대형주 외국인/기관 수급</b>
{kr_str}
✅ = 외국인 + 기관 동시 순매수

━━━━━━━━━━━━━━━━━━━
🔧 <b>반도체 소부장 수급</b>
{sobujang_str}
✅ = 외국인 + 기관 동시 순매수

━━━━━━━━━━━━━━━━━━━
📌 최종 판단은 본인이 직접 확인 후 결정"""


# ── 텔레그램 전송 ──────────────────────────────────────

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=10)
    resp.raise_for_status()
    print("전송 완료")


# ── 메인 ──────────────────────────────────────────────

def main():
    print("데이터 수집 중...")

    # 미국 데이터
    sox_data  = get_price_info("^SOX")
    us_stocks = [get_price_info(t) for t in US_CANDIDATES]

    # 한국 예측 지표
    kr_pred = {t: get_price_info(t) for t in KR_PREDICTORS}

    # KIS 토큰 + 한국 대형주 수급
    kis_token = get_kis_token()

    # 소부장 수급
    sobujang_flows = {}
    if kis_token:
        for code, name in KR_SOBUJANG.items():
            sobujang_flows[code] = (name, get_kr_investor_flow(code, kis_token))

    msg = build_message(sox_data, us_stocks, kr_pred, KR_CANDIDATES, kis_token, sobujang_flows)
    print(msg)
    send_telegram(msg)


if __name__ == "__main__":
    main()
