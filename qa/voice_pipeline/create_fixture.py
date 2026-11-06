"""Create the deterministic non-speech WAV used by browser pipeline tests."""

import math
import struct
import wave
from pathlib import Path


OUTPUT = Path(__file__).parent / "fixtures" / "pipeline_tone.wav"
SAMPLE_RATE = 24000
DURATION_SECONDS = 1.0
FREQUENCY_HZ = 440


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(SAMPLE_RATE * DURATION_SECONDS)
    with wave.open(str(OUTPUT), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for index in range(frame_count):
            ramp = min(1.0, index / 240, (frame_count - index) / 240)
            sample = int(8000 * ramp * math.sin(2 * math.pi * FREQUENCY_HZ * index / SAMPLE_RATE))
            frames.extend(struct.pack("<h", sample))
        wav.writeframes(frames)
    print("Wrote", OUTPUT)


if __name__ == "__main__":
    main()
