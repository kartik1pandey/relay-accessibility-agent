"""
record_live_scenes.py — real screen recordings of the demo's live,
scriptable moments (Scenes 5 and 6 in DEMO_SCRIPT.md), using ffmpeg's
ddagrab (DXGI Desktop Duplication) to capture the monitor, cropped down to
just the target window's own rectangle.

Why cropped-window capture, not full-desktop: this machine had a live,
active WhatsApp video call surface itself as the foreground window twice
during earlier attempts, despite passing a point-in-time "is the screen
clear" check each time — a one-off check can't guard against something
that resurfaces mid-recording. The fix here is structural, not timing-
based: the target window is pinned HWND_TOPMOST and continuously
re-asserted for the whole recording (a merely-foregrounded call window,
not itself marked topmost, can't get above it), AND the final output is
cropped to exactly that window's rectangle — so even in the worst case,
nothing outside that rectangle can appear in the recording regardless of
what else is happening on the rest of the screen.

Two other real findings from building this:
- gdigrab (BitBlt-based desktop/window capture) recorded both Windows
  Terminal and conhost.exe as a solid black content pane on this machine —
  DWM-composited/hardware-accelerated console rendering doesn't reach
  BitBlt capture here. ddagrab (DXGI Desktop Duplication) captures the
  real composited framebuffer correctly.
- A freshly spawned console's visible window belongs to a different
  process (Windows Terminal or conhost) than the python.exe PID that
  launched it, so foregrounding must match by window title, not PID.

Run one scene at a time:
    python record_live_scenes.py notepad
    python record_live_scenes.py browser
"""

import ctypes
import subprocess
import sys
import threading
import time
from ctypes import wintypes

FFMPEG = r"C:\Users\karti\tools\ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
CLIPS_DIR = r"D:\Qualcomm\demo\clips"
QUALCOMM_PYTHON = r"C:\Users\karti\.venvs\qualcomm312\Scripts\python.exe"
AGENT_DIR = r"D:\Qualcomm\agent"

user32 = ctypes.windll.user32
shcore = ctypes.windll.shcore
shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE — makes
# GetWindowRect return true physical pixels, matching what ddagrab
# actually captures (this machine runs at 125% scaling: 1536x864 logical
# vs. 1920x1080 physical — without this call the two coordinate spaces
# silently mismatch and the crop rectangle lands in the wrong place).

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SW_MAXIMIZE = 3

_WINDOW_TITLE = "RelayDemoRecording"
_SET_TITLE = f"$host.UI.RawUI.WindowTitle = '{_WINDOW_TITLE}';"


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def _find_window_by_title(title_substring: str, retries: int = 30, delay: float = 0.3):
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    found = []

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if title_substring.lower() in buf.value.lower():
            found.append(hwnd)
            return False
        return True

    proc = EnumWindowsProc(_callback)
    for _ in range(retries):
        found.clear()
        user32.EnumWindows(proc, 0)
        if found:
            return found[0]
        time.sleep(delay)
    return None


def _pin_topmost(hwnd) -> None:
    user32.ShowWindow(hwnd, SW_MAXIMIZE)
    user32.SetForegroundWindow(hwnd)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)


def _unpin_topmost(hwnd) -> None:
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)


def _window_rect(hwnd) -> tuple:
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


class _TopmostGuard:
    """Re-asserts HWND_TOPMOST every 0.4s for as long as it's running —
    a single call at launch isn't enough if something else (e.g. a call
    app) later steals foreground; this keeps winning that fight for the
    whole recording."""

    def __init__(self, hwnd):
        self.hwnd = hwnd
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            _pin_topmost(self.hwnd)
            self._stop.wait(0.4)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)
        _unpin_topmost(self.hwnd)


def _run_visible_terminal(command: str) -> subprocess.Popen:
    return subprocess.Popen(
        ["conhost.exe", "powershell.exe", "-NoProfile", "-NoExit", "-Command", command],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


MONITOR_W, MONITOR_H = 1920, 1080  # physical pixels — see the DPI-awareness note above


def _record_cropped(output_path: str, duration: float, rect: tuple) -> subprocess.Popen:
    left, top, right, bottom = rect
    # A maximized window's GetWindowRect can extend slightly past the real
    # screen (invisible resize-border padding, e.g. -9..1929 on a
    # 1920-wide screen) — clamp to the actual captured frame so the crop
    # filter gets valid, in-bounds parameters instead of silently failing.
    left = max(0, left)
    top = max(0, top)
    right = min(MONITOR_W, right)
    bottom = min(MONITOR_H, bottom)
    w, h = right - left, bottom - top
    w -= w % 2  # libx264 requires even width/height
    h -= h % 2
    vf = f"hwdownload,format=bgra,crop={w}:{h}:{left}:{top}"
    proc = subprocess.Popen(
        [
            FFMPEG, "-y",
            "-f", "lavfi", "-i", f"ddagrab=output_idx=0,{vf}",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            output_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def record_notepad_scene(duration: float = 25.0) -> None:
    out_path = rf"{CLIPS_DIR}\scene05_raw.mp4"
    cmd = f'{_SET_TITLE} cd "{AGENT_DIR}"; & "{QUALCOMM_PYTHON}" demo_integration_notepad.py'
    term_proc = _run_visible_terminal(cmd)
    try:
        _record_one_window(_WINDOW_TITLE, out_path, duration)
    finally:
        term_proc.terminate()
    print("Done.")


def _record_one_window(title_substring: str, out_path: str, duration: float, existing_proc=None) -> None:
    hwnd = _find_window_by_title(title_substring)
    if hwnd is None:
        raise RuntimeError(f"No window matching {title_substring!r} found.")
    guard = _TopmostGuard(hwnd)
    guard.start()
    time.sleep(0.5)
    rect = _window_rect(hwnd)
    print(f"{title_substring!r} window rect (physical px): {rect}")
    print(f"Recording (window-cropped) for {duration}s -> {out_path}")
    ffmpeg_proc = _record_cropped(out_path, duration, rect)
    output, _ = ffmpeg_proc.communicate()
    guard.stop()
    if ffmpeg_proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (code {ffmpeg_proc.returncode}):\n{output[-3000:]}")


def record_browser_scene(terminal_duration: float = 30.0, edge_duration: float = 8.0) -> None:
    terminal_clip = rf"{CLIPS_DIR}\scene06_terminal_raw.mp4"
    edge_clip = rf"{CLIPS_DIR}\scene06_edge_raw.mp4"
    out_path = rf"{CLIPS_DIR}\scene06_raw.mp4"

    cmd = f'{_SET_TITLE} cd "{AGENT_DIR}"; & "{QUALCOMM_PYTHON}" demo_integration_browser_cdp.py'
    term_proc = _run_visible_terminal(cmd)
    try:
        _record_one_window(_WINDOW_TITLE, terminal_clip, terminal_duration)
    finally:
        term_proc.terminate()

    # The demo script has now run for real (Wikipedia navigated, real
    # set_text write done) — a short second cropped capture of the live
    # Edge window shows the actual "Snapdragon" text that landed, not
    # just the terminal's own confirmation line.
    _record_one_window("Wikipedia", edge_clip, edge_duration)

    concat_list = rf"{CLIPS_DIR}\scene06_concat.txt"
    with open(concat_list, "w") as f:
        f.write(f"file '{terminal_clip}'\nfile '{edge_clip}'\n")
    subprocess.run(
        [
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-vf", "scale=1920:1080,setsar=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            out_path,
        ],
        check=True,
    )
    print("Done.")


SCENES = {
    "notepad": record_notepad_scene,
    "browser": record_browser_scene,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in SCENES:
        print(f"Usage: python record_live_scenes.py {{{'|'.join(SCENES)}}}")
        sys.exit(1)
    SCENES[sys.argv[1]]()
