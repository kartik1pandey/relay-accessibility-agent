# What's left — and it's yours to do

Everything code-completable is done. What remains needs your own accounts,
your own hardware decisions, your own voice, or your own submission.
Deadline: **Sep 30, 2026, 11:59 PM IST** — the intake form can't be edited
after submitting, so the real target is **Sep 28–29**.

---

## 1. Get real Snapdragon access (do this first — it gates everything else)

**a. Create your Qualcomm ID.** Go to Qualcomm AI Hub
(`aihub.qualcomm.com`) and sign up — standard email + password flow. This
account has to be yours; nothing about it can be done on your behalf.

**b. Get an AI Hub API token.** Once signed in, find the API token in your
account settings and configure it locally:
```
pip install qai-hub
qai-hub configure --api_token <YOUR_TOKEN>
```

**c. Decide your hardware path** — three real options, pick one:
- **Your own Snapdragon X Elite/X2 Elite Windows machine**, if you have or
  can borrow one. Most direct — everything in this repo runs natively.
- **A retail demo unit** — Croma or Reliance Digital stores in India have
  Snapdragon Copilot+ PC demo zones; ask staff if you can run your own code
  on a display unit (results vary by store/staff).
- **AI Hub's cloud device farm** — no physical hardware needed. Submit a
  compile/profile job via the `qai_hub` Python API against a real,
  remote Snapdragon device and get back real numbers. Start here:
  `qai-hub list-devices` after configuring your token, then
  `qai_hub.submit_compile_job(...)` / `submit_profile_job(...)` per AI
  Hub's own docs. This is almost certainly your fastest path to a first
  real number.

**d. Once you're on real hardware or the device farm:** confirm the actual
GenieX Python API against what `models.py` already has (transformers-style
`AutoModelForCausalLM`/`AutoModelForVision2Seq`, `device_map="npu"`,
`.generate(...)`) — paste back whatever you get, error or success, and it
can be corrected against real output. Then run the same tests already in
this repo (`agent/test_tasks.py`, the integration test pattern) for real
latency and accuracy numbers on actual Snapdragon hardware.

## 2. Two quick fixes only you can make on this machine

**a. Sign into Outlook before you rely on it.** Open the Outlook app,
sign in with your real Microsoft account, and let it fully sync before
your demo — its launch-to-ready timing was observed to vary (sometimes
~5s, sometimes past 10s), so don't launch it cold on camera.

**b. Decide push-to-talk vs. always-listening.** Worth thinking through
with the actual target user in mind, not just abstractly: push-to-talk
needs a reliable button press, which cuts against the point for someone
with limited hand mobility — always-listening (with the clear visual
"listening" state `relay_ui.jsx` already has) probably fits the pitch
better, at the cost of a real privacy tradeoff (continuous audio capture)
you should be able to explain in the write-up either way. Update
`CLAUDE.md`'s open question once you've decided.

## 3. Record the demo video

**a. Pick recording software.** Windows' built-in Xbox Game Bar
(`Win+G` → record) works for simple screen capture with no install; OBS
Studio (free) if you want more control over multiple sources/audio
levels.

**b. Follow `DEMO_SCRIPT.md`'s shot list, in order:**
1. `npm run dev` in `web/`, screen-record the `relay_ui.jsx` walkthrough
   (Scene 4) — let its real `speechSynthesis` narration play
2. Re-run `agent/test_tasks.py` or the mocked-reasoner integration test
   fresh, screen-record the real terminal output (Scene 5) — rerun it
   right before recording so the numbers are current, not stale
3. Screen-record `relay_admin_ui.jsx`'s live rule tester (Scene 7)
4. Record your own voiceover — either live while screen-recording, or
   separately and synced in editing. Keep Scene 5's honesty line
   verbatim: say plainly that the reasoning step is simulated and why

**c. Edit and export.** Any editor works — trim clips to the script's
rough timings, layer voiceover if recorded separately, export as MP4.
Check the real Unstop form (next step) for any length/size limit before
your final export.

## 4. Confirm the actual Unstop submission mechanics

**a. Log into the real Unstop competition page** you registered through —
not a guess, the actual listing.

**b. Find the submission/intake form** and read every field before
preparing content around it: video (upload vs. link — if it wants a
link, upload your finished video to YouTube as *unlisted* first, or
Google Drive with link-sharing on), repo link, write-up (pasted text vs.
file upload — `WRITEUP.md` is ready either way), any category/tech-stack
fields.

**c. Prepare everything to match those exact constraints**, then do one
full read-through of the form before submitting — there's no edit after.

**d. Submit by Sep 28–29.** Not the 30th. No exceptions if the form
locks at the deadline.

## 5. Before you submit — housekeeping

**a. Push this repo to GitHub, public** (submissions are made public per
`CLAUDE.md`):
```
cd D:\Qualcomm
git init
git add .
git commit -m "Snapdragon AI Lab submission: Relay"
git remote add origin <your-new-repo-url>
git branch -M main
git push -u origin main
```
`.gitignore` already excludes `node_modules/`, `__pycache__/`, and the
audit log — nothing sensitive should end up committed, but do one
`git status` glance before the push regardless.

**b. Optional: host `web/showcase.html` somewhere with a real URL** beyond
the Claude Artifact link — it's fully static, no build step. GitHub Pages
(enable in repo Settings → Pages, point at `web/`), or drag-and-drop it
into Netlify/Vercel, both work in minutes.

**c. Final read-through** of `WRITEUP.md` and the live Unstop form
together, side by side, before hitting submit.

---

## What you do NOT need to re-verify

Everything in `CLAUDE.md`'s "Resolved since the scaffold was written"
section, and `build_checklist.jsx` (now showing real, accurate progress
via localStorage) — guardrails, perception across all three apps,
platform glue, STT, TTS, the full integration loop, accessibility
compliance. All of it was actually run, not asserted. Cite it, don't redo
it.
