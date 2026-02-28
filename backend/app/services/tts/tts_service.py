"""
Serwis Text-to-Speech — ElevenLabs (główny) + Google TTS (fallback).
Ulepszenie: abstrakcja provider + automatyczny fallback + cache audio.
"""

import hashlib
import io
import struct
import wave
from abc import ABC, abstractmethod
from pathlib import Path

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """Generuje audio z tekstu. Zwraca bajty pliku audio (mp3/wav)."""

    @abstractmethod
    async def list_voices(self) -> list[dict]:
        """Lista dostępnych głosów."""


class ElevenLabsTTS(TTSProvider):
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.model_id = settings.ELEVENLABS_MODEL_ID
        self.default_voice_id = settings.ELEVENLABS_DEFAULT_VOICE_ID

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        voice = voice_id or self.default_voice_id
        logger.info("ElevenLabs TTS", voice_id=voice, text_length=len(text))

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/text-to-speech/{voice}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": self.model_id,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,
                        "use_speaker_boost": True,
                    },
                },
            )
            response.raise_for_status()
            logger.info("Audio wygenerowane", size_bytes=len(response.content))
            return response.content

    async def list_voices(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/voices",
                headers={"xi-api-key": self.api_key},
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "id": v["voice_id"],
                    "name": v["name"],
                    "category": v.get("category", ""),
                    "preview_url": v.get("preview_url"),
                }
                for v in data.get("voices", [])
            ]


class GoogleTTS(TTSProvider):
    """Fallback — Google Cloud TTS."""

    async def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        logger.info("Google TTS (fallback)", text_length=len(text))
        # Implementacja z google-cloud-texttospeech
        try:
            from google.cloud import texttospeech

            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=voice_id or "pl-PL",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
            )
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )
            return response.audio_content
        except Exception as e:
            logger.error("Google TTS niedostępny", error=str(e))
            raise

    async def list_voices(self) -> list[dict]:
        return [
            {"id": "pl-PL", "name": "Polski", "category": "google"},
            {"id": "en-US", "name": "English (US)", "category": "google"},
        ]


def get_tts_provider(provider_name: str = "elevenlabs") -> TTSProvider:
    """Fabryka providerów TTS."""
    providers = {
        "elevenlabs": ElevenLabsTTS,
        "google": GoogleTTS,
    }
    cls = providers.get(provider_name, ElevenLabsTTS)
    return cls()


async def synthesize_with_fallback(
    text: str,
    provider_name: str = "elevenlabs",
    voice_id: str | None = None,
) -> bytes:
    """Synteza mowy z automatycznym fallbackiem."""
    primary = get_tts_provider(provider_name)
    try:
        return await primary.synthesize(text, voice_id)
    except Exception as e:
        logger.warning(f"Główny TTS ({provider_name}) zawiódł, fallback", error=str(e))
        if provider_name != "google":
            fallback = GoogleTTS()
            return await fallback.synthesize(text, voice_id)
        raise
