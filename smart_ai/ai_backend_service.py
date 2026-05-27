#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - Python 3.8 compatibility fallback.
    ZoneInfo = None


WHISPER_MODEL = None
TORCH = None
PREFERENCE_DEVICE = "cpu"

MODEL_INFO: dict = {
    "status": "booting",
    "torchLoaded": False,
    "cuda": False,
    "device": "unknown",
    "whisperLoaded": False,
    "whisperModel": "",
    "whisperDevice": "",
    "computeType": "",
    "preferenceLoaded": False,
    "preferenceDevice": "cpu",
    "qwenReady": False,
    "lastError": "",
}

QWEN_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
QWEN_DEFAULT_MODEL = "qwen3.6-plus"


def note_error(prefix: str, exc: Exception | str) -> None:
    current = str(MODEL_INFO.get("lastError") or "").strip()
    text = f"{prefix}:{exc}"
    MODEL_INFO["lastError"] = f"{current} {text}".strip()


def load_backend() -> None:
    global WHISPER_MODEL, TORCH, PREFERENCE_DEVICE
    started = time.time()
    MODEL_INFO.update({
        "status": "loading",
        "torchLoaded": False,
        "cuda": False,
        "device": "unknown",
        "whisperLoaded": False,
        "whisperModel": "",
        "whisperDevice": "",
        "computeType": "",
        "preferenceLoaded": False,
        "preferenceDevice": "cpu",
        "qwenReady": False,
        "lastError": "",
    })

    try:
        import torch

        TORCH = torch
        MODEL_INFO["torchLoaded"] = True
        MODEL_INFO["torchVersion"] = torch.__version__
        MODEL_INFO["cuda"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            MODEL_INFO["device"] = torch.cuda.get_device_name(0)
            _ = torch.zeros((32, 32), device="cuda")
            PREFERENCE_DEVICE = "cuda"
        else:
            MODEL_INFO["device"] = "cpu"
            PREFERENCE_DEVICE = "cpu"
        MODEL_INFO["preferenceLoaded"] = True
        MODEL_INFO["preferenceDevice"] = PREFERENCE_DEVICE
    except Exception as exc:
        note_error("torch", exc)
        TORCH = None
        PREFERENCE_DEVICE = "cpu"

    try:
        from faster_whisper import WhisperModel

        model_size = os.environ.get("SMARTCLASSROOM_WHISPER_MODEL", "base")
        preferred_device = os.environ.get("SMARTCLASSROOM_WHISPER_DEVICE", "cuda" if MODEL_INFO.get("cuda") else "cpu")
        compute_type = os.environ.get("SMARTCLASSROOM_WHISPER_COMPUTE", "float16" if preferred_device == "cuda" else "int8")
        try:
            WHISPER_MODEL = WhisperModel(model_size, device=preferred_device, compute_type=compute_type)
            MODEL_INFO.update({
                "whisperLoaded": True,
                "whisperModel": model_size,
                "whisperDevice": preferred_device,
                "computeType": compute_type,
            })
        except Exception as gpu_exc:
            WHISPER_MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
            MODEL_INFO.update({
                "whisperLoaded": True,
                "whisperModel": model_size,
                "whisperDevice": "cpu",
                "computeType": "int8",
                "gpuFallback": str(gpu_exc),
            })
    except Exception as exc:
        note_error("whisper", exc)

    MODEL_INFO["qwenReady"] = bool(os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY"))
    MODEL_INFO["status"] = "ready" if MODEL_INFO.get("whisperLoaded") and MODEL_INFO.get("preferenceLoaded") else "degraded"
    MODEL_INFO["loadMs"] = int((time.time() - started) * 1000)


def response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8") or "{}")


def read_jsonl(path: str | Path, limit: int) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def safe_number(value, fallback: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except Exception:
        return fallback


def recommend_with_torch(samples: list[dict], events: list[dict]) -> dict:
    if not samples:
        return {
            "fanOnC": 27.5,
            "fanOffC": 25.5,
            "ledMax": 210,
            "statusMax": 180,
            "confidence": 0.15,
        }

    if TORCH is None:
        temps = [safe_number(sample.get("temperatureC"), 26.0) for sample in samples]
        occupied_temps = [safe_number(sample.get("temperatureC"), 26.0) for sample in samples if safe_number(sample.get("occupied")) > 0]
        target = sorted(occupied_temps or temps)[max(0, int(0.42 * len(occupied_temps or temps)) - 1)]
        return {
            "fanOnC": round(max(24.0, min(33.0, target + 1.1)), 1),
            "fanOffC": round(max(20.0, min(32.0, target - 0.6)), 1),
            "ledMax": 210,
            "statusMax": 180,
            "confidence": 0.25,
        }

    device = PREFERENCE_DEVICE if MODEL_INFO.get("cuda") else "cpu"
    temps = TORCH.tensor([safe_number(s.get("temperatureC"), 26.0) for s in samples], dtype=TORCH.float32, device=device)
    occupied = TORCH.tensor([1.0 if safe_number(s.get("occupied")) > 0 else 0.0 for s in samples], dtype=TORCH.float32, device=device)
    fan = TORCH.tensor([1.0 if safe_number(s.get("fan")) > 0 or safe_number(s.get("pwm")) > 0 else 0.0 for s in samples], dtype=TORCH.float32, device=device)
    light = TORCH.tensor([safe_number(s.get("light"), 420.0) for s in samples], dtype=TORCH.float32, device=device)

    occupied_mask = occupied > 0.5
    occupied_temp = temps[occupied_mask] if TORCH.any(occupied_mask) else temps
    target_temp = float(TORCH.quantile(occupied_temp, 0.42).detach().cpu().item())
    fan_duty = float(fan.mean().detach().cpu().item())
    light_q = float(TORCH.quantile(light, 0.35).detach().cpu().item())

    config_events = [
        event for event in events
        if isinstance(event.get("settings"), dict) and isinstance(event["settings"].get("auto"), dict)
    ]
    if config_events:
        auto = config_events[-1]["settings"]["auto"]
        prior_on = safe_number(auto.get("fanOnC"), target_temp + 1.0)
        prior_off = safe_number(auto.get("fanOffC"), target_temp - 0.6)
        prior_led = safe_number(auto.get("ledMax"), 210)
        prior_status = safe_number(auto.get("statusMax"), 180)
    else:
        prior_on = target_temp + 1.1
        prior_off = target_temp - 0.7
        prior_led = 210
        prior_status = 180

    fan_on = 0.62 * prior_on + 0.38 * (target_temp + (0.8 if fan_duty < 0.45 else 1.35))
    fan_off = min(fan_on - 0.5, 0.62 * prior_off + 0.38 * (target_temp - 0.55))
    led_max = prior_led + (12 if light_q < 240 else -8 if light_q > 620 else 0)
    confidence = min(0.94, 0.22 + len(samples) / 500.0 + len(config_events) / 18.0)

    return {
        "fanOnC": round(max(24.0, min(33.0, fan_on)), 1),
        "fanOffC": round(max(20.0, min(fan_on - 0.5, fan_off)), 1),
        "ledMax": int(max(70, min(255, round(led_max)))),
        "statusMax": int(max(40, min(255, round(prior_status)))),
        "confidence": round(confidence, 3),
    }


def analytics_recommend(payload: dict) -> dict:
    samples = payload.get("samples")
    events = payload.get("events")
    if not isinstance(samples, list):
        samples = read_jsonl(payload.get("samplesPath", ""), 1600)
    if not isinstance(events, list):
        events = read_jsonl(payload.get("eventsPath", ""), 400)
    recommendation = recommend_with_torch(samples[-1600:], events[-400:])
    return {
        "ok": True,
        "engine": "persistent-torch",
        "torchLoaded": bool(MODEL_INFO.get("torchLoaded")),
        "torchVersion": MODEL_INFO.get("torchVersion"),
        "cuda": bool(MODEL_INFO.get("cuda")),
        "device": MODEL_INFO.get("device"),
        "preferenceDevice": PREFERENCE_DEVICE,
        "sampleCount": len(samples),
        "eventCount": len(events),
        "recommendedAuto": recommendation,
        "expectedData": {
            "minimumUsefulSamples": 160,
            "minimumPreferenceEvents": 5,
            "currentUtility": "high" if len(samples) >= 160 and len(events) >= 5 else "warming_up",
            "features": ["temperatureC", "occupied", "light", "fanDuty", "manualOverrides", "configEvents"],
        },
    }


def strip_json_envelope(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return "{}"
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    first = raw.find("{")
    last = raw.rfind("}")
    if first >= 0 and last > first:
        return raw[first:last + 1]
    return raw


def qwen_state(api_key: str = "") -> dict:
    return {
        "baseUrl": os.environ.get("QWEN_BASE_URL", QWEN_DEFAULT_BASE_URL),
        "model": os.environ.get("QWEN_MODEL", QWEN_DEFAULT_MODEL),
        "apiKeyPresent": bool(api_key or os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")),
        "thinkingDisabled": True,
        "structuredJsonOnly": True,
    }


def local_time_string() -> str:
    if ZoneInfo is None:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")


def qwen_plan(payload: dict) -> dict:
    api_key = str(payload.get("apiKey") or os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY") or "")
    if not api_key:
        return {
            "ok": False,
            "error": "missing_api_key",
            "qwen": qwen_state(api_key),
            "plan": {
                "confidence": 0,
                "reply": "Qwen API key is not configured.",
                "tasks": [{"action": "noop", "title": "Missing API key", "note": "No device action was taken."}],
            },
        }

    transcript = str(payload.get("transcript") or "").strip()
    if not transcript:
        return {"ok": False, "error": "empty_transcript", "qwen": qwen_state(api_key)}

    base_url = str(payload.get("baseUrl") or os.environ.get("QWEN_BASE_URL") or QWEN_DEFAULT_BASE_URL)
    model = str(payload.get("model") or os.environ.get("QWEN_MODEL") or QWEN_DEFAULT_MODEL)
    now_ms = int(payload.get("nowUnixMs") or time.time() * 1000)
    current_local_time = str(payload.get("currentLocalTime") or local_time_string())
    timezone = str(payload.get("timezone") or "Asia/Shanghai")

    system_prompt = "\n".join([
        "You are the Smart Classroom task planner.",
        "Return one JSON object only. Do not output Markdown.",
        "Convert the user's natural-language command into a linear timeline of executable tasks.",
        "You may decide how many tasks are needed. Split compound requests into ordered tasks.",
        "Use delaySec as seconds relative to now. Example: 'in 3 minutes' => delaySec=180.",
        "For chained timing, calculate cumulative delaySec from now.",
        "If the user gives an absolute time, use currentLocalTime and timezone to convert it into delaySec.",
        "Do not hide executable device actions inside note.",
        "Allowed actions: noop, wait, return_auto, set_manual, set_auto_config, preset, command.",
        "manual may include enabled,lamp,fan,pwm,buzzer,status. status must be ALL/R/Y/G/OFF.",
        "auto may include fanOnC,fanOffC,ledMax,statusMax,lightDark,lightBright.",
        "presetId must be comfort, energy, presentation, or safety.",
        "command must be ping, buzz, demo_on, demo_off, or status_on.",
        "Never invent raw hardware commands. Use only the allowed actions and fields.",
        "Keep the plan practical for a classroom IoT demo. Safety alarm behavior on UNO has priority.",
        "Output schema: {planId, confidence, reply, tasks:[{id,title,action,delaySec,risk,note,manual,auto,presetId,command}]}."
    ])

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps({
                "transcript": transcript,
                "nowUnixMs": now_ms,
                "currentLocalTime": current_local_time,
                "timezone": timezone,
                "telemetry": payload.get("telemetry") or {},
                "settings": payload.get("settings") or {},
                "allowedManualStatus": ["ALL", "R", "Y", "G", "OFF"],
                "examples": [
                    {
                        "input": "Switch to manual mode in 3 minutes, set fan PWM to 180, then return to automatic mode 2 minutes later.",
                        "output": {
                            "confidence": 0.95,
                            "reply": "I planned two delayed tasks.",
                            "tasks": [
                                {"id": "manual_after_3m", "title": "Switch to manual cooling", "action": "set_manual", "delaySec": 180, "risk": "medium", "manual": {"enabled": True, "fan": True, "pwm": 180, "status": "ALL"}},
                                {"id": "auto_after_5m", "title": "Return to automatic mode", "action": "return_auto", "delaySec": 300, "risk": "low"},
                            ],
                        },
                    }
                ],
            }, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "enable_thinking": False,
        "response_format": {"type": "json_object"},
    }

    request = urllib.request.Request(
        base_url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=float(os.environ.get("QWEN_TIMEOUT_SEC", "60"))) as result:
            data = json.loads(result.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        return {"ok": False, "error": f"qwen_http_{exc.code}", "detail": detail, "qwen": qwen_state(api_key)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "qwen": qwen_state(api_key)}

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        plan = json.loads(strip_json_envelope(content))
    except Exception as exc:
        return {"ok": False, "error": f"qwen_json_parse:{exc}", "raw": content[:1000], "qwen": qwen_state(api_key)}
    return {"ok": True, "qwen": qwen_state(api_key), "model": model, "plan": plan}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args) -> None:
        return

    def do_OPTIONS(self) -> None:
        response(self, 204, {})

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            response(self, 200, {
                "ok": True,
                "backend": MODEL_INFO,
                "qwen": qwen_state(),
                "endpoints": ["/health", "/transcribe", "/analytics/recommend", "/qwen/plan"],
            })
            return
        response(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        path = self.path.rstrip("/")
        try:
            payload = read_json_body(self)
        except Exception:
            response(self, 400, {"ok": False, "error": "bad_json"})
            return

        if path == "/transcribe":
            audio_path = Path(str(payload.get("audioPath") or ""))
            if not audio_path.exists():
                response(self, 400, {"ok": False, "error": "audio_missing"})
                return
            if WHISPER_MODEL is None:
                response(self, 503, {"ok": False, "error": "whisper_not_loaded", "backend": MODEL_INFO})
                return
            try:
                segments, info = WHISPER_MODEL.transcribe(
                    str(audio_path),
                    beam_size=3,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 450},
                    language=os.environ.get("SMARTCLASSROOM_WHISPER_LANGUAGE") or None,
                )
                text = "".join(segment.text for segment in segments).strip()
                response(self, 200, {
                    "ok": True,
                    "text": text,
                    "language": info.language,
                    "languageProbability": round(float(info.language_probability or 0), 4),
                    "model": MODEL_INFO.get("whisperModel"),
                    "device": MODEL_INFO.get("whisperDevice"),
                    "backend": MODEL_INFO,
                })
            except Exception as exc:
                response(self, 500, {"ok": False, "error": str(exc), "backend": MODEL_INFO})
            return

        if path == "/analytics/recommend":
            try:
                response(self, 200, analytics_recommend(payload))
            except Exception as exc:
                response(self, 500, {"ok": False, "error": str(exc), "backend": MODEL_INFO})
            return

        if path == "/qwen/plan":
            result = qwen_plan(payload)
            response(self, 200 if result.get("ok") or result.get("error") == "missing_api_key" else 502, result)
            return

        response(self, 404, {"ok": False, "error": "not_found"})


def main() -> int:
    parser = argparse.ArgumentParser(description="Persistent Smart Classroom AI backend.")
    parser.add_argument("--host", default=os.environ.get("SMARTCLASSROOM_AI_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SMARTCLASSROOM_AI_BACKEND_PORT", "8765")))
    args = parser.parse_args()
    load_backend()
    print(json.dumps({"ok": True, "listening": f"http://{args.host}:{args.port}", "backend": MODEL_INFO}, ensure_ascii=False), flush=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
