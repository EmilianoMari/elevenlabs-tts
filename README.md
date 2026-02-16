# ElevenLabs TTS Proxy

FastAPI proxy server for ElevenLabs text-to-speech API.

## Features

- **Turbo v2.5** - Ultra-fast, low-latency synthesis
- **Multilingual v3** - High-quality expressive voices
- **Streaming support** - Real-time audio generation
- **Voice cloning** - Use any ElevenLabs voice ID
- **API key security** - Hides ElevenLabs API key from frontend

## Configuration

Set `ELEVENLABS_API_KEY` environment variable:

```bash
export ELEVENLABS_API_KEY=your_api_key_here
```

## Endpoints

- `GET /health` - Health check
- `GET /languages` - List supported languages
- `GET /voices?language=it` - List available voices
- `POST /synthesize` - Generate complete audio
- `POST /synthesize/stream` - Stream audio chunks

## Models

- `turbo` - ElevenLabs Turbo v2.5 (fastest, lowest latency)
- `multilingual` - ElevenLabs Multilingual v3 (highest quality, expressive)

## Example

```bash
curl -X POST http://localhost:8005/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Ciao, sono ElevenLabs!",
    "language": "it",
    "voice": "zcAOhNBS3c14rBihAFp1",
    "model": "turbo",
    "stability": 0.5,
    "similarity_boost": 0.75
  }' \
  --output audio.mp3
```

## Default Voices

### Italian
- Giovanni (M) - `zcAOhNBS3c14rBihAFp1`
- Matilda (F) - `XrExE9yKIg1WjnnlVkGX`

### English
- Rachel (F) - `21m00Tcm4TlvDq8ikWAM`
- Drew (M) - `29vD33N1CtxCmqQRPOHJ`
- Clyde (M) - `2EiwWnXFnvU5JabPnv8n`
- And more...

## Production Deployment

The service will be deployed via GitHub Actions to Nomad cluster with:
- Encrypted API key via Nomad secrets
- Public exposure via Traefik
- CORS enabled for tts-web frontend

## License

Part of Agent24 TTS infrastructure.
