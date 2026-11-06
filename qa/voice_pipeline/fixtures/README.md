# Test audio fixture

`pipeline_tone.wav` is generated locally by `python create_fixture.py`. It is
mono, 24 kHz, PCM16, one second long, and contains a 440 Hz tone with short
ramps at both ends. It contains no voice, personal data, or external recording.

The Playwright Live test uses it only to prove that the browser recorder sends
non-empty audio bytes to both scripted upstream doubles. The upload double
returns fixed reference text regardless of audio. These are deterministic UI
and transport checks; they do not test speech recognition or translation
quality.
