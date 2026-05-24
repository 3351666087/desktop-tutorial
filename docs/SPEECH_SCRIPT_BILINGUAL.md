# Smart Classroom 中英双语演讲稿

建议时长：8 到 10 分钟。  
讲解策略：先证明本地安全与边缘控制，再讲 IoT 网络和 Dashboard，最后讲 AI 与数据。不要一开始就讲 AI。

## 0:00-0:45 开场 / Opening

**中文**

大家好，我们的项目是 **Smart Classroom Energy-Saving, Safety & Asset Monitoring System**。它不是一个单独传感器实验，而是一个小型智慧教室 IoT 服务。系统由 Arduino UNO、ESP32 和电脑端 Dashboard 组成：UNO 负责本地实时控制，ESP32 负责网络和 MQTT，电脑网页负责可视化、配置、数据分析和语音/AI 操作。

**English**

Good morning. Our project is the **Smart Classroom Energy-Saving, Safety and Asset Monitoring System**. It is not just a single-sensor lab exercise; it is a small IoT service for a classroom. The system has three layers: Arduino UNO for local real-time control, ESP32 for network and MQTT gateway, and a laptop dashboard for visualization, configuration, analytics, and voice or AI operation.

## 0:45-1:45 系统架构 / Architecture

**中文**

我们最重要的架构决策是“本地优先”。UNO 是 Edge Control Node，所有和安全、节能、执行器有关的实时逻辑都在 UNO 上运行。ESP32 不直接接传感器，也不直接控制继电器，它只通过 UART 接收 UNO 的 telemetry，再发布到 MQTT。这样即使 Wi-Fi 或网页断开，安全报警、风扇、灯和蜂鸣器仍然可以在 UNO 上独立工作。

**English**

The most important architecture decision is **local-first control**. The UNO is the edge control node. All real-time safety, energy-saving, and actuator logic runs on the UNO. The ESP32 does not directly read the sensors or drive the relay. It receives telemetry from the UNO through UART and publishes it to MQTT. Therefore, even if Wi-Fi or the web dashboard is offline, the safety alarm, fan, lamp, and buzzer can still work locally.

## 1:45-2:45 硬件层 / Hardware Layer

**中文**

硬件输入包括 PIR 人体传感器、TEMT6000 光照传感器、LM35 温度传感器、Gas Sensor、Flame Sensor，以及紧急测试按钮。输出包括 LED 模拟教室灯、继电器控制 12V 风扇、D9 风扇 PWM、D3 Tach 转速反馈、蜂鸣器和红黄绿状态灯。这里还有一个实际工程问题：LM35 最终由 ESP32 的 5V 供电后漂移明显改善，这说明我们不仅写了代码，也做了硬件调试和电源问题排查。

**English**

The inputs include a PIR motion sensor, TEMT6000 light sensor, LM35 temperature sensor, gas sensor, flame sensor, and emergency test button. The outputs include an LED classroom lamp, a relay-controlled 12V fan, fan PWM on D9, tachometer feedback on D3, a buzzer, and a red-yellow-green status light module. One real engineering issue was the LM35 drift. After powering the LM35 from the ESP32 5V pin, the drift improved significantly. This shows that the project includes real hardware debugging, not only software coding.

## 2:45-4:00 UNO 边缘控制 / UNO Edge Control

**中文**

UNO 的程序不是阻塞式 delay，而是用 millis 运行周期任务。主循环分为 readSensors、updateButton、updateControlLogic、applyActuators、updateBuzzer、updateSerialOutput 和 sendTelemetryToESP32。系统模式包括 NORMAL、LIGHTING、COOLING、ENERGY_SAVING、SAFETY_ALARM 和 SENSOR_ERROR。优先级最高的是 SAFETY_ALARM，其次才是传感器错误、降温、照明、节能和正常状态。

**English**

The UNO firmware is non-blocking. It uses millis instead of long delay calls. The main loop is organized into readSensors, updateButton, updateControlLogic, applyActuators, updateBuzzer, updateSerialOutput, and sendTelemetryToESP32. The system modes include NORMAL, LIGHTING, COOLING, ENERGY_SAVING, SAFETY_ALARM, and SENSOR_ERROR. The highest priority is SAFETY_ALARM, followed by sensor error, cooling, lighting, energy-saving, and normal monitoring.

## 4:00-5:10 安全报警演示 / Safety Alarm Demo

**中文**

现在我们先演示最高优先级的 Safety Alarm。触发条件有三个：气体浓度超过阈值、火焰传感器检测到火焰、或者按下紧急测试按钮。为了安全，我们现场只按按钮模拟。当 Safety Alarm 触发时，系统会进入红灯状态，蜂鸣器间歇报警，风扇继电器强制打开，PWM 设置为高值，同时 Serial 和 MQTT 都会输出报警状态。这个逻辑会覆盖其他节能逻辑。

**English**

Now we demonstrate the highest-priority Safety Alarm. It can be triggered by three conditions: gas value above threshold, flame detection, or the emergency test button. For safety, we use the button for the live demo. When Safety Alarm is triggered, the red status light turns on, the buzzer beeps intermittently, the fan relay is forced on, PWM goes high, and both Serial and MQTT report the warning state. This logic overrides all other energy-saving behavior.

## 5:10-6:10 节能与舒适 / Energy Saving and Comfort

**中文**

没有安全报警时，系统会进入节能舒适逻辑。如果有人并且光线暗，教室灯会打开；如果环境光足够亮，即使 PIR 检测到人，灯也不会浪费电。无人超过设定时间后，灯会关闭。温度方面，风扇不是简单地一直开或一直关，而是根据阈值和 PWM 控制保持舒适。Tach RPM 使用中断读取，如果读不到 RPM，不会阻塞整个系统。

**English**

When there is no safety alarm, the system uses the energy-saving and comfort logic. If someone is present and the room is dark, the classroom lamp turns on. If ambient light is already bright enough, the lamp stays off even when motion is detected. After the room is unoccupied for the timeout period, the lamp turns off. For cooling, the fan is controlled by temperature thresholds and PWM instead of being only fully on or fully off. Tach RPM is read by interrupt, and if RPM is unavailable, the system still continues working.

## 6:10-7:20 ESP32 + MQTT / ESP32 and MQTT

**中文**

UNO 每秒输出一行 SC2 telemetry，例如 mode、pir、light、temp、gas、flame、fan、pwm、rpm 和 status。ESP32 用 Serial2 接收这行数据，解析后发布完整 JSON 到 MQTT topic，同时把关键字段拆分成多个 topic。ESP32 也负责接收 Dashboard 的配置命令，再通过 UART 发回 UNO。UNO 会返回 ACK，所以网页可以知道配置是否真正生效。

**English**

The UNO sends one SC2 telemetry line every second, including mode, PIR, light, temperature, gas, flame, fan, PWM, RPM, and status. The ESP32 receives this line through Serial2, parses it, and publishes a full JSON message to MQTT. It also publishes key fields into separate MQTT topics. The ESP32 receives configuration commands from the dashboard and sends them back to the UNO through UART. The UNO replies with ACK, so the dashboard knows whether the command was actually applied.

## 7:20-8:30 Web Dashboard / Dashboard

**中文**

Dashboard 是运维入口。它可以显示当前模式、传感器数值、风扇状态、灯状态、红黄绿灯状态、实时图表和历史趋势。它支持自动/手动模式切换，手动模式下可以控制灯、风扇、蜂鸣器、状态灯和阈值。配置会永久保存，点击 Apply 后会通过 MQTT 和 UART 立即下发。网页也做了移动端适配，手机连入同一局域网后可以打开并操作。

**English**

The dashboard is the operations interface. It displays the current mode, sensor values, fan state, lamp state, traffic light state, live charts, and historical trends. It supports automatic and manual mode switching. In manual mode, the operator can control the lamp, fan, buzzer, status light, and thresholds. The configuration is persisted, and when Apply is clicked, the command is sent immediately through MQTT and UART. The dashboard is also mobile-friendly, so a phone on the same local network can open and operate it.

## 8:30-9:25 AI、语音与数据 / AI, Voice and Data

**中文**

AI 模块的重点不是聊天，而是把自然语言转成结构化多步骤任务。例如用户说“三分钟后切换为手动模式并把风扇调高”，Qwen 会输出带时间轴的结构化任务。系统执行完成后会自动清除时间轴任务。语音输入可以通过网页麦克风按钮采集，再接 faster-whisper 转文字。我们还加入了数据收集和偏好统计，为后续预测舒适区间、优化节能策略提供基础。

**English**

The AI module is not just a chatbot. Its purpose is to convert natural language into structured multi-step tasks. For example, if a user says, “switch to manual mode in three minutes and increase the fan,” Qwen generates a structured timeline task. After the task is completed, it is automatically cleared. Voice input can be captured through the browser microphone button and transcribed by faster-whisper. We also added data collection and preference statistics, which provide a foundation for future comfort prediction and energy strategy optimization.

## 9:25-10:00 总结 / Closing

**中文**

总结一下，这个项目的强点是系统完整：有传感器输入，有本地边缘控制，有真实执行器，有安全报警最高优先级，有 ESP32 网络网关，有 MQTT，有 Dashboard，有移动端，有数据分析，也有 AI 结构化任务。它体现了 IoT application/service、hardware/software components、architecture、security/privacy、operations 和 practical use-case。

**English**

To summarize, the strength of this project is system completeness. It has sensor inputs, local edge control, real actuators, highest-priority safety alarm, ESP32 network gateway, MQTT, dashboard, mobile support, data analytics, and AI structured task planning. It demonstrates an IoT application and service, hardware and software components, architecture, security and privacy considerations, operations, and a practical classroom use-case.

## 备用问答 / Backup Q&A

**Q: 为什么不用 ESP32 直接控制所有东西？**  
中文：因为 UNO 已经连接所有实时硬件，控制逻辑本地运行更稳定；ESP32 做网关，架构更清晰。  
English: Because the UNO already owns the real-time hardware loop. Keeping local control on the UNO is more robust, while the ESP32 acts as a clean IoT gateway.

**Q: 如果网络断了怎么办？**  
中文：安全报警、灯、风扇和蜂鸣器仍在 UNO 本地工作；网页只是失去远程监控和配置能力。  
English: Safety alarm, lamp, fan, and buzzer still work locally on the UNO. Only remote monitoring and configuration are unavailable.

**Q: AI 有什么真实价值？**  
中文：AI 把自然语言转成可执行的多步骤控制任务，尤其适合非技术人员操作教室设备。  
English: AI converts natural language into executable multi-step control tasks, which is useful for non-technical classroom operators.

**Q: 项目后续怎么变成产品？**  
中文：可以增加 MQTT 认证、TLS、外壳、保险丝、继电器隔离、电源滤波、真实照明负载和长期数据模型。  
English: The next steps would be MQTT authentication, TLS, enclosure, fuse protection, relay isolation, power filtering, real lighting loads, and a longer-term data model.
