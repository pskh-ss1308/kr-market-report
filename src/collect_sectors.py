"""업종 등락·거래대금 수집 — KIS OpenAPI 공식 엔드포인트.

사용 API:
  [국내주식] 업종/기타 > 국내업종 현재지수
  TR_ID: FHPUP02100000
  출처: KIS Developers (https://apiportal.koreainvestment.com)

'주목 섹터'  = 거래대금(자금 쏠림) 상위
'강세 섹터'  = 등락률 상위
'약세 섹터'  = 등락률 하위
"""
from __future__ import annotations
import config
from kis_auth import get_access_token, kis_get

# (섹터명, 업종코드, 시장)
# KIS 업종코드: 0~999 코스피, 1000~ 코스닥
SECTORS = [
    # KOSPI 주요 업종
    ("음식료품",        "004", "KOSPI"),
    ("섬유의복",        "006", "KOSPI"),
    ("종이목재",        "007", "KOSPI"),
    ("화학",           "008", "KOSPI"),
    ("의약품",         "009", "KOSPI"),
    ("비금속광물",      "010", "KOSPI"),
    ("철강금속",        "011", "KOSPI"),
    ("기계",           "012", "KOSPI"),
    ("전기전자",        "013", "KOSPI"),
    ("의료정밀",        "014", "KOSPI"),
    ("운수장비",        "015", "KOSPI"),
    ("유통업",         "016", "KOSPI"),
    ("전기가스업",      "017", "KOSPI"),
    ("건설업",         "018", "KOSPI"),
    ("운수창고",        "019", "KOSPI"),
    ("통신업",         "020", "KOSPI"),
    ("금융업",         "021", "KOSPI"),
    ("은행",           "022", "KOSPI"),
    ("증권",           "024", "KOSPI"),
    ("보험",           "025", "KOSPI"),
    ("서비스업",        "026", "KOSPI"),
    ("제조업",         "028", "KOSPI"),
    # KOSDAQ 주요 업종
    ("IT부품",         "1006", "KOSDAQ"),
    ("디지털컨텐츠",    "1007", "KOSDAQ"),
    ("소프트웨어",      "1008", "KOSDAQ"),
    ("인터넷",         "1009", "KOSDAQ"),
    ("통신방송서비스",  "1010", "KOSDAQ"),
    ("IT종합",         "1011", "KOSDAQ"),
    ("제약",           "1015", "KOSDAQ"),
    ("기타제조",        "1020", "KOSDAQ"),
    ("반도체",         "1032", "KOSDAQ"),
    ("바이오",         "1034", "KOSDAQ"),
    ("2차전지",        "1035", "KOSDAQ"),
    ("방송서비스",      "1036", "KOSDAQ"),
]


def _fetch_sector(name: str, code: str, market: str,
                  app_key: str, token: str) -> dict | None:
    try:
        mkt_div = "J" if market == "KOSPI" else "Q"
        data = kis_get(
            path="/uapi/domestic-stock/v1/quotations/inquire-index-price",
            params={
                "fid_cond_mrkt_div_code": mkt_div,
                "fid_input_iscd": code,
            },
            app_key=app_key,
            access_token=token,
            tr_id="FHPUP02100000",
        )
        output = data.get("output", {})
        if not output:
            return None

        chg_str  = output.get("bstp_nmix_prdy_ctrt", "0")   # 전일대비율
        val_str  = output.get("acml_tr_pbmn", "0")           # 누적거래대금(원)

        change_pct = float(chg_str) if chg_str else None
        try:
            value_eok = round(int(str(val_str).replace(",", "") or "0") / 1e8, 1)
        except Exception:  # noqa: BLE001
            value_eok = None

        return {
            "sector": name,
            "market": market,
            "change_pct": change_pct,
            "value_eok": value_eok,
        }
    except Exception as e:  # noqa: BLE001
        print(f"[collect_sectors] {name}({code}) 수집 실패: {e}")
        return None


def collect_sectors(top_n: int = 5) -> dict:
    """KIS API로 업종 등락·거래대금 수집 후 주목·강세·약세 섹터 산출."""
    empty = {
        "top_by_value": [], "top_by_change": [], "bottom_by_change": [],
        "all_count": 0,
        "source": "KIS OpenAPI — 국내업종 현재지수 (TR: FHPUP02100000)",
        "note": "주목도=거래대금 상위, 강세/약세=등락률 기준",
    }

    if not config.KIS_APP_KEY or not config.KIS_APP_SECRET:
        print("[collect_sectors] KIS_APP_KEY/SECRET 미설정 → 섹터 수집 건너뜀")
        return empty

    try:
        token = get_access_token(config.KIS_APP_KEY, config.KIS_APP_SECRET)
    except Exception as e:  # noqa: BLE001
        print(f"[collect_sectors] KIS 토큰 발급 실패: {e}")
        return empty

    rows = []
    for name, code, market in SECTORS:
        row = _fetch_sector(name, code, market, config.KIS_APP_KEY, token)
        if row:
            rows.append(row)

    by_val = sorted([r for r in rows if r["value_eok"]],
                    key=lambda x: x["value_eok"], reverse=True)
    by_chg = sorted([r for r in rows if r["change_pct"] is not None],
                    key=lambda x: x["change_pct"], reverse=True)

    return {
        "top_by_value":    by_val[:top_n],
        "top_by_change":   by_chg[:top_n],
        "bottom_by_change": by_chg[-top_n:][::-1] if len(by_chg) >= top_n else by_chg[::-1],
        "all_count": len(rows),
        "source": "KIS OpenAPI — 국내업종 현재지수 (TR: FHPUP02100000)",
        "note": "주목도=거래대금 상위, 강세/약세=등락률 기준",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(collect_sectors(), ensure_ascii=False, indent=2))
