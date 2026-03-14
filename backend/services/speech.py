import os
import httpx

API_KEY = os.getenv("DEEPGRAM_API_KEY")

# Deepgram Aura TTS voices — https://developers.deepgram.com/docs/tts-models
DEEPGRAM_VOICES = {
    "asteria": "Asteria (Female, US)",
    "luna": "Luna (Female, US)",
    "stella": "Stella (Female, US)",
    "athena": "Athena (Female, UK)",
    "hera": "Hera (Female, US)",
    "orion": "Orion (Male, US)",
    "arcas": "Arcas (Male, US)",
    "perseus": "Perseus (Male, US)",
    "angus": "Angus (Male, Ireland)",
    "orpheus": "Orpheus (Male, US)",
    "helios": "Helios (Male, UK)",
    "zeus": "Zeus (Male, US)",
}

DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"


def text_to_speech(text: str, voice: str = "asteria") -> bytes:
    """Convert text to audio bytes using Deepgram Aura TTS."""
    if not API_KEY:
        raise RuntimeError("Deepgram TTS is not configured")

    if voice not in DEEPGRAM_VOICES:
        voice = "asteria"

    # Clean text for better speech
    clean = text.replace("•", "").replace("#", "").replace("*", "")

    response = httpx.post(
        DEEPGRAM_TTS_URL,
        headers={
            "Authorization": f"Token {API_KEY}",
            "Content-Type": "application/json",
        },
        json={"text": clean},
        params={"model": f"aura-{voice}-en", "encoding": "mp3"},
        timeout=15.0,
    )
    response.raise_for_status()
    return response.content


def get_voices() -> dict:
    """Return available Deepgram TTS voices."""
    return DEEPGRAM_VOICES if API_KEY else {}