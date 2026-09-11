"""
test_guardrails_adversarial.py — deliberately tries to trip the
confirmation gate (and the block list) with plausible real control names
from each of the three target apps. This is build_checklist.jsx's test-3
item: "Deliberately try to trip the confirmation gate, both to fire it and
to over-fire it."

Honest caveat, worth stating rather than hiding: for Outlook and Microsoft
Edge, these control names are *plausible, not directly observed* — the
Chromium accessibility gap documented in CLAUDE.md means their real
sensitive controls (a real Delete button, a real Clear browsing data menu
item) never actually surfaced in this session's live perception.py runs.
Media Player's cases, by contrast, are drawn from names actually observed
live (see CLAUDE.md's Resolved section). This file tests the rule ENGINE
against realistic inputs either way — it is not a substitute for testing
guardrails.check() against Outlook/Edge's real controls once their content
is actually reachable (via the vision-fallback path, most likely).

Run: python test_guardrails_adversarial.py
"""

from guardrails import check, explain, GateDecision, TargetElement

# (app, control name, control type, expected tier, real-or-plausible)
CASES = [
    # --- Outlook — plausible, not directly observed (see module docstring) ---
    ("Outlook", "Delete", "Button", GateDecision.CONFIRM, "plausible"),
    ("Outlook", "Send", "Button", GateDecision.CONFIRM, "plausible"),
    ("Outlook", "Archive", "Button", GateDecision.ALLOW, "plausible"),
    # real gap found here 2026-09-10: \bdelete\b didn't match "deleted" (word
    # boundaries don't span past-tense forms) — fixed in guardrails.py by
    # widening to \bdelet\w*\b; this case is what caught it
    ("Outlook", "Empty deleted items folder", "MenuItem", GateDecision.CONFIRM, "plausible"),
    ("Outlook", "Reply", "Button", GateDecision.ALLOW, "plausible"),
    ("Outlook", "Sign out", "MenuItem", GateDecision.CONFIRM, "plausible"),

    # --- Microsoft Edge — plausible, not directly observed ---
    ("Microsoft Edge", "Clear browsing data", "Button", GateDecision.ALLOW, "plausible — no pattern matches 'clear' alone"),
    ("Microsoft Edge", "Delete browsing history", "MenuItem", GateDecision.CONFIRM, "plausible"),
    ("Microsoft Edge", "New Tab", "Button", GateDecision.ALLOW, "real, observed live"),
    ("Microsoft Edge", "Search tabs", "Button", GateDecision.ALLOW, "real, observed live"),
    ("Microsoft Edge", "Reset settings to default", "Button", GateDecision.ALLOW, "plausible — no pattern matches 'reset' alone"),

    # --- Media Player — drawn from real, live-observed elements ---
    ("Media Player", "Search", "Button", GateDecision.ALLOW, "real, observed live"),
    ("Media Player", "Open file(s)", "SplitButton", GateDecision.ALLOW, "real, observed live"),
    ("Media Player", "Delete from library", "MenuItem", GateDecision.CONFIRM, "plausible"),
    ("Media Player", "Play", "Button", GateDecision.ALLOW, "plausible"),

    # --- Cross-app block-list cases (should fire regardless of app) ---
    ("Outlook", "Factory reset", "MenuItem", GateDecision.BLOCK, "plausible, cross-app"),
    ("Microsoft Edge", "Disable firewall", "MenuItem", GateDecision.BLOCK, "plausible, cross-app"),
    ("Media Player", "Reformat drive", "MenuItem", GateDecision.BLOCK, "plausible, cross-app"),
]


def main() -> None:
    all_pass = True
    for app, name, control_type, expected, provenance in CASES:
        target = TargetElement(name=name, control_type=control_type, app_name=app)
        got = check(target)
        status = "PASS" if got is expected else "FAIL"
        if got is not expected:
            all_pass = False
        print(f"[{status}] ({app}, {provenance}) {explain(target, got)}")

    print()
    print("ALL PASS" if all_pass else "SOME CASES FAILED — see above")


if __name__ == "__main__":
    main()
