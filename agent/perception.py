"""
perception.py — reads the current screen as structured data first, and
only falls back to a vision model when the accessibility tree doesn't
give you enough to work with. Also owns action execution, since acting
on an element only makes sense against the same tree you just read it
from.

Verify the exact `uiautomation` API against its own docs before running
this on a real device — the shapes below reflect its documented design
(each control type maps to an XxxControl class with Name/AutomationId
search and a small set of interaction methods), but exact method names
can drift between versions.

Reference: https://github.com/yinkaisheng/Python-UIAutomation-for-Windows

Real, verified finding (2026-09-10, tested against a live Microsoft Edge
window on this machine, https://example.com loaded): walking the UIA tree
up to 14 levels deep (285 elements total) surfaces window chrome — tab
bar, toolbars, minimize/maximize/close — but never the actual page content
(no "Example Domain" heading, no page links). This isn't a depth problem;
Chromium-based apps only build their *complete* accessibility tree for a
detected assistive-technology client under conditions this scaffold hasn't
confirmed it satisfies. Practical consequence: for Microsoft Edge
specifically, `tree_is_usable` can come back True from chrome controls
alone, while the model still has no real page content to act on — the
vision-fallback path is likely doing more of the real work for Edge than
for Mail or a media player, not a rare edge case. Flagged honestly rather
than patched around; see CLAUDE.md's Open Questions.

Media Player, by contrast, verified cleanly the same day: 211 elements,
113 named+enabled, and real actionable content (Search, Open file(s), a
Recent media list) — not just chrome. `tree_is_usable` and `act_on` both
behaved as designed on the first real try.

Outlook (the real app behind `TARGET_APPS["mail"]` on this machine —
see agent.py) didn't render a main window at all on first launch; its
process started but stayed windowless, pending an account sign-in.
Once signed in and verified: **the same Chromium limitation as Edge,
confirmed, not just suspected.** Outlook's tree contains a "Chrome
Legacy Window" pane — the identical node Edge's tree showed — and
walking 12 levels deep surfaces only window chrome (Minimize/Maximize/
Close), never real mail content (no inbox items, no subject lines, no
compose button). `tree_is_usable` still comes back True from chrome
alone (7 named+enabled elements meets the threshold). This means **two
of the three target apps** (Outlook and Edge) are both Chromium/WebView2
-based under the hood and share this exact limitation — not a rare edge
case affecting one app, a real architectural pattern affecting most of
this scaffold's target surface. Media Player, a native app, remains the
one target app that exposes real content cleanly via UI Automation.
Practical consequence: the vision-fallback path (screenshot + VLM) is
likely doing the *majority* of real content-level work for two of three
target apps, not the minority-case fallback the architecture doc
originally implied.

**Update 2026-09-10, for Edge specifically: a real, verified fix exists —
see `cdp_perception.py`.** Competitive research (COMPETITIVE_RESEARCH.md)
surfaced that a similar project sidesteps this exact class of problem by
reading the DOM directly instead of an OS accessibility API. Edge exposes
the same capability itself via the Chrome DevTools Protocol: launched with
`--remote-debugging-port=9222 --remote-allow-origins=*`, real page content
(headings, links, a real search input) was read, a real value was typed
into a real input and confirmed by re-reading the live DOM afterward, and
a real click was dispatched against a real element found by its visible
text — all verified against live pages, not simulated. This doesn't extend
to Outlook (a desktop app, not a browser tab CDP can attach to) — that
Chromium/WebView2 limitation remains genuinely open for it.
"""

import concurrent.futures
import time
from dataclasses import dataclass, field
from typing import Optional, List

try:
    import uiautomation as auto
except ImportError:
    # Lets this module be imported (and its logic unit-tested) on a
    # non-Windows dev machine. Anything that actually touches `auto`
    # will raise a clear RuntimeError instead of failing at import time.
    auto = None


@dataclass
class ScreenElement:
    name: str
    control_type: str
    automation_id: str = ""
    is_enabled: bool = True
    bounding_rect: Optional[tuple] = None


@dataclass
class ScreenState:
    window_title: str
    elements: List[ScreenElement]
    tree_is_usable: bool  # False is what triggers the vision fallback


# How many named, enabled controls a window needs before the tree is
# trusted over falling back to vision. Tune this against your three
# target apps — it's the single most important constant in this file,
# and the only way to get it right is to test it against the real apps.
MIN_USABLE_ELEMENTS = 4

# How many levels deep to walk beneath the window. Confirmed 2026-09-10
# against a live Microsoft Edge window: its own window-chrome controls
# (Minimize/Maximize/Close, the tab bar) sit at depth 5, not depth 2 as
# originally assumed here — Chromium-based apps nest their UIA tree far
# deeper than e.g. Notepad's. Real page content (address bar, page DOM)
# sits deeper still; a depth-2 walk against Edge finds close to nothing
# and always falls through to the vision path.
MAX_WALK_DEPTH = 6


def _walk(control, depth: int, elements: list) -> None:
    if depth > MAX_WALK_DEPTH:
        return
    for child in control.GetChildren():
        elements.append(_to_screen_element(child))
        _walk(child, depth + 1, elements)


def _require_windows():
    if auto is None:
        raise RuntimeError(
            "uiautomation is only available on Windows — run this on the target device."
        )


# Characters some apps embed invisibly in their own window titles.
# Confirmed 2026-09-10 against a live Microsoft Edge window: its real title
# is "...Microsoft​ Edge" — a zero-width space right after "Microsoft" —
# which silently breaks a naive substring search for "Microsoft Edge".
# uiautomation's own SubName matching does a raw substring check against
# that title, so it fails the same way; hence the hand-rolled search below
# instead of `auto.WindowControl(SubName=...)`.
_INVISIBLE_CHARS = ("​", "‌", "‍", "﻿")


def _normalize_title(title: str) -> str:
    for ch in _INVISIBLE_CHARS:
        title = title.replace(ch, "")
    return title


def _find_window(window_title_substring: str, timeout: float = 2.0):
    target = window_title_substring.lower()
    deadline = time.time() + timeout
    while True:
        for w in auto.GetRootControl().GetChildren():
            if w.ControlTypeName == "WindowControl" and target in _normalize_title(w.Name or "").lower():
                return w
        if time.time() >= deadline:
            return None
        time.sleep(0.1)


def read_ui_tree(window_title_substring: str) -> ScreenState:
    """Read the live UI Automation tree for the named window."""
    _require_windows()

    window = _find_window(window_title_substring)
    if window is None:
        return ScreenState(window_title=window_title_substring, elements=[], tree_is_usable=False)

    elements = []
    _walk(window, 1, elements)

    named_enabled = [e for e in elements if e.name and e.is_enabled]
    return ScreenState(
        window_title=window.Name,
        elements=elements,
        tree_is_usable=len(named_enabled) >= MIN_USABLE_ELEMENTS,
    )


def _to_screen_element(control) -> ScreenElement:
    return ScreenElement(
        name=control.Name,
        control_type=control.ControlTypeName,
        automation_id=getattr(control, "AutomationId", ""),
        is_enabled=control.IsEnabled,
        bounding_rect=control.BoundingRectangle,
    )


def describe_via_vision(screenshot_path: str, reasoner, prompt: str = None) -> str:
    """Fallback path: hand a screenshot to the vision model and get back
    a plain-text description the reasoning layer can use the same way
    it would use a tree dump. `reasoner` is a models.LocalReasoner.

    Takes a file path, not raw bytes — matches GenieX's real VLM contract
    (`AutoModelForVision2Seq.generate(..., images=[path])`), confirmed in
    models.py."""
    prompt = prompt or (
        "Describe the visible, interactable controls on this screen: "
        "buttons, links, fields, and their approximate labels."
    )
    return reasoner.describe_image(screenshot_path, prompt)


class AppNotRespondingError(RuntimeError):
    """Raised when an action doesn't complete within ACTION_TIMEOUT_SECONDS
    — the target app's own message loop appears hung, not just slow.
    Distinct from LookupError (element genuinely gone) on purpose: agent.py
    gives the user a different, honest message for each."""


# How long to wait for a single UI Automation action (Click/SetValue/Wheel)
# before treating the app as non-responding rather than just busy. These
# calls are normally near-instant; a real hang looks nothing like a slow
# but healthy 200ms response, so this doesn't need to be generous.
ACTION_TIMEOUT_SECONDS = 5.0


def act_on(element: ScreenElement, action: str, value: str = "") -> None:
    """Execute an action against a real element found via read_ui_tree.

    Re-fetches the element by name right before acting, since the
    screen may have changed since it was first read — never act on a
    stale reference from a previous turn."""
    _require_windows()

    control = auto.Control(searchDepth=20, Name=element.name, ControlTypeName=element.control_type)
    if not control.Exists(maxSearchSeconds=2):
        raise LookupError(
            f"'{element.name}' is no longer on screen — the screen changed since it was read."
        )

    def _dispatch() -> None:
        if action == "click":
            control.Click()
        elif action == "set_text":
            control.GetValuePattern().SetValue(value)
        elif action == "scroll_down":
            control.WheelDown()
        elif action == "scroll_up":
            control.WheelUp()
        else:
            raise ValueError(f"Unhandled action type: {action!r}")

    # A real hang here means the target app's message loop stopped
    # responding, not that this call is merely slow — run it on a worker
    # thread so a genuine hang can be detected and reported instead of
    # freezing the whole agent.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_dispatch)
        try:
            future.result(timeout=ACTION_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise AppNotRespondingError(
                f"'{element.name}' ({element.control_type}) didn't respond within "
                f"{ACTION_TIMEOUT_SECONDS}s — the app may be hung, not just slow."
            )
