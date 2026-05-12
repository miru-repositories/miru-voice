"""Debug helper: records 3 seconds of audio and prints RMS / chunk count.

If RMS is near 0 → mic silent / wrong device / WASAPI exclusive blocking.
If chunk count is 0 → capture loop never produced anything (stream open failed).
"""
import asyncio
import sys
import numpy as np
import sounddevice as sd

from dictado.audio_capture import AudioCapture


async def main():
    print("=== Available input devices ===", flush=True)
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            mark = " (default)" if i == sd.default.device[0] else ""
            print(f"  [{i}] {d['name']}{mark}  in={d['max_input_channels']}", flush=True)

    print("\n=== Recording 3 seconds via AudioCapture ===", flush=True)
    cap = AudioCapture()
    chunks = []
    async for chunk in cap.stream(duration=3.0):
        chunks.append(chunk)

    print(f"\n=== Result ===", flush=True)
    print(f"chunks received: {len(chunks)}", flush=True)
    if chunks:
        audio = np.concatenate(chunks)
        rms = float(np.sqrt((audio ** 2).mean()))
        peak = float(np.abs(audio).max())
        print(f"total samples: {len(audio)} ({len(audio)/16000:.2f}s)", flush=True)
        print(f"RMS:  {rms:.4f}  (threshold for non-silence: 0.005)", flush=True)
        print(f"Peak: {peak:.4f}", flush=True)
        if rms < 0.005:
            print(">>> mic appears SILENT — would be skipped by orchestrator", flush=True)
        else:
            print(">>> mic captured speech — orchestrator should transcribe", flush=True)
    else:
        print(">>> ZERO chunks received — WASAPI/device error", flush=True)


asyncio.run(main())
