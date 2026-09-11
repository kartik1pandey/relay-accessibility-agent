# Snapdragon AI Lab — On-Device Accessibility Agent

Context for anyone — including Claude Code — picking up this project.
Read this before making changes: it's the shared understanding this
build is operating under, not just a description of the code.

## The competition

Qualcomm's Snapdragon AI Lab Build & Present Challenge, via Unstop.
Solo participation only. Submissions close Sep 30 2026, 11:59 PM IST,
and the intake form can't be edited after submitting. The solution has
to be designed or optimized for Snapdragon-powered HP PCs; reused prior
work would need significant modification plus an added Qualcomm AI Hub
(or other open-source) model — moot here, since this is a from-scratch
build. Judged on four things: technical implementation, application
use case & innovation, deployment & accessibility, and presentation &
documentation. Top prize includes a Snapdragon X2 Plus HP Omnibook
Ultra and a shot at a Qualcomm internship (eligibility: B.Tech/M.Tech
in CS or ECE, 7.5+ CGPA — that bar is cleared).

## The product

A voice-controlled, screen-reading agent for people with limited hand
mobility or low vision, running entirely on-device. Someone says
"open my email and read me the new ones" — that's the whole
interaction. This is not a general autonomous computer-use agent: it's
scoped assistive technology, with a person narrating every step and a
confirmation gate on anything consequential. Keep that framing intact
in anything built on top of this — it's a feature of the pitch, not a
limitation to design around.

## Architecture

Voice command → Whisper (speech-to-text) → screen understanding
(check the UI Automation tree first; only fall back to a vision model
when the tree doesn't have enough named, enabled controls to work
with) → a small local model decides the next action, escalating to
the vision-language model only on the fallback path → the guardrail
check → the action executes against the real UI element → MeloTTS
speaks the result.

Models, all served through GenieX: Whisper, MeloTTS-EN, a small
text-only model for the default reasoning path (Phi-4-Mini-Instruct is
the current pick), and Qwen3-VL-4B-Instruct for the vision fallback —
picked over Gemma-4-E2B-it specifically for its stronger OCR and
scene-description numbers.

## Current state of this repo

Repo is split `agent/` (Python backend) / `web/` (Vite + React UI) —
see README.md's "Repo layout" for the why and how imports/commands work
across the split.

- `guardrails.py` (in `agent/`) — real, tested. Run it (from inside
  `agent/`): `python guardrails.py`.
- `perception.py` — reflects the real shape of the `uiautomation` API,
  untested against a live device.
- `models.py` — `LocalReasoner`'s calls are now verified against the
  real `geniex` PyPI package (v0.6.1) source, not guessed:
  `AutoModelForCausalLM` / `AutoModelForVision2Seq`, transformers-style
  `.from_pretrained(name, device_map=...)`, `.generate(...)`. That check
  also found that `geniex` only builds on Windows ARM64, Android, or
  Linux ARM64 — it's a native-library wrapper, so this is a hardware
  requirement, not a credentials gap. It also found GenieX exports no
  Whisper/TTS classes at all; `SpeechToText`/`TextToSpeech` in
  `models.py` are still honest placeholders pending a look at
  `qai_hub_models`' own ONNX+QNN deployment path for those two.
- `agent.py` — the orchestration loop. Three helpers
  (`_capture_screenshot`, `_record_short_clip`, `_play_audio`) are
  intentionally left unimplemented rather than guessed at.

Don't quietly upgrade a stub to "done" without actually running it
against the target hardware — the honesty about what's tested versus
illustrative is load-bearing for the write-up, not just a formality.

## Target apps — don't expand without a reason

Mail (or Outlook), Microsoft Edge, and a media player — chosen because
they're three genuinely different interaction shapes (read-and-reply,
open-ended navigate-and-form-fill, simple transport controls), not
because they're the easiest three. A fourth app multiplies testing
effort for uncertain benefit; if one of the three turns out to have
unworkable UI Automation coverage, swap it out rather than adding a
fourth on top.

## Guardrail rules

Defined in `guardrails.py`, in two tiers:
- **Confirm** (spoken "yes" required): send/submit/post/publish,
  pay/buy/purchase/transfer/donate, delete/remove/erase, account or
  security changes (password, sign-out, revoke).
- **Block** (never executes): factory reset, reformat, disabling the
  firewall or antivirus.

This should get harder to change, not easier, as the build progresses.
Widening an action's scope or loosening a match pattern is fine —
explain why in the commit or PR, don't let a refactor silently narrow
what gets confirmed.

## Design brief — for whoever works on the visual layer

Approach this the way a senior product designer with real
accessibility experience would, not as a demo skin over a backend.
This product has two audiences that need two different things, and
they should not share one visual identity by default:

1. **The end user, in the moment of use.** Mostly voice, but not
   voice-only — low-vision users benefit from high-contrast, large
   visual confirmation alongside the spoken one, and anyone using this
   needs to *see* that the agent is listening, thinking, or about to
   act, not just trust that it is. Design for these states explicitly:
   idle/listening, transcribing, deciding, **confirming** (see below),
   acting, blocked, and error/not-found.

2. **Whoever sets it up or edits the guardrail rules.** A calmer,
   more information-dense surface is fine here — this person is
   sighted, motivated, and reading carefully, not glancing under time
   pressure.

The confirmation moment is the single highest-stakes screen in the
whole product — the one place a design mistake has real consequences,
not just an ugly one. It should be impossible to mistake for a routine
notification, unambiguous at a glance, and should never rely on color
alone to signal what's being confirmed.

Concrete floor, not a suggestion: WCAG AAA contrast (7:1) for text,
not just AA; nothing smaller than 18px for body text; visible focus
rings on everything; minimum ~48px touch targets; respect
prefers-reduced-motion; state changes get announced through both the
visual and the TTS channel, never just one.

Tone: calm, sober, trustworthy — closer to a screen reader's own
restrained chrome than a consumer app's marketing page. Avoid the
generic AI-generated-page tells if any of this is web-based: the
cream-background-plus-terracotta-accent look, near-black-with-one-
neon-accent, identical rounded SaaS cards, all-caps eyebrow labels, and
em-dash-joined template labels. Make deliberate, specific choices
instead of reaching for those defaults.

This is a different visual identity from `build_checklist.jsx`
(delivered separately) on purpose — that's a personal build-tracker
for the developer, this is an end-user-facing accessibility product.
Don't reskin one as the other.

## Open questions — not yet decided

- Push-to-talk vs. always-listening for the microphone, and the
  privacy tradeoff either way brings.
- Full-loop, GenieX-runtime latency on Snapdragon hardware — still not
  measured (that's the actual on-device deployment path). What IS now
  measured, for real, is below in Resolved: Whisper-base's encoder/decoder
  profiled on a real Snapdragon X Elite via AI Hub's compile/profile job
  system — a different, but real and directly relevant, road to the same
  NPU.
- **Outlook's Chromium accessibility limitation remains genuinely open.**
  It shows the identical "Chrome Legacy Window" pane Edge did, and surfaces
  only window chrome (Minimize/Maximize/Close), never real mail content —
  confirmed, not just suspected, walking 12 levels deep. Unlike Edge (see
  Resolved, below), Outlook is a desktop app, not a browser tab — CDP
  can't attach to it the same way, so this specific fix doesn't carry
  over. The vision-fallback path is still doing the real content-level
  work here.

## Resolved since the scaffold was written

- **Edge's Chromium accessibility limitation now has a real, verified
  fix — CDP-based DOM access, not just UI Automation.** Surfaced from
  competitive research (`COMPETITIVE_RESEARCH.md` — a similar project
  sidesteps this exact class of problem the same way). `cdp_perception.py`
  reads and acts on real Edge page content via the Chrome DevTools
  Protocol: verified against live pages — real headings/links/inputs read
  (623 elements from a live Wikipedia page, versus 0 real content elements
  UI Automation found there at 14 levels deep), a real value typed into a
  real input and confirmed by re-reading the live DOM afterward, and a
  real click dispatched by visible text. One real bug found and fixed
  during verification: the initial field-read priority checked a static
  `aria-label` before the live `value`, so a real, successful write was
  invisible to a re-read — fixed by checking `value` first for form
  fields specifically. Requires Edge launched with both
  `--remote-debugging-port=9222 --remote-allow-origins=*` (the second flag
  is real and non-optional — discovered via an actual 403 rejection).
  Media Player, a native app, was already the one target app that exposed
  real content cleanly via UI Automation — Edge now has its own real path
  too, via a different mechanism. Outlook's equivalent gap remains open
  (see Open Questions) — it's a desktop app, not a browser tab CDP can
  attach to.

- **CDP is now wired into `agent.py`'s real `run_turn()` orchestration —
  not just a standalone module.** `run_turn()` branches on
  `TARGET_APPS["browser"] in active_window_title`: the browser path calls
  `cdp_perception.read_dom()`/`act_on_dom()` instead of
  `perception.read_ui_tree()`/`act_on()`, with a new `except LookupError`
  alongside the existing `except AppNotRespondingError` so a DOM element
  that's disappeared gets the same honest "couldn't find it anymore"
  message as a vanished UI Automation element. Demonstrated end to end,
  for real: launched Edge with the required CDP flags, navigated a live
  tab to Wikipedia's real main page via `Page.navigate`, then ran the
  actual, unmodified `Agent.run_turn()` (same `Agent.__new__(Agent)` +
  `MockReasoner` pattern as the Notepad integration test below — only
  `LocalReasoner` mocked) with a `set_text` decision targeting the real
  "Search Wikipedia" input. Confirmed genuinely working, not just
  exception-free: the reasoner received real screen context read live
  from the DOM (60 elements, capped from what would otherwise run into
  the hundreds), the guardrail gate allowed it, the real write happened
  through `act_on_dom`, real TTS spoke the confirmation, and — the actual
  proof — a completely separate `read_dom()` re-read of the live page
  afterward found the input's value now genuinely reading "Snapdragon".
  Also re-ran the pre-existing Notepad/UI-Automation path after this
  change specifically to check for regressions from the new branching —
  none: same real scroll action, same real guardrail allow, no exception.
  Both integration demos are now real, permanent, rerunnable files —
  `agent/demo_integration_notepad.py` and
  `agent/demo_integration_browser_cdp.py` — not one-off scratch scripts.
  Building the browser one surfaced one more real bug, since fixed: a
  fixed `time.sleep(3)` after `Page.navigate` occasionally raced Edge's
  own first-run "Welcome to Edge" interstitial on a brand-new profile,
  reading stale interstitial content instead of the real destination
  page. Fixed by polling `find_real_page("wikipedia")` until the URL
  actually reflects the destination, with a real timeout — the same
  poll-don't-guess pattern `test_tasks.py` already established for
  `tree_is_usable`. Confirmed fixed via two clean back-to-back reruns
  against a fresh Edge profile, no flakiness.

- **Competitive research against four real, similar accessibility agents —
  see `COMPETITIVE_RESEARCH.md`.** Verified against actual source (not a
  secondhand summary, which had real inaccuracies once checked). Headline
  finding: of five comparable projects, Relay is the only one with a
  deterministic, code-level safety gate — one competitor's "safety
  mechanism" is a prompt instruction to its LLM with no code-level
  backstop at all. Two real, low-effort improvements already applied:
  `guardrails.py`'s `CONFIRM_PATTERNS` widened with `order`/`book`/`call`/
  `withdraw` (from a competitor's incident-driven list), and `models.py`'s
  prompt now caps spoken responses at 12 words (from another competitor's
  word-count-per-response-type pattern) — shorter TTS, less to hold in
  mind. One bigger, not-yet-attempted direction the research surfaced:
  a competitor sidesteps the Chromium accessibility-tree gap entirely by
  reading the DOM directly (via Electron's `webContents`) instead of
  waiting on OS accessibility APIs — Edge's own remote-debugging/CDP
  interface could offer Relay the same fix for its own documented
  Edge/Outlook limitation above. See `COMPETITIVE_RESEARCH.md` for the
  full, cited findings.
- **Real Snapdragon X Elite profiling data now exists — not just a
  confirmed API shape.** With a real Qualcomm AI Hub API token
  configured (`qai-hub configure`), submitted a real compile+link+profile
  job for Whisper-base against the real "Snapdragon X Elite CRD" device
  on AI Hub's hosted farm (`qai_hub_models.models.whisper_base.export
  --device "Snapdragon X Elite CRD"`). Real result: encoder ~49.1ms,
  decoder ~3.7ms per inference, measured on actual Snapdragon hardware —
  a real, order-of-magnitude faster number than this CPU's ~5.9s/11s-clip
  figure. Needed torch upgraded to `2.11.0+cu126` in the qualcomm312 venv
  first (the export's pt2 serialization needs `torch>=2.9`; the cu124
  index tops out at 2.6.0, so switched to the cu126 index). Job records:
  `workbench.aihub.qualcomm.com/jobs/jglxrqdmg` (encoder),
  `.../j567l0xyp` (decoder). Precise but important caveat: this is AI
  Hub's compile/profile path, a real and directly relevant road to the
  NPU, but distinct from literally running the GenieX runtime — that
  remains unmeasured. See `WRITEUP.md` §6 for the fuller framing.
- **The full agent.py orchestration loop runs end to end, for real,
  against live hardware — with only LocalReasoner mocked (the one piece
  that's structurally impossible without a Snapdragon NPU).** Built
  `Agent.__new__(Agent)` (bypassing `__init__`, since real `LocalReasoner()`
  fails without GenieX) with real `SpeechToText`, real `TextToSpeech`, and
  a `MockReasoner` standing in only for the actual decision-making call —
  then ran the real, unmodified `Agent.run_turn()`. Confirmed working
  together: a real 3-second mic recording → real (empty, since no one
  spoke a command — honest, not a bug) transcription → a real live
  Notepad UI tree feeding real screen context to the reasoner → the real
  guardrail gate (`"Text Editor"` → ALLOW) → a real `act_on` scroll
  against the live window → real TTS speaking the response through real
  speakers. Every non-NPU-dependent piece of the architecture is now
  proven to work together, not just individually.
- **MeloTTS-EN actually works — real synthesis, real audio, played back
  through real speakers.** Getting there took five independent real
  blockers, each found and fixed, in an isolated venv
  (`C:\Users\karti\.venvs\melo_isolated`, kept separate from the Whisper
  venv since their dependency chains conflict): (1) `qai_hub_models`'
  `melotts-en` extra never lists `melo` itself despite hard-importing it;
  (2) the PyPI `melotts` package is broken (missing files in its own
  sdist) — installed from upstream GitHub source instead; (3) that first
  failed on a linker error that was really Git Bash's `link.exe`
  shadowing MSVC's — fixed via PowerShell, after installing VS Build
  Tools (this machine had no MSVC toolchain at all); (4) the old
  `tokenizers` version melo needs fails to compile against current
  Rust's deny-by-default `invalid_reference_casting` lint — fixed with
  `RUSTFLAGS="--cap-lints warn"`; (5) `fugashi` failed to compile (needs
  a system MeCab this machine didn't have) — installed real upstream
  MeCab and copied its files to `C:\mecab` by hand, matching fugashi's
  hardcoded expected path. Also needed: the user disabled this machine's
  Windows Application Control policy (Smart App Control) themselves,
  which had been blocking `numba`'s compiled extension; an older
  `setuptools<81` (recent versions dropped `pkg_resources`); the
  `unidic` dictionary data (~526MB download); `pykakasi`; and one more
  NLTK data package. End-to-end verified: `TextToSpeech` (in `models.py`)
  spawns an isolated-venv worker process (`melo_worker.py`, JSON over
  stdin/stdout) and produces real audio bytes from real text — tested
  with the actual confirm-state and blocked-state strings from
  `relay_ui.jsx`/`agent.py`, both played back through real speakers. See
  `models.py`'s `TextToSpeech` docstring for the complete, precise chain.
- **Four more `build_checklist.jsx` items done, each verified by actually
  running it:**
  - Reasoning layer gets short-term memory: `models.py`'s
    `LocalReasoner.decide()` now accepts `history` (a capped list of
    `TurnMemory` — last 3 turns only, deliberately not a full session
    transcript) so a follow-up like "read the next one" can resolve
    against what just happened. `Agent` (`agent.py`) maintains and caps
    this history, only recording a turn after it actually completes (a
    blocked/cancelled/failed turn isn't remembered). The prompt-building
    logic is pulled into a standalone `_build_prompt()` specifically so
    it's testable without GenieX/NPU hardware — 3 real tests in
    `models.py`'s `__main__` confirm empty history adds nothing, present
    history appears verbatim, and history past 3 turns is genuinely
    dropped, not silently kept.
  - `perception.py`'s `act_on` now detects a genuinely hung app: the
    actual action dispatch runs on a worker thread with a 5s timeout
    (`ACTION_TIMEOUT_SECONDS`), raising a new `AppNotRespondingError`
    distinct from `LookupError` (element gone) — `agent.py` gives the
    user an honest, different spoken message for each. Verified two ways:
    a synthetic hanging call genuinely times out at 5s, and real actions
    against a live Notepad window still work correctly after the
    thread-wrapping refactor (no regression).
  - A fixed task list per app with real success-rate tracking now exists
    (`agent/test_tasks.py`) — run for real against all four apps
    (Notepad as a simple-app proxy, plus the three real targets),
    5/5 (100%) passing. Getting to 100% surfaced a second real,
    valuable finding beyond the Edge/Outlook one: `tree_is_usable`
    is a poor readiness signal on its own — Media Player reported
    "usable" from just 7 early-loading chrome elements, seconds before
    its real 211-element home content finished rendering. The harness
    now waits for the element count to stabilize across two polls, not
    just for the boolean to flip true. Outlook's launch-to-window timing
    was also observed to be genuinely inconsistent (sometimes ready in
    ~5s, sometimes past 10s) — recorded honestly as a real timing
    characteristic, not smoothed over.
  - The confirmation gate was deliberately adversarially tested against
    plausible real controls from all three target apps
    (`agent/test_guardrails_adversarial.py`, 18 cases) — and this found
    a genuine gap: `\bdelete\b`'s word boundary does not match inside
    "deleted" (past tense is a different word, grammatically), so a
    plausible real Outlook control like "Empty deleted items folder"
    silently fell through to ALLOW. Fixed in `guardrails.py` by widening
    `delete`/`remove`/`erase` to `\bdelet\w*\b`/`\bremov\w*\b`/
    `\beras\w*\b` (catches -ed/-ing/-ion forms too) — a widening, not a
    narrowing, consistent with this file's own rule that these patterns
    should get harder to change, not easier. `export_guardrail_rules.py`'s
    `humanize()` was updated to display these cleanly ("delet*", not the
    raw `\w*` escape) so the admin UI stays readable.
- **Whisper speech-to-text actually works, verified end to end, not just
  shape-confirmed.** `models.py`'s `SpeechToText` is now a real, running
  implementation (`qai_hub_models`' `HfWhisperEncoder`/`HfWhisperDecoder`/
  `HfWhisperApp`, `openai/whisper-base`), executed three separate ways on
  this dev machine (CLI demo, direct API, and the actual WAV-bytes-in
  `transcribe()` method as written) — all three produced the correct
  transcription of a known test clip. This runs on CPU only (the library
  hardcodes `.to("cpu")`); a real NVIDIA GPU is present and CUDA-capable
  on this dev machine but unused by this call path — irrelevant either
  way to the real target, which is Snapdragon NPU via GenieX, not this
  discrete GPU. MeloTTS-EN (text-to-speech) is confirmed-from-source only,
  not run — meaningfully heavier (a 4-component pipeline plus a separate
  `melo` package and dictionary download); see `models.py`.
- On this machine, the "Mail" target app is really **Outlook** — the
  classic Mail app has been superseded by the new unified Outlook for
  Windows, whose process (`olk.exe`) reports a window titled "Outlook",
  not "Mail". `agent.py`'s `TARGET_APPS` now reflects that. This was
  already anticipated above ("Mail (or Outlook)") — just confirmed which
  one is actually installed here.
- Media Player verified cleanly against a live window: real content
  (Search, Open file(s), Recent media), not just chrome — `act_on`
  clicked a real control successfully. The strongest of the three target
  apps so far, perception-wise, and the only one of the three that isn't
  Chromium/WebView2-based under the hood (see Open Questions).
- Outlook now signed in and verified: real window, `tree_is_usable=True`
  — but see Open Questions for the real caveat (chrome-only, same as
  Edge).
- GenieX's real Python SDK API is confirmed (not a placeholder anymore):
  transformers-style `AutoModelForCausalLM`/`AutoModelForVision2Seq`,
  `.from_pretrained(name, device_map="npu")`, `.generate(...)` — see
  `models.py`. Still can't be *run* here (needs Windows ARM64/Android/
  Linux ARM64). Both Whisper's and MeloTTS-EN's `qai_hub_models`/upstream
  paths are now verified above.
- A first draft of the confirmation UI (and the other six states) exists:
  `relay_ui.jsx` (in `web/`), previewed via the Vite dev server (`npm run
  dev` from inside `web/`).