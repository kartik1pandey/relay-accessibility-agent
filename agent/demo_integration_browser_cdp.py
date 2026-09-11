"""
demo_integration_browser_cdp.py — runs the real, unmodified Agent.run_turn()
end to end against a live Microsoft Edge tab, through the CDP path added to
run_turn() specifically for Edge (see agent.py and cdp_perception.py). Only
LocalReasoner is mocked — see demo_integration_notepad.py's docstring for
why that's the one honest gap.

What this proves that demo_integration_notepad.py doesn't: the *other*
branch of run_turn()'s `is_browser` split — real screen context read via
cdp_perception.read_dom() instead of perception.read_ui_tree(), and a real
action executed via cdp_perception.act_on_dom() instead of perception
.act_on(). Confirmed genuinely working, not just exception-free: after
run_turn() completes, this script independently re-reads the live DOM and
checks the search box's value actually changed — a completely separate
code path from the one that wrote it, so a silent no-op write can't hide
behind a clean exit.

Prerequisite: Edge must already be running with:
    --remote-debugging-port=9222 --remote-allow-origins=*
(the second flag is real and non-optional — recent Chromium rejects the
CDP websocket without it; see cdp_perception.py's module docstring). Any
real, already-open http(s) tab is fine — this script navigates it to
Wikipedia's real main page itself.

Run: python demo_integration_browser_cdp.py
"""

import time

from agent import Agent
from models import ActionDecision, SpeechToText, TextToSpeech
from cdp_perception import find_real_page, _cdp_send, read_dom
from silent_wav import silent_wav

SEARCH_VALUE = "Snapdragon"


class MockReasoner:
    """Stands in only for the GenieX/NPU-dependent decision step."""

    def decide(self, transcript, screen_context, history=None):
        print(f"--- reasoner saw {len(screen_context.splitlines())} lines of real screen context, e.g.:")
        for line in screen_context.splitlines()[:5]:
            print("   ", line)
        return ActionDecision(
            control_name="Search Wikipedia",
            control_type="input",
            action="set_text",
            value=SEARCH_VALUE,
            say=f"Typed {SEARCH_VALUE} into the search box.",
        )


def _navigate_to_wikipedia(timeout: float = 15.0) -> None:
    import websocket
    page = find_real_page("")
    if page is None:
        raise RuntimeError(
            "No live Edge tab found — launch Edge with "
            "--remote-debugging-port=9222 --remote-allow-origins=* first."
        )
    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=10)
    try:
        _cdp_send(ws, "Page.navigate", {"url": "https://en.wikipedia.org/wiki/Main_Page"})
    finally:
        ws.close()

    # Real finding from building this script: a brand-new Edge profile's own
    # first-run "Welcome to Edge" interstitial can still be settling when
    # Page.navigate fires, so a fixed sleep occasionally raced it — poll for
    # the real URL to actually reflect Wikipedia instead of guessing a delay.
    deadline = time.time() + timeout
    while time.time() < deadline:
        if find_real_page("wikipedia") is not None:
            return
        time.sleep(0.5)
    raise RuntimeError("Navigation to Wikipedia did not complete within timeout.")


def main() -> None:
    print("=== Navigating the live Edge tab to Wikipedia via real CDP Page.navigate ===")
    _navigate_to_wikipedia()

    agent = Agent.__new__(Agent)  # bypass __init__ — real LocalReasoner() needs GenieX
    agent.stt = SpeechToText()
    agent.tts = TextToSpeech()
    agent.reasoner = MockReasoner()
    agent.history = []

    print("=== Running real agent.run_turn() against the live Edge/Wikipedia tab ===")
    agent.run_turn(silent_wav(), "Microsoft Edge")
    print(f"=== run_turn() completed. agent.history now: {agent.history}")

    print("=== Independently re-reading the live DOM to confirm the write actually stuck ===")
    state = read_dom("wikipedia")
    match = next((e for e in state.elements if e.name == SEARCH_VALUE), None)
    if match is None:
        raise AssertionError(f"Re-read did not find an element named {SEARCH_VALUE!r} — write did not stick.")
    print(f"=== Confirmed: search box now reads {match.name!r} — a real write through a real re-read. ===")


if __name__ == "__main__":
    main()
