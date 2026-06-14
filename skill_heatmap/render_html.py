"""
집계 결과 → deepflow 스타일 히트맵 HTML
코스피/코스닥/US 섹션 + 종목 팝업 + 인사이트 + 진입후보
"""

from pathlib import Path
from datetime import date, timedelta


COLOR_SCALE = [
    (8,    "#0d5c2e", "#a8f0c6"),
    (4,    "#1a7a40", "#b8f5cd"),
    (2,    "#2a9a55", "#c8fad8"),
    (0.5,  "#3db870", "#e0fde8"),
    (0,    "#5cd48a", "#003818"),
    (-0.5, "#f07070", "#3b0000"),
    (-2,   "#d84040", "#fddcdc"),
    (-5,   "#b82020", "#fecece"),
    (-9,   "#8c0f0f", "#ffbcbc"),
]

SKILL_TOOLTIPS = {
    "vcp":                 "VCP (Volatility Contraction Pattern) — 변동성 수축 후 신고가 돌파 패턴. Mark Minervini 전략 기반.",
    "sector_rotation":     "섹터 로테이션 — 20일 모멘텀 상위 + 거래량 증가 종목 추종.",
    "flow_momentum":       "플로우 모멘텀 — 거래량 폭발(평균 1.8배↑) + 당일 양봉 + MA20 위.",
    "pre_surge":           "급등 전 징후 — 볼린저밴드 수축 + 거래량 급감 후 반등 조짐 포착.",
    "contrarian_reversal": "역추세 반전 — RSI 35 이하 과매도 구간에서 당일 양봉 전환 신호.",
    "narrative_momentum":  "내러티브 모멘텀 — 52주 신고가 근처(-20%) + 강한 단기 모멘텀 추종.",
    "value_chain":         "밸류체인 — 중기 모멘텀(20일 3%↑) + MA20 상승 + 안정적 거래량.",
    "best_of_best":        "베스트오브베스트 — 위 스킬 중 2개 이상 동시 충족 종목만 선별.",
}

HOLD_WEEKS  = {"W09","W10","W12","W13","W19","W22","W23"}
SKILL_ORDER = [
    "vcp","sector_rotation","flow_momentum","pre_surge",
    "contrarian_reversal","narrative_momentum","value_chain","best_of_best",
]
WEEKS = [f"W{w:02d}" for w in range(1, 54)]


def _color(v):
    for threshold, bg, fg in COLOR_SCALE:
        if v >= threshold:
            return bg, fg
    return "#5c0000", "#ffacac"


def _cell_html(data, skill, week):
    if not data:
        return "<td></td>"
    v       = data["mean"]
    n       = data["n"]
    wr      = data["win_rate"]
    tickers = data.get("tickers", "").replace("'", "\\'")
    sign    = "+" if v >= 0 else ""
    bg, fg  = _color(v)
    onclick = f"showTickers('{skill}','{week}','{tickers}')"
    return (
        f'<td><span class="cell" style="background:{bg};color:{fg};cursor:pointer" onclick="{onclick}">'
        f'<span class="ret">{sign}{v:.1f}</span>'
        f'<span class="meta">n{n}·{wr}%</span>'
        f'</span></td>'
    )


def _build_table(heatmap_data, benchmark, hold_weeks, bm_label):
    used_weeks = set()
    for sk_data in heatmap_data.values():
        used_weeks.update(sk_data.keys())
    week_cols = sorted(w for w in WEEKS if w in used_weeks)

    if not week_cols:
        return "<p style='color:#666;font-size:11px;padding:12px'>데이터 없음</p>"

    thead = '<th class="skill-col">스킬 \\ 주</th>'
    for w in week_cols:
        hold  = w in hold_weeks
        badge = '<span class="hold-badge">HOLD</span>' if hold else ""
        cls   = ' class="wh hold-week"' if hold else ' class="wh"'
        thead += f"<th{cls}>{badge}{w}</th>"

    bm = f'<td class="skill-col bm-label">{bm_label}</td>'
    if benchmark:
        for w in week_cols:
            v = benchmark.get(w)
            if v is None:
                bm += "<td></td>"
            else:
                cls  = "bm-pos" if v > 0 else "bm-neg"
                sign = "+" if v > 0 else ""
                bm += f'<td class="{cls}">{sign}{v:.1f}</td>'
    else:
        bm += "<td></td>" * len(week_cols)

    rows = ""
    for sk in SKILL_ORDER:
        data    = heatmap_data.get(sk, {})
        tooltip = SKILL_TOOLTIPS.get(sk, "")
        cells   = (
            f'<td class="skill-col">'
            f'<span class="skill-name" data-tip="{tooltip}">{sk} '
            f'<span class="tip-icon">?</span></span></td>'
        )
        for w in week_cols:
            cells += _cell_html(data.get(w), sk, w)
        rows += f"<tr>{cells}</tr>\n"

    return f"""<div class="table-wrap">
<table>
  <thead><tr>{thead}</tr></thead>
  <tbody>
    <tr>{bm}</tr>
    {rows}
  </tbody>
</table>
</div>"""


def _build_insights(insights):
    if not insights:
        return ""
    type_style = {
        "positive": "border-left:3px solid #2a9a55; background:#0d2e1a;",
        "negative": "border-left:3px solid #d84040; background:#2e0d0d;",
        "neutral":  "border-left:3px solid #888; background:#1a1a1a;",
    }
    items = ""
    for ins in insights:
        st = type_style.get(ins["type"], type_style["neutral"])
        items += f'<li style="padding:8px 12px;margin:6px 0;border-radius:4px;{st}">{ins["icon"]} {ins["text"]}</li>\n'
    return f"""<div class="insight-box">
  <h2>📋 주간 인사이트 (최근 4주 기준)</h2>
  <ul style="list-style:none;padding:0;margin:0;">{items}</ul>
</div>"""


def _next_week_label():
    today    = date.today()
    next_mon = today + timedelta(days=(7 - today.weekday()))
    week_num = next_mon.isocalendar().week
    return f"W{week_num:02d}", next_mon.strftime("%m/%d")


def _build_candidates(scan_results):
    if not scan_results:
        return ""

    next_week, next_mon = _next_week_label()
    rows = ""

    for sk, data in scan_results.items():
        kr_items = data.get("kr", [])
        us_items = data.get("us", [])
        if not kr_items and not us_items:
            continue

        tooltip = SKILL_TOOLTIPS.get(sk, "")
        ko_name = data.get("ko_name", sk)

        kr_html = ""
        for item in kr_items:
            kr_html += (
                f'<span class="cand-item">'
                f'{item["name"]} '
                f'<span class="cand-price">{item["close"]:,}원</span>'
                f'<span class="cand-date">{item["signal_date"]}</span>'
                f'</span>'
            )

        us_html = ""
        for item in us_items:
            us_html += (
                f'<span class="cand-item">'
                f'{item["name"]} '
                f'<span class="cand-price">${item["close"]}</span>'
                f'<span class="cand-date">{item["signal_date"]}</span>'
                f'</span>'
            )

        rows += f"""<tr>
  <td class="cand-skill">
    <span class="skill-name" data-tip="{tooltip}">{sk}
      <span class="tip-icon">?</span>
    </span>
    <span class="cand-ko">{ko_name}</span>
  </td>
  <td class="cand-tickers">
    {"<div class='cand-market-label'>🇰🇷 KR</div>" + kr_html if kr_html else ""}
    {"<div class='cand-market-label'>🇺🇸 US</div>" + us_html if us_html else ""}
  </td>
</tr>"""

    if not rows:
        return ""

    return f"""<div class="candidate-box">
  <h2>🎯 {next_week} 진입 후보 ({next_mon}~ 대응)</h2>
  <p class="cand-sub">현재 시점 기준 각 스킬 조건을 만족하는 종목 · 다음 주 월요일({next_mon}) 진입 검토</p>
  <div class="table-wrap">
  <table class="cand-table">
    <thead><tr>
      <th style="text-align:left;min-width:150px;padding-left:6px;">스킬</th>
      <th style="text-align:left;">후보 종목</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</div>"""


def render(
    heatmap_kospi,
    heatmap_kosdaq,
    heatmap_us,
    output_path  = "docs/heatmap.html",
    benchmark_kr = None,
    insights     = None,
    scan_results = None,
):
    generated = date.today().strftime("%Y-%m-%d")
    this_year = date.today().year

    kospi_table  = _build_table(heatmap_kospi,  benchmark_kr, HOLD_WEEKS, "📋 코스피 최악일낙폭")
    kosdaq_table = _build_table(heatmap_kosdaq, {},           set(),       "📋 코스닥 최악일낙폭")
    us_table     = _build_table(heatmap_us,     {},           set(),       "📋 S&P500 최악일낙폭")

    insight_html   = _build_insights(insights or [])
    candidate_html = _build_candidates(scan_results or {})

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>트레이딩 스킬 주간 수익률 히트맵 {this_year}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0e1117; color: #e0e0e0; font-family: 'Pretendard', sans-serif; font-size: 12px; padding: 20px; }}
  h1 {{ font-size: 15px; font-weight: 500; margin-bottom: 10px; margin-top: 28px; }}
  h1:first-of-type {{ margin-top: 0; }}
  h2 {{ font-size: 13px; font-weight: 500; margin-bottom: 8px; color: #ccc; }}
  .sub {{ font-size: 10px; color: #888; margin-bottom: 16px; line-height: 1.7; }}
  .sub b {{ color: #e85555; }}
  .table-wrap {{ overflow-x: auto; margin-bottom: 24px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 2px 3px; text-align: center; vertical-align: middle; }}
  .skill-col {{ text-align: left; min-width: 170px; padding-left: 6px; color: #ccc; font-size: 11px; }}
  .wh {{ font-size: 10px; color: #888; min-width: 56px; }}
  .hold-week {{ color: #e85555; font-weight: 500; }}
  .hold-badge {{ font-size: 8px; background: #e85555; color: #fff; border-radius: 3px; padding: 0 3px; display: block; margin: 0 auto 2px; width: fit-content; }}
  .bm-label {{ font-size: 10px; color: #666; }}
  .bm-pos {{ color: #4caf7d; font-size: 10px; }}
  .bm-neg {{ color: #e85555; font-size: 10px; }}
  .cell {{ border-radius: 4px; padding: 3px 4px; display: inline-block; width: 100%; min-width: 50px; }}
  .ret {{ font-weight: 500; font-size: 11px; display: block; }}
  .meta {{ font-size: 9px; opacity: 0.85; display: block; line-height: 1.2; }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  .skill-name {{ position: relative; cursor: default; }}
  .tip-icon {{ display: inline-block; width: 13px; height: 13px; border-radius: 50%; background: #444; color: #aaa; font-size: 9px; text-align: center; line-height: 13px; margin-left: 3px; cursor: pointer; }}
  .skill-name:hover::after {{ content: attr(data-tip); position: absolute; left: 0; top: 18px; background: #1e2530; color: #ddd; font-size: 10px; line-height: 1.5; padding: 6px 10px; border-radius: 4px; border: 1px solid #444; white-space: normal; width: 240px; z-index: 99; }}
  .insight-box {{ margin-top: 8px; margin-bottom: 24px; }}
  .insight-box li {{ font-size: 11px; line-height: 1.6; color: #ddd; }}
  .candidate-box {{ margin-top: 32px; margin-bottom: 24px; }}
  .cand-sub {{ font-size: 10px; color: #888; margin-bottom: 10px; }}
  .cand-table td {{ vertical-align: top; padding: 6px 4px; border-bottom: 1px solid #1e2530; }}
  .cand-skill {{ min-width: 150px; padding-left: 6px !important; }}
  .cand-ko {{ display: block; font-size: 10px; color: #888; margin-top: 2px; }}
  .cand-tickers {{ text-align: left !important; }}
  .cand-market-label {{ font-size: 10px; color: #888; margin: 4px 0 2px; }}
  .cand-item {{ display: inline-block; background: #1a2535; border-radius: 4px; padding: 3px 8px; margin: 2px; font-size: 11px; }}
  .cand-price {{ color: #4caf7d; margin-left: 4px; font-size: 10px; }}
  .cand-date {{ color: #888; margin-left: 4px; font-size: 10px; }}
  .generated {{ font-size: 10px; color: #555; margin-top: 12px; }}
  .modal-bg {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:200; }}
  .modal-bg.active {{ display:flex; align-items:center; justify-content:center; }}
  .modal {{ background:#1a1f2e; border:1px solid #333; border-radius:8px; padding:20px; min-width:340px; max-width:500px; max-height:80vh; overflow-y:auto; }}
  .modal-title {{ font-size:13px; font-weight:500; margin-bottom:12px; color:#ddd; }}
  .modal-close {{ float:right; cursor:pointer; color:#888; font-size:16px; line-height:1; }}
  .ticker-item {{ display:flex; justify-content:space-between; align-items:center; padding:6px 8px; margin:3px 0; border-radius:4px; font-size:11px; }}
  .ticker-item.pos {{ background:#0d2e1a; color:#a8f0c6; }}
  .ticker-item.neg {{ background:#2e0d0d; color:#ffacac; }}
  .ticker-name {{ font-weight:500; }}
  .ticker-right {{ display:flex; align-items:center; gap:8px; }}
  .ticker-ret {{ font-size:11px; font-weight:500; }}
  .ticker-date {{ font-size:10px; opacity:0.7; }}
</style>
</head>
<body>

<div class="sub">
  지표: 5일 보유 신호 수익률(d5_return)의 주간 평균 · 셀 = 평균 수익률(%), 아래 = 표본수 n·승률<br>
  <b>🚩</b> 맨 왼쪽 시장 최악 일일 낙폭이 <b>-4%</b> 이하인 주는
  <span style="background:#e85555;color:#fff;padding:0 3px;border-radius:3px;font-size:9px;">HOLD</span> (현금 권장)
  · 스킬명 옆 <span style="background:#444;color:#aaa;padding:0 4px;border-radius:50%;font-size:9px;">?</span> 마우스 올리면 설명 · 셀 클릭 시 종목 리스트
</div>

<h1>🇰🇷 KR 코스피 — 주간 수익률 매트릭스 ({this_year})</h1>
{kospi_table}

<h1>🇰🇷 KR 코스닥 — 주간 수익률 매트릭스 ({this_year})</h1>
{kosdaq_table}

<h1>🇺🇸 US — 주간 수익률 매트릭스 ({this_year})</h1>
{us_table}

{insight_html}
{candidate_html}

<p class="generated">생성일: {generated} · FinanceDataReader 기반 자동 계산</p>

<div class="modal-bg" id="modalBg" onclick="closeModal(event)">
  <div class="modal" id="modal">
    <div class="modal-title" id="modalTitle"></div>
    <div id="modalBody"></div>
  </div>
</div>

<script>
function showTickers(skill, week, raw) {{
  const items = raw.split('|').filter(Boolean);
  document.getElementById('modalTitle').innerHTML =
    '<span class="modal-close" onclick="document.getElementById(\\'modalBg\\').classList.remove(\\'active\\')">✕</span>' +
    '<b>' + skill + '</b> · ' + week + ' <span style="color:#888;font-size:10px;">(' + items.length + '개 종목)</span>';
  let html = '';
  items.forEach(item => {{
    const m = item.match(/^(.+?)\\(([+-]?[\\d.]+)%,([\\d/]+)\\)$/);
    if (!m) return;
    const [, name, ret, dt] = m;
    const pos = parseFloat(ret) >= 0;
    html += `<div class="ticker-item ${{pos?'pos':'neg'}}">
      <span class="ticker-name">${{name}}</span>
      <span class="ticker-right">
        <span class="ticker-ret">${{pos?'+':''}}${{ret}}%</span>
        <span class="ticker-date">${{dt}}</span>
      </span>
    </div>`;
  }});
  document.getElementById('modalBody').innerHTML = html || '<p style="color:#666;font-size:11px;">데이터 없음</p>';
  document.getElementById('modalBg').classList.add('active');
}}

function closeModal(e) {{
  if (e.target === document.getElementById('modalBg')) {{
    document.getElementById('modalBg').classList.remove('active');
  }}
}}
</script>
</body>
</html>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")
    print(f"[OK] HTML 저장 완료: {output_path}")
