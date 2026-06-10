"""투자자별 수급 수집 — KIS OpenAPI 공식 엔드포인트.

사용 API:
  [국내주식] 기본시세 > 주식현재가 투자자
  TR_ID: FHKST01010900
  출처: KIS Developers (https://apiportal.koreainvestment.com)

외국인·기관·개인 순매수(억원)와 총 거래대금을 코스피·코스닥 시장별로 수집한다.
종목 단위가 아닌 시장 전체 수급은 업종지수(0001=코스피, 1001=코스닥)의
투자자 데이터로 산출하는 공식 방식이다.
"""
from __future__ import annotations
import config
from kis_auth import get_access_token, kis_get

# 시장 대표 업종코드
MARKET_CODES = {
    "KOSPI":  "0001",
    "KOSDAQ": "1001",
}

INVESTOR_MAP = {
    "frgn_ntby_qty":  "외국인",
    "orgn_ntby_qty":  "기관합계",
    "indvdl_ntby_qty": "개인",
}


def _eok(v) -> float:
    """문자열 수량 → 억원 환산 (1주=1천원 추정치 아님, KIS 반환값 자체가 금액)."""
    try:
        return round(int(str(v).replace(",", "").replace("-", "").strip() or "0")
                     * (-1 if str(v).strip().startswith("-") else 1) / 1e8, 1)
    except Exception:  # noqa: BLE001
        return 0.0


def _flows_for(market: str, market_code: str,
               app_key: str, token: str) -> dict | None:
    try:
        data = kis_get(
            path="/uapi/domestic-stock/v1/quotations/inquire-investor",
            params={
                "fid_cond_mrkt_div_code": "U",   # 업종
                "fid_input_iscd": market_code,
            },
            app_key=app_key,
            access_token=token,
            tr_id="FHKST01010900",
        )
        output = data.get("output", {})
        if not output:
            return None

        net_eok = {}
        for field, label in INVESTOR_MAP.items():
            raw = output.get(field, "0")
            net_eok[label] = _eok(raw)

        # 총거래대금: acml_tr_pbmn (누적거래대금, 단위 원)
        total_raw = output.get("acml_tr_pbmn", "0")
        try:
            total_eok = round(int(str(total_raw).replace(",", "") or "0") / 1e8, 1)
        except Exception:  # noqa: BLE001
            total_eok = None

        return {
            "market": market,
            "net_eok": net_eok,
            "total_trading_value_eok": total_eok,
        }
    except Exception as e:  # noqa: BLE001
        print(f"[collect_flows] {market} 수급 수집 실패: {e}")
        return None


def collect_flows(trade_date: str) -> dict:  # noqa: ARG001  trade_date는 참조용
    """KIS API로 당일 코스피·코스닥 투자자별 수급 수집."""
    out = {
        "date": trade_date,
        "by_market": [],
        "source": "KIS OpenAPI — 주식현재가 투자자 (TR: FHKST01010900)",
    }

    if not config.KIS_APP_KEY or not config.KIS_APP_SECRET:
        print("[collect_flows] KIS_APP_KEY/SECRET 미설정 → 수급 수집 건너뜀")
        return out

    try:
        token = get_access_token(config.KIS_APP_KEY, config.KIS_APP_SECRET)
    except Exception as e:  # noqa: BLE001
        print(f"[collect_flows] KIS 토큰 발급 실패: {e}")
        return out

    for market, code in MARKET_CODES.items():
        row = _flows_for(market, code, config.KIS_APP_KEY, token)
        if row:
            out["by_market"].append(row)

    return out


if __name__ == "__main__":
    import json, datetime as dt
    print(json.dumps(
        collect_flows(dt.date.today().strftime("%Y%m%d")),
        ensure_ascii=False, indent=2))
