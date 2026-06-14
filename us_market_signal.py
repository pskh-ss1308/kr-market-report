"""
us_market_signal.py
────────────────────────────────────────────────────────
미국 + 한국 시장 신호 → 텔레그램 알림 + data.json 생성
매일 아침 6:00 KST 자동 실행

필요 환경변수 (GitHub Secrets):
  TELEGRAM_TOKEN   - 텔레그램 봇 토큰
  TELEGRAM_CHAT_ID - 채팅 ID
  KIS_APP_KEY      - 한국투자증권 API 키
  KIS_APP_SECRET   - 한국투자증권 API 시크릿
────────────────────────────────────────────────────────
"""

import os, json, requests, yfinance as yf
from datetime import datetime, timezone, timedelta
from pathlib import Path

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
KIS_APP_KEY      = os.environ.get("KIS_APP_KEY", "")
KIS_APP_SECRET   = os.environ.get("KIS_APP_SECRET", "")
KST = timezone(timedelta(hours=9))

US_CANDIDATES = ["NVDA", "AMZN"]
KR_CANDIDATES = {
    "005930": "삼성전자", "000660": "SK하이닉스",
    "005380": "현대차",   "051910": "LG화학", "035420": "NAVER",
}
KR_SOBUJANG = {
    "042700": "한미반도체",    "240810": "원익IPS",
    "036930": "주성엔지니어링","319660": "피에스케이",
    "031980": "피에스케이홀딩스","058470": "리노공업",
    "084370": "유진테크",      "067310": "하나마이크론",
}
KR_PREDICTORS = {
    "NQ=F": "나스닥 선물", "KORU": "KORU ETF",
    "^SOX": "SOX 반도체지수", "KRW=X": "달러/원 환율",
}

# ── KIS ───────────────────────────────────────────────
def get_kis_token():
    if not KIS_APP_KEY: return ""
    try:
        r = requests.post(
            "https://openapi.koreainvestment.com:9443/oauth2/tokenP",
            json={"grant_type":"client_credentials","appkey":KIS_APP_KEY,"appsecret":KIS_APP_SECRET},
            timeout=10)
        return r.json().get("access_token","")
    except: return ""

def get_kr_investor_flow(code, token):
    if not token: return {"error":True}
    try:
        r = requests.get(
            "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-investor",
            headers={"authorization":f"Bearer {token}","appkey":KIS_APP_KEY,
                     "appsecret":KIS_APP_SECRET,"tr_id":"FHKST01010900",
                     "content-type":"application/json; charset=utf-8"},
            params={"fid_cond_mrkt_div_code":"J","fid_input_iscd":code},
            timeout=10)
        raw = r.json()
        output = raw.get("output",[])
        data = output[0] if isinstance(output,list) and output else output if isinstance(output,dict) else {}
        price = float(data.get("stck_clpr") or data.get("stck_prpr") or 0)
        frgn  = round(int(data.get("frgn_ntby_qty") or 0) * price / 1e8, 1)
        inst  = round(int(data.get("orgn_ntby_qty") or 0) * price / 1e8, 1)
        return {"foreign":frgn,"institution":inst,"both_buying":frgn>0 and inst>0,"error":False}
    except: return {"error":True}

# ── Yahoo Finance ─────────────────────────────────────
def get_price_info(ticker):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d")
        if hist.empty or len(hist)<2: return {"ticker":ticker,"error":True}
        last = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2]
        chg  = (last-prev)/prev*100
        try:
            h1m = tk.history(period="1mo")
            w_idx = -6 if len(h1m)>=6 else 0
            ret_1w = (last-h1m["Close"].iloc[w_idx])/h1m["Close"].iloc[w_idx]*100
            ret_1m = (last-h1m["Close"].iloc[0])/h1m["Close"].iloc[0]*100
        except: ret_1w=ret_1m=None
        result = {"ticker":ticker,"close":round(last,2),"change_pct":round(chg,2),
                  "ret_1w":round(ret_1w,1) if ret_1w is not None else None,
                  "ret_1m":round(ret_1m,1) if ret_1m is not None else None,"error":False}
        if ticker in US_CANDIDATES:
            vol = hist["Volume"].iloc[-1]; avg = hist["Volume"].mean()
            result["volume_ratio"] = round(vol/avg,1) if avg>0 else 1.0
            info = tk.info
            w52h = info.get("fiftyTwoWeekHigh",0)
            result["near_52w_high"] = bool(last/w52h>=0.90) if w52h>0 else False
        return result
    except: return {"ticker":ticker,"error":True}

def get_kr_price_returns(code):
    for sfx in [".KS",".KQ"]:
        try:
            tk = yf.Ticker(code+sfx)
            hist = tk.history(period="1mo")
            if hist.empty or len(hist)<2: continue
            last  = hist["Close"].iloc[-1]
            w_idx = -6 if len(hist)>=6 else 0
            return {"ret_1w":round((last-hist["Close"].iloc[w_idx])/hist["Close"].iloc[w_idx]*100,1),
                    "ret_1m":round((last-hist["Close"].iloc[0])/hist["Close"].iloc[0]*100,1),"error":False}
        except: continue
    return {"error":True}

# ── 판단 ──────────────────────────────────────────────
def sox_signal(chg):
    if chg>=1.5: return "강세","🟢"
    if chg>=-1.0: return "보합","🟡"
    return "약세","🔴"

def krw_signal(close):
    if close<1340: return "원화강세 (외국인 유입 우호적)","🟢"
    if close<1390: return "보통","🟡"
    return "원화약세 (외국인 이탈 주의)","🔴"

def korea_outlook(preds):
    score=0
    nq=preds.get("NQ=F",{}); koru=preds.get("KORU",{})
    sox=preds.get("^SOX",{}); krw=preds.get("KRW=X",{})
    if not nq.get("error")   and nq.get("change_pct",0)>0:   score+=2
    if not koru.get("error") and koru.get("change_pct",0)>0: score+=3
    if not sox.get("error")  and sox.get("change_pct",0)>1.5:score+=1
    if not krw.get("error")  and krw.get("close",9999)<1390: score+=1
    if score>=5: return "매수 우호적","🟢"
    if score>=3: return "중립 — 종목별 판단","🟡"
    return "관망 권장","🔴"

# ── 텔레그램 ──────────────────────────────────────────
def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":TELEGRAM_CHAT_ID,"text":msg,"parse_mode":"HTML"},
        timeout=10).raise_for_status()

# ── data.json 저장 ────────────────────────────────────
def save_json(data):
    Path("docs").mkdir(exist_ok=True)
    with open("docs/data.json","w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
    print("docs/data.json 저장 완료")

# ── 메인 ──────────────────────────────────────────────
def main():
    now_kst = datetime.now(KST)
    now_str  = now_kst.strftime("%Y-%m-%d %H:%M KST")

    # 이번 주 레이블 (W + 연간 주차)
    week_label = "W" + now_kst.strftime("%V")

    print("데이터 수집 중...")
    sox_data  = get_price_info("^SOX")
    us_stocks = [get_price_info(t) for t in US_CANDIDATES]
    kr_pred   = {t: get_price_info(t) for t in KR_PREDICTORS}
    kis_token = get_kis_token()

    # 한국 종목 수급 + 수익률
    kr_all = {}
    for code, name in {**KR_CANDIDATES, **KR_SOBUJANG}.items():
        flow = get_kr_investor_flow(code, kis_token)
        ret  = get_kr_price_returns(code)
        group = "대형주" if code in KR_CANDIDATES else "소부장"
        kr_all[code] = {"name":name,"group":group,"flow":flow,"ret":ret}

    outlook, out_icon = korea_outlook(kr_pred)

    # ── 텔레그램 메시지 ──
    sox_line = "⚪ SOX: 조회 실패"
    if not sox_data.get("error"):
        sig, icon = sox_signal(sox_data["change_pct"])
        sox_ret = ""
        if sox_data.get("ret_1w") is not None:
            sox_ret = f"  (1주 {sox_data['ret_1w']:+.1f}% | 1개월 {sox_data['ret_1m']:+.1f}%)"
        sox_line = f"{icon} SOX 반도체지수: {sox_data['close']:,.0f} ({sox_data['change_pct']:+.2f}%){sox_ret} → {sig}"

    us_lines=[]
    for d in us_stocks:
        if d.get("error"): us_lines.append(f"  • {d['ticker']}: 조회 실패"); continue
        tags=[]
        if d.get("volume_ratio",0)>=1.5: tags.append(f"거래량 {d['volume_ratio']:.1f}배")
        if d.get("near_52w_high"): tags.append("52주 고점 근처")
        tag_str=" | ".join(tags) if tags else "신호 없음"
        sox_weak = not sox_data.get("error") and sox_data["change_pct"]<-1.0
        caution  = " ⚠️반도체약세" if sox_weak and d["ticker"] in ["NVDA","AMD"] else ""
        ret_str  = "\n      📈 1주 {:+.1f}% | 1개월 {:+.1f}%".format(d['ret_1w'],d['ret_1m']) if d.get("ret_1w") is not None else ""
        us_lines.append(f"  • {d['ticker']}: ${d['close']:,.2f} ({d['change_pct']:+.2f}%)  [{tag_str}]{caution}{ret_str}")

    pred_lines=[]
    for ticker, name in KR_PREDICTORS.items():
        d=kr_pred.get(ticker,{"error":True})
        if d.get("error"): pred_lines.append(f"  • {name}: 조회 실패"); continue
        chg=d["change_pct"]
        if ticker=="KRW=X":
            sig,icon=krw_signal(d["close"])
            pred_lines.append(f"  {icon} {name}: {d['close']:,.0f}원  → {sig}")
        else:
            icon="🟢" if chg>0 else "🔴"
            ret_str=f"  (1주 {d['ret_1w']:+.1f}% | 1개월 {d['ret_1m']:+.1f}%)" if d.get("ret_1w") is not None else ""
            pred_lines.append(f"  {icon} {name}: {chg:+.2f}%{ret_str}")

    def flow_lines(codes):
        lines=[]
        for code in codes:
            info=kr_all.get(code,{}); name=info.get("name",code)
            flow=info.get("flow",{"error":True}); ret=info.get("ret",{"error":True})
            if flow.get("error"): lines.append(f"  • {name}: 조회 실패"); continue
            mark=" ✅" if flow["both_buying"] else ""
            ret_str="\n      📈 1주 {:+.1f}% | 1개월 {:+.1f}%".format(ret['ret_1w'],ret['ret_1m']) if not ret.get("error") else ""
            lines.append(f"  • {name}: 외국인 {flow['foreign']:+.0f}억 | 기관 {flow['institution']:+.0f}억{mark}{ret_str}")
        return "\n".join(lines)

    msg = f"""🌏 <b>시장 신호</b> | {now_str}

━━━━━━━━━━━━━━━━━━━
🇺🇸 <b>미국 시장</b>
{sox_line}

📈 <b>매수 후보</b>
{chr(10).join(us_lines)}

━━━━━━━━━━━━━━━━━━━
🇰🇷 <b>한국 장 예측</b>
{chr(10).join(pred_lines)}

{out_icon} <b>오늘 한국 장 전망: {outlook}</b>

📊 <b>대형주 외국인/기관 수급</b>
{flow_lines(KR_CANDIDATES.keys())}
✅ = 외국인 + 기관 동시 순매수

━━━━━━━━━━━━━━━━━━━
🔧 <b>반도체 소부장 수급</b>
{flow_lines(KR_SOBUJANG.keys())}
✅ = 외국인 + 기관 동시 순매수

━━━━━━━━━━━━━━━━━━━
📌 최종 판단은 본인이 직접 확인 후 결정"""

    print(msg)
    send_telegram(msg)
    print("텔레그램 전송 완료")

    # ── data.json 생성 ──
    def kr_row(code):
        info=kr_all.get(code,{}); flow=info.get("flow",{}); ret=info.get("ret",{})
        return {
            "name": info.get("name",code),
            "group": info.get("group",""),
            "ret_1w": ret.get("ret_1w") if not ret.get("error") else None,
            "ret_1m": ret.get("ret_1m") if not ret.get("error") else None,
            "frgn": flow.get("foreign",0) if not flow.get("error") else 0,
            "inst": flow.get("institution",0) if not flow.get("error") else 0,
            "both": flow.get("both_buying",False) if not flow.get("error") else False,
        }

    data_json = {
        "updated": now_str,
        "week": week_label,
        "sox": {
            "close": sox_data.get("close",0),
            "change_pct": sox_data.get("change_pct",0),
            "ret_1w": sox_data.get("ret_1w"),
            "ret_1m": sox_data.get("ret_1m"),
            "signal": sox_signal(sox_data.get("change_pct",0))[0] if not sox_data.get("error") else "오류"
        },
        "predictors": {
            t: {
                "name": KR_PREDICTORS[t],
                "close": round(kr_pred[t].get("close",0),2),
                "change_pct": round(kr_pred[t].get("change_pct",0),2),
                "ret_1w": kr_pred[t].get("ret_1w"),
                "ret_1m": kr_pred[t].get("ret_1m"),
            } for t in KR_PREDICTORS if not kr_pred[t].get("error")
        },
        "outlook": outlook,
        "us_stocks": [
            {
                "ticker": d["ticker"],
                "close": d.get("close",0),
                "change_pct": d.get("change_pct",0),
                "ret_1w": d.get("ret_1w"),
                "ret_1m": d.get("ret_1m"),
                "volume_ratio": d.get("volume_ratio",1.0),
                "near_52w_high": d.get("near_52w_high",False),
            } for d in us_stocks if not d.get("error")
        ],
        "kr_stocks": [kr_row(c) for c in list(KR_CANDIDATES.keys())+list(KR_SOBUJANG.keys())],
    }

    save_json(data_json)

if __name__ == "__main__":
    main()
