"""
집계 결과 → deepflow 스타일 히트맵 HTML 파일 생성
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

def _color(v: float) -> tuple[str,str]:
    for threshold, bg, fg in COLOR_SCALE:
        if v >= threshold:
            return bg, fg
    return "#5c0000", "#ffacac"

def _cell_html(data: dict | None) -> str:
    if not data:
        return "<td></td>"
    v      = data["mean"]
    n      = data["n"]
    wr     = data["win_rate"]
    sign   = "+" if v >= 0 else ""
    bg, fg = _color(v)
    return (
        f'<td><span class="cell" style="background:{bg};color:{fg}">'
        f'<span class="ret">{sign}{v:.1f}</span>'
        f'<span class="meta">n{n}·{wr}%</span>'
        f'</span></td>'
    )


HOLD_WEEKS  = {"W09","W10","W12","W13","W19","W22","W23"}
SKILL_ORDER = [
    "vcp","sector_rotation","flow_momentum","pre_surge",
    "contrarian_reversal","narrative_momentum","value_chain","best_of_best",
]
WEEKS = [f"W{w:02d}" for w in range(1, 54)]


def render(
    heatmap_data: dict,
    output_path:  str = "output/heatmap.html",
    benchmark:    dict | None = None,
    title:        str = "🇰🇷 KR — 주간 수익률 매트릭스",
):
    used_weeks = set()
    for sk_data in heatmap_data.values():
        used_weeks.update(sk_data.keys())
    week_cols = sorted(w for w in WEEKS if w in used_weeks)

    thead_cells = '<th class="skill-col">스킬 \\ 주</th>'
    for w in week_cols:
        hold  = w in HOLD_WEEKS
        badge = '<span class="hold-badge">HOLD</span>' if hold else ""
        cls   = ' class="wh hold-week"' if hold else ' class="wh"'
        thead_cells += f"<th{cls}>{badge}{w}</th>"

    bm_cells = '<td class="skill-col bm-label">📋 코스피 최악일낙폭</td>'
    if benchmark:
        for w in week_cols:
            v = benchmark.get(w)
            if v is None:
                bm_cells += "<td></td>"
            else:
                cls  = "bm-pos" if v > 0 else "bm-neg"
                sign = "+" if v > 0 else ""
                bm_cells += f'<td class="{cls}">{sign}{v:.1f}</td>'
    else:
        bm_cells += "<td></td>" * len(week_cols)

    skill_rows = ""
    for sk in SKILL_ORDER:
        data  = heatmap_data.get(sk, {})
        cells = f'<td class="skill-col">{sk}</td>'
        for w in week_cols:
            cells += _cell_html(data.get(w))
        skill_rows += f"<tr>{cells}</tr>\n"

    generated = date.today().strftime("%Y-%m-%d")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>트레이딩 스킬 주간 수익률 히트맵</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0e1117; color: #e0e0e0; font-family: 'Pretendard', sans-serif; font-size: 12px; padding: 20px; }}
  h1 {{ font-size: 15px; font-weight: 500; margin-bottom: 8px; }}
  .sub {{ font-size: 10px; color: #888; margin-bottom: 16px; line-height: 1.7; }}
  .sub b {{ color: #e85555; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 2px 3px; text-align: center; vertical-align: middle; }}
  .skill-col {{ text-align: left; min-width: 130px; padding-left: 6px; color: #ccc; font-size: 11px; }}
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
  .generated {{ font-size: 10px; color: #555; margin-top: 12px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="sub">
  지표: 5일 보유 신호 수익률(d5_return)의 주간 평균 · 셀 = 평균 수익률(%), 아래 = 표본수 n·승률<br>
  <b>🚩</b> 맨 왼쪽 시장 최악 일일 낙폭이 <b>-4%</b> 이하인 주는
  <span style="background:#e85555;color:#fff;padding:0 3px;border-radius:3px;font-size:9px;">HOLD</span> (현금 권장)
</div>
<div class="table-wrap">
<table>
  <thead><tr>{thead_cells}</tr></thead>
  <tbody>
    <tr>{bm_cells}</tr>
    {skill_rows}
  </tbody>
</table>
</div>
<p class="generated">생성일: {generated} · KIS OpenAPI 기반 자동 계산</p>
</body>
</html>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding="utf-8")
    print(f"[OK] HTML 저장 완료: {output_path}")
