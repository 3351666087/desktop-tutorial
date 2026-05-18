# Smart Classroom 环境拉取与运行说明

本文档给组员用于从零拉取环境、烧录代码、运行 Web Dashboard。当前项目已经把真实 Wi-Fi / Qwen API key / 本地运行数据排除在交付包外，现场需要按说明填写本机配置。

## 1. 项目结构

| 目录 / 文件 | 作用 |
|---|---|
| `UNO_Phase3_TelemetryPatch/` | Arduino UNO 最终固件：传感器、状态机、继电器、蜂鸣器、红绿灯、UART telemetry |
| `ESP32_3B_MQTT_Gateway/` | ESP32 最终固件：UART、Wi-Fi、MQTT、LM35 ADC on GPIO34/GPIO35 |
| `SmartClassroom_WebDashboard/` | Node.js 本地 MQTT broker + Web Dashboard + WebSocket + Qwen/voice 接口 |
| `smart_ai/` | faster-whisper / 偏好模型辅助脚本 |
| `docs/` | PPT、组装 PDF、演示脚本、中文说明 |
| `flash_uno.py` | UNO 自动编译/烧录脚本 |
| `run_smartclassroom.py` | 一键启动本地 Web Dashboard |
| `smartclassroom_launcher.py` | PySide6 启动器 UI |

## 2. 必装软件

| 软件 | 用途 | 备注 |
|---|---|---|
| Arduino CLI | 编译 / 烧录 UNO 和 ESP32 | 当前电脑用 Scoop 安装过 `arduino-cli` |
| Node.js 18+ | 运行 Web Dashboard | `node -v` 检查版本 |
| Python 3.10+ 或 Conda | 运行启动脚本、ASR、偏好模型 | 推荐单独建 conda 环境 |
| Git | 拉取代码 / 查看版本 | 可选但推荐 |
| CP210x / CH340 驱动 | ESP32 / UNO 串口识别 | 如果看不到 COM 口再装 |

## 3. Arduino CLI Core / Library

如果是新电脑，先安装 Arduino AVR core 和 ESP32 core。

```powershell
arduino-cli core update-index
arduino-cli core install arduino:avr

arduino-cli config init --overwrite
arduino-cli config set board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32
```

ESP32 固件还需要 `PubSubClient`：

```powershell
arduino-cli lib install PubSubClient
```

UNO 使用 `SoftwareSerial`，这是 AVR 内置库，不需要额外安装。

## 4. Node.js Dashboard 环境

进入 Web Dashboard 目录安装依赖：

```powershell
cd SmartClassroom_WebDashboard
npm install
cd ..
```

运行：

```powershell
python .\run_smartclassroom.py
```

默认服务：

| 服务 | 地址 |
|---|---|
| Web Dashboard | `http://localhost:3000` |
| LAN Dashboard | `http://<电脑局域网IP>:3000` |
| HTTPS microphone page | `https://<电脑局域网IP>:3443` |
| MQTT broker | `<电脑局域网IP>:1883` |

## 5. ESP32 Wi-Fi / MQTT 配置

复制示例配置：

```powershell
Copy-Item .\ESP32_3B_MQTT_Gateway\credentials.example.h .\ESP32_3B_MQTT_Gateway\credentials.h
```

编辑 `ESP32_3B_MQTT_Gateway/credentials.h`：

```cpp
#define SMARTCLASSROOM_WIFI_SSID "SmartClassroom-IoT"
#define SMARTCLASSROOM_WIFI_PASSWORD "12345678"
#define SMARTCLASSROOM_MQTT_HOST "192.168.137.1"
```

说明：

- `credentials.h` 不会进入 Git，也不会进入公开交付。
- 如果使用 Windows 热点，常见 MQTT host 是 `192.168.137.1`。
- 如果使用路由器，运行 `ipconfig` 找电脑当前 IPv4 地址，然后填到 `SMARTCLASSROOM_MQTT_HOST`。

## 6. 烧录 UNO

先插 UNO，查看 COM 口：

```powershell
arduino-cli board list
```

自动烧录：

```powershell
python .\flash_uno.py --sketch .\UNO_Phase3_TelemetryPatch
```

如果脚本没有自动识别端口，可以手动指定：

```powershell
arduino-cli compile --fqbn arduino:avr:uno .\UNO_Phase3_TelemetryPatch
arduino-cli upload -p COMx --fqbn arduino:avr:uno .\UNO_Phase3_TelemetryPatch
```

把 `COMx` 换成实际 UNO 端口。

## 7. 烧录 ESP32

先插 ESP32，查看 COM 口：

```powershell
arduino-cli board list
```

编译：

```powershell
arduino-cli --config-file .\arduino-cli-esp32.yaml compile --fqbn esp32:esp32:esp32 .\ESP32_3B_MQTT_Gateway
```

上传：

```powershell
arduino-cli --config-file .\arduino-cli-esp32.yaml upload -p COMx --fqbn esp32:esp32:esp32 --upload-property upload.speed=115200 .\ESP32_3B_MQTT_Gateway
```

把 `COMx` 换成 ESP32 实际端口。

## 8. Qwen / Voice 可选配置

Dashboard 支持 Qwen text/voice command planner，但 API key 不放在代码包里。

推荐用环境变量：

```powershell
$env:DASHSCOPE_API_KEY="你的key"
python .\run_smartclassroom.py
```

或者在 Dashboard 页面里通过本地配置写入 `SmartClassroom_WebDashboard/data/secrets.json`。该目录默认被忽略，不会上传。

语音识别依赖 faster-whisper。如果本机已有 conda 环境，可在对应环境里安装：

```powershell
pip install faster-whisper
```

没有语音环境也不影响主系统运行，文本命令和 Dashboard 手动控制仍可用。

## 9. 推荐现场启动顺序

1. 接好所有 GND：UNO GND、ESP32 GND、12V adapter - 必须共地。
2. 开电脑热点或连接同一局域网。
3. 运行 `python .\run_smartclassroom.py`，确认 Dashboard 打开。
4. 给 ESP32 上电，等 Dashboard 显示 ESP32 / MQTT online。
5. 给 UNO 上电，等 telemetry 每秒更新。
6. 最后接入 12V fan adapter。
7. 等待 10-20 秒，让 LM35 / ADC / telemetry 稳定。

## 10. 成功现象

| 项目 | 成功现象 |
|---|---|
| ESP32 | Serial Monitor 显示 Wi-Fi connected / MQTT connected |
| UNO | Serial 每秒输出状态，Dashboard telemetry age 小于 2 秒 |
| Dashboard | WebSocket connected，MQTT online，卡片和图表持续更新 |
| 灯光 | 人体 + 暗光时 LED 亮，亮光/无人时熄灭 |
| 风扇 | 温度策略或安全报警触发时继电器和 PWM 工作 |
| 安全报警 | 按 D4 emergency button 后红灯、蜂鸣器、风扇高档 |
| Qwen timeline | 文本命令生成任务时间轴，执行后自动清除 |

## 11. 常见问题

| 问题 | 处理 |
|---|---|
| Dashboard 打不开 | 确认 `npm install` 完成；检查 3000 端口是否被占用 |
| ESP32 MQTT offline | 检查 `credentials.h` 的 SSID / password / MQTT host；确认电脑和 ESP32 在同一网络 |
| ESP32 收不到 UNO telemetry | 检查 UNO A5 -> 10k -> ESP32 GPIO16，GPIO16 -> 20k -> GND，且 UNO/ESP32 共地 |
| Dashboard 点按钮无效 | 检查 ESP32 GPIO17 -> UNO A4；看 ACK 是否更新 |
| 温度异常高 | LM35 VCC 接 ESP32 5V/VIN；OUT 接 GPIO34；GPIO34/GPIO35 100k 下拉存在 |
| 风扇不转 | 检查 12V adapter、继电器 COM/NO、风扇 Red/Black、共地 |
| 红绿灯不亮 | 检查 R/Y/G 是否分别接 D10/D11/D12，GND 是否接 UNO GND |

## 12. GitHub

当前代码已经推送到：

```text
https://github.com/3351666087/desktop-tutorial
```

建议后续把仓库重命名为：

```text
smart-classroom-iot104tc
```
