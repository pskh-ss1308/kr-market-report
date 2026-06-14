"""
실용적 인사이트 — 최근 3~4주 기준 현재 상태 + 다음 주 전략 제안
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


def _recent_avg(heatmap_data, skill, n=4):
    """특정 스킬의 최근 n주 평균 수익률"""
    weeks = _sorted_weeks(heatmap_data)
    recent = weeks[-n:]
    vals = [
        heatmap_data[skill][w]["mean"]
        for w in recent
        if skill in heatmap_data and w in heatmap_data[skill]
    ]
    return sum(vals) / len(vals) if vals else None


def _recent_winrate(heatmap_data, skill, n=4):
    """특정 스킬의 최근 n주 평균 승률"""
    weeks = _sorted_weeks(heatmap_data)
    recent = weeks[-n:]
    vals = [
        heatmap_data[skill][w]["win_rate"]
        for w in recent
        if skill in heatmap_data and w in heatmap_data[skill]
    ]
    return sum(vals) / len(vals) if vals else None


def _consecutive_trend(heatmap_data, skill):
    """최근 연속 양수/음수 주 수 반환 (양수면 +n, 음수면 -n)"""
    weeks = _sorted_weeks(heatmap_data)
    if skill not in heatmap_data:
        return 0
    sk_data = heatmap_data[skill]
    count = 0
    sign  = None
    for w in reversed(weeks):
        if w not in sk_data:
            break
        v = sk_data[w]["mean"]
        cur_sign = 1 if v > 0 else -1
        if sign is None:
            sign = cur_sign
        if cur_sign != sign:
            break
        count += 1
    return sign * count if sign else 0


def _current_week(heatmap_data):
    weeks = _sorted_weeks(heatmap_data)
    return weeks[-1] if weeks else "?"


def _week_avg_all(heatmap_data, week):
    vals = [
        v["mean"]
        for sk_data in heatmap_data.values()
        for w, v in sk_data.items()
        if w == week
    ]
    return sum(vals) / len(vals) if vals else 0.0


def generate_insights(heatmap_kr, heatmap_us=None):
    insights = []
    weeks = _sorted_weeks(heatmap_kr)
    if not weeks:
        return insights

    current_week = weeks[-1]
    prev_week    = weeks[-2] if len(weeks) >= 2 else None

    # ── 1. 이번 주 추천 스킬 (최근 4주 평균 수익률 + 승률 기준) ──
    skill_scores = {}
    for sk in heatmap_kr:
        avg = _recent_avg(heatmap_kr, sk, n=4)
        wr  = _recent_winrate(heatmap_kr, sk, n=4)
        if avg is not None and wr is not None:
            skill_scores[sk] = (avg, wr)

    if skill_scores:
        best_sk = max(skill_scores, key=lambda s: skill_scores[s][0])
        avg, wr = skill_scores[best_sk]
        insights.append({
            "icon": "🎯",
            "text": f"이번 주 추천 스킬: {SKILL_KO.get(best_sk, best_sk)} — 최근 4주 평균 {avg:+.1f}%, 승률 {wr:.0f}%로 현재 가장 안정적.",
            "type": "positive",
        })

        # 주의 스킬
        worst_sk = min(skill_scores, key=lambda s: skill_scores[s][0])
        w_avg, w_wr = skill_scores[worst_sk]
        if w_avg < 0:
            insights.append({
                "icon": "🚫",
                "text": f"이번 주 주의 스킬: {SKILL_KO.get(worst_sk, worst_sk)} — 최근 4주 평균 {w_avg:+.1f}%, 승률 {w_wr:.0f}%. 단독 진입 자제 권장.",
                "type": "negative",
            })

    # ── 2. 연속 강세 스킬 탐지 ────────────────────────────
    for sk in heatmap_kr:
        trend = _consecutive_trend(heatmap_kr, sk)
        if trend >= 3:
            insights.append({
                "icon": "🔥",
                "text": f"{SKILL_KO.get(sk, sk)} {trend}주 연속 양수 진행 중 — 모멘텀 유지. 추세 추종 관점에서 유효한 구간.",
                "type": "positive",
            })
        elif trend <= -2:
            insights.append({
                "icon": "❄️",
                "text": f"{SKILL_KO.get(sk, sk)} {abs(trend)}주 연속 음수 — 현재 작동하지 않는 전략. 이번 주 신호 무시 권장.",
                "type": "negative",
            })

    # ── 3. 이번 주 시장 전반 상태 ────────────────────────
    cur_avg = _week_avg_all(heatmap_kr, current_week)
    if cur_avg > 2:
        insights.append({
            "icon": "📈",
            "text": f"최신 집계 주차({current_week}) 전략 평균 {cur_avg:+.1f}% — 시장 전반 강세. 공격적 포지션 유효.",
            "type": "positive",
        })
    elif cur_avg < -1:
        insights.append({
            "icon": "📉",
            "text": f"최신 집계 주차({current_week}) 전략 평균 {cur_avg:+.1f}% — 시장 전반 약세. 현금 비중 확대 고려.",
            "type": "negative",
        })
    else:
        insights.append({
            "icon": "📊",
            "text": f"최신 집계 주차({current_week}) 전략 평균 {cur_avg:+.1f}% — 혼조세. 선별적 접근 필요.",
            "type": "neutral",
        })

    # ── 4. best_of_best 최근 상태 ────────────────────────
    bob = heatmap_kr.get("best_of_best", {})
    if current_week in bob:
        v = bob[current_week]
        if v["mean"] > 1.0 and v["n"] >= 3:
            insights.append({
                "icon": "⭐",
                "text": f"복합신호(best_of_best) {current_week} 유효 — {v['n']}개 종목, 평균 {v['mean']:+.1f}%, 승률 {v['win_rate']}%. 복수 스킬 충족 종목 우선 검토.",
                "type": "positive",
            })

    # ── 5. KR vs US 최근 비교 ────────────────────────────
    if heatmap_us:
        kr_scores = [s[0] for s in skill_scores.values()]
        us_skill_scores = {}
        for sk in heatmap_us:
            avg = _recent_avg(heatmap_us, sk, n=4)
            if avg is not None:
                us_skill_scores[sk] = avg
        us_scores = list(us_skill_scores.values())

        if kr_scores and us_scores:
            kr_avg = sum(kr_scores) / len(kr_scores)
            us_avg = sum(us_scores) / len(us_scores)
            if kr_avg > us_avg:
                insights.append({
                    "icon": "🇰🇷",
                    "text": f"최근 4주 KR({kr_avg:+.1f}%) > US({us_avg:+.1f}%) — 국내 시장 모멘텀 우위. KR 전략 집중 유효.",
                    "type": "positive",
                })
            else:
                insights.append({
                    "icon": "🇺🇸",
                    "text": f"최근 4주 US({us_avg:+.1f}%) > KR({kr_avg:+.1f}%) — 미국 시장 모멘텀 우위. US 전략 병행 고려.",
                    "type": "positive",
                })

    # ── 6. 다음 주 한 줄 전략 제안 ───────────────────────
    pos_skills = [sk for sk, (avg, wr) in skill_scores.items() if avg > 0 and wr >= 55]
    if pos_skills:
        names = ", ".join([SKILL_KO.get(s, s) for s in pos_skills[:3]])
        insights.append({
            "icon": "💡",
            "text": f"다음 주 전략 제안: {names} 신호 발생 종목 위주로 대응. 승률 55% 이상 + 양수 수익률 유지 중.",
            "type": "positive",
        })

    return insights
