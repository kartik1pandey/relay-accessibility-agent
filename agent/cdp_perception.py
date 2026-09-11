"""
cdp_perception.py — reads and acts on real Chromium DOM content via the
Chrome DevTools Protocol (CDP), for Microsoft Edge specifically.

Why this exists: perception.py's UI Automation tree read genuinely cannot
see Edge's real page content — verified 2026-09-10 (walked 14 levels deep,
285 elements, all chrome, zero page content; see perception.py's module
docstring). This surfaced from competitive research
(COMPETITIVE_RESEARCH.md) — a similar project (Sally) sidesteps the exact
same problem for its own browser automation by reading the DOM directly
instead of an OS accessibility API. CDP is Edge's own equivalent
direct-DOM-access path, and it's built into Edge already — no extra
install needed on the target machine, just a launch flag.

Verified working end to end 2026-09-10, against real live pages (a static
page and a real Wikipedia page): real page content read (headings, links,
a real search input), a real value typed into a real input field and
confirmed by re-reading the live DOM afterward, and a real click dispatched
against a real element found by its visible text.

Requires Edge launched with both:
  --remote-debugging-port=9222 --remote-allow-origins=*
The second flag is a real, non-optional requirement discovered directly by
hitting a 403 error: recent Chromium versions reject CDP websocket
connections without it.

This is a genuinely separate path from perception.py's UI Automation
approach, not a drop-in replacement for it — Notepad/Media Player/Outlook's
own window chrome still need UI Automation (and Outlook's real content is
its own separate, still-open question — see CLAUDE.md). This module is
specifically for reading/acting on a Chromium browser's actual page
content, returning the same ScreenState/ScreenElement shape perception.py
uses so agent.py's existing matching logic works unchanged either way.
"""

import json

try:
    import requests
    import websocket  # the `websocket-client` package
except ImportError:
    requests = None
    websocket = None

from perception import ScreenElement, ScreenState

CDP_HOST = "http://localhost:9222"

# Real content-bearing tags this reads — mirrors what a screen reader
# would actually surface as meaningful/actionable, not every DOM node.
_CONTENT_SELECTOR = "h1, h2, h3, a, button, input, textarea, select, p"


def _require_cdp_deps() -> None:
    if requests is None or websocket is None:
        raise RuntimeError(
            "cdp_perception needs `requests` and `websocket-client` "
            "(pip install requests websocket-client)."
        )


def find_real_page(url_substring: str = "") -> dict | None:
    """Finds the first real, user-facing tab (skips edge://, chrome-
    extension://, and other internal pages) whose URL contains
    url_substring. Requires Edge to have been launched with
    --remote-debugging-port=9222 --remote-allow-origins=*."""
    _require_cdp_deps()
    resp = requests.get(f"{CDP_HOST}/json", timeout=5)
    for target in resp.json():
        if (
            target["type"] == "page"
            and target["url"].startswith("http")
            and url_substring in target["url"]
        ):
            return target
    return None


def _cdp_send(ws, method: str, params: dict = None, msg_id: int = 1) -> dict:
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        response = json.loads(ws.recv())
        if response.get("id") == msg_id:
            return response


MAX_ELEMENTS = 60  # a real, live page can return 600+ raw matches (Wikipedia's
# main page did) — far more than a reasoning-model prompt should carry.
# Filtered to on-screen (offsetParent !== null, i.e. not display:none/detached)
# elements first, then capped, rather than an arbitrary slice of the raw list.


def read_dom(url_substring: str = "", max_elements: int = MAX_ELEMENTS) -> ScreenState:
    """Reads real page content from a live Edge tab via CDP — the actual
    fix for perception.py's documented Edge content gap, not a
    UI-Automation-tree read. Returns the same ScreenState/ScreenElement
    shape perception.py uses, so agent.py's existing matching logic
    (`e.name == decision.control_name`) works unchanged."""
    _require_cdp_deps()
    page = find_real_page(url_substring)
    if page is None:
        return ScreenState(window_title=url_substring, elements=[], tree_is_usable=False)

    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=10)
    try:
        # Real bug found and fixed 2026-09-10: for a form field (input/
        # textarea), `el.value` (the live, current content) must be
        # checked BEFORE aria-label/placeholder (a static, unchanging
        # identifier) — the original priority order meant a real typed
        # value was silently invisible to a re-read whenever the field
        # also had an aria-label, even though the underlying act_on_dom()
        # write had genuinely succeeded. Verified via a direct
        # `input.value` check that the write worked; the read just wasn't
        # looking in the right place.
        js = f"""
        (() => {{
            const out = [];
            document.querySelectorAll('{_CONTENT_SELECTOR}').forEach(el => {{
                if (out.length >= {max_elements}) return;
                if (el.offsetParent === null) return;  // skip hidden/detached elements
                const isField = el.tagName === 'INPUT' || el.tagName === 'TEXTAREA';
                const text = (
                    isField
                        ? (el.value || el.getAttribute('aria-label') || el.placeholder || '')
                        : (el.innerText || el.getAttribute('aria-label') || el.value || el.placeholder || '')
                ).trim().slice(0, 120);
                if (!text) return;
                out.push({{
                    tag: el.tagName.toLowerCase(),
                    text: text,
                    disabled: !!el.disabled,
                }});
            }});
            return JSON.stringify(out);
        }})()
        """
        resp = _cdp_send(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
        raw = resp["result"]["result"]["value"]
    finally:
        ws.close()

    elements = [
        ScreenElement(
            name=item["text"],
            control_type=item["tag"],
            is_enabled=not item["disabled"],
        )
        for item in json.loads(raw)
    ]
    named_enabled = [e for e in elements if e.name and e.is_enabled]
    return ScreenState(
        window_title=page["title"],
        elements=elements,
        tree_is_usable=len(named_enabled) > 0,
    )


def act_on_dom(url_substring: str, element_name: str, action: str, value: str = "") -> None:
    """Executes a real action against a real DOM element found by its
    visible text/label — the CDP equivalent of perception.py's act_on."""
    _require_cdp_deps()
    page = find_real_page(url_substring)
    if page is None:
        raise LookupError(f"No live Edge tab matching {url_substring!r}")

    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=10)
    try:
        escaped_name = json.dumps(element_name)
        escaped_value = json.dumps(value)
        if action == "click":
            js = f"""
            (() => {{
                const els = [...document.querySelectorAll('a, button, input, [role="button"]')];
                const target = els.find(el => (el.innerText || el.value || '').trim() === {escaped_name});
                if (!target) return "NOT_FOUND";
                target.click();
                return "CLICKED";
            }})()
            """
        elif action == "set_text":
            js = f"""
            (() => {{
                const els = [...document.querySelectorAll('input, textarea')];
                const target = els.find(el => (el.placeholder || el.getAttribute('aria-label') || '').trim() === {escaped_name});
                if (!target) return "NOT_FOUND";
                target.focus();
                target.value = {escaped_value};
                target.dispatchEvent(new Event('input', {{bubbles: true}}));
                return "SET";
            }})()
            """
        else:
            raise ValueError(f"Unhandled action type for CDP: {action!r}")

        resp = _cdp_send(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
        result = resp["result"]["result"]["value"]
        if result == "NOT_FOUND":
            raise LookupError(f"{element_name!r} not found in the live DOM")
    finally:
        ws.close()
