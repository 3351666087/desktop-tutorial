#!/usr/bin/env python
"""
PySide6 serial console for SmartClassroom_UNO_Phase1.

It reads the Arduino UNO 9600 baud serial status lines and displays:
PIR, occupancy, light gate, LM35 temperature, relay fan, soft PWM, tach/RPM, fan health, and mode.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime

import serial
from serial.tools import list_ports

from PySide6.QtCore import QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


DEFAULT_BAUD = 9600
LINE_PATTERN = re.compile(r"([A-Za-z][A-Za-z0-9]*)=([^\s]+)")


@dataclass
class PortInfo:
    device: str
    label: str


class SerialReader(QThread):
    line_received = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, port: str, baud: int) -> None:
        super().__init__()
        self.port = port
        self.baud = baud
        self._running = True
        self._serial: serial.Serial | None = None

    def run(self) -> None:
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=0.25)
            self._serial.reset_input_buffer()
            self.status_changed.emit(f"Connected to {self.port} @ {self.baud}")
        except serial.SerialException as exc:
            self.error_occurred.emit(f"Could not open {self.port}: {exc}")
            return

        while self._running:
            try:
                raw = self._serial.readline()
            except serial.SerialException as exc:
                self.error_occurred.emit(f"Serial read failed: {exc}")
                break

            if not raw:
                continue

            line = raw.decode("utf-8", errors="ignore").replace("\x00", "").strip()
            if line:
                self.line_received.emit(line)

        if self._serial and self._serial.is_open:
            self._serial.close()
        self.status_changed.emit("Disconnected")

    def stop(self) -> None:
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.cancel_read()
            except Exception:
                pass
        self.wait(1500)


class MetricCard(QFrame):
    def __init__(self, title: str, unit: str = "") -> None:
        super().__init__()
        self.unit = unit
        self.setObjectName("MetricCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitle")

        self.value_label = QLabel("--")
        self.value_label.setObjectName("MetricValue")
        self.value_label.setMinimumHeight(38)

        self.detail_label = QLabel("")
        self.detail_label.setObjectName("MetricDetail")
        self.detail_label.setMinimumHeight(18)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def set_value(self, value: str, detail: str = "", state: str = "normal") -> None:
        self.value_label.setText(value)
        self.detail_label.setText(detail)
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Smart Classroom UNO Console")
        self.resize(1120, 760)

        self.reader: SerialReader | None = None
        self.line_count = 0
        self.latest_values: dict[str, str] = {}

        self.port_combo = QComboBox()
        self.baud_spin = QSpinBox()
        self.baud_spin.setRange(1200, 250000)
        self.baud_spin.setValue(DEFAULT_BAUD)
        self.baud_spin.setSingleStep(1200)

        self.refresh_button = QPushButton("Refresh")
        self.connect_button = QPushButton("Connect")
        self.autoscroll_checkbox = QCheckBox("Auto-scroll")
        self.autoscroll_checkbox.setChecked(True)

        self.status_label = QLabel("Disconnected")
        self.last_update_label = QLabel("Last update: --")
        self.line_count_label = QLabel("Lines: 0")

        self.cards = {
            "pir": MetricCard("PIR Motion"),
            "occupancy": MetricCard("Occupancy"),
            "light": MetricCard("Light Sensor"),
            "light_gate": MetricCard("Light Gate"),
            "temperature": MetricCard("LM35 Temperature", "C"),
            "gas": MetricCard("Gas Sensor"),
            "flame": MetricCard("Flame Sensor"),
            "emergency": MetricCard("Emergency Button"),
            "safety": MetricCard("Safety Layer"),
            "fan_relay": MetricCard("Fan Relay"),
            "led": MetricCard("Classroom LED"),
            "fan_pwm": MetricCard("Fan PWM"),
            "fan_target": MetricCard("Fan Target"),
            "rpm": MetricCard("Fan RPM"),
            "tach": MetricCard("Tach Pulses"),
            "fan_health": MetricCard("Fan Health"),
            "mode": MetricCard("Current Mode"),
        }

        self.light_bar = QProgressBar()
        self.light_bar.setRange(0, 1023)
        self.temp_bar = QProgressBar()
        self.temp_bar.setRange(0, 50)
        self.pwm_bar = QProgressBar()
        self.pwm_bar.setRange(0, 255)
        self.target_bar = QProgressBar()
        self.target_bar.setRange(0, 255)
        self.rpm_bar = QProgressBar()
        self.rpm_bar.setRange(0, 5000)

        self.raw_log = QPlainTextEdit()
        self.raw_log.setReadOnly(True)
        self.raw_log.setMaximumBlockCount(500)
        self.raw_log.setObjectName("RawLog")

        self._build_ui()
        self._connect_signals()
        self.refresh_ports()
        QTimer.singleShot(500, self.auto_connect_if_possible)

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Smart Classroom UNO Console")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Phase 1 local serial monitor for occupancy lighting, LM35 cooling, soft fan PWM, relay, and tach")
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        root.addLayout(header)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Port"))
        controls.addWidget(self.port_combo, 2)
        controls.addWidget(QLabel("Baud"))
        controls.addWidget(self.baud_spin)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.connect_button)
        controls.addWidget(self.autoscroll_checkbox)
        controls.addStretch(1)
        controls.addWidget(self.line_count_label)
        root.addLayout(controls)

        card_grid = QGridLayout()
        card_grid.setHorizontalSpacing(12)
        card_grid.setVerticalSpacing(12)
        ordered_cards = [
            "pir",
            "occupancy",
            "light",
            "light_gate",
            "temperature",
            "gas",
            "flame",
            "emergency",
            "safety",
            "fan_relay",
            "led",
            "fan_pwm",
            "fan_target",
            "rpm",
            "tach",
            "fan_health",
            "mode",
        ]
        for index, key in enumerate(ordered_cards):
            row = index // 3
            col = index % 3
            card_grid.addWidget(self.cards[key], row, col)
        root.addLayout(card_grid)

        gauges = QGroupBox("Analog and Actuator Levels")
        gauges_layout = QGridLayout(gauges)
        gauges_layout.setContentsMargins(14, 14, 14, 14)
        gauges_layout.setHorizontalSpacing(12)
        gauges_layout.setVerticalSpacing(10)
        self._add_gauge(gauges_layout, 0, "Light A0", self.light_bar)
        self._add_gauge(gauges_layout, 1, "Temperature C", self.temp_bar)
        self._add_gauge(gauges_layout, 2, "Fan PWM actual", self.pwm_bar)
        self._add_gauge(gauges_layout, 3, "Fan PWM target", self.target_bar)
        self._add_gauge(gauges_layout, 4, "Fan RPM", self.rpm_bar)
        root.addWidget(gauges)

        log_group = QGroupBox("Raw Serial Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.addWidget(self.raw_log)
        root.addWidget(log_group, 1)

        self.setCentralWidget(central)

        status = QStatusBar()
        status.addWidget(self.status_label, 1)
        status.addPermanentWidget(self.last_update_label)
        self.setStatusBar(status)

        self.setStyleSheet(
            """
            QWidget {
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 10.5pt;
                color: #20242a;
                background: #f5f7f8;
            }
            #AppTitle {
                font-size: 22pt;
                font-weight: 700;
                color: #111827;
            }
            #AppSubtitle {
                color: #5d6673;
            }
            QPushButton, QComboBox, QSpinBox {
                min-height: 30px;
                border: 1px solid #c7cdd4;
                border-radius: 6px;
                padding: 4px 9px;
                background: #ffffff;
            }
            QPushButton:hover {
                border-color: #476f95;
                background: #eef5fb;
            }
            QPushButton:pressed {
                background: #ddeaf3;
            }
            #MetricCard {
                background: #ffffff;
                border: 1px solid #d8dde3;
                border-radius: 8px;
            }
            #MetricCard[state="ok"] {
                border-left: 5px solid #2f8f5b;
            }
            #MetricCard[state="warn"] {
                border-left: 5px solid #b7791f;
            }
            #MetricCard[state="error"] {
                border-left: 5px solid #c24135;
            }
            #MetricCard[state="active"] {
                border-left: 5px solid #2b6cb0;
            }
            #MetricTitle {
                font-size: 9.5pt;
                color: #667085;
                font-weight: 600;
            }
            #MetricValue {
                font-size: 21pt;
                font-weight: 700;
                color: #111827;
            }
            #MetricDetail {
                color: #697386;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d8dde3;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QProgressBar {
                border: 1px solid #cbd3dc;
                border-radius: 5px;
                background: #eef1f4;
                text-align: center;
                min-height: 22px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: #3b82a0;
            }
            #RawLog {
                background: #111827;
                color: #e5edf5;
                border: 1px solid #2d3748;
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas, "Cascadia Mono", monospace;
                font-size: 9.5pt;
            }
            """
        )

    def _add_gauge(self, layout: QGridLayout, row: int, label: str, bar: QProgressBar) -> None:
        label_widget = QLabel(label)
        label_widget.setMinimumWidth(110)
        layout.addWidget(label_widget, row, 0)
        layout.addWidget(bar, row, 1)

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.connect_button.clicked.connect(self.toggle_connection)

    @Slot()
    def refresh_ports(self) -> None:
        current = self.port_combo.currentData()
        self.port_combo.clear()

        ports = self.available_ports()
        for port in ports:
            self.port_combo.addItem(port.label, port.device)

        if not ports:
            self.port_combo.addItem("No serial ports found", "")
            return

        target_index = 0
        for index, port in enumerate(ports):
            if current and port.device == current:
                target_index = index
                break
            if "arduino" in port.label.lower() or "uno" in port.label.lower():
                target_index = index
                break
        self.port_combo.setCurrentIndex(target_index)

    def available_ports(self) -> list[PortInfo]:
        ports = []
        for port in list_ports.comports():
            description = port.description or "Serial Port"
            hwid = port.hwid or ""
            label = f"{port.device} - {description}"
            if hwid:
                label += f" [{hwid}]"
            ports.append(PortInfo(port.device, label))
        return ports

    @Slot()
    def auto_connect_if_possible(self) -> None:
        port = self.port_combo.currentData()
        if port and not (self.reader and self.reader.isRunning()):
            self.connect_serial()

    @Slot()
    def toggle_connection(self) -> None:
        if self.reader and self.reader.isRunning():
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self) -> None:
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "No Port", "No serial port is selected.")
            return

        baud = self.baud_spin.value()
        self.reader = SerialReader(port, baud)
        self.reader.line_received.connect(self.handle_line)
        self.reader.status_changed.connect(self.set_status)
        self.reader.error_occurred.connect(self.handle_error)
        self.reader.finished.connect(self.reader_finished)
        self.reader.start()

        self.connect_button.setText("Disconnect")
        self.port_combo.setEnabled(False)
        self.baud_spin.setEnabled(False)
        self.refresh_button.setEnabled(False)

    def disconnect_serial(self) -> None:
        if self.reader:
            self.reader.stop()

    @Slot()
    def reader_finished(self) -> None:
        self.connect_button.setText("Connect")
        self.port_combo.setEnabled(True)
        self.baud_spin.setEnabled(True)
        self.refresh_button.setEnabled(True)

    @Slot(str)
    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    @Slot(str)
    def handle_error(self, text: str) -> None:
        self.set_status(text)
        self.raw_log.appendPlainText(f"[ERROR] {text}")
        self.reader_finished()

    @Slot(str)
    def handle_line(self, line: str) -> None:
        self.line_count += 1
        self.line_count_label.setText(f"Lines: {self.line_count}")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.raw_log.appendPlainText(f"{timestamp}  {line}")
        if self.autoscroll_checkbox.isChecked():
            self.raw_log.verticalScrollBar().setValue(self.raw_log.verticalScrollBar().maximum())

        parsed = self.parse_line(line)
        if not parsed:
            return

        self.latest_values.update(parsed)
        self.update_metrics()
        self.last_update_label.setText(f"Last update: {timestamp}")

    def parse_line(self, line: str) -> dict[str, str]:
        parsed = dict(LINE_PATTERN.findall(line))
        if "temperatureC" in parsed:
            parsed["temperatureError"] = "true" if "(ERROR)" in parsed["temperatureC"] else "false"
            parsed["temperatureC"] = parsed["temperatureC"].replace("(ERROR)", "")
        return parsed

    def update_metrics(self) -> None:
        values = self.latest_values

        pir = values.get("PIR", "--")
        self.cards["pir"].set_value(
            "Motion" if pir == "motion" else "No motion" if pir == "no_motion" else pir,
            "D2 PIR output",
            "active" if pir == "motion" else "normal",
        )

        occupancy = values.get("occupancy", "--")
        self.cards["occupancy"].set_value(
            "Occupied" if occupancy == "occupied" else "Vacant" if occupancy == "vacant" else occupancy,
            "10s grace after motion",
            "active" if occupancy == "occupied" else "normal",
        )

        light_value = self.to_int(values.get("lightValue"))
        light_state = values.get("light", "--")
        self.cards["light"].set_value(
            str(light_value) if light_value is not None else "--",
            f"{light_state} on A0",
            "warn" if light_state == "dark" else "normal",
        )
        if light_value is not None:
            self.light_bar.setValue(max(0, min(1023, light_value)))

        light_gate = values.get("lightGate", "--")
        self.cards["light_gate"].set_value(
            "Enabled" if light_gate == "enabled" else "Blocked" if light_gate == "blocked" else light_gate,
            "bright-room LED lockout",
            "active" if light_gate == "enabled" else "normal",
        )

        temp = self.to_float(values.get("temperatureC"))
        sensor_temp = values.get("sensorTempC", "--")
        temp_comp = values.get("tempComp", "--")
        temp_source = values.get("tempSource", "--")
        temp_raw = values.get("tempRaw", "--")
        temp_voltage = values.get("tempVoltage", "--")
        vcc = values.get("vcc", "--")
        temp_error = values.get("temperatureError") == "true"
        if temp is None:
            temp_text = "--"
            temp_state = "normal"
        else:
            temp_text = f"{temp:.1f} C"
            temp_state = "error" if temp_error else "warn" if temp >= 26.0 else "ok"
            self.temp_bar.setValue(max(0, min(50, round(temp))))
        self.cards["temperature"].set_value(
            temp_text,
            f"sensor={sensor_temp} C comp={temp_comp} source={temp_source} raw={temp_raw} v={temp_voltage} V vcc={vcc} V",
            temp_state,
        )

        gas_value = self.to_int(values.get("gasValue"))
        gas_baseline = values.get("gasBaseline", "--")
        gas_warning = values.get("gasWarning", "false") == "true"
        gas_danger = values.get("gasDanger", "false") == "true"
        gas_state = "error" if gas_danger else "warn" if gas_warning else "normal"
        self.cards["gas"].set_value(
            str(gas_value) if gas_value is not None else "--",
            f"baseline={gas_baseline} warning={str(gas_warning).lower()} danger={str(gas_danger).lower()}",
            gas_state,
        )

        flame_digital = values.get("flameDigital", "--")
        flame_analog = values.get("flameAnalog", "--")
        flame_suspicious = values.get("flameSuspicious", "false") == "true"
        flame_detected = values.get("flameDetected", "false") == "true"
        flame_state = "error" if flame_detected else "warn" if flame_suspicious else "normal"
        self.cards["flame"].set_value(
            "Detected" if flame_detected else "Clear",
            f"DO={flame_digital} AO={flame_analog} suspicious={str(flame_suspicious).lower()}",
            flame_state,
        )

        demo_emergency = values.get("demoEmergency", "false") == "true"
        self.cards["emergency"].set_value(
            "Pressed" if demo_emergency else "Released",
            "D4 INPUT_PULLUP test button",
            "error" if demo_emergency else "normal",
        )

        safety_alarm = values.get("safetyAlarm", "false") == "true"
        safety_reason = values.get("safetyReason", "NONE")
        self.cards["safety"].set_value(
            "ALARM" if safety_alarm else "Clear",
            f"reason={safety_reason}",
            "error" if safety_alarm else "normal",
        )

        fan_relay = values.get("fanRelay", "--")
        if fan_relay == "--":
            fan_relay = values.get("fanRelayState", "--")
        self.cards["fan_relay"].set_value(
            fan_relay,
            "D6 relay output",
            "active" if fan_relay == "ON" else "normal",
        )

        led = values.get("LED", "--")
        self.cards["led"].set_value(
            led,
            "D5 classroom light",
            "active" if led == "ON" else "normal",
        )

        pwm = self.to_int(values.get("fanPWM"))
        if pwm is None:
            pwm = self.to_int(values.get("fanPwmValue"))
        self.cards["fan_pwm"].set_value(
            str(pwm) if pwm is not None else "--",
            "D9 25kHz actual output",
            "active" if pwm and pwm > 0 else "normal",
        )
        if pwm is not None:
            self.pwm_bar.setValue(max(0, min(255, pwm)))

        fan_target = self.to_int(values.get("fanTarget"))
        self.cards["fan_target"].set_value(
            str(fan_target) if fan_target is not None else "--",
            "temperature-mapped target",
            "active" if fan_target and fan_target > 0 else "normal",
        )
        if fan_target is not None:
            self.target_bar.setValue(max(0, min(255, fan_target)))

        rpm = self.to_int(values.get("estimatedRPM"))
        self.cards["rpm"].set_value(
            str(rpm) if rpm is not None else "--",
            "from D3 tach interrupt",
            "active" if rpm and rpm > 0 else "normal",
        )
        if rpm is not None:
            self.rpm_bar.setValue(max(0, min(5000, rpm)))

        tach = self.to_int(values.get("tachPulses"))
        self.cards["tach"].set_value(
            str(tach) if tach is not None else "--",
            "total interrupt count",
            "normal",
        )

        fan_health = values.get("fanHealth", "--")
        fan_health_state = {
            "RUNNING": "active",
            "STARTING": "warn",
            "STANDBY": "normal",
            "NO_TACH": "error",
        }.get(fan_health, "normal")
        self.cards["fan_health"].set_value(fan_health, "tach-based health", fan_health_state)

        mode = values.get("mode", "--")
        mode_state = {
            "NORMAL": "ok",
            "LIGHTING": "active",
            "COOLING": "active",
            "AIR_QUALITY_WARNING": "warn",
            "VERIFYING": "warn",
            "ENERGY_SAVING": "ok",
            "SAFETY_ALARM": "error",
            "SENSOR_ERROR": "error",
        }.get(mode, "normal")
        self.cards["mode"].set_value(mode, "UNO control mode", mode_state)

    def to_int(self, value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(float(value))
        except ValueError:
            return None

    def to_float(self, value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def closeEvent(self, event) -> None:
        if self.reader and self.reader.isRunning():
            self.reader.stop()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
