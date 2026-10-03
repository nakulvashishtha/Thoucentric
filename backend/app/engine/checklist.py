"""Auto-approval checklist (section 8.3). All nine tests must pass; every test reports threshold and actual."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChecklistInput:
    origin_type: str
    is_belief: bool
    tier: int | None
    traced: bool
    corroborated: bool            # a second independent item within tolerance (only matters for Tier 3)
    recent: bool
    recency_actual: str
    recency_window: int
    convertible: bool
    convertible_actual: str
    verified: bool
    verified_actual: str
    duplicate_of: str | None
    privacy_flag: bool
    supports_must_have: bool
    sets_pass_line: bool
    never_auto_origins: list[str] = field(default_factory=lambda: ["client_file", "expert_note", "open_web"])


def run_checklist(c: ChecklistInput) -> list[dict]:
    tests: list[dict] = []

    def add(name: str, ok: bool, threshold: str, actual: str) -> None:
        tests.append({"test": name, "pass": bool(ok), "threshold": threshold, "actual": actual})

    origin_label = {"client_file": "client file", "expert_note": "expert note", "open_web": "open web",
                    "firm_archive": "firm archive", "paid_db": "paid database", "benchmark": "benchmark"}
    src_ok = c.origin_type not in c.never_auto_origins and not c.is_belief
    actual = "the client's belief" if c.is_belief else origin_label.get(c.origin_type, c.origin_type)
    add("Source type", src_ok, "not client, expert, open web or the client's belief", actual)

    if c.tier in (1, 2):
        tier_ok, tier_actual = True, f"Tier {c.tier}"
    elif c.tier == 3:
        tier_ok = c.traced and c.corroborated
        tier_actual = "Tier 3, " + ("traced and corroborated" if tier_ok else
                                     "not traced" if not c.traced else "not corroborated")
    elif c.tier == 4:
        tier_ok, tier_actual = False, "Tier 4"
    else:
        tier_ok, tier_actual = False, "no tier (person-decided)"
    add("Credibility tier", tier_ok, "Tier 1 or 2 (Tier 3 only if traced and corroborated)", tier_actual)

    add("Recent", c.recent, f"dated within {c.recency_window} months", c.recency_actual)
    add("Traced", c.traced, "names its original source or method", "yes" if c.traced else "no")
    add("Convertible", c.convertible, "on the idea's measure", c.convertible_actual)
    add("Quote verified", c.verified, "figure found in the quoted text", c.verified_actual)
    add("Not a copy", c.duplicate_of is None, "not a copy of a counted original",
        "original" if c.duplicate_of is None else f"copy of {c.duplicate_of}")
    add("Privacy", not c.privacy_flag, "no private client data", "clean" if not c.privacy_flag else "flagged")
    load = c.supports_must_have or c.sets_pass_line
    add("Not load-bearing", not load, "does not support a must-have or set a pass line",
        "supports a must-have" if c.supports_must_have else "sets a pass line" if c.sets_pass_line else "no")
    return tests


def all_pass(tests: list[dict]) -> bool:
    return all(t["pass"] for t in tests)


def failing(tests: list[dict]) -> list[str]:
    return [t["test"] for t in tests if not t["pass"]]
