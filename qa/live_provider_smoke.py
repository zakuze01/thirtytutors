"""Explicit, quota-consuming provider smoke; never part of automated unit tests.

Reads COMPANION_GEMINI_API_KEY from the environment. Saves only result metadata,
never credentials, transcripts or PCM. Does not test microphone/playback quality.
"""

import argparse
import asyncio
import importlib.metadata
import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types


async def probe(model, voice):
    key = os.environ.get("COMPANION_GEMINI_API_KEY")
    if not key:
        return {"status": "INCONCLUSIVE", "reason": "missing environment key"}
    started = time.perf_counter()
    audio_bytes = 0
    client = genai.Client(api_key=key)
    try:
        async with asyncio.timeout(45):
            async with client.aio.live.connect(
                model=model,
                config=types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    system_instruction="You are an AI English practice partner. Be concise.",
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))
                    ),
                ),
            ) as session:
                await session.send_client_content(
                    turns=[{"role": "user", "parts": [{"text": "Say one short greeting in English."}]}], turn_complete=True
                )
                async for message in session.receive():
                    content = message.server_content
                    if content and content.model_turn:
                        for part in content.model_turn.parts or []:
                            if part.inline_data and part.inline_data.data:
                                audio_bytes += len(part.inline_data.data)
        return {
            "status": "PASS" if audio_bytes else "FAIL",
            "audio_bytes_received": audio_bytes,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "scope": "provider text-to-audio transport only; not spoken bilingual acceptance",
        }
    except Exception as error:
        # Provider exception text may include credentials/request data. Do not serialize it.
        return {"status": "FAIL", "error_type": type(error).__name__}
    finally:
        await client.aio.aclose()
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-paid-api", action="store_true", help="Explicitly authorize this run to use API quota")
    parser.add_argument("--model", required=True, help="Currently available Live model ID for your key")
    parser.add_argument("--voice", default="Zephyr")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_paid_api:
        parser.error("Live requests are opt-in; pass --allow-paid-api to authorize quota use")
    result = asyncio.run(probe(args.model, args.voice))
    result.update(model=args.model, voice=args.voice, sdk=importlib.metadata.version("google-genai"))
    args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["status"])
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
