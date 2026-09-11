"""
generate_narration.py — synthesizes the demo video's narration lines
through the project's own real, verified TextToSpeech pipeline
(agent/models.py, MeloTTS-EN via the isolated venv) rather than a
separately-recorded human voice actor.

Each scene's [VO] lines from DEMO_SCRIPT.md are concatenated into one
narration line and synthesized to demo/narration/sceneNN.wav. This is a
real synthesis pass, not a stub — it can take several minutes total on
CPU (see models.py's TextToSpeech docstring: ~50s for the first, shorter
call including worker startup; per-line cost after that scales with text
length, not a fixed per-call floor).

Run from inside agent/ (so its own imports resolve), pointing at this
script's path, e.g.:
    C:\\Users\\karti\\.venvs\\qualcomm312\\Scripts\\python.exe ^
        D:\\Qualcomm\\demo\\generate_narration.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from models import TextToSpeech

OUT_DIR = os.path.join(os.path.dirname(__file__), "narration")

# One entry per scene — the exact [VO]/[VO, human]/[VO, continued] lines
# from DEMO_SCRIPT.md, concatenated in the order they're spoken.
NARRATION = {
    "scene01": (
        "Say what you'd like me to do. "
        "For someone with limited hand mobility, or low vision, "
        "that's the whole interaction with their computer."
    ),
    "scene02": (
        "This is Relay, a voice-controlled, screen-reading agent that runs "
        "entirely on-device. It's built for one thing: giving someone who "
        "can't reliably point-and-click, or can't reliably read a screen, "
        "real control over their PC, without handing that control to a "
        "black box."
    ),
    "scene03": (
        "Voice comes in through Whisper. The screen gets read as "
        "structured data first, the accessibility tree, and only falls "
        "back to a vision model when that tree doesn't have enough to "
        "work with. A small local model decides the next step. Every "
        "decision passes through a guardrail before anything executes. "
        "And the result gets spoken back through Melo T T S."
    ),
    "scene04": (
        "Here's the state machine end users actually see, live. Watch "
        "the confirm screen specifically, it's the single highest-stakes "
        "moment in the product, so it's built to be impossible to mistake "
        "for a routine notification: different shape, different color, "
        "and it's spoken out loud, not just shown."
    ),
    "scene05": (
        "Every piece of that state machine is backed by something that "
        "actually runs, not just illustrated. This is a real "
        "microphone-shaped recording, transcribed by a real Whisper "
        "model, checked against a live window's real accessibility tree, "
        "gated by the real guardrail engine, and spoken back through a "
        "real text-to-speech model, all on this laptop, right now. "
        "The one piece simulated here is the decision-making step itself, "
        "the small reasoning model that picks the action. That one "
        "genuinely needs Snapdragon's on-device N P U to run, which this "
        "dev machine doesn't have. Everything else you just watched is "
        "real."
    ),
    "scene06": (
        "Two of this agent's three target apps, Edge and Outlook, turned "
        "out to be built on Chromium, and Chromium simply doesn't expose "
        "real page content through Windows' accessibility tree the way a "
        "native app does. That's not a bug in this code, it's a real "
        "limitation this project found and verified directly, not "
        "assumed. For Edge specifically, there's now a real fix: reading "
        "and acting on the page through the same Chrome DevTools Protocol "
        "browser engineers use to debug it. Watch: the agent finds the "
        "real search box on a real Wikipedia page, types into it, and "
        "then, in a completely separate step, reads the live page back to "
        "prove the write actually landed, not just that the code didn't "
        "crash."
    ),
    "scene07": (
        "Three genuinely different interaction shapes: read-and-reply, "
        "open-ended navigation, and simple transport controls. Not the "
        "easiest three to fake, the three that actually stress different "
        "parts of the architecture. Two of three now have a real, working "
        "content path. The third, Outlook, is an honestly open problem, "
        "and it's written down as one."
    ),
    "scene08": (
        "This dev machine doesn't have Snapdragon hardware, but Qualcomm "
        "A I Hub does, and it's real. Whisper-base was actually compiled "
        "and profiled against a real Snapdragon X Elite over A I Hub's "
        "hosted device farm: about forty-nine milliseconds for the "
        "encoder, under four for the decoder, on real silicon, an order "
        "of magnitude faster than the same model on this laptop's C P U. "
        "It's worth being precise about what this is and isn't: it's a "
        "real compile-and-profile run on the actual target hardware, not "
        "a simulation, but it's not the same as running the full GenieX "
        "runtime end to end, which still needs physical device access "
        "this build doesn't have yet."
    ),
    "scene09": (
        "There's a second surface, for whoever configures this: calmer, "
        "denser, and it reads the actual guardrail rules from the code, "
        "not a hand-maintained copy that can drift out of sync."
    ),
    "scene10": (
        "Built from scratch, verified at every stage we could verify it, "
        "and honest about the one stage we couldn't. Thanks for watching."
    ),
}


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    tts = TextToSpeech()

    for scene_id, text in NARRATION.items():
        out_path = os.path.join(OUT_DIR, f"{scene_id}.wav")
        print(f"--- synthesizing {scene_id} ({len(text)} chars)...")
        start = time.time()
        audio = tts.speak(text)
        with open(out_path, "wb") as f:
            f.write(audio)
        print(f"    wrote {out_path} in {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
