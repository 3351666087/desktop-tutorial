#!/usr/bin/env python
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "SmartClassroom_WebDashboard"
SECRETS_PATH = WEB_DIR / "data" / "secrets.json"
AI_PORT = os.environ.get("SMARTCLASSROOM_AI_TEST_PORT", "8768")


def find_ai_python() -> Path:
    configured = os.environ.get("SMARTCLASSROOM_ASR_PYTHON")
    candidates = [
        Path(configured) if configured else None,
        Path.home() / ".conda" / "envs" / "media-asr" / "python.exe",
        Path("D:/conda/envs/media-asr/python.exe"),
        Path("D:/conda/python.exe"),
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate and candidate.exists() and candidate.is_file():
            return candidate
    return Path(sys.executable)


def load_key() -> str:
    if os.environ.get("DASHSCOPE_API_KEY"):
        return os.environ["DASHSCOPE_API_KEY"]
    if not SECRETS_PATH.exists():
        return ""
    return str(json.loads(SECRETS_PATH.read_text(encoding="utf-8-sig")).get("dashscopeApiKey") or "")


def get_json(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict, timeout: float = 90.0) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(port: str, proc: subprocess.Popen, timeout_sec: int = 90) -> dict:
    deadline = time.time() + timeout_sec
    last_error = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"AI backend exited early: {output[-2000:]}")
        try:
            return get_json(f"http://127.0.0.1:{port}/health", timeout=2)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(1)
    raise TimeoutError(f"AI backend health timeout: {last_error}")


def main() -> int:
    api_key = load_key()
    if not api_key:
        print(json.dumps({"ok": False, "error": "missing_dashscope_key"}, ensure_ascii=False))
        return 2

    ai_python = find_ai_python()
    env = os.environ.copy()
    env.update({
        "PYTHONUTF8": "1",
        "SMARTCLASSROOM_WHISPER_MODEL": env.get("SMARTCLASSROOM_WHISPER_MODEL", "base"),
        "SMARTCLASSROOM_WHISPER_DEVICE": env.get("SMARTCLASSROOM_WHISPER_DEVICE", "cuda"),
        "SMARTCLASSROOM_WHISPER_COMPUTE": env.get("SMARTCLASSROOM_WHISPER_COMPUTE", "float16"),
        "SMARTCLASSROOM_AI_BACKEND_PORT": AI_PORT,
        "DASHSCOPE_API_KEY": api_key,
    })

    proc = subprocess.Popen(
        [str(ai_python), str(ROOT / "smart_ai" / "ai_backend_service.py"), "--port", AI_PORT],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        health = wait_for_health(AI_PORT, proc)
        backend = health.get("backend", {})
        samples = [
            {"temperatureC": 25.3, "occupied": 1, "fan": 0, "pwm": 0, "light": 380},
            {"temperatureC": 26.2, "occupied": 1, "fan": 1, "pwm": 120, "light": 420},
            {"temperatureC": 27.4, "occupied": 1, "fan": 1, "pwm": 180, "light": 450},
            {"temperatureC": 24.9, "occupied": 0, "fan": 0, "pwm": 0, "light": 690},
        ] * 50
        events = [{"settings": {"auto": {"fanOnC": 26.5, "fanOffC": 25.2, "ledMax": 220, "statusMax": 200}}}]
        analytics = post_json(f"http://127.0.0.1:{AI_PORT}/analytics/recommend", {"samples": samples, "events": events}, timeout=30)
        qwen = post_json(
            f"http://127.0.0.1:{AI_PORT}/qwen/plan",
            {
                "transcript": "3分钟后切换为手动模式，风扇PWM设为180，再过2分钟恢复自动模式",
                "telemetry": {"temperatureC": 26.8, "occupied": 1, "mode": "NORMAL"},
                "settings": {"manual": {"enabled": False}, "auto": {"fanOnC": 26.0, "fanOffC": 24.5}},
                "timezone": "Asia/Shanghai",
            },
            timeout=120,
        )
        plan = qwen.get("plan", {})
        ok = (
            backend.get("status") == "ready"
            and backend.get("cuda") is True
            and backend.get("whisperLoaded") is True
            and backend.get("whisperDevice") == "cuda"
            and analytics.get("engine") == "persistent-torch"
            and analytics.get("preferenceDevice") == "cuda"
            and qwen.get("ok") is True
            and len(plan.get("tasks") or []) >= 2
        )
        print(json.dumps({
            "ok": ok,
            "aiPython": str(ai_python),
            "health": {
                "status": backend.get("status"),
                "cuda": backend.get("cuda"),
                "device": backend.get("device"),
                "whisperLoaded": backend.get("whisperLoaded"),
                "whisperDevice": backend.get("whisperDevice"),
                "preferenceDevice": backend.get("preferenceDevice"),
                "qwenReady": backend.get("qwenReady"),
            },
            "analytics": {
                "engine": analytics.get("engine"),
                "preferenceDevice": analytics.get("preferenceDevice"),
                "recommendedAuto": analytics.get("recommendedAuto"),
            },
            "qwen": {
                "model": qwen.get("model") or qwen.get("qwen", {}).get("model"),
                "taskCount": len(plan.get("tasks") or []),
                "tasks": [
                    {key: task.get(key) for key in ["title", "action", "delaySec"]}
                    for task in (plan.get("tasks") or [])
                ],
            },
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
