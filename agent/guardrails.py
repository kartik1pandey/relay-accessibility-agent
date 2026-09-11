"""
guardrails.py — the confirmation-gate and hard-block rule engine.

This is the one module in this scaffold that's fully real, not a stub:
it's plain pattern matching, no model call needed, so there's nothing
here that depends on hardware you don't have yet.

Design: every action the reasoning layer wants to take is checked here
BEFORE it reaches the actuator. Three outcomes:
  - ALLOW   : execute immediately
  - CONFIRM : speak a confirmation prompt, wait for a spoken "yes",
              then execute
  - BLOCK   : refuse outright, and say why

Match against the UI Automation element's Name, ControlType, and any
AutomationId — not against a free-text guess of what the user meant —
so this stays auditable: you can point at exactly which rule fired
and why, for any action, after the fact.
"""

from dataclasses import dataclass
from enum import Enum
import re


class GateDecision(Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    BLOCK = "block"


@dataclass
class TargetElement:
    """A normalized view of the UI element the agent wants to act on."""
    name: str              # e.g. "Send", "Delete conversation", "Submit"
    control_type: str      # e.g. "Button", "MenuItem", "Hyperlink"
    automation_id: str = ""
    app_name: str = ""     # e.g. "Outlook", "Microsoft Edge"


# --- Rule lists ---------------------------------------------------------
# Keep these as plain, editable lists. Add app-specific entries as you
# test against real apps — this list will grow faster than any other
# part of the project, and that is expected, not a sign something's wrong.

CONFIRM_PATTERNS = [
    r"\bsend\b", r"\bsubmit\b", r"\bpost\b", r"\bpublish\b", r"\breply all\b",
    r"\bpay\b", r"\bbuy\b", r"\bpurchase\b", r"\bcheckout\b", r"\btransfer\b", r"\bdonate\b",
    # \bdelet\w*\b (not just \bdelete\b) catches "deleted"/"deletion"/"deleting" too —
    # widened 2026-09-10 after adversarial testing (test_guardrails_adversarial.py)
    # found a real gap: \bdelete\b's word boundary does NOT match inside "deleted",
    # so a plausible real control like "Empty deleted items folder" silently fell
    # through to ALLOW. Same reasoning applied to remove/erase. Widening, not
    # narrowing — consistent with this file's own "harder to change, not easier" rule.
    r"\bdelet\w*\b", r"\bremov\w*\b", r"\bempty trash\b", r"\beras\w*\b", r"\bunsubscribe\b",
    r"\bchange password\b", r"\bdelete account\b", r"\bsign out\b", r"\brevoke\b", r"\bdisable\b",
    # Added 2026-09-10 from competitive research (COMPETITIVE_RESEARCH.md):
    # ScreenSaathi's SafetyGuard.kt's IRREVERSIBLE_HINTS list — built after a
    # real incident (their model confidently tapped "Pay Now" on a banking
    # screen) — includes these four real gaps this list didn't have yet.
    r"\border\b", r"\bbook\b", r"\bcall\b", r"\bwithdraw\b",
]

BLOCK_PATTERNS = [
    r"\bfactory reset\b", r"\breformat\b", r"\bwipe device\b", r"\buninstall windows\b",
    r"\bdisable firewall\b", r"\bdisable antivirus\b",
]

# App-specific additions go here as you find them during testing, e.g.:
# CONFIRM_PATTERNS.append(r"\barchive all\b")  # discovered while testing Outlook


def _matches_any(text: str, patterns: list) -> bool:
    text = text.lower()
    return any(re.search(p, text) for p in patterns)


def check(target: TargetElement) -> GateDecision:
    """Return the gate decision for a proposed action on `target`."""
    haystack = f"{target.name} {target.control_type} {target.automation_id}"

    if _matches_any(haystack, BLOCK_PATTERNS):
        return GateDecision.BLOCK
    if _matches_any(haystack, CONFIRM_PATTERNS):
        return GateDecision.CONFIRM
    return GateDecision.ALLOW


def explain(target: TargetElement, decision: GateDecision) -> str:
    """A short, human-readable reason — used both in the spoken prompt
    and in the audit log, so what the user hears and what gets logged
    always match."""
    if decision is GateDecision.BLOCK:
        return f'Blocked: "{target.name}" matches a hard-blocked action and will never run.'
    if decision is GateDecision.CONFIRM:
        return f'Needs confirmation: "{target.name}" matches a sensitive-action pattern.'
    return f'Allowed: "{target.name}" did not match any confirm or block pattern.'


if __name__ == "__main__":
    # a handful of sanity checks you can run right now, no hardware needed
    cases = [
        (TargetElement(name="Send", control_type="Button"), GateDecision.CONFIRM),
        (TargetElement(name="Scroll down", control_type="Pane"), GateDecision.ALLOW),
        (TargetElement(name="Reformat drive", control_type="MenuItem"), GateDecision.BLOCK),
        (TargetElement(name="Play", control_type="Button"), GateDecision.ALLOW),
        (TargetElement(name="Delete conversation", control_type="MenuItem"), GateDecision.CONFIRM),
    ]
    for target, expected in cases:
        got = check(target)
        status = "PASS" if got is expected else "FAIL"
        print(f"[{status}] {explain(target, got)}")
