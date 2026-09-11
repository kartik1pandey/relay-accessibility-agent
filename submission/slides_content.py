"""
slides_content.py — single source of truth for the pitch deck, shared by
build_pptx.py (editable .pptx for Unstop's PPT upload) and
build_html_deck.py (rendered to PDF for Unstop's PDF upload). Every claim
here traces to CLAUDE.md / WRITEUP.md / COMPETITIVE_RESEARCH.md's verified
findings — nothing here is aspirational or unverified without being
labeled as such.
"""

TITLE = "Relay"
SUBTITLE = "An on-device, voice-controlled, screen-reading accessibility agent"
EVENT = "Snapdragon AI Lab Build & Present Challenge"

SLIDES = [
    {
        "kind": "title",
        "title": TITLE,
        "subtitle": SUBTITLE,
        "footer": EVENT,
    },
    {
        "kind": "content",
        "eyebrow": "THE PROBLEM",
        "title": "Point-and-click assumes hands and eyesight most people don't have",
        "bullets": [
            "People with limited hand mobility or low vision can't reliably operate a Windows PC through a mouse and a screen alone.",
            "Existing screen readers describe a screen; they don't act on it. Existing automation agents act, but weren't built for this population's safety needs.",
            "The gap: a voice-first agent that both understands the screen and acts on it — with a person narrating every step.",
        ],
    },
    {
        "kind": "content",
        "eyebrow": "THE PRODUCT",
        "title": '"Open my email and read me the new ones" — that’s the whole interaction',
        "bullets": [
            "Voice in, spoken result out. No pointing, no reading required.",
            "Deliberately not a general autonomous computer-use agent — scoped assistive technology.",
            "A person narrates every step, and nothing consequential happens without a spoken “yes.” That's a feature of the design, not a limitation.",
        ],
    },
    {
        "kind": "diagram",
        "eyebrow": "ARCHITECTURE",
        "title": "Screen understanding is tree-first, vision-second — not the other way around",
        "steps": [
            "Voice command",
            "Whisper (speech-to-text)",
            "Screen understanding — UI Automation tree first, vision model on fallback",
            "Small local reasoning model decides the next action",
            "Guardrail check — ALLOW / CONFIRM (spoken yes) / BLOCK",
            "Action executes against the real UI element",
            "MeloTTS speaks the result",
        ],
    },
    {
        "kind": "table",
        "eyebrow": "THE DIFFERENTIATOR — VERIFIED AGAINST FOUR REAL COMPARABLE PROJECTS",
        "title": "Relay is the only one with a deterministic, code-level safety gate",
        "columns": ["Project", "Safety mechanism", "Enforcement"],
        "rows": [
            ["Deft", "None found anywhere in either backing repo", "N/A — unconditional dispatch"],
            ["Orbit", "None — but never takes actions at all", "N/A"],
            ["ScreenSaathi", "Keyword list downgrades risky plans to guide-only", "Code-level, deterministic"],
            ["Sally", "A prompt instruction asking the model nicely", "Model-enforced only — no code backstop"],
            ["Relay", "Two-tier ALLOW / CONFIRM / BLOCK + spoken yes + audit log", "Code-level, deterministic, pre-execution"],
        ],
        "note": "Sourced from reading each project's real, public source code — not a secondhand summary. See COMPETITIVE_RESEARCH.md.",
    },
    {
        "kind": "content",
        "eyebrow": "VERIFIED, NOT CLAIMED",
        "title": "Every non-NPU piece of the pipeline has been run for real, on this machine",
        "bullets": [
            "Whisper speech-to-text: real transcription of a known test clip, 3 independent ways.",
            "MeloTTS-EN: real synthesis, real audio, played back through real speakers.",
            "The full agent.py orchestration loop: a real mic recording → real transcription → real UI Automation tree read → real guardrail gate → real action → real speech, proven end to end against a live window.",
            "Chromium accessibility gap (Edge/Outlook can't be read via UI Automation): found, verified, and fixed for Edge via Chrome DevTools Protocol — demonstrated live against a real Wikipedia page.",
            "The one honest gap: LocalReasoner itself needs Snapdragon's on-device NPU (GenieX), which this dev machine doesn't have.",
        ],
    },
    {
        "kind": "stats",
        "eyebrow": "REAL SNAPDRAGON HARDWARE — QUALCOMM AI HUB",
        "title": "Whisper-base, compiled and profiled on a real Snapdragon X Elite",
        "stats": [
            {"value": "~49.1 ms", "label": "encoder"},
            {"value": "~3.7 ms", "label": "decoder"},
        ],
        "note": (
            "A real compile + profile job on Qualcomm AI Hub's hosted device farm — "
            "not a simulation, and an order of magnitude faster than this laptop's CPU. "
            "Precisely scoped: this is AI Hub's compile/profile path, not yet a full "
            "GenieX runtime measurement, which needs physical device access."
        ),
    },
    {
        "kind": "content",
        "eyebrow": "TWO SURFACES, TWO AUDIENCES",
        "title": "The end user in the moment of use, and whoever configures the guardrails",
        "bullets": [
            "End-user runtime UI: 7 explicit states (listening, transcribing, deciding, confirming, acting, blocked, error) — WCAG AAA contrast (7:1), verified by computed contrast ratios, not eyeballed.",
            "The confirmation screen is the single highest-stakes moment in the product: distinct shape and color, never color alone, spoken aloud as well as shown.",
            "Guardrail-admin surface: reads guardrails.py's real CONFIRM/BLOCK patterns directly — can't drift out of sync with a hand-maintained copy.",
        ],
    },
    {
        "kind": "content",
        "eyebrow": "HONEST ROADMAP",
        "title": "What's real, what's next",
        "bullets": [
            "Open: Outlook's Chromium accessibility gap — same limitation as Edge, but it's a desktop app CDP can't attach to. Still unsolved, documented as such.",
            "Open: full GenieX-runtime, on-device latency for the reasoning model — needs physical Snapdragon hardware, not yet measured.",
            "Done: 18 adversarial guardrail tests across all 3 target apps, a fixed task-list harness (100% pass rate), and short-term reasoning memory (last 3 turns).",
            "This submission was built without physical Snapdragon hardware — every claim here is labeled by exactly how it was verified.",
        ],
    },
    {
        "kind": "closing",
        "title": "Thank you",
        "lines": [
            "github.com/kartik1pandey/relay-accessibility-agent",
            EVENT,
        ],
    },
]
