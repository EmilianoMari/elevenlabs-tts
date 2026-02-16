"""
ElevenLabs TTS Proxy Server
FastAPI proxy for ElevenLabs API with support for Turbo v2.5 and Multilingual v3.
Hides API key from frontend.
"""

import asyncio
import logging
import os
import struct
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ElevenLabs configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Model IDs
MODEL_TURBO_V2_5 = "eleven_turbo_v2_5"
MODEL_MULTILINGUAL_V3 = "eleven_multilingual_v2"  # v3 is branded as v2 in API

# Supported languages (subset for UI)
SUPPORTED_LANGUAGES = {
    "it": "Italian",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "pt": "Portuguese",
    "pl": "Polish",
    "nl": "Dutch",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "ru": "Russian",
    "hi": "Hindi",
    "tr": "Turkish",
}

# Popular ElevenLabs voices
DEFAULT_VOICES = {
    "en": [
        {"name": "Rachel (F)", "id": "21m00Tcm4TlvDq8ikWAM"},
        {"name": "Drew (M)", "id": "29vD33N1CtxCmqQRPOHJ"},
        {"name": "Clyde (M)", "id": "2EiwWnXFnvU5JabPnv8n"},
        {"name": "Paul (M)", "id": "5Q0t7uMcjvnagumLfvZi"},
        {"name": "Domi (F)", "id": "AZnzlk1XvdvUeBnXmlld"},
        {"name": "Dave (M)", "id": "CYw3kZ02Hs0563khs1Fj"},
        {"name": "Fin (M)", "id": "D38z5RcWu1voky8WS1ja"},
        {"name": "Sarah (F)", "id": "EXAVITQu4vr4xnSDxMaL"},
        {"name": "Antoni (M)", "id": "ErXwobaYiN019PkySvjV"},
        {"name": "Thomas (M)", "id": "GBv7mTt0atIp3BR8iCZE"},
    ],
    "it": [
        {"name": "Giovanni (M)", "id": "zcAOhNBS3c14rBihAFp1"},
        {"name": "Matilda (F)", "id": "XrExE9yKIg1WjnnlVkGX"},
    ],
}

# HTTP client
http_client: httpx.AsyncClient | None = None


# ── Lifespan ──────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    logger.info("Starting ElevenLabs TTS Proxy Server...")

    if not ELEVENLABS_API_KEY:
        logger.error("ELEVENLABS_API_KEY environment variable not set!")
        logger.warning("Server will start but API calls will fail.")
    else:
        logger.info("ElevenLabs API key configured")

    # Create HTTP client for API calls
    http_client = httpx.AsyncClient(timeout=60.0)

    logger.info("Server ready")
    yield

    logger.info("Shutting down...")
    if http_client:
        await http_client.aclose()


app = FastAPI(
    title="ElevenLabs TTS Proxy API",
    description="Proxy for ElevenLabs API (Turbo v2.5 + Multilingual v3)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────


class SynthesizeRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    language: str = Field(default="en", description="Language code (ISO 639-1)")
    voice: str | None = Field(default=None, description="Voice ID (ElevenLabs voice ID)")
    model: str = Field(default="turbo", description="Model: 'turbo' (v2.5) or 'multilingual' (v3)")
    stability: float = Field(default=0.5, ge=0.0, le=1.0, description="Voice stability (0-1)")
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0, description="Clarity + similarity (0-1)")


class LanguageInfo(BaseModel):
    code: str
    name: str


class VoiceInfo(BaseModel):
    name: str
    file: str  # Using 'file' field for voice_id to match other backends


# ── Endpoints ─────────────────────────────────────────────────────────────


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model": "elevenlabs-proxy",
        "api_key_configured": bool(ELEVENLABS_API_KEY),
    }


@app.get("/languages", response_model=list[LanguageInfo])
async def list_languages():
    return [LanguageInfo(code=code, name=name) for code, name in SUPPORTED_LANGUAGES.items()]


@app.get("/voices", response_model=list[VoiceInfo])
async def list_voices(language: str | None = None):
    """List available ElevenLabs voices (subset of popular voices)."""
    result = []

    if language and language in DEFAULT_VOICES:
        for v in DEFAULT_VOICES[language]:
            result.append(VoiceInfo(name=v["name"], file=v["id"]))
    else:
        # Return all voices
        for lang_voices in DEFAULT_VOICES.values():
            for v in lang_voices:
                result.append(VoiceInfo(name=v["name"], file=v["id"]))

    return result


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=503, detail="ElevenLabs API key not configured")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Select model
    model_id = MODEL_TURBO_V2_5 if request.model == "turbo" else MODEL_MULTILINGUAL_V3

    # Select voice (default to Rachel for English, Giovanni for Italian)
    voice_id = request.voice
    if not voice_id:
        if request.language == "it":
            voice_id = "zcAOhNBS3c14rBihAFp1"  # Giovanni
        else:
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    # Prepare ElevenLabs API request
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": request.text,
        "model_id": model_id,
        "voice_settings": {
            "stability": request.stability,
            "similarity_boost": request.similarity_boost,
        },
    }

    try:
        response = await http_client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        # Return audio directly
        return Response(content=response.content, media_type="audio/mpeg")

    except httpx.HTTPStatusError as e:
        logger.exception(f"ElevenLabs API error: {e.response.status_code}")
        error_detail = e.response.text
        raise HTTPException(status_code=e.response.status_code, detail=f"ElevenLabs API error: {error_detail}")
    except Exception as e:
        logger.exception("Synthesis error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize/stream")
async def synthesize_stream(request: SynthesizeRequest):
    """Streaming TTS via ElevenLabs streaming endpoint."""
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=503, detail="ElevenLabs API key not configured")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    model_id = MODEL_TURBO_V2_5 if request.model == "turbo" else MODEL_MULTILINGUAL_V3

    voice_id = request.voice
    if not voice_id:
        if request.language == "it":
            voice_id = "zcAOhNBS3c14rBihAFp1"
        else:
            voice_id = "21m00Tcm4TlvDq8ikWAM"

    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": request.text,
        "model_id": model_id,
        "voice_settings": {
            "stability": request.stability,
            "similarity_boost": request.similarity_boost,
        },
    }

    async def audio_generator():
        try:
            async with http_client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()

                # Stream audio chunks from ElevenLabs
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    if chunk:
                        # Length-prefix format for consistency with other backends
                        yield struct.pack('<I', len(chunk)) + chunk

            # End-of-stream signal
            yield struct.pack('<I', 0)

        except httpx.HTTPStatusError as e:
            logger.exception(f"ElevenLabs streaming error: {e.response.status_code}")
        except Exception as e:
            logger.exception("Stream error")

    return StreamingResponse(
        audio_generator(),
        media_type="application/octet-stream",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
