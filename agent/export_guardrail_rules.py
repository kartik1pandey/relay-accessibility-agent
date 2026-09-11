"""
export_guardrail_rules.py — writes guardrails.py's real CONFIRM_PATTERNS and
BLOCK_PATTERNS out to ../web/guardrail_rules.json, for the admin UI to read.

Why a JSON export instead of hand-copying the lists into the UI: the admin
surface must never drift from the actual rule engine (see CLAUDE.md — "this
should get harder to change, not easier"). Re-run this after editing
guardrails.py; the UI always reflects whatever this file last produced, not a
frozen copy someone forgot to update.

Writes across the repo's agent/ -> web/ split (see the top-level README) —
the path below is relative to this file's own location, not the working
directory, so this runs correctly whether invoked as `python
export_guardrail_rules.py` from inside agent/ or `python
agent/export_guardrail_rules.py` from the repo root.

Run: python export_guardrail_rules.py
"""

import json
import os
import re

from guardrails import CONFIRM_PATTERNS, BLOCK_PATTERNS

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "web", "guardrail_rules.json")


def humanize(pattern: str) -> str:
    """Turn a raw regex like r"\\bchange password\\b" into "change password"
    for display — strips the word-boundary anchors this file's patterns
    consistently use. Falls back to the raw pattern if it doesn't match that
    shape, so an unusual future pattern is shown honestly rather than mangled.

    A trailing `\\w*` stem wildcard (e.g. r"\\bdelet\\w*\\b", matching
    delete/deleted/deletion alike — see guardrails.py's CONFIRM_PATTERNS)
    displays as "delet*", not the raw escape sequence."""
    m = re.fullmatch(r"\\b(.+)\\b", pattern)
    if not m:
        return pattern
    inner = m.group(1)
    if inner.endswith(r"\w*"):
        return inner[: -len(r"\w*")] + "*"
    return inner


def to_rules(patterns: list, tier: str) -> list:
    return [{"pattern": p, "phrase": humanize(p), "tier": tier} for p in patterns]


if __name__ == "__main__":
    rules = {
        "confirm": to_rules(CONFIRM_PATTERNS, "confirm"),
        "block": to_rules(BLOCK_PATTERNS, "block"),
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
    print(
        f"wrote {os.path.normpath(OUTPUT_PATH)}: "
        f"{len(rules['confirm'])} confirm patterns, {len(rules['block'])} block patterns"
    )
