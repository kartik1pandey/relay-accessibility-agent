"""
silent_wav.py — a tiny shared helper for the demo_integration_*.py scripts:
builds a real WAV-encoded byte string of silence, the same shape a real
microphone recording would be, so SpeechToText.transcribe() has something
real to run against without needing a person to speak into a live mic on
cue. The resulting (empty) transcript is honest, not a bug — see the demo
scripts' own docstrings.
"""

import io
import wave


def silent_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()
