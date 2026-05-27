#!/usr/bin/env python
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "SmartClassroom_WebDashboard"
SECRETS_PATH = WEB_DIR / "data" / "secrets.json"
HTTP_URL = "http://localhost:3000"
HTTPS_URL = "https://localhost:3443"
AI_BACKEND_URL = "http://127.0.0.1:8765"


def lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def find_ai_python() -> str:
    configured = os.environ.get("SMARTCLASSROOM_ASR_PYTHON")
    if configured and Path(configured).exists():
        return configured
    candidates = [
        Path.home() / ".conda" / "envs" / "media-asr" / "python.exe",
        Path("D:/conda/envs/media-asr/python.exe"),
        Path("D:/conda/python.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def read_json_url(url: str, timeout: float = 3.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_dashscope_key() -> str:
    if os.environ.get("DASHSCOPE_API_KEY"):
        return os.environ["DASHSCOPE_API_KEY"]
    try:
        secrets = json.loads(SECRETS_PATH.read_text(encoding="utf-8-sig"))
        return str(secrets.get("dashscopeApiKey") or "")
    except Exception:
        return ""


class Launcher(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Smart Classroom Launcher")
        self.resize(920, 580)
        self.web_process: subprocess.Popen | None = None
        self.console_process: subprocess.Popen | None = None
        self.ai_process: subprocess.Popen | None = None

        self.status = QLabel("Ready")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)

        start = QPushButton("一键启动 Web + MQTT + AI")
        open_web = QPushButton("打开 Web Dashboard")
        open_secure = QPushButton("打开 HTTPS 声控页")
        open_console = QPushButton("打开 PySide6 调试台")
        check_ai = QPushButton("检查 AI / Qwen 链路")
        stop = QPushButton("停止服务")

        start.clicked.connect(self.start_all)
        open_web.clicked.connect(lambda: webbrowser.open(HTTP_URL))
        open_secure.clicked.connect(lambda: webbrowser.open(HTTPS_URL))
        open_console.clicked.connect(self.open_console)
        check_ai.clicked.connect(self.check_ai_health)
        stop.clicked.connect(self.stop_all)

        row = QHBoxLayout()
        for button in [start, open_web, open_secure, open_console, check_ai, stop]:
            row.addWidget(button)

        box = QVBoxLayout()
        box.addWidget(QLabel(f"LAN HTTPS microphone URL: https://{lan_ip()}:3443"))
        box.addWidget(QLabel(f"AI backend: {AI_BACKEND_URL}"))
        box.addLayout(row)
        box.addWidget(self.status)
        box.addWidget(self.log)

        root = QWidget()
        root.setLayout(box)
        self.setCentralWidget(root)

        QTimer.singleShot(250, self.start_all)
        QTimer.singleShot(1800, lambda: webbrowser.open(HTTP_URL))
        QTimer.singleShot(2400, self.open_console)

    def append(self, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log.appendPlainText(f"[{stamp}] {text}")
        self.status.setText(text)

    def start_all(self) -> None:
        self.start_ai_backend()
        self.start_web()

    def start_ai_backend(self) -> None:
        if self.ai_process and self.ai_process.poll() is None:
            self.append("AI backend already running.")
            return
        ai_python = find_ai_python()
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("SMARTCLASSROOM_WHISPER_MODEL", "base")
        env.setdefault("SMARTCLASSROOM_WHISPER_DEVICE", "cuda")
        env.setdefault("SMARTCLASSROOM_WHISPER_COMPUTE", "float16")
        env.setdefault("SMARTCLASSROOM_AI_BACKEND_PORT", "8765")
        dashscope_key = load_dashscope_key()
        if dashscope_key:
            env.setdefault("DASHSCOPE_API_KEY", dashscope_key)
        self.ai_process = subprocess.Popen(
            [ai_python, str(ROOT / "smart_ai" / "ai_backend_service.py")],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.append(f"Starting AI backend with {ai_python}; loading torch/faster-whisper to GPU if available.")
        QTimer.singleShot(4500, self.check_ai_health)

    def start_web(self) -> None:
        if self.web_process and self.web_process.poll() is None:
            self.append("Web service already running.")
            return
        env = os.environ.copy()
        env.setdefault("WEB_PORT", "3000")
        env.setdefault("WEB_HTTPS_PORT", "3443")
        env.setdefault("SMARTCLASSROOM_AI_BACKEND_URL", AI_BACKEND_URL)
        env.setdefault("SMARTCLASSROOM_ASR_PYTHON", find_ai_python())
        dashscope_key = load_dashscope_key()
        if dashscope_key:
            env.setdefault("DASHSCOPE_API_KEY", dashscope_key)
        self.web_process = subprocess.Popen(
            ["node", "server.js"],
            cwd=WEB_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.append("Started Web Dashboard + local MQTT broker.")

    def check_ai_health(self) -> None:
        try:
            health = read_json_url(f"{HTTP_URL}/api/health/ai", timeout=4.0)
            qwen = health.get("qwen", {})
            backend = health.get("backend", {})
            loaded = backend.get("backend", backend)
            self.append(
                "AI/Qwen health: "
                f"backend={loaded.get('status', backend.get('status', 'unknown'))}, "
                f"cuda={loaded.get('cuda', False)}, "
                f"whisper={loaded.get('whisperLoaded', False)}, "
                f"qwenKey={qwen.get('apiKeyPresent', False)}, "
                f"model={qwen.get('model', '-')}"
            )
        except Exception as exc:
            self.append(f"AI/Qwen health check pending or failed: {exc}")

    def open_console(self) -> None:
        if self.console_process and self.console_process.poll() is None:
            self.append("PySide6 console already running.")
            return
        self.console_process = subprocess.Popen(
            [sys.executable, str(ROOT / "uno_console.py")],
            cwd=ROOT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.append("Opened PySide6 debug console.")

    def stop_all(self) -> None:
        for name, proc in [("Web service", self.web_process), ("AI backend", self.ai_process)]:
            if proc and proc.poll() is None:
                proc.terminate()
                self.append(f"Stopped {name}.")
        if not ((self.web_process and self.web_process.poll() is None) or (self.ai_process and self.ai_process.poll() is None)):
            self.append("Services stopped or not started from this launcher.")

    def closeEvent(self, event) -> None:
        self.stop_all()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    window = Launcher()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
