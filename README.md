# Smart Classroom Energy-Saving, Safety & Asset Monitoring System

An Arduino UNO + ESP32 IoT classroom prototype for energy saving, safety alarm, and operational monitoring. The system is designed for the IoT104TC group project lab demonstration: it combines real edge sensing/control, a Wi-Fi/MQTT gateway, a local web dashboard, data collection, and AI-assisted command planning.

## What This Project Demonstrates

- **Real edge control**: Arduino UNO reads sensors and controls lamp, buzzer, relay fan, PWM, tachometer, and status lights.
- **Safety-first behavior**: gas, flame, and emergency test button override normal energy-saving logic.
- **Layered IoT architecture**: UNO edge node, ESP32 gateway, laptop MQTT broker/dashboard/AI service.
- **Operational dashboard**: live telemetry, charts, manual/auto mode, preset strategies, logs, ACK feedback, and command timeline.
- **AI command planner**: Qwen text/voice commands are converted into structured timed tasks such as "3 minutes later switch to manual mode".
- **Practical classroom use-case**: automatic lighting, ventilation, alarm signaling, and facility-style remote supervision.

## System Architecture

```text
Sensors / Actuators
  PIR, light, gas, flame, button, LED, buzzer, relay fan, PWM, tach, status light
        |
        v
Arduino UNO R3 - Edge Control Node
  - real-time sensor reading
  - mode state machine
  - actuator safety priority
  - UART telemetry / command ACK
        |
        | SoftwareSerial 9600 baud, SC2 CSV
        v
ESP32 - IoT Gateway
  - UART receiver/transmitter
  - Wi-Fi reconnect
  - MQTT publish/subscribe
  - ESP32-side LM35 ADC route on GPIO34
        |
        | MQTT over LAN
        v
Laptop Service Layer
  - local MQTT broker
  - Web dashboard
  - WebSocket live updates
  - HTTPS microphone endpoint
  - Qwen task planner
  - preference/data analytics
```

## Repository Map

```text
UNO_Phase3_TelemetryPatch/        Final UNO firmware with Phase 1+2+3 logic
ESP32_3B_MQTT_Gateway/            Final ESP32 MQTT gateway firmware
SmartClassroom_WebDashboard/      Node.js MQTT broker + web dashboard + AI endpoints
smart_ai/                         ASR and preference-model helper scripts
docs/                             Assembly checklist, presentation, demo support files
flash_uno.py                      Arduino CLI flashing helper for UNO
run_smartclassroom.py             One-command local environment launcher
smartclassroom_launcher.py        PySide6 launcher UI
NodeRED_Phase3D_Setup.md          Optional Node-RED/MQTT Explorer setup notes
```

## Hardware Summary

### Modules From the 48-Piece Kit Photo

| Photo No. | Module | Used In Current Build | Function |
|---:|---|---|---|
| #4 | Traffic Light Module | Yes | R/Y/G classroom status indicator |
| #5 | Active Buzzer Module | Yes | short alert and safety alarm pattern |
| #16 | Flame Sensor | Yes | flame DO/AO safety detection |
| #18 | PIR Motion Sensor | Yes | occupancy detection |
| #25 | Analog Gas Sensor | Yes | air/gas safety warning |
| #30 | TEMT6000 Light Sensor | Yes | ambient light detection |
| #39 | LM35 Temperature Sensor | Yes | temperature sensing, powered by ESP32 5V |
| #38 | 5V Single Relay Module | Replaced | current build uses a separate 6-port relay module |
| #7 | Digital Push Button Module | Not used | current build uses a bare 4-leg tactile button |

### Extra Hardware

- KS0001 Keyestudio UNO R3
- ESP32 development board
- 6-port relay module
- 12V 4-wire fan
- 12V 2A adapter
- discrete classroom LED + 220 ohm resistor
- bare emergency test button
- UART divider resistors: 10k ohm and 20k ohm
- LM35/ADC stabilizing pulldowns: 100k ohm on GPIO34 and GPIO35
- **No capacitors are used in the current assembly**

## Pin Map

### Arduino UNO

| Function | UNO Pin |
|---|---|
| PIR OUT | D2 |
| fan tach | D3 |
| emergency button | D4 |
| classroom LED | D5 |
| fan relay IN | D6 |
| active buzzer | D7 |
| flame DO | D8 |
| fan PWM | D9 |
| status red | D10 |
| status yellow | D11 |
| status green | D12 |
| light sensor SIG | A0 |
| gas sensor AO | A1 |
| legacy LM35 input | A2 |
| flame AO | A3 |
| UART RX from ESP32 | A4 |
| UART TX to ESP32 | A5 |

### ESP32

| Function | ESP32 Pin |
|---|---|
| UART RX2 from UNO A5 | GPIO16 |
| UART TX2 to UNO A4 | GPIO17 |
| LM35 OUT ADC | GPIO34 |
| dummy ADC reference | GPIO35 |
| unused UART TX guard | GPIO25 |

## Software Requirements

### Arduino

- `arduino-cli`
- Arduino AVR core for UNO
- ESP32 Arduino core
- UNO library: `SoftwareSerial` is built in for AVR
- ESP32 libraries: `WiFi.h`, `PubSubClient`, `Preferences`

### Dashboard

- Node.js 18+
- npm dependencies in `SmartClassroom_WebDashboard/package.json`
- Optional Python/Conda environment for ASR and preference analysis

## Quick Start

### 1. ESP32 credentials

Copy the example credential file:

```powershell
Copy-Item .\ESP32_3B_MQTT_Gateway\credentials.example.h .\ESP32_3B_MQTT_Gateway\credentials.h
```

Edit `credentials.h` for the laptop hotspot or router:

```cpp
#define SMARTCLASSROOM_WIFI_SSID "SmartClassroom-IoT"
#define SMARTCLASSROOM_WIFI_PASSWORD "12345678"
#define SMARTCLASSROOM_MQTT_HOST "192.168.137.1"
```

`credentials.h` is intentionally ignored by Git.

### 2. Flash UNO

```powershell
python .\flash_uno.py --sketch .\UNO_Phase3_TelemetryPatch
```

### 3. Flash ESP32

```powershell
arduino-cli --config-file .\arduino-cli-esp32.yaml compile --fqbn esp32:esp32:esp32 .\ESP32_3B_MQTT_Gateway
arduino-cli --config-file .\arduino-cli-esp32.yaml upload -p COM6 --fqbn esp32:esp32:esp32 --upload-property upload.speed=115200 .\ESP32_3B_MQTT_Gateway
```

Adjust `COM6` if the ESP32 port differs.

### 4. Run dashboard

```powershell
python .\run_smartclassroom.py
```

Dashboard URLs:

- Local: `http://localhost:3000`
- LAN HTTPS microphone endpoint: `https://<laptop-ip>:3443`

## Operating Modes

| Mode | Meaning |
|---|---|
| `NORMAL` | sensors normal, no active special behavior |
| `LIGHTING` | occupied and dark enough, classroom LED enabled |
| `COOLING` | temperature policy requests fan ventilation |
| `ENERGY_SAVING` | no occupancy or bright lockout, outputs reduced |
| `SAFETY_ALARM` | gas/flame/demo emergency overrides all normal logic |
| `SENSOR_ERROR` | sensor value is invalid or unsafe |
| `MANUAL` | dashboard or AI command manually controls actuators |

Safety alarm has the highest priority.

## MQTT Topics

Main telemetry:

```text
smartclassroom/edge1/telemetry
```

Key topics:

```text
smartclassroom/edge1/status
smartclassroom/edge1/mode
smartclassroom/edge1/safety/alarm
smartclassroom/edge1/sensors/occupancy
smartclassroom/edge1/sensors/light
smartclassroom/edge1/sensors/temperature
smartclassroom/edge1/sensors/gas
smartclassroom/edge1/sensors/flame
smartclassroom/edge1/actuators/lamp
smartclassroom/edge1/actuators/fan
smartclassroom/edge1/actuators/rpm
smartclassroom/edge1/actuators/status_light
smartclassroom/edge1/command
smartclassroom/edge1/command_ack
```

## Qwen Task Planner

The dashboard supports text and voice commands. Qwen returns a structured plan:

```json
{
  "confidence": 0.98,
  "reply": "Planned timed classroom actions.",
  "tasks": [
    {
      "action": "set_manual",
      "delaySec": 180,
      "manual": { "enabled": true, "fan": true, "pwm": 180, "status": "ALL" }
    },
    {
      "action": "return_auto",
      "delaySec": 300
    }
  ]
}
```

Supported planner actions:

- `noop`
- `wait`
- `return_auto`
- `set_manual`
- `set_auto_config`
- `preset`
- `command`

The dashboard automatically clears completed timelines after 30 seconds.

## Security and Privacy Notes

- API keys are stored server-side only in `SmartClassroom_WebDashboard/data/secrets.json` or environment variables.
- `data/secrets.json`, voice uploads, telemetry JSONL logs, certificates, and ESP32 `credentials.h` are ignored by Git.
- Voice input uses HTTPS for LAN devices because browser microphones require a secure context.
- The demo broker currently allows local anonymous MQTT for lab simplicity. A production version should add authentication, TLS, and role-based access.

## Demo Script

Recommended 10-minute flow:

1. Show architecture: UNO edge node, ESP32 gateway, laptop service layer.
2. Show live telemetry cards and charts.
3. Trigger occupancy/lighting and explain energy-saving behavior.
4. Raise temperature policy or manual fan to show ventilation.
5. Press emergency button to show safety alarm priority.
6. Use dashboard manual mode and command ACK.
7. Use Qwen text command with a timed task plan.
8. Close with practical classroom deployment and security/privacy notes.

## Known Prototype Boundaries

- LM35 analog sensing is sensitive to grounding and high-impedance ADC behavior; the current build powers LM35 from ESP32 5V and uses GPIO34/GPIO35 compensation with pulldown resistors.
- No capacitors are installed in the current classroom demo hardware.
- Asset monitoring is represented through operational state and device health indicators; a future version can add RFID, BLE tags, or accelerometer-based asset detection.
