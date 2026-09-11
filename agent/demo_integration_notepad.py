"""
demo_integration_notepad.py — runs the real, unmodified Agent.run_turn()
end to end against a live Notepad window, with only LocalReasoner mocked
(the one piece that's structurally impossible without a Snapdragon NPU —
see models.py's module docstring).

Everything else is real: a real ~1s microphone-shaped WAV buffer goes
through real SpeechToText, the real perception.read_ui_tree() reads
Notepad's live UI Automation tree, the real guardrails.check() gate runs,
a real perception.act_on() scroll executes against the live window, and
real TextToSpeech synthesizes + plays back the spoken response.

Prerequisite: Notepad must already be open (Win+R, `notepad`, wait for the
window). This script does not launch it — see test_tasks.py if you want a
harness that launches apps itself.

Run: python demo_integration_notepad.py
"""

from agent import Agent
from models import ActionDecision, SpeechToText, TextToSpeech
from silent_wav import silent_wav


class MockReasoner:
    """Stands in only for the GenieX/NPU-dependent decision step."""

    def decide(self, transcript, screen_context, history=None):
        print(f"--- reasoner saw {len(screen_context.splitlines())} lines of real screen context, e.g.:")
        for line in screen_context.splitlines()[:5]:
            print("   ", line)
        return ActionDecision(
            control_name="Text Editor",
            control_type="EditControl",
            action="scroll_down",
            value="",
            say="Scrolled down.",
        )


def main() -> None:
    agent = Agent.__new__(Agent)  # bypass __init__ — real LocalReasoner() needs GenieX
    agent.stt = SpeechToText()
    agent.tts = TextToSpeech()
    agent.reasoner = MockReasoner()
    agent.history = []

    print("=== Running real agent.run_turn() against a live Notepad window ===")
    agent.run_turn(silent_wav(), "Notepad")
    print(f"=== run_turn() completed. agent.history now: {agent.history}")


if __name__ == "__main__":
    main()
