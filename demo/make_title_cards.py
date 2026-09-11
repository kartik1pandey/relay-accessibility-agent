"""
make_title_cards.py — renders the demo video's non-live scenes (no
screen-recorded footage: the problem statement, the architecture diagram,
the three-app numbers, the Snapdragon AI Hub numbers, and the close card)
as real 1920x1080 PNG images via Pillow, using the exact palette already
shipped in web/relay_ui.jsx (#F5F7F4 / #10151A / #1B6B6E / #3F4A47) so the
video's visual identity matches the real product instead of inventing a
separate one just for the recording.

Run: python make_title_cards.py
"""

import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
OUT_DIR = os.path.join(os.path.dirname(__file__), "cards")

BG = "#F5F7F4"
INK = "#10151A"
INK_SOFT = "#3F4A47"
ACCENT = "#1B6B6E"
ACCENT_TEXT = "#0B4547"

FONT_DIR = r"C:\Windows\Fonts"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


F_DISPLAY = lambda size: _font("segoeuib.ttf", size)  # Segoe UI Bold
F_BODY = lambda size: _font("segoeui.ttf", size)
F_MONO = lambda size: _font("consola.ttf", size)


def _wrapped(draw, text, font, max_width, line_spacing=1.35):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) > max_width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _draw_wrapped_centered(draw, text, font, cy, max_width, fill, line_spacing=1.35):
    lines = _wrapped(draw, text, font, max_width)
    line_h = font.size * line_spacing
    total_h = line_h * len(lines)
    y = cy - total_h / 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text((W / 2 - w / 2, y), line, font=font, fill=fill)
        y += line_h


def _base_card(eyebrow: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((120, 90), eyebrow, font=F_MONO(28), fill=ACCENT_TEXT)
    d.line([(120, 140), (W - 120, 140)], fill="#D8DED8", width=2)
    return img, d


def card_scene02() -> Image.Image:
    img, d = _base_card("RELAY — THE PROBLEM")
    _draw_wrapped_centered(
        d,
        'Not a general computer-use agent. Scoped assistive technology — '
        'a person narrates every step, and nothing consequential happens '
        'without a spoken yes.',
        F_DISPLAY(64),
        H / 2,
        1500,
        INK,
    )
    return img


def card_scene03() -> Image.Image:
    img, d = _base_card("RELAY — ARCHITECTURE")
    steps = [
        "Voice command",
        "Whisper (speech-to-text)",
        "Screen understanding — UI Automation tree first, vision model on fallback",
        "Small local reasoning model decides the next action",
        "Guardrail check — ALLOW / CONFIRM (spoken yes) / BLOCK",
        "Action executes against the real UI element",
        "MeloTTS speaks the result",
    ]
    top = 220
    gap = (H - top - 120) / (len(steps) - 1)
    for i, step in enumerate(steps):
        y = top + i * gap
        is_gate = "Guardrail" in step
        color = ACCENT_TEXT if is_gate else INK
        font = F_DISPLAY(40) if is_gate else F_BODY(38)
        w = d.textlength(step, font=font)
        d.text((W / 2 - w / 2, y - 20), step, font=font, fill=color)
        if i < len(steps) - 1:
            ax = W / 2
            d.line([(ax, y + 28), (ax, y + gap - 24)], fill="#B9C3BC", width=3)
            d.polygon(
                [(ax - 10, y + gap - 34), (ax + 10, y + gap - 34), (ax, y + gap - 18)],
                fill="#B9C3BC",
            )
    return img


def card_scene07() -> Image.Image:
    img, d = _base_card("RELAY — THREE APPS, ONE AGENT")
    cols = [
        ("Media Player", "211 elements\n113 named + enabled", "Native app — cleanest\nreal content of the three", ACCENT_TEXT),
        ("Microsoft Edge", "0 real content elements\nvia UI Automation", "Solved via Chrome\nDevTools Protocol", ACCENT_TEXT),
        ("Outlook", "Chrome Legacy Window\npane, chrome only", "Same limitation as Edge —\nstill honestly open", "#8A4A2E"),
    ]
    col_w = (W - 240) / 3
    for i, (title, stat, note, accent) in enumerate(cols):
        x0 = 120 + i * col_w
        cx = x0 + col_w / 2
        d.text((cx - d.textlength(title, font=F_DISPLAY(46)) / 2, 320), title, font=F_DISPLAY(46), fill=INK)
        y = 420
        for line in stat.split("\n"):
            w = d.textlength(line, font=F_MONO(34))
            d.text((cx - w / 2, y), line, font=F_MONO(34), fill=accent)
            y += 46
        y += 40
        for line in note.split("\n"):
            w = d.textlength(line, font=F_BODY(30))
            d.text((cx - w / 2, y), line, font=F_BODY(30), fill=INK_SOFT)
            y += 42
    return img


def card_scene08() -> Image.Image:
    img, d = _base_card("REAL SNAPDRAGON X ELITE PROFILING — QUALCOMM AI HUB")
    title = "Whisper-base, compiled and profiled on real Snapdragon hardware"
    w = d.textlength(title, font=F_DISPLAY(46))
    d.text((W / 2 - w / 2, 260), title, font=F_DISPLAY(46), fill=INK)

    pairs = [("~49.1 ms", "encoder"), ("~3.7 ms", "decoder")]
    col_w = (W - 400) / 2
    for i, (num, label) in enumerate(pairs):
        cx = 200 + col_w / 2 + i * col_w
        w = d.textlength(num, font=F_DISPLAY(110))
        d.text((cx - w / 2, 420), num, font=F_DISPLAY(110), fill=ACCENT_TEXT)
        w2 = d.textlength(label, font=F_MONO(32))
        d.text((cx - w2 / 2, 560), label, font=F_MONO(32), fill=INK_SOFT)

    caveat = (
        "A real compile + profile job on Qualcomm AI Hub's hosted device farm — "
        "not a simulation, and not yet a full GenieX runtime measurement."
    )
    _draw_wrapped_centered(d, caveat, F_BODY(32), 760, 1400, INK_SOFT)

    for i, job in enumerate(["workbench.aihub.qualcomm.com/jobs/jglxrqdmg", "workbench.aihub.qualcomm.com/jobs/j567l0xyp"]):
        w = d.textlength(job, font=F_MONO(24))
        d.text((W / 2 - w / 2, 900 + i * 36), job, font=F_MONO(24), fill=INK_SOFT)
    return img


def card_scene10() -> Image.Image:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    title = "Relay"
    w = d.textlength(title, font=F_DISPLAY(140))
    d.text((W / 2 - w / 2, 380), title, font=F_DISPLAY(140), fill=BG)
    sub = "Snapdragon AI Lab Build & Present Challenge"
    w2 = d.textlength(sub, font=F_BODY(40))
    d.text((W / 2 - w2 / 2, 560), sub, font=F_BODY(40), fill="#9FB3AC")
    return img


CARDS = {
    "scene02": card_scene02,
    "scene03": card_scene03,
    "scene07": card_scene07,
    "scene08": card_scene08,
    "scene10": card_scene10,
}


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for scene_id, builder in CARDS.items():
        img = builder()
        out_path = os.path.join(OUT_DIR, f"{scene_id}.png")
        img.save(out_path)
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
