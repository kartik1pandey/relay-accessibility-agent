"""
test_tasks.py — a fixed task list per target app, run for real against live
windows on this machine, with a success-rate report. This is build_checklist
.jsx's test-2 item: "Build a fixed task list per target app and track
success rate against it."

Tasks are deliberately safe and reversible (scrolls, opening a non-destructive
search panel) — never anything that would need a guardrail confirm/block in
real use, since this harness runs unattended.

Outlook's task is honestly different from the other three: its real content
is Chromium/WebView2-based and doesn't surface any control safe to click
without disrupting the window (see CLAUDE.md's Open Questions) — so its
"task" is a coverage check (tree_is_usable), not an action, and that
difference is reported plainly rather than papered over with a fake action.

Run: python test_tasks.py
"""

import subprocess
import time
from dataclasses import dataclass, field

from perception import read_ui_tree, act_on, AppNotRespondingError


@dataclass
class Task:
    name: str
    control_name: str = ""
    control_type: str = ""
    action: str = ""
    action_only: bool = True  # False for a coverage-only check (Outlook)


@dataclass
class AppSpec:
    key: str
    window_title: str
    launch: callable
    tasks: list = field(default_factory=list)
    settle_seconds: float = 1.5


def _launch_notepad():
    subprocess.Popen(["notepad.exe"])


def _launch_edge():
    subprocess.Popen(["cmd", "/c", "start", "msedge", "https://example.com"], shell=False)


def _launch_media_player():
    subprocess.Popen(
        ["explorer.exe", r"shell:AppsFolder\Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic"]
    )


def _launch_outlook():
    subprocess.Popen(
        ["explorer.exe", r"shell:AppsFolder\microsoft.windowscommunicationsapps_8wekyb3d8bbwe!microsoft.windowslive.mail"]
    )


APPS = [
    AppSpec(
        key="notepad",
        window_title="Notepad",
        launch=_launch_notepad,
        settle_seconds=3.0,
        tasks=[
            Task(name="scroll down", control_name="Text Editor", control_type="EditControl", action="scroll_down"),
            Task(name="scroll up", control_name="Text Editor", control_type="EditControl", action="scroll_up"),
        ],
    ),
    AppSpec(
        key="media_player",
        window_title="Media Player",
        launch=_launch_media_player,
        settle_seconds=6.0,  # verified 2026-09-10: home content can take a few seconds to
                             # fully render (7 elements if checked early, 211 once settled)
        tasks=[
            Task(name="open search", control_name="Search", control_type="ButtonControl", action="click"),
        ],
    ),
    AppSpec(
        key="edge",
        window_title="Microsoft Edge",
        launch=_launch_edge,
        settle_seconds=6.0,  # real page load takes longer than a native app launch
        tasks=[
            Task(name="open tab search", control_name="Search tabs", control_type="ButtonControl", action="click"),
        ],
    ),
    AppSpec(
        key="outlook",
        window_title="Outlook",
        launch=_launch_outlook,
        settle_seconds=20.0,  # observed 2026-09-10: launch-to-window timing is genuinely
                              # inconsistent across relaunches — sometimes ready in ~5s,
                              # sometimes still windowless past 10s. Not something this
                              # harness can paper over; recorded, not hidden.
        tasks=[
            # Honest difference from the other three: Outlook's real content
            # is Chromium/WebView2-based (see CLAUDE.md) and no control safe
            # to click without disrupting the window has been found — this
            # checks tree coverage, not an action.
            Task(name="tree is usable (coverage only, no safe action found)", action_only=False),
        ],
    ),
]


def _wait_until_usable(app: AppSpec, timeout: float) -> tuple:
    """Polls read_ui_tree until the element count stabilizes across two
    consecutive polls — NOT just until tree_is_usable flips True.

    Real finding, 2026-09-10: tree_is_usable alone is a poor readiness
    signal for an app still rendering. Media Player reported
    tree_is_usable=True from just 7 (chrome) elements seconds before its
    real home content (211 elements) finished loading — the same class of
    issue as Edge/Outlook's chrome-only tree (see CLAUDE.md), just
    transient here rather than permanent. Waiting for the count to settle
    catches this; waiting for the boolean alone does not."""
    deadline = time.time() + timeout
    last_count = -1
    stable_streak = 0
    while True:
        try:
            screen = read_ui_tree(app.window_title)
            count = len(screen.elements)
            usable = screen.tree_is_usable
        except Exception:
            count, usable = last_count, False
        if count == last_count and count > 0:
            stable_streak += 1
        else:
            stable_streak = 0
        last_count = count
        if usable and stable_streak >= 2:  # same count on 2 consecutive polls, ~0.6s apart
            return True, count
        if time.time() >= deadline:
            return usable, max(last_count, 0)
        time.sleep(0.3)


def run_task(app: AppSpec, task: Task) -> tuple:
    """Returns (passed: bool, detail: str)."""
    try:
        screen = read_ui_tree(app.window_title)
    except Exception as e:
        return False, f"read_ui_tree raised: {e}"

    if not task.action_only:
        return screen.tree_is_usable, f"tree_is_usable={screen.tree_is_usable}"

    if not screen.tree_is_usable:
        return False, "tree_is_usable=False, nothing to act on"

    target = next((e for e in screen.elements if e.name == task.control_name), None)
    if target is None:
        return False, f'"{task.control_name}" not found among {len(screen.elements)} elements'

    try:
        act_on(target, task.action)
    except AppNotRespondingError as e:
        return False, f"app not responding: {e}"
    except Exception as e:
        return False, f"act_on raised: {e}"

    return True, "ok"


def main():
    results = []
    for app in APPS:
        print(f"\n=== {app.key} ===")
        app.launch()
        ready, elements_seen = _wait_until_usable(app, timeout=app.settle_seconds)
        print(f"  (ready={ready}, {elements_seen} elements seen after waiting)")
        for task in app.tasks:
            passed, detail = run_task(app, task)
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {task.name} — {detail}")
            results.append((app.key, task.name, passed))

    print("\n=== summary ===")
    by_app = {}
    for app_key, _, passed in results:
        by_app.setdefault(app_key, []).append(passed)
    for app_key, outcomes in by_app.items():
        rate = sum(outcomes) / len(outcomes) * 100
        print(f"  {app_key}: {sum(outcomes)}/{len(outcomes)} ({rate:.0f}%)")
    total_passed = sum(1 for *_, p in results if p)
    print(f"  overall: {total_passed}/{len(results)} ({total_passed / len(results) * 100:.0f}%)")


if __name__ == "__main__":
    main()
