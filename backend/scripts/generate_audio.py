"""
scripts/generate_audio.py
--------------------------
Generates static WAV audio files for MatrAI using Sarvam AI's
Text-to-Speech API (Bulbul v3 model).

Files generated (saved to static/):
  - greeting_hi.wav  — Hindi welcome message
  - consent_hi.wav   — Hindi consent prompt (TRAI IVR standard)

Usage:
    # From the backend/ directory with venv activated:
    python scripts/generate_audio.py

    # Or with explicit API key override:
    SARVAM_API_KEY=sk-xxx python scripts/generate_audio.py

Requirements:
    - SARVAM_API_KEY set in .env (or environment)
    - sarvamai SDK  (pip install -U sarvamai)
    - pydantic-settings, python-dotenv  (already in requirements.txt)

References:
    Sarvam TTS REST API — https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/text-to-speech/rest-api
    Bulbul v3 model    — https://docs.sarvam.ai/api-reference-docs/getting-started/models/bulbul
"""

from __future__ import annotations

import base64
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the backend root is on sys.path so app.config is importable
# when this script is run from either backend/ or its parent.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent   # .../backend/
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402  (path set above)

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
STATIC_DIR = ROOT / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Audio clips to generate
# ---------------------------------------------------------------------------

@dataclass
class AudioClip:
    """Represents a single TTS generation task."""
    filename: str           # output filename (no extension)
    text: str               # text to synthesise
    language_code: str      # Sarvam BCP-47 code, e.g. "hi-IN"
    speaker: str            # Sarvam speaker name
    pace: float = 0.95      # 0.5–2.0; slightly slower for IVR clarity
    model: str = "bulbul:v3"


CLIPS: list[AudioClip] = [
    AudioClip(
        filename="greeting_hi",
        text=(
            "Namaste, MatrAI mein aapka swagat hai. "
            "Main ek sahayak hoon jo garbhavastha aur mahila swasthya mein "
            "aapki madad karti hoon. Kripya apni baat shuru karein."
        ),
        language_code="hi-IN",
        speaker="anushka",   # warm female voice — appropriate for healthcare IVR
        pace=0.90,           # slightly slower for first-time callers
    ),
    AudioClip(
        filename="consent_hi",
        text=(
            "Hum is call ko record karenge taaki doctor ise dekh sakein. "
            "Sehmati dene ke liye 1 dabayein, anyatha 2 dabayein."
        ),
        language_code="hi-IN",
        speaker="anushka",
        pace=0.88,           # consent must be clearly audible
    ),
]


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------

def _decode_and_save(audio_base64: str, output_path: Path) -> None:
    """Decode a base64 WAV string from Sarvam and write it to disk."""
    audio_bytes = base64.b64decode(audio_base64)
    output_path.write_bytes(audio_bytes)
    size_kb = len(audio_bytes) / 1024
    print(f"  ✓ Saved: {output_path.relative_to(ROOT)}  ({size_kb:.1f} KB)")


def generate_clip(client, clip: AudioClip) -> Path:
    """
    Call the Sarvam TTS REST API for a single AudioClip and save the result.

    Args:
        client: An authenticated SarvamAI client instance.
        clip:   The AudioClip definition to generate.

    Returns:
        Path to the saved .wav file.

    Raises:
        RuntimeError: If the API response contains no audio data.
    """
    output_path = STATIC_DIR / f"{clip.filename}.wav"

    print(f"\n[{clip.filename}]")
    print(f"  Language : {clip.language_code}")
    print(f"  Speaker  : {clip.speaker}")
    print(f"  Pace     : {clip.pace}")
    print(f"  Text     : {clip.text[:80]}{'...' if len(clip.text) > 80 else ''}")
    print(f"  Calling Sarvam TTS API (model={clip.model}) ...")

    response = client.text_to_speech.convert(
        target_language_code=clip.language_code,
        text=clip.text,
        model=clip.model,
        speaker=clip.speaker,
        pace=clip.pace,
    )

    # The SDK returns an object with an `audios` list of base64-encoded strings
    if not response.audios:
        raise RuntimeError(
            f"Sarvam API returned no audio data for clip '{clip.filename}'. "
            f"Full response: {response}"
        )

    _decode_and_save(response.audios[0], output_path)
    return output_path


def main() -> None:
    """Entry point: load settings, build client, generate all clips."""
    print("=" * 60)
    print("  MatrAI — Static Audio Generator (Sarvam AI Bulbul v3)")
    print("=" * 60)

    # Load credentials from .env via Pydantic settings
    settings = get_settings()

    if not settings.sarvam_api_key or settings.sarvam_api_key.startswith("your_"):
        print(
            "\n⚠  SARVAM_API_KEY is not set or still a placeholder.\n"
            "   Add your real key to backend/.env and re-run.\n"
        )
        sys.exit(1)

    # Import here so the script is importable even without sarvamai installed
    try:
        from sarvamai import SarvamAI  # noqa: PLC0415
    except ImportError:
        print(
            "\n✗ sarvamai is not installed.\n"
            "  Run:  pip install -U sarvamai\n"
        )
        sys.exit(1)

    client = SarvamAI(api_subscription_key=settings.sarvam_api_key)

    generated: list[Path] = []
    errors: list[tuple[str, Exception]] = []

    for clip in CLIPS:
        try:
            path = generate_clip(client, clip)
            generated.append(path)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ FAILED — {exc}")
            errors.append((clip.filename, exc))

    # Summary
    print("\n" + "=" * 60)
    print(f"  Done.  {len(generated)}/{len(CLIPS)} clip(s) generated successfully.")
    if generated:
        print("\n  Generated files:")
        for p in generated:
            print(f"    • {p.relative_to(ROOT)}")
    if errors:
        print("\n  Failed clips:")
        for name, err in errors:
            print(f"    ✗ {name}: {err}")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
