# Demo video script — Relay

Target runtime: ~3:15–3:45. Every shot below is something that can actually be
screen-recorded on this repo *today* — nothing here requires footage that
doesn't exist yet. Where the real Snapdragon NPU isn't available, the script
says so on-screen and in the voiceover, rather than implying it's there. That
honesty is itself part of the pitch (see `WRITEUP.md` §7) — lean into it,
don't hide it.

Legend: **[VISUAL]** what's on screen · **[VO]** voiceover line ·
**[NOTE]** what's actually real vs. what's being said out loud as context.

---

## Scene 1 — Cold open (0:00–0:15)

**[VISUAL]** Black screen, then `relay_ui.jsx`'s Listening state fades in
(mic icon, "Listening", teal palette). No demo dock visible yet — crop it out
or scroll it off-screen for this shot.

**[VO]** *"Say what you'd like me to do."* — *(this line is Relay's own,
spoken by the real browser `speechSynthesis` call already wired into the UI —
just let it play, don't re-record a voice actor for this one line)*

**[VO, human]** "For someone with limited hand mobility, or low vision, that's
the whole interaction with their computer."

**[NOTE]** 100% real: this is the actual running `relay_ui.jsx`, not a mockup.

---

## Scene 2 — The problem, fast (0:15–0:35)

**[VISUAL]** Cut to a simple title card or the README's problem framing as
on-screen text: *"Not a general computer-use agent. Scoped assistive
technology — a person narrates every step, and nothing consequential happens
without a spoken yes."*

**[VO]** "This is Relay — a voice-controlled, screen-reading agent that runs
entirely on-device. It's built for one thing: giving someone who can't
reliably point-and-click, or can't reliably read a screen, real control over
their PC — without handing that control to a black box."

**[NOTE]** Framing only, no footage dependency.

---

## Scene 3 — Architecture, in one breath (0:35–0:55)

**[VISUAL]** The architecture diagram from `WRITEUP.md` §2 (voice → Whisper →
screen understanding → reasoning → guardrail → action → MeloTTS), animated or
just held on screen while narrated.

**[VO]** "Voice comes in through Whisper. The screen gets read as structured
data first — the accessibility tree — and only falls back to a vision model
when that tree doesn't have enough to work with. A small local model decides
the next step. Every decision passes through a guardrail before anything
executes. And the result gets spoken back through MeloTTS."

**[NOTE]** Diagram only — no footage dependency.

---

## Scene 4 — The walkthrough (0:55–1:40)

**[VISUAL]** Screen-record `relay_ui.jsx` running in the browser (`npm run
dev` in `web/`), clicking **"Play the 'send an email' walkthrough."** Let it
run for real: Listening → Transcribing → Deciding → **Confirming** → Acting,
with the real `speechSynthesis` narration playing at each step. Hold on the
Confirming state for a beat — call out its distinct sharp-cornered, clay-red
treatment on screen (a text callout: *"Never relies on color alone"*).

**[VO]** "Here's the state machine end users actually see, live. Watch the
confirm screen specifically — it's the single highest-stakes moment in the
product, so it's built to be impossible to mistake for a routine
notification: different shape, different color, and it's spoken out loud, not
just shown."

**[NOTE]** 100% real — this is the actual `relay_ui.jsx` walkthrough feature,
not staged footage. Every state transition and every spoken line here is the
genuine app running.

---

## Scene 5 — It's not just a mockup: the real pipeline (1:40–2:10)

**[VISUAL]** Cut to a terminal, inside `agent/`. Run:
```
python demo_integration_notepad.py
```
against a live, already-open Notepad window. Let the terminal output scroll
naturally — it prints the real screen context lines the reasoner saw, the
real guardrail decision, and the final recorded turn. Overlay small text
labels next to the key printed lines: "real mic," "real transcription," "real
UI tree," "real guardrail decision," "real action," "real speech."

**[VO]** "Every piece of that state machine is backed by something that
actually runs — not just illustrated. This is a real microphone-shaped
recording, transcribed by a real Whisper model, checked against a live
window's real accessibility tree, gated by the real guardrail engine, and
spoken back through a real text-to-speech model — all on this laptop, right
now."

**[VO, continued — the one honest caveat]** "The one piece simulated here is
the decision-making step itself — the small reasoning model that picks the
action. That one genuinely needs Snapdragon's on-device NPU to run, which
this dev machine doesn't have. Everything else you just watched is real."

**[NOTE]** This is the load-bearing honesty moment (see `WRITEUP.md` §7) —
say it plainly, don't rush past it or bury it in small text. It's a strength,
not an apology: most demos at this stage either fake the whole loop or don't
show it at all. `demo_integration_notepad.py` is a real, checked-in,
rerunnable file — not a one-off scratch script — so this is reproducible on
camera, not just described.

---

## Scene 6 — The browser gap, closed (2:10–2:45)

**[VISUAL]** Two-part shot.
1. Briefly show `perception.py`'s real finding on screen as text: walking
   Edge's UI Automation tree 14 levels deep surfaces window chrome —
   never real page content. A quick, honest "this didn't work" beat, not
   glossed over.
2. Cut to a terminal. With Edge already running
   (`--remote-debugging-port=9222 --remote-allow-origins=*`) on a real page,
   run:
   ```
   python demo_integration_browser_cdp.py
   ```
   Split-screen or picture-in-picture the live Edge window next to the
   terminal so the viewer watches the real search box actually fill in with
   "Snapdragon" as the script runs — then the terminal's final line confirms
   it via an independent re-read of the live page.

**[VO]** "Two of this agent's three target apps — Edge and Outlook — turned
out to be built on Chromium, and Chromium simply doesn't expose real page
content through Windows' accessibility tree the way a native app does. That's
not a bug in this code, it's a real limitation this project found and
verified directly, not assumed. For Edge specifically, there's now a real
fix: reading and acting on the page through the same Chrome DevTools Protocol
browser engineers use to debug it. Watch — the agent finds the real search
box on a real Wikipedia page, types into it, and then, in a completely
separate step, reads the live page back to prove the write actually landed —
not just that the code didn't crash."

**[NOTE]** 100% real, and this is the differentiator scene — see
`COMPETITIVE_RESEARCH.md`: this exact class of fix is what one comparable
project uses to solve the same problem for its own browser support, and
building it here was directly informed by that research, cited honestly
rather than copied silently. `demo_integration_browser_cdp.py` is the real,
checked-in script — building it also surfaced and fixed a real timing race
(a fixed sleep occasionally raced Edge's own first-run interstitial); see
`CLAUDE.md`'s Resolved section if asked about it.

---

## Scene 7 — Three different apps, one agent (2:45–3:00)

**[VISUAL]** Quick triptych, ~5s each, using the real numbers from
`CLAUDE.md`'s Resolved section:
1. Media Player — 211 elements, 113 named+enabled, real actionable content
   (Search, Open file(s), Recent media) — the cleanest of the three, and the
   only one not built on Chromium.
2. Edge — now solved via CDP (Scene 6).
3. Outlook — same Chromium limitation as Edge, confirmed at 12 levels deep,
   still genuinely open (it's a desktop app, not a browser tab CDP can attach
   to) — say this plainly rather than skip it.

**[VO]** "Three genuinely different interaction shapes — read-and-reply,
open-ended navigation, and simple transport controls — not the easiest three
to fake, the three that actually stress different parts of the
architecture. Two of three now have a real, working content path. The third
— Outlook — is an honestly open problem, and it's written down as one."

**[NOTE]** Real data from the session's actual perception.py and
cdp_perception.py runs — don't fabricate polished B-roll to cover the
Outlook gap; saying it's open is more credible than hiding it.

---

## Scene 8 — Real numbers from real Snapdragon hardware (3:00–3:20)

**[VISUAL]** A simple on-screen card: "Whisper-base, compiled and profiled on
a real Snapdragon X Elite CRD via Qualcomm AI Hub's hosted device farm —
encoder ~49.1ms, decoder ~3.7ms per inference," with the two real AI Hub job
links shown small underneath
(`workbench.aihub.qualcomm.com/jobs/jglxrqdmg`, `.../j567l0xyp`).

**[VO]** "This dev machine doesn't have Snapdragon hardware — but Qualcomm AI
Hub does, and it's real. Whisper-base was actually compiled and profiled
against a real Snapdragon X Elite over AI Hub's hosted device farm: about
49 milliseconds for the encoder, under 4 for the decoder, on real silicon —
an order of magnitude faster than the same model on this laptop's CPU. It's
worth being precise about what this is and isn't: it's a real compile-and-
profile run on the actual target hardware, not a simulation — but it's not
the same as running the full GenieX runtime end to end, which still needs
physical device access this build doesn't have yet."

**[NOTE]** Say the caveat plainly, same as Scene 5's — precision here is a
credibility asset, not a hedge to rush past.

---

## Scene 9 — The other audience: the admin surface (3:20–3:35)

**[VISUAL]** Quick cut to `relay_admin_ui.jsx` — scroll through the
guardrail rule list, then use the live "try a control" tester (type "Delete"
→ show it resolve to CONFIRM in real time).

**[VO]** "There's a second surface, for whoever configures this — calmer,
denser, and it reads the actual guardrail rules from the code, not a
hand-maintained copy that can drift out of sync."

**[NOTE]** 100% real, live interaction — not a static screenshot.

---

## Scene 10 — Close (3:35–3:45)

**[VISUAL]** Return to the Listening state, held for a beat. Fade to a simple
end card: project name, "Snapdragon AI Lab Build & Present Challenge," repo
link.

**[VO]** "Built from scratch, verified at every stage we could verify it —
and honest about the one stage we couldn't. Thanks for watching."

---

## Shot list / recording checklist

- [ ] `web/`: `npm run dev`, record the full auto-play walkthrough (Scene 4)
- [ ] Open Notepad, then from inside `agent/`: `python
      demo_integration_notepad.py` (Scene 5) — rerun it fresh right before
      recording so the printed transcript/history line is current, not stale
      copy-paste
- [ ] Launch Edge with `--remote-debugging-port=9222
      --remote-allow-origins=* --no-first-run` pointed at any real http(s)
      page, then from inside `agent/`: `python
      demo_integration_browser_cdp.py` (Scene 6) — screen-record the live
      Edge window alongside the terminal so the search box fill-in is
      visible, not just the terminal text
- [ ] Terminal or simple visualization of the three `perception.py`/
      `cdp_perception.py` numbers (Scene 7) — reuse the actual figures from
      `CLAUDE.md`'s Resolved section rather than re-deriving them live on
      camera (saves time, same honesty)
- [ ] The Snapdragon X Elite AI Hub numbers card (Scene 8) — pull the two
      real job URLs from `CLAUDE.md`'s Resolved section verbatim
- [ ] `relay_admin_ui.jsx` live tester interaction (Scene 9)
- [ ] Voiceover recorded separately, or live-narrated over the screen
      recordings — either works, but keep Scenes 5 and 8's caveat lines
      verbatim, they're doing real work for the pitch

## What NOT to do

- Don't stage a "successful" full voice command through a real target app —
  that would require the reasoning model, which can't run here. Showing the
  mocked-reasoner integration demos *and saying so* is more credible than
  editing around the gap.
- Don't imply the AI Hub profiling numbers (Scene 8) are a full GenieX
  runtime measurement — they're a real compile/profile job on real hardware,
  a genuinely different (and honestly weaker) claim than "the whole loop ran
  on-device," and the script says so explicitly.
- Don't cut Scene 5's or Scene 8's caveat lines for time. They're the two
  highest-leverage sentences in the whole script.
