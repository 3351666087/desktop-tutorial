#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys

from faster_whisper import WhisperModel


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "missing_audio_path"}, ensure_ascii=False))
        return 2

    audio_path = sys.argv[1]
    model_size = os.environ.get("SMARTCLASSROOM_WHISPER_MODEL", "base")
    device = os.environ.get("SMARTCLASSROOM_WHISPER_DEVICE", "cuda")
    compute_type = os.environ.get("SMARTCLASSROOM_WHISPER_COMPUTE", "float16")

    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        audio_path,
        beam_size=3,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 450},
        language=os.environ.get("SMARTCLASSROOM_WHISPER_LANGUAGE") or None,
    )
    text = "".join(segment.text for segment in segments).strip()
    print(json.dumps({
        "ok": True,
        "text": text,
        "language": info.language,
        "languageProbability": round(float(info.language_probability or 0), 4),
        "model": model_size,
        "device": device
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
