"""
집계 결과 → deepflow 스타일 히트맵 HTML
KR + US 위아래 배치 / 스킬 툴팁 / 인사이트 / 종목 클릭 팝업
"""

from pathlib import Path
from datetime import date


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
    v        = data["mean"]
    n        = data["n"]
    wr       = data["win_rate"]
    tickers  = data.get("tickers", "")
    sign     = "+" if v >= 0 else ""
    bg, fg   = _color(v)
    onclick  = f"showTickers('{skill}','{week}',`{tickers}`)"
    return (
        f'<td><span class="cell" style="background:{bg};color:{fg};cursor:pointer" onclick="{onclick}">'
        f'<span class="ret">{sign}{v:.1f}</span>'
        f'<span class="meta">n{n}·{wr}%</span>'
        f'</span></td>'
    )


def _build_table(heatmap_data, benchmark, hold_weeks, flag, market_label, bm_label):
    used_weeks = set()
    for sk_data in heatmap_data.values():
        used_weeks.update(sk_data.keys())
    week_cols = sorted(w for w in WEEKS if w in used_weeks)

    thead = f'<th class="skill-col">{flag} {market_label}</th>'
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
  <h2>📋 주간 인사이트</h2>
  <ul style="list-style:none;padding:0;margin:0;">{items}</ul>
</div>"""


def render(
    heatmap_kr,
    output_path  = "docs/heatmap.html",
    benchmark_kr = None,
    heatmap_us   = None,
    benchmark_us = None,
    insights     = None,
):
    generated = date.today().strftime("%Y-%m-%d")

    kr_table = _build_table(
        heatmap_kr, benchmark_kr, HOLD_WEEKS,
        "KR", "주간 수익률 매트릭스", "📋 코스피 최악일낙폭"
    )

    us_section = ""
    if heatmap_us:
        us_table = _build_table(
            heatmap_us, benchmark_us, set(),
            "US", "주간 수익률 매트릭스", "📋 S&P500 최악일낙폭"
        )
        us_section = f"<h1>🇺🇸 US — 주간 수익률 매트릭스</h1>\n{us_table}"

    insight_html = _build_insights(insights or [])

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>트레이딩 스킬 주간 수익률 히트맵</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0e1117; color: #e0e0e0; font-family: 'Pretendard', sans-serif; font-size: 12px; padding: 20px; }}
  h1 {{ font-size: 15px; font-weight: 500; margin-bottom: 6px; margin-top: 28px; }}
  h1:first-of-type {{ margin-top: 0; }}
  h2 {{ font-size: 13px; font-weight: 500; margin-bottom: 10px; color: #ccc; }}
  .sub {{ font-size: 10px; color: #888; margin-bottom: 16px; line-height: 1.7; }}
  .sub b {{ color: #e85555; }}
  .table-wrap {{ overflow-x: auto; margin-bottom: 32px; }}
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
  .generated {{ font-size: 10px; color: #555; margin-top: 12px; }}

  /* 팝업 */
  .modal-bg {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:200; }}
  .modal-bg.active {{ display:flex; align-items:center; justify-content:center; }}
  .modal {{ background:#1a1f2e; border:1px solid #333; border-radius:8px; padding:20px; min-width:320px; max-width:480px; max-height:80vh; overflow-y:auto; }}
  .modal-title {{ font-size:13px; font-weight:500; margin-bottom:12px; color:#ddd; }}
  .modal-close {{ float:right; cursor:pointer; color:#888; font-size:16px; }}
  .ticker-item {{ display:flex; justify-content:space-between; padding:6px 8px; margin:3px 0; border-radius:4px; font-size:11px; }}
  .ticker-item.pos {{ background:#0d2e1a; color:#a8f0c6; }}
  .ticker-item.neg {{ background:#2e0d0d; color:#ffacac; }}
  .ticker-name {{ font-weight:500; }}
  .ticker-ret {{ font-size:11px; }}
  .ticker-date {{ font-size:10px; color:#888; margin-left:8px; }}
</style>
</head>
<body>

<div class="sub">
  지표: 5일 보유 신호 수익률(d5_return)의 주간 평균 · 셀 = 평균 수익률(%), 아래 = 표본수 n·승률<br>
  <b>🚩</b> 맨 왼쪽 시장 최악 일일 낙폭이 <b>-4%</b> 이하인 주는
  <span style="background:#e85555;color:#fff;padding:0 3px;border-radius:3px;font-size:9px;">HOLD</span> (현금 권장)
  · 스킬명 옆 <span style="background:#444;color:#aaa;padding:0 4px;border-radius:50%;font-size:9px;">?</span> 에 마우스를 올리면 설명 · 셀 클릭 시 해당 종목 리스트
</div>

<h1>🇰🇷 KR — 주간 수익률 매트릭스</h1>
{kr_table}
{us_section}
{insight_html}
<p class="generated">생성일: {generated} · KIS OpenAPI 기반 자동 계산</p>

<!-- 종목 팝업 -->
<div class="modal-bg" id="modalBg" onclick="closeModal(event)">
  <div class="modal" id="modal">
    <div class="modal-title" id="modalTitle">
      <span class="modal-close" onclick="document.getElementById('modalBg').classList.remove('active')">✕</span>
    </div>
    <div id="modalBody"></div>
  </div>
</div>

<script>
function showTickers(skill, week, raw) {{
  const items = raw.split('|').filter(Boolean);
  document.getElementById('modalTitle').innerHTML =
    '<span class="modal-close" onclick="document.getElementById(\\'modalBg\\').classList.remove(\\'active\\')">✕</span>' +
    skill + ' · ' + week + ' (' + items.length + '개 종목)';

  let html = '';
  items.forEach(item => {{
    // 형식: TICKER(+1.2%,03/15)
    const m = item.match(/^(.+?)\\(([+-]?[\\d.]+)%,([\\d/]+)\\)$/);
    if (!m) return;
    const [, ticker, ret, dt] = m;
    const pos = parseFloat(ret) >= 0;
    html += `<div class="ticker-item ${{pos?'pos':'neg'}}">
      <span class="ticker-name">${{ticker}}</span>
      <span>
        <span class="ticker-ret">${{pos?'+':''}}${{ret}}%</span>
        <span class="ticker-date">${{dt}}</span>
      </span>
    </div>`;
  }});
  document.getElementById('modalBody').innerHTML = html;
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
