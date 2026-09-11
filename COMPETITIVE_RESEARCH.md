# Competitive research — four real accessibility agents, verified against source

Four repos surfaced as similar projects (voice + screen-reading + accessibility
+ on-device-leaning): `bedda-tech/deft`, `Debashich/Orbit`,
`NITISH-R-G/ScreenSaathi`, `Manoj7ar/Sally`. All four are confirmed real
(3–23 stars, all created within the last several months — small,
hackathon/personal-project scale, not established products). Findings below
came from actually reading their source via the GitHub API, not from the
secondhand AI-generated summary that prompted this research — that summary
turned out to have real inaccuracies (Sally is macOS-only and fully
cloud-dependent, not on-device; ScreenSaathi does execute actions, it doesn't
just guide; Orbit's "never touch the screen" is aspirational framing, not
literal). Treat this document as the verified version.

## The headline finding: Relay's guardrail system has no real counterpart

| Project | Safety mechanism | Enforcement |
|---|---|---|
| **Deft** | None found anywhere in either backing repo | N/A — fully autonomous, unconditional dispatch |
| **Orbit** | None — but structurally moot, it never takes actions at all | N/A |
| **ScreenSaathi** | `SafetyGuard.kt`, an `IRREVERSIBLE_HINTS` keyword list, downgrades a risky plan to guide-only | Code-level, deterministic |
| **Sally** | A natural-language instruction inside the Gemini prompt itself ("never mark send/submit/delete/... as safe") | **Model-enforced only — no code-level backstop at all** |
| **Relay** | Two-tier ALLOW/CONFIRM/BLOCK, pattern-matched against Name/ControlType/AutomationId, a spoken "yes" gate, a persisted audit log | Code-level, deterministic, pre-execution |

This is worth stating plainly and confidently in the write-up: of five
comparable projects, **Relay is the only one with a deterministic,
code-level safety gate that doesn't depend on an LLM correctly following an
instruction.** Sally's approach (a prompt asking the model nicely) is a real,
named example of exactly the failure mode Relay's architecture was designed
to avoid from the start.

## Concrete, verified findings per project

**Deft** (`bedda-tech/deft` + two backing repos) — a fully autonomous Android
agent, no safety gate anywhere, immediate unconditional action dispatch
(`ActionDispatcher.kt`). Real, adaptable technical choices: its
accessibility-tree-to-text format includes bounding-box coordinates and
state flags inline (`[Button] "OK" (clickable) [100,200-300,400]`), and it
matches elements by a stable composite ID (window + resource-name/hash), not
name alone. Its end-user UI is a single generic "Working..." overlay bubble —
no distinct visual states.

**Orbit** (`Debashich/Orbit`) — pure advisory perception for blind/low-vision
mobility (GPS/compass/camera → Gemma 4 → spoken guidance); it never taps,
swipes, or operates anything, so the total absence of a safety gate isn't a
gap, there's nothing to gate. Real, working wake-word tolerance list (23
misrecognition variants). Real fixed word-count caps per response type
(≤10/20/25 words) baked into its prompt protocol.

**ScreenSaathi** (`NITISH-R-G/ScreenSaathi`) — genuinely does execute actions
(click/type/launch), with a real `SafetyGuard` that downgrades (not blocks)
risky plans to guide-only, using an `IRREVERSIBLE_HINTS` list: pay, send,
submit, confirm, delete, remove, buy, order, book, transfer, call, checkout,
purchase, withdraw. A code comment documents the real incident that produced
this guard: their model once confidently tapped "Pay Now" on a banking
screen under a plain confidence-threshold approach, which they explicitly
concluded was insufficient. Its "acting" visual state is a cursor that
travels along a curved path to the target and blooms into a ring on arrival
— a deliberate design choice (a documented code comment explains a static
highlight "read as appearing, not guiding").

**Sally** (`Manoj7ar/Sally`) — macOS-only, cloud-only (Gemini + ElevenLabs),
push-to-talk. Its one real architectural strength: because it's an Electron
app that owns the browser via `webContents`, it reads real page content by
injecting a script directly into the DOM (`PageContext`: interactive
elements with role/label/coordinates, headings, landmarks) — sidestepping
the OS-accessibility-tree problem entirely for web content. Its safety
mechanism is prompt-only, with no code-level enforcement at all.

## What this changes for Relay — concrete actions

**Done immediately, low effort / real value:**
1. Widened `guardrails.py`'s `CONFIRM_PATTERNS` with real gaps ScreenSaathi's
   incident-driven list surfaced: `order`, `book`, `call`, `withdraw` (not
   previously covered).
2. Added an explicit spoken-response length constraint to
   `models.py`'s prompt (Orbit's ≤10/20/25-word pattern) — shorter TTS
   responses reduce both latency and cognitive load for the same target
   population.

**Worth doing next, moderate effort:**
3. Enrich `perception.py`'s tree-to-text serialization with bounding-box
   coordinates and enabled/focused state flags (Deft's format) — helps a
   reasoning model disambiguate duplicate-named controls, which Relay's
   current plain `ControlType: "Name"` format can't do.
4. A cursor-travel-then-bloom animation for `relay_ui.jsx`'s "acting" state,
   adapting ScreenSaathi's documented reasoning (travel reads as guidance;
   an instant highlight reads as a notification).

**The big one — done, not just proposed:**
5. **Built and verified `cdp_perception.py`**, adapting Sally's DOM-access
   insight to Edge's own Chrome DevTools Protocol (CDP): real page content
   read (623 elements from a live Wikipedia page, vs. 0 real content
   elements UI Automation found there), a real value typed into a real
   input and confirmed by re-reading the live DOM, a real click by visible
   text. Requires Edge launched with
   `--remote-debugging-port=9222 --remote-allow-origins=*` (the second
   flag is real and non-optional, discovered via an actual 403 error).
   One real bug found and fixed along the way: initial field-read
   priority checked a static `aria-label` before the live `value`, making
   a genuinely successful write invisible to a re-read. See `CLAUDE.md`'s
   Resolved section and `cdp_perception.py`'s module docstring for the
   full account. Outlook's equivalent gap remains open — it's a desktop
   app, not a browser tab CDP can attach to.
   **Since wired into `agent.py`'s real `run_turn()` itself** (branches
   on the active window being Edge, not just callable standalone) and
   demonstrated end to end against a live Wikipedia tab — see CLAUDE.md's
   Resolved section for the full run.

**Confirmed as a real, not just claimed, differentiator:** Relay's two-tier
deterministic guardrail engine and its 7-state accessible UI have no
meaningful counterpart in any of the four projects surveyed. State this with
confidence, backed by the citations above — it's now a researched claim, not
an assumption.
