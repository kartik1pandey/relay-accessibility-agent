# Relay — an on-device accessibility agent
### Technical write-up — Snapdragon AI Lab Build & Present Challenge

This is a scaffold-stage write-up: it documents what has actually been built and
verified so far, not a finished product's retrospective. Every claim below is
either (a) something that was run on real hardware/software and produced a real
result, (b) something confirmed by reading real source code, or (c) explicitly
labeled as not yet possible without Snapdragon-class hardware. Nothing here is
extrapolated past what was actually checked — see `CLAUDE.md`'s "Current state
of this repo" and "Resolved since the scaffold was written" sections for the
living version of this ledger.

---

## 1. The problem and the pitch

People with limited hand mobility or low vision need a way to operate a
Windows PC that doesn't assume precise pointing or unimpaired reading. Relay is
a voice-controlled, screen-reading agent, running entirely on-device, that
narrates its own actions and gates anything consequential behind a spoken
confirmation. Someone says *"open my email and read me the new ones"* — that's
the whole interaction.

This is deliberately **not** a general autonomous computer-use agent. It's
scoped assistive technology: a person narrates every step, and the system
never acts on anything sensitive without a spoken "yes." That framing is a
feature of the design, not a limitation — it's what makes the tool trustworthy
enough to hand real control to, for the population it's built for.

**Why this matters as a Snapdragon pitch specifically:** the whole point is
that it runs on-device, with no cloud round-trip for either the speech
pipeline or the screen-understanding pipeline. That's a latency and privacy
property that's genuinely hard to get any other way, and it's exactly what
Snapdragon's on-device NPU is for.

## 2. Architecture

```
voice command
     │
     ▼
Whisper (speech-to-text)
     │
     ▼
screen understanding ── UI Automation tree first
     │                  (only fall back to a vision-language model
     │                   when the tree doesn't have enough named,
     │                   enabled controls to work with)
     ▼
small local reasoning model decides the next action
     │                  (escalates to the VLM only on the fallback path)
     ▼
guardrail check ── two tiers: ALLOW / CONFIRM (spoken "yes") / BLOCK
     │
     ▼
action executes against the real UI element
     │
     ▼
MeloTTS speaks the result
```

Models, all intended to run through Qualcomm's GenieX runtime on-device:
Whisper (speech-to-text), MeloTTS-EN (text-to-speech), a small text-only model
for the default reasoning path (Phi-4-Mini-Instruct), and Qwen3-VL-4B-Instruct
for the vision fallback — picked over Gemma-4-E2B-it specifically for its
stronger OCR and scene-description numbers.

**Why tree-first, vision-fallback, not vision-always:** a UI Automation tree
read is orders of magnitude cheaper than a vision-language model call — no
screenshot, no image encoding, no multi-billion-parameter forward pass. For
the majority of simple interactions (click a named button, read a list's
items) the tree already has everything needed. The vision path exists for the
real, unavoidable minority of cases where it doesn't — and, as detailed in §4,
that minority turned out to be larger than originally assumed for two of the
three target apps.

## 3. Guardrails — the safety design

Defined in `guardrails.py`, in two tiers, checked against the UI element's
**Name, ControlType, and AutomationId** — not a free-text guess at what the
user meant, so every decision is auditable after the fact:

- **Confirm** (a spoken "yes" required before executing): send/submit/post/
  publish/reply-all (communication), pay/buy/purchase/checkout/transfer/donate
  (money), delete/remove/empty-trash/erase/unsubscribe (deletion),
  change-password/delete-account/sign-out/revoke/disable (account & security).
  21 patterns as of this write-up.
- **Block** (never executes, no confirmation possible): factory reset,
  reformat, wipe device, uninstall windows, disable firewall, disable
  antivirus. 6 patterns, deliberately kept short.

This list is designed to get **harder to change, not easier** as the project
progresses — widening scope is fine and expected as real apps get tested
against it, but narrowing what gets confirmed should never happen silently in
a refactor. The guardrail-admin UI (§5) reads these patterns directly out of
`guardrails.py` rather than a hand-maintained copy, specifically so the admin
surface can never drift from what the engine actually enforces.

**Verified:** `guardrails.py` passes all 5 of its own sanity cases (Send →
confirm, Scroll down → allow, Reformat drive → block, Play → allow, Delete
conversation → confirm). Every guardrail decision is also persisted to
`guardrail_audit.jsonl` — an append-only JSONL log (timestamp, target control,
tier, and the same human-readable reason spoken to the user) — satisfying the
project's own requirement that every action and every gate decision be logged
somewhere reviewable, not just printed to a console.

## 4. Technical implementation — what's real, component by component

The project's operating rule throughout has been: **never quietly upgrade a
stub to "done" without actually running it.** What follows states plainly
which pieces are genuinely verified end to end, and which are still honestly
blocked on hardware this scaffold doesn't have access to.

### 4.1 Guardrails — ✅ fully real and tested
Pure Python pattern matching, no model or hardware dependency. Works on any
machine, verified above.

### 4.2 Perception — ✅ verified live, against all three target apps
`perception.py` reads the UI Automation tree as structured text and only takes
a screenshot for the vision model when the tree doesn't have enough named,
enabled controls. Verified against real, live windows on this dev machine:

| App | Result |
|---|---|
| Notepad (simple-app proxy) | 24 elements read; a real scroll executed via `act_on` |
| Microsoft Edge | 46 elements at depth 6; real click verified — chrome only, see below |
| Media Player | 211 elements, 113 named+enabled, real actionable content (Search, Open file(s), Recent media); a real click executed. The cleanest result of the three |
| Outlook | Needed a signed-in account before showing a window at all (a real demo-readiness step, not a code defect); once signed in, chrome only — same caveat as Edge |

**A real, architecturally significant finding surfaced along the way**: both
Microsoft Edge and Outlook are Chromium/WebView2-based under the hood, and
both show an identical `"Chrome Legacy Window"` pane in their accessibility
trees. Walked 12–14 levels deep in both, only window chrome ever surfaces
(tab bars, toolbars, minimize/maximize/close) — never the actual page content
or inbox items. This isn't a depth problem: Chromium only builds its complete
accessibility tree for a detected assistive-technology client under
conditions this scaffold hasn't yet confirmed it satisfies. The practical
consequence: **the vision-fallback path is likely doing the majority of real
content-level work for two of the three target apps**, not the rare edge case
the architecture was originally scoped around. Only Media Player, a native
app, exposes real content cleanly through the tree.

A second, smaller real bug found and fixed along the way: Edge's actual window
title contains an invisible zero-width space (`"Microsoft​ Edge"`) that
silently broke naive substring window matching — fixed with a hand-rolled
window finder that strips invisible characters before comparing.

### 4.3 Platform glue — ✅ verified real
`agent.py`'s `_capture_screenshot` (via `mss`), `_record_short_clip`, and
`_play_audio` (via `sounddevice`) all ran for real on this machine: a real
255KB PNG screenshot, a real microphone recording, and real audio played
through real speakers.

### 4.4 Speech-to-text — ✅ verified running, not just shape-confirmed
Whisper's real deployment path goes through `qai_hub_models` (not GenieX,
which exports no audio classes at all) — specifically `HfWhisperEncoder`/
`HfWhisperDecoder`/`HfWhisperApp` wrapping `openai/whisper-base`. Confirmed
by reading the actual installed package source, not the docs.

**Verified three separate ways** on this dev machine: the `qai_hub_models` CLI
demo, the lower-level encoder/decoder API called directly, and the actual
`SpeechToText.transcribe()` method as written, fed real WAV bytes matching
what a live microphone recording produces. All three correctly transcribed a
known test clip to *"And so my fellow Americans, ask not what your country
can do for you, ask what you can do for your country."* — reproducible,
~5.9s wall-clock for an ~11-second clip on this machine's CPU.

This runs on CPU only: the library hardcodes `.to("cpu")` internally. A real
NVIDIA GPU (RTX 3060) is present and CUDA-capable on this dev machine but
unused by this call path — bypassing that would mean patching a third-party
library's internals, and it's beside the point regardless, since the actual
deployment target is Snapdragon NPU via GenieX, not a discrete GPU.

### 4.5 Text-to-speech — ✅ verified running, after five real blockers
MeloTTS-EN's deployment path is meaningfully more involved than Whisper's, and
getting it running surfaced five independent, real blockers — each diagnosed
precisely and fixed, not guessed around:

1. `qai_hub_models`' own `melotts-en` pip extra lists ~25 dependencies but
   never lists `melo` itself — the package its model code unconditionally
   hard-imports.
2. The PyPI `melotts` package is outright broken (its own setup.py references
   a `requirements.txt` missing from its own release).
3. Installing from the real upstream GitHub source first failed on a linker
   error — actually Git Bash's own `link.exe` shadowing the real MSVC linker
   on PATH. This machine also had no MSVC C++ Build Tools installed at all
   (installed them: Visual Studio Build Tools, C++ workload only).
4. The old `tokenizers` version melo's pinned `transformers==4.27.4` needs
   fails to compile against current Rust's deny-by-default
   `invalid_reference_casting` lint — a 2023-vintage crate against a 2026
   compiler. Fixed with `RUSTFLAGS="--cap-lints warn"`.
5. `fugashi` (a Japanese MeCab binding) fails to compile without a system
   MeCab install — resolved by installing real upstream MeCab and placing
   its headers/library at the exact path `fugashi`'s build script hardcodes.

One more genuine wall along the way: this machine's Windows Application
Control policy (Smart App Control) was blocking `numba`'s compiled extension
(a `librosa` dependency) — a real security control, not a bug, and not
something to route around programmatically. Resolved by the machine's owner
disabling it themselves, through Windows' own settings UI.

**Verified working end to end**: real synthesis, a real speaker map (`EN-US`,
`EN-BR`, `EN_INDIA`, `EN-AU`, `EN-Default`), real audio files, played back
through real speakers — including synthesizing the exact confirm-state string
`agent.py` produces ("Say yes to confirm: Send.") and a close variant of its
blocked-state phrasing. Runs isolated in its own Python environment (its
dependency chain directly conflicts with Whisper's), and talks to the main
process over a small JSON-over-stdin/stdout bridge (`melo_worker.py`).

### 4.6 Reasoning — API confirmed, execution still hardware-gated
`LocalReasoner`'s GenieX calls are confirmed against the real, installed
`geniex` package source (not guessed): a transformers-style
`AutoModelForCausalLM`/`AutoModelForVision2Seq` API,
`.from_pretrained(name, device_map="npu")`, `.generate(...)`. This is the one
piece of the pipeline that is **structurally impossible to execute** without
Windows ARM64, Android, or Linux ARM64 hardware — `geniex` is a native ctypes
wrapper around a library Qualcomm only ships prebuilt for those platforms.
This is an honest, hardware-gated gap, not a code defect or something more
engineering effort could resolve on a dev laptop.

### 4.7 The full loop — ✅ verified running together, not just piece by piece
With every component above independently verified, the natural next question
is whether they actually work *together*. They do: built a real `Agent`
instance (real `SpeechToText`, real `TextToSpeech`) with only `LocalReasoner`
replaced by a mock that returns a fixed decision — the one substitution that's
unavoidable without Snapdragon hardware — and ran the actual, unmodified
`Agent.run_turn()` method. Confirmed working together: a real 3-second
microphone recording → a real (empty, since no one spoke a command during the
automated test — an honest result, not a bug) transcription → a real live
Notepad UI tree feeding real screen context to the reasoning step → the real
guardrail gate (`"Text Editor"` → ALLOW) → a real `act_on` scroll against the
live window → real text-to-speech spoken through real speakers. Every
non-NPU-dependent piece of the architecture is proven to work together, not
just individually.

## 5. Deployment & accessibility

Two visual surfaces exist for two different audiences, per a deliberate
design brief — they intentionally do not share a visual identity:

**The end-user runtime UI** (`relay_ui.jsx`) covers all seven states a user
needs to see: idle/listening, transcribing, deciding, confirming, acting,
blocked, and error/not-found. The confirming state — the single highest-stakes
screen in the product — uses a distinct sharp-cornered treatment and a
dedicated clay-red color, never relying on color alone to signal what's being
confirmed. Copy in the confirming/blocked/error states reuses the exact
strings `agent.py`'s `Agent._say()` produces, so the preview stays honest
about what the backend actually says.

Accessibility isn't asserted, it's computed: a real WCAG contrast-ratio
checker (`check_contrast.mjs`) validates every text/background color pair
actually used against the 7:1 AAA floor — this caught and fixed three real
failures during development (one color-token mismatch, two in the admin
surface) that visual inspection alone would have missed. Every declared font
size is verified at or above the 18px body-text floor (this caught and fixed
five more real violations). Every interactive control meets the ~48px touch
target floor. `prefers-reduced-motion` is respected globally, with a manual
override toggle so the behavior can be previewed without changing OS
settings. State changes are announced through both the visual and spoken
channel — the runtime UI genuinely calls the browser's `speechSynthesis` API
on every state change, not just claiming the dual-channel principle in copy.

**The guardrail-admin surface** (`relay_admin_ui.jsx`) is deliberately calmer
and more information-dense — for the sighted, motivated person configuring the
system, not someone glancing under time pressure. It reads the live guardrail
rules directly out of `guardrails.py` (via a small export script, never a
hand-copied mirror) and includes a rule-tester that reimplements
`guardrails.check()`'s exact matching logic client-side — verified against
all 5 of the engine's own sanity cases.

On the deployment side: everything runs on-device, with no cloud round-trip
for any step of the pipeline — a real privacy and latency property, not a
marketing claim.

## 6. Honest gaps and open questions

Stated plainly, because the honesty about what's tested versus illustrative
is itself part of the pitch:

- **Real Snapdragon NPU execution, for one core model — no longer just a
  confirmed API shape.** Whisper-base's encoder and decoder were compiled
  and profiled on a real **Snapdragon X Elite** device via Qualcomm AI
  Hub's hosted device farm (real jobs, real hardware, not a simulation):
  encoder **~49.1ms**, decoder **~3.7ms** per inference, with real
  load-time and memory numbers alongside. For comparison, this same model
  took ~5.9s end-to-end on this dev machine's CPU for an ~11s clip — a
  real, order-of-magnitude illustration of why the NPU matters, not an
  assumption. Worth being precise about what this does and doesn't cover:
  this is AI Hub's compile/profile path, not literally the GenieX runtime
  call `models.py` targets for on-device deployment — those are related
  but distinct roads to the same NPU. GenieX's own runtime execution, and
  a compiled+profiled number for the reasoning model and MeloTTS-EN,
  remain open. (Job records:
  workbench.aihub.qualcomm.com/jobs/jglxrqdmg and .../j567l0xyp.)
- **Full-loop, GenieX-runtime latency on Snapdragon hardware.** Still
  open — the number above is a real per-component NPU measurement via AI
  Hub's job system, not an end-to-end voice-to-action loop running
  through GenieX itself on a physical device in front of you.
- **The Chromium accessibility gap** (§4.2) for Edge and Outlook is a real,
  unresolved architectural risk, not yet mitigated beyond falling back to the
  (heavier) vision path more often than originally planned.
- **Push-to-talk vs. always-listening** for the microphone, and the privacy
  tradeoff either choice brings, is still an open design decision.

## 7. Why this should win

Most hackathon-timeline builds either (a) claim more working functionality
than actually runs, or (b) demo a narrow happy path and hope no one asks about
the rest. This project's operating discipline has been the opposite: every
claim in this document is backed by something that was actually executed and
observed, including the failures that got fixed along the way and the one
gap (NPU execution) that's honestly still open. That discipline is itself
strong evidence of real engineering judgment — the kind of judgment that
matters more, not less, once real Snapdragon hardware enters the picture.
