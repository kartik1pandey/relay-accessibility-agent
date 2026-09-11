"""
models.py — wrappers around the models this agent uses.

Update, verified 2026-09-09: the LLM/VLM calls below are no longer a
guess. Pulled the real `geniex` package (v0.6.1) from PyPI and read its
actual source — the client SDK's Python source is public, so this part
needed no device or Qualcomm account to confirm. Real API:
`AutoModelForCausalLM` / `AutoModelForVision2Seq`, both with a
transformers-style `.from_pretrained(name, device_map=...)` and a
`.generate(prompt, ...)` returning a `GenerateOutput` (`.text`, plus a
`.profile` with per-call timing built in — free latency numbers on
every generation, worth logging for the write-up).

One thing this DID surface: `pip install geniex` refuses to build on
generic Linux x86_64 — its setup script detects the platform and
raises, because the package is a thin ctypes wrapper around a native
library Qualcomm only ships prebuilt for Windows ARM64, Android, and
Linux ARM64. That's a hard platform requirement, not a missing
credential — this import will only actually work on target-class
hardware. Wrapped below so the rest of this file still reads and
type-checks even where geniex itself can't install.

Honest gap: GenieX's own package only exports LLM/VLM classes — no
Whisper or TTS entry point anywhere in it. Speech-to-text and
text-to-speech almost certainly deploy through a different path (the
qai_hub_models ONNX + QNN pipeline directly) — that part below is
still a placeholder, flagged as such, not verified the way the
reasoning model calls now are.
"""

from dataclasses import dataclass
import json

try:
    from geniex import AutoModelForCausalLM, AutoModelForVision2Seq
except ImportError:
    # Expected on any machine that isn't Windows ARM64 / Android / Linux
    # ARM64 — see the module docstring. Lets this file still be read,
    # imported, and have its non-geniex logic tested elsewhere.
    AutoModelForCausalLM = None
    AutoModelForVision2Seq = None


@dataclass
class ActionDecision:
    control_name: str
    control_type: str
    action: str            # "click" | "set_text" | "scroll_down" | "scroll_up"
    value: str = ""
    say: str = ""           # what to speak back to the user, if anything


@dataclass
class TurnMemory:
    """One past turn, kept only so the reasoner can resolve a follow-up
    like "read the next one" or "reply to that" — deliberately short-term:
    Agent (see agent.py) caps this to the last few turns, not the whole
    session. Holds just enough to disambiguate a pronoun, not a full
    conversation transcript."""
    transcript: str
    control_name: str
    action: str


def _build_prompt(transcript: str, screen_context: str, history: list = None) -> str:
    """Pulled out from LocalReasoner.decide so the prompt shape itself is
    testable without GenieX/NPU hardware — see this file's __main__."""
    history_block = ""
    if history:
        recent = history[-3:]  # short-term memory: last 3 turns only
        lines = "\n".join(
            f'  - said "{h.transcript}", did {h.action} on "{h.control_name}"'
            for h in recent
        )
        history_block = (
            "Recent turns, for resolving a follow-up like \"it\", \"that\", "
            f'or "the next one":\n{lines}\n\n'
        )
    return (
        history_block
        + f'User said: "{transcript}"\n\n'
        + f"Current screen:\n{screen_context}\n\n"
        + "Reply with exactly one action as JSON, and nothing else:\n"
        '{"control_name": "...", "control_type": "...", "action": "...", '
        '"value": "...", "say": "..."}\n\n'
        # Added 2026-09-10 from competitive research (COMPETITIVE_RESEARCH.md):
        # Orbit's prompt protocol enforces a hard word cap per response type
        # (Mobility <=10 words, Description <=20, General <=25). Applying the
        # same idea here, one cap for the single response field this project
        # has: shorter spoken confirmations mean less TTS latency and less to
        # hold in mind for someone who may be relying on hearing, not reading,
        # to follow along.
        '"say" must be 12 words or fewer.'
    )


class LocalReasoner:
    """The decision-making step — the calls this class makes are
    verified against the real GenieX API (see module docstring),
    even though they can only actually run on target-class hardware.

    Defaults to a small text-only model for the common case; only
    loads the heavier vision-language model the first time a turn
    actually needs it, so the common (tree-was-usable) path stays
    fast and light on memory."""

    def __init__(
        self,
        text_model_id: str = "microsoft/Phi-4-mini-instruct",
        vlm_model_id: str = "Qwen/Qwen3-VL-4B-Instruct",
    ):
        if AutoModelForCausalLM is None:
            raise RuntimeError(
                "geniex isn't installed/installable here — run this on "
                "Windows ARM64, Android, or Linux ARM64."
            )
        self.text_model = AutoModelForCausalLM.from_pretrained(
            text_model_id, device_map="npu"
        )
        self._vlm_model_id = vlm_model_id
        self._vlm = None  # lazy-loaded

    @property
    def vlm(self):
        if self._vlm is None:
            self._vlm = AutoModelForVision2Seq.from_pretrained(
                self._vlm_model_id, device_map="npu"
            )
        return self._vlm

    def decide(
        self, transcript: str, screen_context: str, history: list = None
    ) -> ActionDecision:
        """`screen_context` is either a UI-tree text dump or, on the
        vision-fallback path, the VLM's own scene description — this
        prompt treats both the same way, which is the point.

        `history` (a list of `TurnMemory`, oldest first) lets a follow-up
        like "read the next one" resolve against what just happened —
        optional and short: Agent (agent.py) keeps only the last few
        turns, not a running session transcript."""
        prompt = _build_prompt(transcript, screen_context, history)
        output = self.text_model.generate(prompt, max_new_tokens=200)
        # output.profile.ttft / .decode_speed are real per-call latency
        # numbers GenieX hands back for free — log these, don't re-derive them.
        return _parse_decision(output.text)

    def describe_image(self, screenshot_path: str, prompt: str) -> str:
        output = self.vlm.generate(prompt, images=[screenshot_path], max_new_tokens=200)
        return output.text


class SpeechToText:
    """VERIFIED RUNNING 2026-09-10, not just shape-confirmed — actually
    executed on this dev machine (Python 3.12 venv at
    C:\\Users\\karti\\.venvs\\qualcomm312), CPU, real audio in, real text
    out, reproduced twice (once via qai_hub_models' own CLI demo, once via
    this exact direct API called standalone):

        Transcription: And so my fellow Americans, ask not what your
        country can do for you, ask what you can do for your country.

    (~5.9s wall-clock for one ~11s test clip, CPU. Not a latency number
    that means anything for Snapdragon NPU — see the GPU note below.)

    Package layout note: qai_hub_models' installed release (0.61.0) has
    these classes under `qai_hub_models.models._shared.hf_whisper`, not
    `qai_hub_models.models.templates.hf_whisper` as the GitHub main
    branch's source currently shows — real drift between HEAD and the
    released package, confirmed by actually importing both ways.

    Honest GPU note: `HfWhisperApp.__init__` hardcodes `.to("cpu")` on
    both encoder and decoder unconditionally, so this always runs on CPU
    through this call path — even though CUDA is genuinely available on
    this dev machine (confirmed separately: `torch.cuda.is_available()`
    is True, an NVIDIA GeForce RTX 3060 Laptop GPU). Forcing GPU use here
    would mean bypassing that hardcoded path and reimplementing the
    encode/decode loop directly — real surgery into a third-party
    library's internals, not attempted, and beside the point anyway: the
    competition's actual target is Snapdragon NPU via GenieX, not this
    discrete GPU. This CPU run's value is proving the model/tokenizer/
    audio pipeline genuinely works, not benchmarking it.

    `transcribe()` below accepts the same `audio_bytes: bytes` shape the
    rest of this file already uses (matching agent.py's
    `_record_short_clip`), decoding WAV bytes to the float32 ndarray
    `HfWhisperApp.transcribe()` expects. This exact WAV-bytes-in path is
    also verified: the demo clip re-encoded to WAV bytes (matching what
    `agent.py`'s `_pcm_to_wav_bytes` produces) transcribed correctly
    through this class as written, not just the raw-array path. Not yet
    verified against a *real live microphone* recording specifically
    (only this synthetic WAV re-encoding of the known-good test clip).
    """

    def __init__(self, model_id: str = "openai/whisper-base"):
        from qai_hub_models.models._shared.hf_whisper.app import HfWhisperApp
        from qai_hub_models.models._shared.hf_whisper.model import (
            HfWhisperDecoder,
            HfWhisperEncoder,
        )

        encoder = HfWhisperEncoder.from_pretrained(model_id)
        decoder = HfWhisperDecoder.from_pretrained(model_id)
        self.app = HfWhisperApp(encoder, decoder, model_id)

    def transcribe(self, audio_bytes: bytes) -> str:
        import io
        import wave

        import numpy as np

        with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
            sample_rate = wav.getframerate()
            pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
        audio = pcm.astype(np.float32) / 32768.0
        return self.app.transcribe(audio, sample_rate)


class TextToSpeech:
    """VERIFIED WORKING 2026-09-10 — real synthesis, real audio, played
    back through real speakers. Getting here took five independent real
    blockers, found and fixed one at a time (not guessed, not skipped
    past) in an isolated venv (C:\\Users\\karti\\.venvs\\melo_isolated),
    kept separate from the Whisper venv because melo's dependency chain
    (transformers==4.27.4, tokenizers==0.13.3, a hand-picked language
    stack) can't coexist with Whisper's transformers==4.56.2:

    1. `qai_hub_models`' own `melotts-en` pip extra lists ~25 dependencies
       but never lists `melo` itself — the package its model code
       unconditionally hard-imports.
    2. The `melotts` PyPI package (0.1.1) is broken (missing files in its
       own sdist) — installed from upstream GitHub source instead.
    3. That first failed on a linker error that was really Git Bash's own
       `link.exe` shadowing MSVC's — fixed by installing from PowerShell.
       This machine also had no MSVC C++ Build Tools at all — installed
       Visual Studio Build Tools (C++ workload) to get a real one.
    4. `tokenizers==0.13.3` (needed by melo's pinned transformers) failed
       to compile against current Rust's deny-by-default
       `invalid_reference_casting` lint — fixed with
       `RUSTFLAGS="--cap-lints warn"`.
    5. `fugashi` failed to compile (needs a system MeCab this machine
       didn't have) — installed real upstream MeCab
       (github.com/ikegami-yukino/mecab) and copied its headers/lib to
       `C:\\mecab` by hand, matching fugashi's hardcoded (non-overridable)
       expected path.

    Also needed, once `melo` actually imported: this machine's Windows
    Application Control policy (Smart App Control, confirmed via
    `Win32_DeviceGuard`) was blocking `numba` — disabled by the user via
    Windows Security settings (their call, their machine, not something I
    did or would do myself); plus an older `setuptools<81` (recent
    setuptools dropped `pkg_resources`, which this old `librosa` still
    needs), the `unidic` dictionary data (`python -m unidic download`,
    ~526MB), `pykakasi` (a genuinely-used import in melo's Japanese
    module, unlike fugashi which turned out unnecessary at the Python
    level but *is* needed transitively by `transformers`' MecabTokenizer),
    and one more NLTK data package
    (`averaged_perceptron_tagger_eng`).

    Confirmed working end to end: loaded `TTS(language="EN")`, real
    speaker map (`EN-US`, `EN-BR`, `EN_INDIA`, `EN-AU`, `EN-Default`),
    synthesized "Say yes to confirm: Send." (the actual confirm-state
    text from relay_ui.jsx) to a real ~2.2s WAV file, played it through
    real speakers. ~50s on CPU for that one short phrase — no CUDA in
    this isolated venv; not attempted, since the win here was getting it
    working at all, not benchmarking it, and the real target is
    Snapdragon NPU via GenieX regardless.

    This class talks to that isolated environment over a subprocess
    (`melo_worker.py`, one JSON request/response per line on stdin/
    stdout) rather than importing melo directly — the whole reason for
    the isolated venv in the first place is that melo's dependencies
    can't live in this process."""

    def __init__(
        self,
        model_id: str = "melotts_en",
        venv_python: str = None,
    ):
        import json
        import os
        import subprocess

        self.venv_python = venv_python or os.environ.get(
            "MELO_VENV_PYTHON",
            r"C:\Users\karti\.venvs\melo_isolated\Scripts\python.exe",
        )
        worker_path = os.path.join(os.path.dirname(__file__), "melo_worker.py")
        self._proc = subprocess.Popen(
            [self.venv_python, worker_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        ready_line = self._proc.stdout.readline()
        ready = json.loads(ready_line) if ready_line else {}
        if not ready.get("ready"):
            stderr = self._proc.stderr.read()
            raise RuntimeError(
                f"melo_worker failed to start: {ready.get('error')}\n{stderr}"
            )

    def speak(self, text: str) -> bytes:
        import json

        self._proc.stdin.write(json.dumps({"text": text}) + "\n")
        self._proc.stdin.flush()
        response = json.loads(self._proc.stdout.readline())
        if not response.get("ok"):
            raise RuntimeError(f"melo_worker error: {response.get('error')}")
        with open(response["path"], "rb") as f:
            return f.read()


def _parse_decision(raw_json: str) -> ActionDecision:
    data = json.loads(raw_json)
    return ActionDecision(**data)


if __name__ == "__main__":
    # the one part of this file that needs no model or hardware at all
    sample = json.dumps({
        "control_name": "Send", "control_type": "Button",
        "action": "click", "value": "", "say": "Sending it now.",
    })
    print(_parse_decision(sample))

    # _build_prompt (short-term memory) is likewise pure Python — real
    # sanity checks, no GenieX/NPU needed.
    no_history_prompt = _build_prompt("read the new emails", "ListItem: \"Inbox\"")
    assert "Recent turns" not in no_history_prompt, "empty history must add nothing"
    print("[PASS] no history -> no history block in the prompt")

    history = [
        TurnMemory(transcript="read the new emails", control_name="Inbox", action="click"),
        TurnMemory(transcript="open the first one", control_name="Message 1", action="click"),
    ]
    with_history_prompt = _build_prompt("read the next one", "ListItem: \"Message 2\"", history)
    assert 'said "open the first one", did click on "Message 1"' in with_history_prompt
    print("[PASS] history present -> both past turns appear in the prompt")

    long_history = history + [
        TurnMemory(transcript="close it", control_name="Close", action="click"),
        TurnMemory(transcript="go back", control_name="Back", action="click"),
    ]
    truncated_prompt = _build_prompt("read the next one", "ListItem: \"Message 2\"", long_history)
    assert 'said "read the new emails"' not in truncated_prompt, "must not include turns older than the last 3"
    assert 'said "go back"' in truncated_prompt, "must include the most recent turn"
    print("[PASS] history longer than 3 turns -> only the last 3 appear (genuinely short-term)")