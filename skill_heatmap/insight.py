"""
규칙 기반 주간 인사이트 자동 생성
"""

SKILL_KO = {
    "vcp":                 "VCP(변동성수축)",
    "sector_rotation":     "섹터로테이션",
    "flow_momentum":       "플로우모멘텀",
    "pre_surge":           "급등전징후",
    "contrarian_reversal": "역추세반전",
    "narrative_momentum":  "내러티브모멘텀",
    "value_chain":         "밸류체인",
    "best_of_best":        "베스트오브베스트",
}


def _sorted_weeks(heatmap_data):
    weeks = set()
    for sk_data in heatmap_data.values():
        weeks.update(sk_data.keys())
    return sorted(weeks)


def _week_avg(heatmap_data, week):
    vals = [
        v["mean"]
        for sk_data in heatmap_data.values()
        for w, v in sk_data.items()
        if w == week
    ]
    return sum(vals) / len(vals) if vals else 0.0


def _skill_avg(heatmap_data, skill):
    vals = [v["mean"] for v in heatmap_data.get(skill, {}).values()]
    return sum(vals) / len(vals) if vals else 0.0


def generate_insights(heatmap_kr, heatmap_us=None):
    insights = []
    weeks = _sorted_weeks(heatmap_kr)
    if not weeks:
        return insights

    week_avgs  = {w: _week_avg(heatmap_kr, w) for w in weeks}
    best_week  = max(week_avgs, key=week_avgs.get)
    worst_week = min(week_avgs, key=week_avgs.get)

    insights.append({
        "icon": "🏆",
        "text": f"{best_week} — 전략 평균 수익률 최고 주차 ({week_avgs[best_week]:+.1f}%). 대부분 스킬에서 양수 수익률 기록.",
        "type": "positive",
    })
    insights.append({
        "icon": "⚠️",
        "text": f"{worst_week} — 전략 평균 수익률 최저 주차 ({week_avgs[worst_week]:+.1f}%). 시장 전반 약세 구간으로 현금 비중 확대가 유효했을 시기.",
        "type": "negative",
    })

    skill_avgs = {sk: _skill_avg(heatmap_kr, sk) for sk in heatmap_kr if heatmap_kr[sk]}
    if skill_avgs:
        best_skill  = max(skill_avgs, key=skill_avgs.get)
        worst_skill = min(skill_avgs, key=skill_avgs.get)
        insights.append({
            "icon": "📈",
            "text": f"KR 최강 스킬: {SKILL_KO.get(best_skill, best_skill)} (평균 {skill_avgs[best_skill]:+.1f}%) — 해당 기간 가장 안정적인 수익을 기록.",
            "type": "positive",
        })
        if skill_avgs[worst_skill] < 0:
            insights.append({
                "icon": "📉",
                "text": f"KR 주의 스킬: {SKILL_KO.get(worst_skill, worst_skill)} (평균 {skill_avgs[worst_skill]:+.1f}%) — 손실 구간이 많아 단독 활용 시 주의 필요.",
                "type": "negative",
            })

    consecutive_pos, consecutive_neg = [], []
    cur_pos, cur_neg = [], []
    for w in weeks:
        avg = week_avgs[w]
        if avg > 0:
            cur_pos.append(w)
            if cur_neg:
                consecutive_neg.append(cur_neg)
                cur_neg = []
        else:
            cur_neg.append(w)
            if cur_pos:
                consecutive_pos.append(cur_pos)
                cur_pos = []
    if cur_pos: consecutive_pos.append(cur_pos)
    if cur_neg: consecutive_neg.append(cur_neg)

    for g in [g for g in consecutive_pos if len(g) >= 3]:
        insights.append({
            "icon": "🔥",
            "text": f"{g[0]}~{g[-1]} — {len(g)}주 연속 전략 평균 양수. 추세 추종 전략이 유효했던 구간.",
            "type": "positive",
        })
    for g in [g for g in consecutive_neg if len(g) >= 2]:
        insights.append({
            "icon": "🧊",
            "text": f"{g[0]}~{g[-1]} — {len(g)}주 연속 전략 평균 음수. 횡보·하락장 구간으로 HOLD 전략이 효과적.",
            "type": "negative",
        })

    bob_data = heatmap_kr.get("best_of_best", {})
    bob_good = [w for w, v in bob_data.items() if v["mean"] > 1.0 and v["n"] >= 3]
    if bob_good:
        insights.append({
            "icon": "⭐",
            "text": f"복합신호(best_of_best) 유효 주차: {', '.join(bob_good)} — 복수 스킬 동시 충족 종목에서 1% 이상 수익.",
            "type": "positive",
        })

    if heatmap_us:
        us_skill_avgs = {sk: _skill_avg(heatmap_us, sk) for sk in heatmap_us if heatmap_us[sk]}
        kr_total = sum(skill_avgs.values()) / len(skill_avgs) if skill_avgs else 0
        us_total = sum(us_skill_avgs.values()) / len(us_skill_avgs) if us_skill_avgs else 0
        if kr_total > us_total:
            insights.append({
                "icon": "🇰🇷",
                "text": f"해당 기간 KR 전략 평균({kr_total:+.1f}%)이 US({us_total:+.1f}%)를 상회. 국내 모멘텀이 상대적으로 강했던 시기.",
                "type": "positive",
            })
        else:
            insights.append({
                "icon": "🇺🇸",
                "text": f"해당 기간 US 전략 평균({us_total:+.1f}%)이 KR({kr_total:+.1f}%)을 상회. 미국 시장 모멘텀이 더 강했던 시기.",
                "type": "positive",
            })

    recent = weeks[-3:]
    if len(recent) >= 2:
        recent_avgs = [week_avgs[w] for w in recent]
        if all(r > 0 for r in recent_avgs):
            insights.append({
                "icon": "📊",
                "text": f"최근 {len(recent)}주({recent[0]}~{recent[-1]}) 연속 양수 — 현재 시장 모멘텀 유지 중. 추세 추종 전략 유효.",
                "type": "positive",
            })
        elif all(r < 0 for r in recent_avgs):
            insights.append({
                "icon": "📊",
                "text": f"최근 {len(recent)}주({recent[0]}~{recent[-1]}) 연속 음수 — 현재 시장 약세 지속 중. 신규 진입 자제 권장.",
                "type": "negative",
            })
        else:
            insights.append({
                "icon": "📊",
                "text": f"최근 {len(recent)}주({recent[0]}~{recent[-1]}) 혼조세 — 방향성 불명확. 선별적 접근 필요.",
                "type": "neutral",
            })

    return insights
