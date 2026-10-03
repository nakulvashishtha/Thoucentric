"""Verdict logic per idea (section 8.4), adding-up rule (8.5) and fixed 'why' templates."""
from __future__ import annotations

from dataclasses import dataclass, field

from .convert import fmt


@dataclass
class Fig:
    origin: str                 # original_group_id: one per independent source
    low: float
    high: float
    client_reported: bool = False
    calculated: bool = False
    evidence_id: str = ""


def classify(low, high, L, cmp, tol_pct):
    T = abs(L) * tol_pct / 100.0
    d = 1 if cmp == '>=' else -1
    if low != high and low <= L <= high:                 # range straddles the line
        mid = (low + high) / 2
        return ('pass' if (mid - L) * d >= 0 else 'fail'), True
    nearest = low if abs(low - L) <= abs(high - L) else high
    margin = (nearest - L) * d
    return ('pass' if margin >= 0 else 'fail'), abs(margin) <= T


def verdict(figs, L, cmp, tol_pct, fact_type):  # figs: origin, low, high, client_reported, calculated
    n = len({f.origin for f in figs})
    if n < (2 if fact_type == 'market' else 1): return ('not_enough', None)
    cls = [classify(f.low, f.high, L, cmp, tol_pct) for f in figs]
    sides = {c[0] for c in cls}; boundary = any(c[1] for c in cls)
    if len(sides) == 2: return ('conflicting', 'low')
    res = 'holds' if sides == {'pass'} else 'fails'
    single_calc = fact_type == 'market' and n == 1 and all(f.calculated for f in figs)
    if boundary or single_calc: return (res, 'low')
    if all(f.client_reported for f in figs) or n < 2: return (res, 'medium')
    return (res, 'high')


@dataclass
class VerdictResult:
    result: str
    confidence: str             # high | medium | low | none
    reason_codes: list[str] = field(default_factory=list)
    why: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    figure_classes: list[dict] = field(default_factory=list)


RESULT_LABELS = {"holds": "Holds", "fails": "Fails", "conflicting": "Conflicting",
                 "not_enough": "Not enough evidence"}


def with_unit(v: float, unit: str) -> str:
    u = (unit or "").strip()
    return f"{fmt(v)}{'' if u.startswith('%') or not u else ' '}{u}"


def _fig_text(f: Fig) -> str:
    return fmt(f.low) if f.low == f.high else f"{fmt(f.low)} to {fmt(f.high)}"


def evaluate(figs: list[Fig], L: float, cmp: str, tol_pct: float, fact_type: str, unit: str,
             min_sources: dict | None = None) -> VerdictResult:
    """Run the reference verdict and attach reason codes and a plain 'why' built from fixed templates."""
    result, conf = verdict(figs, L, cmp, tol_pct, fact_type)
    need = (min_sources or {}).get(fact_type, 2 if fact_type == "market" else 1)
    n = len({f.origin for f in figs})
    classes = []
    for f in figs:
        side, boundary = classify(f.low, f.high, L, cmp, tol_pct)
        classes.append({"evidence_id": f.evidence_id, "figure": _fig_text(f), "side": side, "boundary": boundary,
                        "client_reported": f.client_reported, "calculated": f.calculated})
    codes: list[str] = []
    line = with_unit(L, unit)
    direction = "at least" if cmp == ">=" else "at most"
    figures = " and ".join(sorted({_fig_text(f) for f in figs})) if figs else ""
    if result == "not_enough":
        codes.append("NOT_ENOUGH_SOURCES")
        if n == 0:
            why = (f"No counted evidence yet. This idea needs {need} independent "
                   f"source{'s' if need > 1 else ''} to be tested against {direction} {line}.")
        else:
            why = (f"Only {n} independent source{'s' if n > 1 else ''} ({figures}); "
                   f"this {'market fact' if fact_type == 'market' else 'idea'} needs {need}.")
        return VerdictResult(result, "none", codes, why, [f.evidence_id for f in figs], classes)

    boundary_figs = [c["figure"] for c in classes if c["boundary"]]
    if result == "conflicting":
        codes.append("CONFLICTING")
        passing = [c["figure"] for c in classes if c["side"] == "pass"]
        failing = [c["figure"] for c in classes if c["side"] == "fail"]
        why = (f"Sources disagree: {' and '.join(passing)} meet{'s' if len(passing) == 1 else ''} the line of "
               f"{direction} {line}, but {' and '.join(failing)} do{'es' if len(failing) == 1 else ''} not.")
    else:
        verb = "meet" if result == "holds" else "miss"
        if len(figs) == 1:
            verb += "es" if verb == "miss" else "s"
        why = f"{figures} {verb} the line of {direction} {line}"
        if boundary_figs:
            codes.append("BOUNDARY")
            why += f", but {' and '.join(boundary_figs)} sits within the tolerance band or straddles the line"
        elif result == "holds":
            codes.append("ALL_PASS_CLEAR")
            why += f", clear of the {fmt(tol_pct)}% tolerance band"
        else:
            codes.append("ALL_FAIL_CLEAR")
            why += f", clear of the {fmt(tol_pct)}% tolerance band"
        single_calc = fact_type == "market" and n == 1 and all(f.calculated for f in figs)
        if single_calc:
            codes.append("SINGLE_CALCULATED")
            why += "; it rests on a single calculated figure"
        if conf == "medium":
            if all(f.client_reported for f in figs):
                codes.append("CLIENT_REPORTED_CAP")
                why += "; client-reported data is capped at Medium confidence"
            else:
                codes.append("SINGLE_SOURCE")
                why += "; only one independent source"
        elif conf == "high":
            codes.append("INDEPENDENT_AGREE")
            why += f"; {n} independent sources agree"
        why += "."
    return VerdictResult(result, conf, codes, why[0].upper() + why[1:], [f.evidence_id for f in figs], classes)


OVERALL_LABELS = {
    "not_achievable": "Not achievable at the agreed pass line",
    "consultant_decides": "The consultant decides",
    "achievable": "Achievable",
}


def adding_up(verdicts: list[dict]) -> tuple[str, str]:
    """verdicts: [{code, must_have, result}] -> (overall, rule_applied text)."""
    must = [v for v in verdicts if v["must_have"]]
    failed = [v["code"] for v in must if v["result"] == "fails"]
    if failed:
        return "not_achievable", f"Must-have {', '.join(failed)} fails, so the plan is not achievable at the agreed pass line."
    unsettled = [v["code"] for v in must if v["result"] in ("conflicting", "not_enough")]
    if unsettled:
        return "consultant_decides", (f"Must-have {', '.join(unsettled)} is not settled, so the consultant decides.")
    return "achievable", "Every must-have idea holds, so the plan is achievable."
