"""
assemble_video.py — combines everything demo/ has built (title cards +
narration for the non-live scenes, real screen recordings + narration for
the live scenes) into per-scene clips at a uniform 1920x1080/30fps/h264+aac
format, then concatenates them in DEMO_SCRIPT.md order into one final
RELAY_DEMO.mp4.

For a title-card scene: loops the still PNG for exactly as long as its
narration audio runs.
For a live-recording scene: uses the real screen capture as the video
track and the narration as the audio track, padding whichever of the two
is shorter (freezing the last video frame, or trailing silence) so neither
gets cut off.

Run: python assemble_video.py
"""

import json
import os
import subprocess

FFMPEG = r"C:\Users\karti\tools\ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
FFPROBE = r"C:\Users\karti\tools\ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffprobe.exe"

BASE = os.path.dirname(__file__)
NARRATION_DIR = os.path.join(BASE, "narration")
CARDS_DIR = os.path.join(BASE, "cards")
CLIPS_DIR = os.path.join(BASE, "clips")
OUT_PATH = os.path.join(BASE, "RELAY_DEMO.mp4")

W, H, FPS = 1920, 1080, 30

# Scene order matches DEMO_SCRIPT.md. "card" scenes use a still PNG;
# "live" scenes use a real screen recording (scene05_raw.mp4 / scene06_raw.mp4).
SCENES = [
    ("scene02", "card"),
    ("scene03", "card"),
    ("scene05", "live"),
    ("scene06", "live"),
    ("scene07", "card"),
    ("scene08", "card"),
    ("scene10", "card"),
]


def _duration(path: str) -> float:
    out = subprocess.check_output([
        FFPROBE, "-v", "error", "-show_entries", "format=duration",
        "-of", "json", path,
    ])
    return float(json.loads(out)["format"]["duration"])


def _build_card_clip(scene_id: str) -> str:
    png = os.path.join(CARDS_DIR, f"{scene_id}.png")
    wav = os.path.join(NARRATION_DIR, f"{scene_id}.wav")
    out = os.path.join(CLIPS_DIR, f"{scene_id}_final.mp4")
    subprocess.run([
        FFMPEG, "-y",
        "-loop", "1", "-i", png,
        "-i", wav,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-vf", f"scale={W}:{H}", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        out,
    ], check=True)
    return out


def _build_live_clip(scene_id: str) -> str:
    raw_video = os.path.join(CLIPS_DIR, f"{scene_id}_raw.mp4")
    wav = os.path.join(NARRATION_DIR, f"{scene_id}.wav")
    out = os.path.join(CLIPS_DIR, f"{scene_id}_final.mp4")

    video_dur = _duration(raw_video)
    audio_dur = _duration(wav)
    pad = max(0.0, audio_dur - video_dur)

    # Freeze the last frame to cover any gap if narration runs longer than
    # the raw capture; real captures were sized generously so this is
    # normally a small or zero pad, not a stretch.
    vf = f"scale={W}:{H},tpad=stop_mode=clone:stop_duration={pad:.2f}" if pad > 0 else f"scale={W}:{H}"

    subprocess.run([
        FFMPEG, "-y",
        "-i", raw_video,
        "-i", wav,
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", vf, "-r", str(FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        out,
    ], check=True)
    return out


def main() -> None:
    os.makedirs(CLIPS_DIR, exist_ok=True)
    clip_paths = []
    for scene_id, kind in SCENES:
        print(f"--- building {scene_id} ({kind}) ---")
        if kind == "card":
            path = _build_card_clip(scene_id)
        else:
            path = _build_live_clip(scene_id)
        clip_paths.append(path)
        print(f"    {path}  ({_duration(path):.1f}s)")

    concat_list_path = os.path.join(CLIPS_DIR, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    print("--- concatenating final video ---")
    subprocess.run([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-c", "copy",
        OUT_PATH,
    ], check=True)
    print(f"Final video: {OUT_PATH}  ({_duration(OUT_PATH):.1f}s)")


if __name__ == "__main__":
    main()
