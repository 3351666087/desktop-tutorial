#!/usr/bin/env python
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import torch


def read_jsonl(path: str, limit: int) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict] = []
    with p.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def safe_number(value, fallback=0.0) -> float:
    try:
        n = float(value)
        return n if math.isfinite(n) else fallback
    except Exception:
        return fallback


def local_recommend(samples: list[dict], events: list[dict]) -> dict:
    if not samples:
        return {
            "fanOnC": 27.5,
            "fanOffC": 25.5,
            "ledMax": 210,
            "statusMax": 180,
            "confidence": 0.15,
        }

    temps = torch.tensor([safe_number(s.get("temperatureC"), 26.0) for s in samples], dtype=torch.float32)
    occupied = torch.tensor([1.0 if safe_number(s.get("occupied")) > 0 else 0.0 for s in samples], dtype=torch.float32)
    fan = torch.tensor([1.0 if safe_number(s.get("fan")) > 0 or safe_number(s.get("pwm")) > 0 else 0.0 for s in samples], dtype=torch.float32)
    light = torch.tensor([safe_number(s.get("light"), 420.0) for s in samples], dtype=torch.float32)

    occupied_mask = occupied > 0.5
    occupied_temp = temps[occupied_mask] if torch.any(occupied_mask) else temps
    target_temp = float(torch.quantile(occupied_temp, 0.42).item())
    fan_duty = float(fan.mean().item())
    light_q = float(torch.quantile(light, 0.35).item())

    config_events = [
        e for e in events
        if isinstance(e.get("settings"), dict) and isinstance(e["settings"].get("auto"), dict)
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
    status_max = prior_status

    confidence = min(0.92, 0.2 + len(samples) / 500.0 + len(config_events) / 20.0)
    return {
        "fanOnC": round(max(24.0, min(33.0, fan_on)), 1),
        "fanOffC": round(max(20.0, min(fan_on - 0.5, fan_off)), 1),
        "ledMax": int(max(70, min(255, round(led_max)))),
        "statusMax": int(max(40, min(255, round(status_max)))),
        "confidence": round(confidence, 3),
    }


def main() -> int:
    samples_path = sys.argv[1] if len(sys.argv) > 1 else ""
    events_path = sys.argv[2] if len(sys.argv) > 2 else ""
    samples = read_jsonl(samples_path, 1600)
    events = read_jsonl(events_path, 400)
    recommendation = local_recommend(samples, events)
    print(json.dumps({
        "ok": True,
        "engine": "torch",
        "torchVersion": torch.__version__,
        "cuda": bool(torch.cuda.is_available()),
        "sampleCount": len(samples),
        "eventCount": len(events),
        "recommendedAuto": recommendation,
        "expectedData": {
            "minimumUsefulSamples": 160,
            "minimumPreferenceEvents": 5,
            "currentUtility": "high" if len(samples) >= 160 and len(events) >= 5 else "warming_up",
            "features": ["temperatureC", "occupied", "light", "fanDuty", "manualOverrides", "configEvents"],
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
