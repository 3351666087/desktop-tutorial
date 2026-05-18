#!/usr/bin/env python
from __future__ import annotations

import os
import socket
import subprocess
import sys
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
HTTP_URL = "http://localhost:3000"
HTTPS_URL = "https://localhost:3443"


def lan_ip() -> str:
    try:
      with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
          s.connect(("8.8.8.8", 80))
          return s.getsockname()[0]
    except OSError:
      return "127.0.0.1"


class Launcher(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Smart Classroom Launcher")
        self.resize(780, 520)
        self.web_process: subprocess.Popen | None = None
        self.console_process: subprocess.Popen | None = None

        self.status = QLabel("Ready")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)

        start = QPushButton("一键启动 Web + MQTT")
        open_web = QPushButton("打开 Web Dashboard")
        open_secure = QPushButton("打开 HTTPS 声控页")
        open_console = QPushButton("打开 PySide6 调试台")
        stop = QPushButton("停止 Web 服务")

        start.clicked.connect(self.start_web)
        open_web.clicked.connect(lambda: webbrowser.open(HTTP_URL))
        open_secure.clicked.connect(lambda: webbrowser.open(HTTPS_URL))
        open_console.clicked.connect(self.open_console)
        stop.clicked.connect(self.stop_web)

        row = QHBoxLayout()
        for button in [start, open_web, open_secure, open_console, stop]:
            row.addWidget(button)

        box = QVBoxLayout()
        box.addWidget(QLabel(f"LAN HTTPS microphone URL: https://{lan_ip()}:3443"))
        box.addLayout(row)
        box.addWidget(self.status)
        box.addWidget(self.log)

        root = QWidget()
        root.setLayout(box)
        self.setCentralWidget(root)

        QTimer.singleShot(250, self.start_web)
        QTimer.singleShot(1200, lambda: webbrowser.open(HTTP_URL))
        QTimer.singleShot(1600, self.open_console)

    def append(self, text: str) -> None:
        self.log.appendPlainText(text)
        self.status.setText(text)

    def start_web(self) -> None:
        if self.web_process and self.web_process.poll() is None:
            self.append("Web service already running.")
            return
        env = os.environ.copy()
        env.setdefault("WEB_PORT", "3000")
        env.setdefault("WEB_HTTPS_PORT", "3443")
        self.web_process = subprocess.Popen(
            ["node", "server.js"],
            cwd=WEB_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self.append("Started Web + MQTT service.")

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

    def stop_web(self) -> None:
        if self.web_process and self.web_process.poll() is None:
            self.web_process.terminate()
            self.append("Stopped Web service.")
        else:
            self.append("Web service is not running from this launcher.")

    def closeEvent(self, event) -> None:
        self.stop_web()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    window = Launcher()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
