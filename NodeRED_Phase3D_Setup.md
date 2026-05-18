# NodeRED_Phase3D_Setup

Project: Smart Classroom Energy-Saving, Safety & Asset Monitoring System

Phase 3 role:

- UNO R3: edge control node, all sensors/actuators/state machine
- ESP32: Wi-Fi + MQTT gateway, no direct sensor control
- Laptop: MQTT broker + MQTT Explorer + Node-RED / FlowFuse Dashboard

## 1. Mosquitto Broker

Create `C:\mosquitto\smartclassroom.conf`:

```conf
listener 1883 0.0.0.0
allow_anonymous true
persistence false
log_type all
```

Start broker:

```powershell
mosquitto -c C:\mosquitto\smartclassroom.conf -v
```

Expected log:

```text
Opening ipv4 listen socket on port 1883.
New client connected from ...
Received PUBLISH from smartclassroom-esp32-edge1
```

If Mosquitto is not installed, the included npm debug dashboard can also start an MQTT broker on port `1883`.

## 2. MQTT Explorer

Connection settings:

- Protocol: `mqtt://`
- Host: `192.168.137.1`
- Port: `1883`
- Username/password: empty
- Client ID: `mqtt-explorer-smartclassroom`

Topics to watch:

```text
smartclassroom/edge1/#
smartclassroom/edge1/telemetry
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
```

## 3. Node-RED Flow

Install Node-RED and FlowFuse Dashboard if needed:

```powershell
npm install -g node-red
cd ~/.node-red
npm install @flowfuse/node-red-dashboard
node-red
```

Flow structure:

```text
mqtt in -> json -> ui-template
```

`mqtt in` node:

- Server: `mqtt://192.168.137.1:1883`
- Topic: `smartclassroom/edge1/telemetry`
- Output: string

`json` node:

- Action: Always convert to JavaScript object

`ui-template` node:

- Group: Smart Classroom
- Size: full width preferred

## 4. FlowFuse Dashboard ui-template

Paste this into the FlowFuse Dashboard `ui-template` node:

```html
<template>
  <div class="sc-shell">
    <div class="sc-header">
      <div>
        <div class="sc-title">Smart Classroom Edge 1</div>
        <div class="sc-subtitle">MQTT Network & Dashboard Layer</div>
      </div>
      <div class="sc-badge" :class="alarm ? 'danger' : online ? 'ok' : 'warn'">
        {{ alarm ? 'SAFETY ALARM' : online ? payload.mode || 'ONLINE' : 'OFFLINE' }}
      </div>
    </div>

    <div class="sc-grid">
      <div class="sc-card">
        <span>Occupancy</span>
        <strong>{{ yesNo(payload.occupied || payload.pir) }}</strong>
        <small>PIR presence</small>
      </div>
      <div class="sc-card">
        <span>Light</span>
        <strong>{{ payload.light ?? '--' }}</strong>
        <small>{{ payload.dark ? 'dark' : 'bright' }}</small>
      </div>
      <div class="sc-card">
        <span>Temperature</span>
        <strong>{{ fmt(payload.temperatureC) }} C</strong>
        <small>LM35 corrected</small>
      </div>
      <div class="sc-card" :class="payload.gasDanger ? 'danger' : ''">
        <span>Gas</span>
        <strong>{{ payload.gas ?? '--' }}</strong>
        <small>{{ payload.gasDanger ? 'danger' : 'normal' }}</small>
      </div>
      <div class="sc-card" :class="payload.flameDetected ? 'danger' : ''">
        <span>Flame</span>
        <strong>{{ yesNo(payload.flameDetected) }}</strong>
        <small>DO {{ payload.flameDigital ?? '--' }} / AO {{ payload.flameAnalog ?? '--' }}</small>
      </div>
      <div class="sc-card">
        <span>Lamp</span>
        <strong>{{ yesNo(payload.lamp) }}</strong>
        <small>classroom LED</small>
      </div>
      <div class="sc-card">
        <span>Fan</span>
        <strong>{{ yesNo(payload.fan) }}</strong>
        <small>PWM {{ payload.pwm ?? '--' }}</small>
      </div>
      <div class="sc-card">
        <span>RPM</span>
        <strong>{{ payload.rpm ?? '--' }}</strong>
        <small>tach feedback</small>
      </div>
      <div class="sc-card">
        <span>Status Light</span>
        <strong>{{ colorName(payload.statusLight) }}</strong>
        <small>R/Y/G module</small>
      </div>
    </div>

    <pre class="sc-raw">{{ JSON.stringify(payload, null, 2) }}</pre>
  </div>
</template>

<script>
export default {
  computed: {
    payload() {
      return this.msg?.payload || {};
    },
    alarm() {
      return Number(this.payload.safetyAlarm || 0) === 1;
    },
    online() {
      return Boolean(this.payload.mode);
    }
  },
  methods: {
    yesNo(v) {
      return Number(v || 0) === 1 ? 'ON' : 'OFF';
    },
    fmt(v) {
      return v === undefined || v === null ? '--' : Number(v).toFixed(1);
    },
    colorName(v) {
      return v === 'R' ? 'RED' : v === 'Y' ? 'YELLOW' : v === 'G' ? 'GREEN' : '--';
    }
  }
}
</script>

<style>
.sc-shell { font-family: Inter, Segoe UI, sans-serif; color: #17202a; }
.sc-header { display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 16px; }
.sc-title { font-size: 24px; font-weight: 800; }
.sc-subtitle { color: #5d6d7e; }
.sc-badge { padding: 8px 12px; border-radius: 6px; font-weight: 800; background: #f8c471; color: #4d3512; }
.sc-badge.ok { background: #58d68d; color: #063b1d; }
.sc-badge.danger { background: #ec7063; color: #fff; }
.sc-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.sc-card { border: 1px solid #d5dbdb; border-left: 4px solid #3498db; border-radius: 6px; padding: 12px; background: #fff; }
.sc-card.danger { border-left-color: #e74c3c; background: #fff5f4; }
.sc-card span { display: block; color: #5d6d7e; font-size: 12px; }
.sc-card strong { display: block; font-size: 24px; margin-top: 4px; }
.sc-card small { color: #7f8c8d; }
.sc-raw { margin-top: 14px; padding: 12px; border-radius: 6px; background: #101820; color: #d6eaf8; overflow: auto; }
</style>
```

## 5. Test Order

1. 3A UART receiver
   - Burn `ESP32_3A_UART_Receiver_Test.ino`
   - Then burn UNO Phase3 patch
   - Expected: ESP32 Serial Monitor prints `RX from UNO: SC2,...`

2. 3B MQTT Gateway
   - Start Windows hotspot `SmartClassroom-IoT`
   - Start Mosquitto or npm debug broker
   - Burn `ESP32_3B_MQTT_Gateway.ino`
   - Expected: Serial Monitor shows Wi-Fi connected, MQTT connected

3. MQTT Explorer
   - Connect to `192.168.137.1:1883`
   - Expected: `smartclassroom/edge1/#` topics appear

4. Node-RED / FlowFuse Dashboard
   - Build `mqtt in -> json -> ui-template`
   - Expected: dashboard cards update each second

## 6. Troubleshooting

ESP32 receives no UART:

- Check common GND between UNO and ESP32.
- Check UNO A5/TX goes to ESP32 GPIO16/RX2.
- Check resistor divider on UNO TX to ESP32 RX.
- Burn UNO Phase3 patch; older UNO sketches do not output SC2 on A5.

ESP32 receives garbled text:

- UNO `espSerial.begin(9600)` and ESP32 `Serial2.begin(9600, SERIAL_8N1, 16, 17)` must match.
- Check 5V-to-3.3V divider; direct UNO TX can corrupt or damage ESP32 RX.

MQTT broker cannot connect:

- Confirm broker is running on `0.0.0.0:1883`.
- Confirm Windows hotspot IPv4 using `ipconfig`; change `MQTT_HOST` if not `192.168.137.1`.
- Allow port `1883` through Windows Firewall.

MQTT Explorer sees no topic:

- Subscribe to `smartclassroom/edge1/#`.
- Check ESP32 Serial Monitor for `MQTT connected`.
- If status is `uno_offline`, ESP32 is online but not receiving UNO telemetry.

Node-RED receives no data:

- Confirm `mqtt in` server is `192.168.137.1:1883`.
- Confirm topic is exactly `smartclassroom/edge1/telemetry`.
- Confirm `json` node is after `mqtt in`.

Dashboard page does not open:

- Start Node-RED and open the FlowFuse Dashboard URL shown in Node-RED.
- Check that `@flowfuse/node-red-dashboard` is installed.

Safety Alarm works on UNO but Dashboard does not update:

- Check UNO A5 to ESP32 GPIO16 UART wiring.
- Check ESP32 Serial Monitor for `RX from UNO: SC2,...`.
- Check MQTT topic `smartclassroom/edge1/telemetry`.

ESP32 reboots frequently:

- Use a stable USB cable and USB port.
- Do not power ESP32 from UNO 5V.
- Disconnect direct 5V UART into ESP32 RX; use the divider.
