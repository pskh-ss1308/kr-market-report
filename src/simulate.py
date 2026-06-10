"""시뮬레이션 레포트 생성기 — Claude API 호출 없음, 비용 0원.

실제 수집된 데이터를 템플릿에 채워 레포트를 만든다.
'데이터가 제대로 들어오는지' '이메일·슬랙이 잘 가는지' '디자인이 맞는지'를
API 비용 없이 검증하는 것이 목적이다.
실전 전환 시 이 파일은 건드리지 않고 config 만 바꾼다.
"""
from __future__ import annotations
import datetime as dt


def _pct_str(v) -> str:
    if v is None:
        return "N/A"
    return f"{'▲' if v >= 0 else '▼'}{abs(v):.2f}%"


def _flows_section(flows: dict) -> str:
    lines = []
    for m in flows.get("by_market", []):
        mkt = m["market"]
        net = m.get("net_eok", {})
        total = m.get("total_trading_value_eok")
        parts = " / ".join(
            f"{who} {'▲' if v >= 0 else '▼'}{abs(v):,.0f}억"
            for who, v in net.items()
        )
        tv = f" · 총거래대금 {total:,.0f}억" if total else ""
        lines.append(f"- **{mkt}**: {parts}{tv} (출처: KRX)")
    return "\n".join(lines) if lines else "- 수급 데이터 없음 (데이터 수집 오류 또는 휴장일 가능성)"


def _corr_table(corr: dict) -> str:
    matrix = corr.get("matrix", {})
    window = corr.get("window_used", "?")
    rows = [f"- 기준: 최근 {window}거래일 일간 수익률 피어슨 상관계수 (출처: 계산값)"]
    for base, others in matrix.items():
        for other, val in others.items():
            direction = "동행↑" if val > 0.5 else "역행↓" if val < -0.3 else "중립"
            rows.append(f"  - {base} ↔ {other}: **{val:+.2f}** ({direction})")
    return "\n".join(rows) if len(rows) > 1 else "  - 상관관계 데이터 없음"


def _sector_section(sectors: dict) -> str:
    lines = [f"(출처: {sectors.get('source','KRX')})"]
    by_val = sectors.get("top_by_value", [])
    by_up = sectors.get("top_by_change", [])
    by_dn = sectors.get("bottom_by_change", [])

    if by_val:
        lines.append("\n**▶ 자금 쏠림 (거래대금 상위 = 주목도)**")
        for i, s in enumerate(by_val, 1):
            v = f"{s['value_eok']:,.0f}억" if s.get("value_eok") else "-"
            c = _pct_str(s.get("change_pct"))
            lines.append(f"  {i}. {s['sector']} ({s['market']}) — 거래대금 {v} / 등락 {c}")
    if by_up:
        lines.append("\n**▶ 강세 섹터 (등락률 상위)**")
        for s in by_up:
            lines.append(f"  - {s['sector']} {_pct_str(s.get('change_pct'))}")
    if by_dn:
        lines.append("\n**▶ 약세 섹터 (등락률 하위)**")
        for s in by_dn:
            lines.append(f"  - {s['sector']} {_pct_str(s.get('change_pct'))}")
    return "\n".join(lines)


def _news_section(news: dict) -> str:
    lines = []
    for region, label in (("kr", "🇰🇷 국내"), ("us", "🇺🇸 미국")):
        items = news.get(region, [])
        if not items:
            continue
        lines.append(f"**{label} 주요 헤드라인**")
        for it in items[:5]:
            pub = it.get("publisher", "")
            title = it.get("title", "")
            link = it.get("link", "")
            lines.append(f"- [{title}]({link}) — {pub}")
    return "\n".join(lines) if lines else "- 뉴스 수집 실패 (RSS 주소 확인 필요)"


def generate_simulation(bundle: dict) -> str:
    today = dt.date.today().isoformat()
    snapshot = bundle.get("snapshot", [])
    sup = bundle.get("supplementary", [])
    flows = bundle.get("flows", {})
    sectors = bundle.get("sectors", {})
    news = bundle.get("news", {})
    corr = bundle.get("correlations", {})

    # 지수 스냅샷 문자열
    idx_lines = []
    for s in snapshot + sup:
        label = s["label"]
        close = s.get("close", "N/A")
        chg = _pct_str(s.get("change_pct"))
        src = s.get("source", "")
        idx_lines.append(f"  - **{label}**: {close:,.2f} ({chg}) (출처: {src})")
    idx_str = "\n".join(idx_lines) if idx_lines else "  - 지수 데이터 없음"

    report = f"""\
> ⚠️ **[시뮬레이션 모드]** 이 레포트는 Claude AI 분석 없이 수집 데이터만으로 자동 생성된 시뮬레이션입니다.
> 데이터 수집 · 이메일 · Slack · 디자인 검증용입니다. 실전 전환 후 이 안내문은 사라집니다.

---

## 1. 오늘 시장 한눈에

**기준일: {today}** (출처: 수집 데이터 기준)

{idx_str}

---

## 2. 수급 & 거래대금

{_flows_section(flows)}

---

## 3. 국내·미국 뉴스 & 지수 상관관계

{_news_section(news)}

**지수 상관관계**
{_corr_table(corr)}

> 🔔 시뮬레이션 모드에서는 뉴스-시장 인과 해석을 제공하지 않습니다. 실전 전환 후 Claude가 분석합니다.

---

## 4. 오늘 주목받은 섹터

{_sector_section(sectors)}

> 🔔 자금 쏠림 이유 분석은 실전 전환 후 Claude가 제공합니다.

---

## 5. 내일 시장 시나리오

> 🔔 시나리오·확률 분석은 실전 전환(SIMULATION_MODE=false) 후 Claude가 제공합니다.

- 상승 시나리오: —
- 중립 시나리오: —
- 하락 시나리오: —
- 체크포인트: ⚠️ 본 레포트는 16:30 KST 작성 기준, 오늘 밤 미국 정규장 미발생 상태입니다.

---

## 6. 한 줄 요약 & 면책

**[시뮬레이션]** 데이터 수집 및 파이프라인 정상 동작 확인 레포트.
본 자료는 투자 자문이 아니며 투자 판단과 책임은 투자자 본인에게 있다.
"""
    return report.strip()
