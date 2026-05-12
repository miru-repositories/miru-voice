"""Debug helper: prints every key press/release with raw key info to a log file.

Run, press some keys, then check the log to see what pynput reports.
Stops after 60 seconds or after pressing Esc.
"""
import time
from pathlib import Path
from pynput import keyboard

LOG = Path(__file__).parent.parent / "debug_keys.log"
START = time.time()


def fmt(key):
    try:
        return f"{key!r} (vk={getattr(key, 'vk', '?')})"
    except Exception:
        return repr(key)


def on_press(key):
    msg = f"[{time.time()-START:6.2f}s] PRESS  {fmt(key)}\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg)
    if key == keyboard.Key.esc:
        return False


def on_release(key):
    msg = f"[{time.time()-START:6.2f}s] RELEASE {fmt(key)}\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg)


LOG.write_text(f"# Started at {time.ctime()}\n# Press Esc to stop, or wait 60s.\n", encoding="utf-8")
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

end_at = time.time() + 60
while time.time() < end_at and listener.is_alive():
    time.sleep(0.5)
listener.stop()

with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"# Stopped at {time.ctime()}\n")
