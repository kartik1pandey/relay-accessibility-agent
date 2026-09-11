# On-device accessibility agent — scaffold

A starting skeleton for the Snapdragon AI Lab Build & Present Challenge:
a voice-controlled, screen-reading accessibility agent that runs
entirely on-device.

## Repo layout

```
agent/    Python backend — guardrails, perception, models, the orchestration loop
web/      Vite + React UI — the two end-user/admin surfaces, previewable in a browser
CLAUDE.md, README.md    docs (repo root — not specific to either half)
```

Python files in `agent/` import each other by plain module name
(`from guardrails import ...`), which works whether you run them from
inside `agent/` or as `python agent/guardrails.py` from the repo root —
Python adds a script's own directory to `sys.path` either way. The `web/`
half is a self-contained Vite project; run its commands from inside
`web/` (or `npm --prefix web run dev` from the root).

## What's real here vs. what's a stub

- **`guardrails.py`** — fully implemented and tested (run it yourself:
  `python guardrails.py` from inside `agent/`). Pure Python pattern
  matching, no model or
  hardware dependency, so it's the one file that already works
  anywhere.
- **`perception.py`** — verified live on this machine (2026-09-10), not
  just plausible, against all three target apps:
  - **Notepad** (proxy for a simple app): 24 elements, a real scroll
    executed via `act_on`.
  - **Microsoft Edge**: 46 elements at depth 6, real click-through
    verified — but see below, this one comes with a real caveat.
  - **Media Player**: 211 elements, 113 named+enabled, real actionable
    content (Search, Open file(s), Recent media) — a real click
    executed via `act_on`. The cleanest result of the three, and the
    only one not built on Chromium (see below).
  - **Outlook**: needed a signed-in account to show a window at all
    (real demo-readiness prerequisite, not a code defect); once signed
    in, `tree_is_usable=True` but — see below — with the same caveat as
    Edge.

  Real, worth-knowing findings surfaced along the way, not guesses:
  - Edge's actual window title has an invisible zero-width space
    embedded in it ("Microsoft&#8203; Edge") that silently broke naive
    substring window matching — fixed with a hand-rolled window finder
    that strips it.
  - **Two of the three target apps share the same Chromium accessibility
    limitation.** Both Edge and Outlook show an identical "Chrome Legacy
    Window" pane in their trees, and both surface only window chrome —
    never real content (no page text in Edge, no inbox items in Outlook)
    — even walked 12-14 levels deep. Chromium/WebView2 only builds a
    complete accessibility tree for a detected AT client under
    conditions this scaffold hasn't confirmed it satisfies. Practical
    consequence: the vision-fallback path is likely doing the *majority*
    of real content-level work for two of three target apps, not the
    rare-case fallback originally assumed. See the module docstring and
    `CLAUDE.md`'s Open Questions.

  Still Windows-only by design; raises a clear error off-Windows.
- **`cdp_perception.py`** — the real, verified fix for Edge's half of the
  Chromium gap above (Outlook's remains open — it's a desktop app, not a
  browser tab CDP can attach to). Reads/acts on Edge's real DOM content
  via the Chrome DevTools Protocol instead of UI Automation. Verified
  against live pages (real headings/links/inputs read, a real value typed
  and confirmed by re-reading the live DOM, a real click by visible text),
  and **wired into `agent.py`'s actual `run_turn()`** — the orchestration
  loop branches to this module specifically when the active window is
  Edge. Demonstrated end to end through the real, unmodified
  `Agent.run_turn()`: a live Edge tab navigated to Wikipedia, a real
  `set_text` action typed into the real search box, confirmed by an
  independent re-read of the live page afterward. Requires Edge launched
  with `--remote-debugging-port=9222 --remote-allow-origins=*`.
- **`models.py`** — the LLM/VLM calls (`LocalReasoner`) are verified,
  not guessed: pulled the real `geniex` package (v0.6.1) from PyPI and
  read its actual source. The real API is a transformers-style
  `AutoModelForCausalLM` / `AutoModelForVision2Seq` with
  `.from_pretrained(name, device_map=...)` and `.generate(...)`. One
  thing that check surfaced: `geniex` refuses to build on generic Linux
  x86_64 — it's a thin wrapper around a native library Qualcomm only
  ships for Windows ARM64, Android, and Linux ARM64, so this only
  actually runs on target-class hardware, not a dev laptop's WSL. Also
  surfaced: GenieX exports no Whisper or TTS classes at all — those go
  through `qai_hub_models` instead, confirmed by reading its real source
  (github.com/qualcomm/ai-hub-models).

  **`SpeechToText` is now genuinely verified, not just shape-confirmed —
  actually run, three ways, on this machine (CPU): the qai_hub_models CLI
  demo, the direct encoder/decoder API, and this class's own
  `transcribe()` method fed real WAV bytes. All three correctly
  transcribed a known test clip
  ("...ask not what your country can do for you...").** ~5.9s wall-clock
  for an ~11s clip on CPU — a real number, not comparable to Snapdragon
  NPU latency. A real NVIDIA GPU is present and CUDA-capable on this dev
  machine, but unused here: `HfWhisperApp` hardcodes CPU internally, and
  forcing GPU would mean bypassing that — real surgery into a third-party
  library, and beside the point anyway since the actual target is
  Snapdragon NPU via GenieX, not this discrete GPU.

  **`TextToSpeech` (MeloTTS-EN) actually works now — real synthesis,
  real audio, played back through real speakers.** Five real blockers
  stood between "confirmed shape" and this working, all fixed: (1)
  `qai_hub_models`' `melotts-en` extra never lists `melo` itself despite
  hard-importing it; (2) the PyPI `melotts` package is broken, installed
  from GitHub source instead; (3) that hit a linker error that was really
  Git Bash's `link.exe` shadowing MSVC's — fixed via PowerShell, after
  installing VS Build Tools (no MSVC toolchain existed on this machine);
  (4) the pinned old `tokenizers` fails to compile against current
  Rust's `invalid_reference_casting` lint — fixed with
  `RUSTFLAGS="--cap-lints warn"`; (5) `fugashi` fails to compile (needs
  system MeCab) — installed real upstream MeCab and copied its files to
  `C:\mecab` by hand, matching fugashi's hardcoded expected path. Also
  needed: the user disabled this machine's Windows Application Control
  policy themselves (their call, on their own machine); an older
  `setuptools<81`; the `unidic` dictionary data; `pykakasi`; one more
  NLTK package. Runs isolated (`C:\Users\karti\.venvs\melo_isolated`) and
  talks to the main process over a small JSON-over-stdin/stdout bridge
  (`melo_worker.py`) — verified end to end with `TextToSpeech.speak()`
  producing real audio from the actual confirm/blocked-state strings
  `relay_ui.jsx` and `agent.py` use. See `models.py`'s `TextToSpeech`
  docstring for the complete, precise chain.
- **`agent.py`** — the orchestration loop. Platform glue is now real and
  verified on this machine: `_capture_screenshot` (via `mss`) captured a
  real 255KB PNG, `_record_short_clip`/`_play_audio` (via `sounddevice`)
  recorded from and played through real devices. Every guardrail
  decision is now also persisted to `guardrail_audit.jsonl` (append-only
  JSONL — timestamp, target control, tier, reason), not just printed.
  `Agent` now carries short-term memory (last 3 turns only) so a
  follow-up like "read the next one" can resolve, and `act_on` failures
  from a genuinely hung app get their own honest spoken message,
  distinct from "couldn't find it." What's still not runnable here: the
  GenieX-backed model calls themselves need Windows ARM64/Android/Linux
  ARM64 hardware.
- **`test_tasks.py`** and **`test_guardrails_adversarial.py`** — a fixed
  task list per app with real success-rate tracking (5/5, 100%, across
  Notepad/Edge/Media Player/Outlook), and 18 adversarial guardrail cases
  drawn from plausible-or-observed real controls in all three target
  apps. Both surfaced real findings, not just passed: the task harness
  found `tree_is_usable` alone is a poor readiness signal (Media Player
  reported "usable" from 7 early chrome elements, before its real
  211-element content rendered); the adversarial suite found and fixed a
  real gap in `guardrails.py` (`\bdelete\b` didn't match "deleted").

## The two UI surfaces

Per `CLAUDE.md`'s design brief, this product has two different visual
identities for two different audiences — neither shares a look with
`build_checklist.jsx` (a personal build-tracker, delivered separately):

- **`relay_ui.jsx`** — the end-user runtime UI. All seven states (idle/
  listening, transcribing, deciding, confirming, acting, blocked,
  error/not-found), WCAG AAA contrast, 18px+ body text, visible focus
  rings, `prefers-reduced-motion` respected. Confirming/blocked/error
  copy reuses the exact strings `agent.py`'s `Agent._say()` produces.
  Includes a demo dock (clearly separated from the product chrome) to
  step through every state, plus real `speechSynthesis` narration so the
  visual-and-spoken-channel-together principle is actually demonstrated,
  not just claimed.
- **`relay_admin_ui.jsx`** — the guardrail-admin surface. Calmer, more
  information-dense, a different palette and typeface from the runtime
  UI. Reads `guardrail_rules.json` (generated from `guardrails.py`'s
  real `CONFIRM_PATTERNS`/`BLOCK_PATTERNS` by
  `export_guardrail_rules.py` — never a hand-copied list that can
  drift) and includes a live rule-tester that reimplements
  `guardrails.check()`'s exact matching logic; verified against all 5 of
  `guardrails.py`'s own sanity cases.

## Design, in one paragraph

Every turn: transcribe the voice command, read the current window's UI
Automation tree as plain text, and only take a screenshot and call the
vision model if that tree doesn't have enough named, enabled controls
to work with. A small text-only model decides the action from the
transcript plus whichever screen context it got. Before anything
executes, `guardrails.py` checks the target control's name against a
confirm-list and a block-list — most actions run immediately, sensitive
ones need a spoken "yes," and a short block-list never runs at all.

## Setup

1. `cd agent && pip install -r requirements.txt` — use 64-bit x64 Python
   if you're on a Snapdragon X Elite/X2 Elite Windows machine; ARM64
   Python breaks `qai_hub_models`. (Confirmed on this dev machine: AMD64,
   64-bit — matches the requirement.) For the STT path specifically
   (`SpeechToText`, verified working — see below), install in a
   **dedicated virtual environment**, not your global Python:
   `qai_hub_models`' pinned torch/torchvision can silently replace an
   existing CUDA-enabled torch with a CPU-only build. Happened twice
   while building this — see `models.py`'s `SpeechToText` docstring.
2. Get onto target-class hardware (or Qualcomm's hosted device farm)
   before trusting the GenieX-backed model calls in `models.py` — see
   that file's module docstring for exactly what's confirmed vs. still
   placeholder.
3. Run `python guardrails.py` (from inside `agent/`) first — it needs no
   hardware and already passes its sanity checks.
4. `cd web && npm install && npm run dev` to preview `relay_ui.jsx` and
   `relay_admin_ui.jsx` in a real browser (tab switcher at
   `http://localhost:5173/`, alongside `build_checklist.jsx`).
5. Pick your three target apps in `agent.py`'s `TARGET_APPS`, and start
   testing `perception.py` against each one individually before wiring
   the full loop together.

## Try it now

```
cd agent
python guardrails.py
python models.py
cd ../web
npm install && npm run dev
```

All three run today, with no device and no model access, and all pass.

## Write-up skeleton — against the four judging criteria

Not a finished write-up — a scaffold so the real one starts from what's
actually true, not a blank page.

- **Technical implementation.** The full `agent.py` orchestration loop
  runs end to end against live hardware, with only `LocalReasoner`
  mocked out (the one piece that's structurally impossible without a
  Snapdragon NPU — needs GenieX): a real mic recording, real speech-to-
  text (Whisper via `qai_hub_models`), a real live UI Automation tree
  (Notepad), the real guardrail gate, a real `act_on` scroll against the
  live window, and real text-to-speech (MeloTTS-EN) spoken back through
  real speakers — all inside the actual, unmodified `run_turn()` method.
  Also verified separately: the guardrail engine (5/5 sanity cases),
  perception against all three target apps, a persisted audit log, and
  the GenieX reasoning API's real shape (confirmed from source, not yet
  runnable without Snapdragon/ARM64 hardware — the one honest gap left).
  State that gap plainly — it's more credible than claiming full NPU
  execution that hasn't touched real hardware.
- **Application use case & innovation.** The pitch: scoped, narrated,
  confirmation-gated assistive tech for limited hand mobility / low
  vision — not a general autonomous computer-use agent. The
  tree-first/vision-fallback architecture, and the two-tier guardrail
  system, are the concrete technical bets behind that pitch.
- **Deployment & accessibility.** On-device only, no cloud round-trip.
  WCAG AAA contrast, 18px+ text, 48px+ touch targets,
  `prefers-reduced-motion`, dual visual+spoken channel for every state —
  all in `relay_ui.jsx`, not just described here.
- **Presentation & documentation.** This README, `CLAUDE.md`, and the
  two previewable UI surfaces themselves. The honesty convention
  throughout — real vs. stub vs. blocked-on-hardware, stated plainly at
  every stage — is itself part of the pitch: judges can see exactly
  what's been verified and what hasn't, not a demo that overclaims.

## See also

`YOUR_TODO.md` in this same folder — what's actually left, in priority
order. Everything code-completable is done; this is exclusively the
account/hardware/recording/submission steps that are yours to drive.

`web/showcase.html` — a third visual surface, distinct from both product
UIs: a presentation-focused "verification ledger" page for judges,
structured as a numbered log of real findings rather than feature
cards. Serve it via the dev server (`npm run dev` in `web/`, then visit
`/showcase.html`) or open the file directly in a browser — it's fully
static. A published, shareable copy also exists as a Claude Artifact.

`WRITEUP.md` in this same folder — the full technical write-up, drafted
against the four judging criteria, drawing only on what's actually
verified elsewhere in this repo. Start there for the submission narrative;
this README is closer to a lab notebook.

`DEMO_SCRIPT.md` in this same folder — a scene-by-scene demo video script,
built entirely around footage this repo can actually produce today (the
real UI walkthrough, the real integration test, the real admin surface),
including a shot list and an explicit "what not to do" list so the one
honest gap (NPU execution) doesn't get edited around.

`CLAUDE.md` in this same folder — competition rules, the full
architecture rationale, and the design brief for the visual layer. Open
this folder in Claude Code and it's picked up automatically.

The project checklist (`build_checklist.jsx`, delivered alongside this)
tracks everything this scaffold doesn't cover — Qualcomm ID/account
setup, model benchmarking on real hardware, per-app testing, demo video,
and submission logistics.
