"""
app/routers/voice.py
---------------------
Custom TTS endpoint for VAPI's "Custom Voice" integration.

VAPI custom voice protocol:
  POST /vapi/voice
  Body (JSON): { "text": "...", "sampleRate": 24000, ... }
  Response:    audio/wav  (raw PCM, 24kHz, 16-bit, mono)

This endpoint:
  1. Receives text from VAPI
  2. Calls Sarvam AI's Bulbul TTS API (Priya / Hindi voice)
  3. Returns raw PCM audio to VAPI

Set this URL in the VAPI dashboard:
  Custom Voice Server URL:
    https://<your-ngrok>.ngrok-free.app/vapi/voice

Sarvam TTS docs: https://docs.sarvam.ai/api-reference-docs/text-to-speech
"""

from __future__ import annotations

import base64
import logging
import struct
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vapi", tags=["Custom Voice"])

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


@router.post("/voice", summary="Custom TTS — Sarvam Priya (Hindi)")
async def custom_voice(request: Request) -> Response:
    """
    VAPI calls this endpoint when it needs speech synthesis.

    Payload from VAPI:
        { "text": "Namaste Behen...", "sampleRate": 24000 }

    Response:
        Raw PCM audio bytes (Content-Type: application/octet-stream)
        OR WAV file (Content-Type: audio/wav) — both accepted by VAPI.
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        logger.warning("Custom voice: invalid JSON payload")
        return Response(status_code=400)

    text: str = body.get("text", "").strip()
    if not text:
        logger.warning("Custom voice: empty text received")
        return Response(status_code=400)

    logger.info("Custom voice TTS: %r (len=%d)", text[:80], len(text))

    settings = get_settings()
    sarvam_key: str = getattr(settings, "sarvam_api_key", "").strip()

    if not sarvam_key:
        logger.error("SARVAM_API_KEY not set — cannot synthesise speech")
        return Response(status_code=503)

    try:
        audio_bytes = await _synthesise_sarvam(text=text, api_key=sarvam_key)
    except Exception as exc:
        logger.error("Sarvam TTS failed: %s", exc, exc_info=True)
        return Response(status_code=502)

    # VAPI expects raw PCM or WAV — return WAV for maximum compatibility
    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Content-Length": str(len(audio_bytes))},
    )


# ---------------------------------------------------------------------------
# Sarvam TTS helper
# ---------------------------------------------------------------------------

async def _synthesise_sarvam(text: str, api_key: str) -> bytes:
    """
    Call Sarvam Bulbul TTS and return WAV bytes.

    Sarvam returns base64-encoded WAV in the response.
    We decode and return the raw WAV bytes.
    """
    payload = {
        "inputs":               [text],
        "target_language_code": "hi-IN",
        "speaker":              "priya",     # priya is available only in bulbul:v3
        "pace":                 1.0,
        "speech_sample_rate":   8000,
        "model":                "bulbul:v3",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            SARVAM_TTS_URL,
            headers={
                "api-subscription-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if not resp.is_success:
            logger.error("Sarvam TTS HTTP %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()

    data = resp.json()
    # Sarvam returns: { "audios": ["<base64-wav>", ...] }
    audios: list = data.get("audios", [])
    if not audios:
        raise ValueError(f"Sarvam returned no audio: {data}")

    wav_bytes: bytes = base64.b64decode(audios[0])
    logger.info("Sarvam TTS: synthesised %d bytes of WAV audio", len(wav_bytes))
    return wav_bytes
