"""
agent.py — the main loop. Wires speech in, screen understanding,
decision-making, the safety gate, and speech out into one turn.

Run this on the target Snapdragon device once models.py's placeholder
imports are pointed at the real GenieX API, and once the three
`NotImplementedError` helpers at the bottom are wired to real libraries.
"""

import io
import json
import tempfile
import wave
from datetime import datetime, timezone

import numpy as np
import sounddevice as sd
from mss import mss
from mss.tools import to_png

from perception import read_ui_tree, describe_via_vision, act_on, AppNotRespondingError
from cdp_perception import read_dom, act_on_dom
from models import SpeechToText, TextToSpeech, LocalReasoner, TurnMemory
from guardrails import check, explain, GateDecision, TargetElement

SAMPLE_RATE = 16000  # Whisper's native input rate
AUDIT_LOG_PATH = "guardrail_audit.jsonl"
MAX_TURN_HISTORY = 3  # short-term only — see models.TurnMemory's docstring


def _log_guardrail_decision(target: TargetElement, gate: GateDecision, reason: str) -> None:
    """Appends one line per guardrail decision to an audit log — plain,
    append-only JSONL so it's easy to grep/tail/parse after the fact. This
    is the "real, persisted audit log" CLAUDE.md's guard-5 checklist item
    calls for; the reason text is the same one spoken to the user, so what
    gets logged and what gets said always match."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": target.app_name,
        "control_name": target.name,
        "control_type": target.control_type,
        "automation_id": target.automation_id,
        "decision": gate.value,
        "reason": reason,
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# Fill in with whatever substring uniquely identifies each app's window
# title on your machine. Start with these three — see the checklist for
# why these three specifically.
#
# Verified live on this machine (2026-09-10): the classic "Mail" app has
# been superseded by the new unified Outlook for Windows here — its
# process is literally named `olk.exe` and its real window title is
# "Outlook", not "Mail" (CLAUDE.md's architecture note already
# anticipated exactly this: "Mail (or Outlook)"). "Media Player" and
# "Microsoft Edge" both matched their real window titles directly.
TARGET_APPS = {
    "mail": "Outlook",
    "browser": "Microsoft Edge",
    "media": "Media Player",
}


class Agent:
    def __init__(self):
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.reasoner = LocalReasoner()
        self.history: list[TurnMemory] = []  # short-term only — see models.TurnMemory

    def run_turn(self, audio_bytes: bytes, active_window_title: str) -> None:
        transcript = self.stt.transcribe(audio_bytes)

        # Edge is Chromium-based; its real page content genuinely doesn't
        # surface via UI Automation (verified 2026-09-10 — see
        # perception.py's module docstring: 0 real content elements found
        # at 14 levels deep). Read/act via CDP for it specifically instead
        # — see cdp_perception.py. Requires Edge launched with both
        # --remote-debugging-port=9222 --remote-allow-origins=*. Every
        # other target app still goes through UI Automation as before.
        is_browser = TARGET_APPS["browser"] in active_window_title
        if is_browser:
            screen = read_dom()
        else:
            screen = read_ui_tree(active_window_title)

        if screen.tree_is_usable:
            screen_context = "\n".join(
                f'{e.control_type}: "{e.name}"' for e in screen.elements if e.name
            )
        else:
            # only take a screenshot and touch the (heavier) VLM when
            # the tree genuinely doesn't give us enough to work with
            screenshot = _capture_screenshot()
            screen_context = describe_via_vision(screenshot, self.reasoner)

        decision = self.reasoner.decide(transcript, screen_context, self.history)

        target = TargetElement(
            name=decision.control_name,
            control_type=decision.control_type,
            app_name=active_window_title,
        )
        gate = check(target)
        reason = explain(target, gate)
        print(f"[guardrail] {reason}")
        _log_guardrail_decision(target, gate, reason)

        if gate is GateDecision.BLOCK:
            self._say(f"I can't do that — {decision.control_name} is blocked.")
            return

        if gate is GateDecision.CONFIRM:
            self._say(f"Say yes to confirm: {decision.control_name}.")
            if not self._await_yes():
                self._say("Okay, cancelled.")
                return

        matching_element = next(
            (e for e in screen.elements if e.name == decision.control_name), None
        )
        if matching_element is None:
            self._say(f'I couldn\'t find "{decision.control_name}" on screen anymore.')
            return

        try:
            if is_browser:
                act_on_dom("", decision.control_name, decision.action, decision.value)
            else:
                act_on(matching_element, decision.action, decision.value)
        except AppNotRespondingError:
            self._say(f"{active_window_title} isn't responding right now. Try again in a moment.")
            return
        except LookupError:
            self._say(f'I couldn\'t find "{decision.control_name}" on screen anymore.')
            return

        # Only remembered after a real, successful action — a turn that
        # got blocked, cancelled, or failed to find its target shouldn't
        # be what a later "the next one" resolves against.
        self.history.append(
            TurnMemory(transcript=transcript, control_name=decision.control_name, action=decision.action)
        )
        self.history = self.history[-MAX_TURN_HISTORY:]

        if decision.say:
            self._say(decision.say)

    def _say(self, text: str) -> None:
        audio = self.tts.speak(text)
        _play_audio(audio)

    def _await_yes(self) -> bool:
        audio = _record_short_clip()
        reply = self.stt.transcribe(audio)
        return "yes" in reply.lower()


# --- Platform glue -------------------------------------------------------
# mss for screenshots, sounddevice for audio in/out — plain, standard
# libraries, verified against a real screen and (where a device is present)
# a real microphone/speaker on this machine. Windows-only in spirit (this
# whole agent is), but none of these three actually require Snapdragon
# hardware to run — only the GenieX-backed model calls in models.py do.

def _capture_screenshot() -> str:
    """Grabs the primary monitor to a temp PNG and returns its path —
    models.LocalReasoner.describe_image expects a file path (see
    perception.describe_via_vision)."""
    with mss() as sct:
        shot = sct.grab(sct.monitors[1])
        path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        to_png(shot.rgb, shot.size, output=path)
    return path


def _record_short_clip(seconds: float = 3.0) -> bytes:
    """Records a short mono clip from the default input device and returns
    it as WAV-encoded bytes — the shape SpeechToText.transcribe expects."""
    samples = sd.rec(
        int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="int16"
    )
    sd.wait()
    return _pcm_to_wav_bytes(samples, SAMPLE_RATE)


def _play_audio(audio_bytes: bytes) -> None:
    """Plays back WAV-encoded bytes, as returned by TextToSpeech.speak."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="int16")
        sd.play(samples, samplerate=wav.getframerate())
        sd.wait()


def _pcm_to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # int16
        wav.setframerate(sample_rate)
        wav.writeframes(samples.tobytes())
    return buf.getvalue()


if __name__ == "__main__":
    print("Platform glue (screenshot/mic/speaker) is wired. The model calls in")
    print("models.py still need Windows ARM64 / Android / Linux ARM64 hardware")
    print("to actually run — see models.py's module docstring.")
