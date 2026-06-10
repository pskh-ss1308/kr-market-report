"""레포트 렌더링: 마크다운 본문 + 데이터 → .md / .html 파일 생성."""
from __future__ import annotations
import os
import datetime as dt
import markdown as md
from jinja2 import Environment, FileSystemLoader, select_autoescape

import config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(ROOT, "templates")
OUT_DIR = os.path.join(ROOT, "reports")


def _news_appendix(news: dict) -> str:
    lines = ["\n## 참고 뉴스 (원문 링크)\n"]
    for region, label in (("kr", "🇰🇷 국내"), ("us", "🇺🇸 미국")):
        items = news.get(region, [])
        if not items:
            continue
        lines.append(f"\n**{label}**\n")
        for it in items[:8]:
            t = it["title"]
            link = it.get("link", "")
            pub = it.get("publisher", "")
            lines.append(f"- [{t}]({link}) — {pub}")
    return "\n".join(lines)


def render(report_md: str, bundle: dict) -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    date = dt.date.today().isoformat()

    full_md = report_md + "\n" + _news_appendix(bundle.get("news", {}))
    body_html = md.markdown(full_md, extensions=["extra", "sane_lists", "nl2br"])

    env = Environment(loader=FileSystemLoader(TPL_DIR),
                      autoescape=select_autoescape(["html"]))
    html = env.get_template("report.html.j2").render(
        date=date,
        snapshot=bundle.get("snapshot", []),
        flows=bundle.get("flows", {}).get("by_market", []),
        body_html=body_html,
        model=config.CLAUDE_MODEL,
    )

    md_path = os.path.join(OUT_DIR, f"{date}.md")
    html_path = os.path.join(OUT_DIR, f"{date}.html")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 국내 증시 데일리 레포트 — {date}\n\n{full_md}\n")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return {"md_path": md_path, "html_path": html_path, "html": html,
            "md": full_md, "date": date}
