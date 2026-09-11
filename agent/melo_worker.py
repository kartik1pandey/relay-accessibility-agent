"""
melo_worker.py — runs inside the isolated melo venv
(C:\\Users\\karti\\.venvs\\melo_isolated), not the main agent environment.

Why a separate process at all: melo's dependency chain (transformers==
4.27.4, tokenizers==0.13.3, a hand-picked language-module stack) cannot
coexist with the Whisper venv's transformers==4.56.2 in one environment
— confirmed the hard way, see models.py's TextToSpeech docstring and
CLAUDE.md's Resolved section for the five real blockers that stood
between "confirmed shape" and this actually working.

Protocol: one JSON object per line on stdin, one JSON object per line
of stdout, flushed immediately. First line on startup is always
{"ready": true} (or {"ready": false, "error": ...} if the model failed
to load) — the caller must read and check that line before sending any
requests.

Request:  {"text": "..."}
Response: {"ok": true, "path": "<absolute path to a WAV file>"}
       or {"ok": false, "error": "..."}

Run standalone to smoke-test: python melo_worker.py, then type
{"text": "hello"} and press enter.
"""

import json
import sys
import tempfile


def main() -> None:
    try:
        from melo.api import TTS

        model = TTS(language="EN", device="auto")
        speaker_id = model.hps.data.spk2id["EN-Default"]
    except Exception as e:
        print(json.dumps({"ready": False, "error": str(e)}), flush=True)
        return

    print(json.dumps({"ready": True}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            text = request["text"]
            out_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
            model.tts_to_file(text, speaker_id, output_path=out_path, quiet=True)
            print(json.dumps({"ok": True, "path": out_path}), flush=True)
        except Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}), flush=True)


if __name__ == "__main__":
    main()
