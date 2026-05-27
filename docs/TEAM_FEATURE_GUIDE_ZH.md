# Smart Classroom 功能逻辑详解（给 4 位组员）

这份文件不是给老师看的“技术炫耀稿”，而是给组员现场分工和讲解用的说明书。目标很简单：每个人都能用最直白的话讲清楚系统有什么功能、每个功能从哪里输入、在哪里判断、最后控制了什么东西。

## 0. 一句话总览

这个系统是一个“本地优先”的智慧教室 IoT 原型。Arduino UNO 像教室里的本地控制器，负责实时读取传感器、判断安全/节能状态、直接控制灯、蜂鸣器、红黄绿灯和 12V 风扇。ESP32 像网络网关，负责把 UNO 的状态送到 MQTT/Web Dashboard，也把网页、语音、Qwen 产生的命令送回 UNO。电脑端负责可视化、配置、数据收集、偏好学习和语音/AI 操作。

## 1. 系统分层

| 层级 | 它是什么 | 直白解释 |
|---|---|---|
| 输入层 | PIR、光照、LM35、Gas、Flame、按钮、Tach | 系统看到的环境和人为操作。 |
| UNO 边缘控制层 | Arduino UNO R3 | 不等网络，直接决定“开灯、关灯、开风扇、报警”。 |
| ESP32 网关层 | ESP32 + UART + Wi-Fi + MQTT | 把 UNO 的状态发到网页，也把网页命令转给 UNO。 |
| Web 运维层 | Node.js Dashboard + MQTT Broker | 给人看的控制台，可以看数据、改阈值、手动控制、看图表。 |
| AI/数据层 | Qwen、faster-whisper、torch 偏好模型 | 把自然语言变成任务，把用户调参习惯变成推荐策略。 |

## 2. 最核心的设计思想

1. **安全优先**：Safety Alarm 的优先级最高。只要气体、火焰或 emergency button 触发，普通节能逻辑全部让路。
2. **本地优先**：UNO 不依赖网页也能工作。网络断了，安全报警、风扇、灯光仍然能由 UNO 控制。
3. **网络增强**：ESP32 和 Dashboard 不是替代 UNO，而是增加远程可视化、配置、记录和智能操作。
4. **可解释智能**：AI 不是聊天摆设。Qwen 输出结构化任务，Dashboard 有 timeline，任务执行完会自动清理。
5. **可现场验证**：每个功能都能用按钮、遮光、加热、网页命令或串口现象证明。

## 3. 功能一：有人且光线暗，自动开教室灯

### 这个功能能干嘛

当 PIR 检测到有人，并且 TEMT6000 光照传感器判断环境偏暗，UNO 会打开 D5 上的 LED，模拟教室灯自动亮起。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | PIR Motion Sensor 的 OUT 接 UNO D2。有人移动时 D2 读到 HIGH。 |
| 2 | TEMT6000 的 SIG 接 UNO A0。UNO 用 analogRead(A0) 得到 lightValue。 |
| 3 | UNO 把 lightValue 和阈值比较，判断 `isDark`。 |
| 4 | 如果 `occupied == true` 且 `isDark == true`，UNO 进入 LIGHTING 或 NORMAL+lighting 状态。 |
| 5 | UNO 输出 D5 HIGH，LED 亮。 |
| 6 | UNO 通过 UART telemetry 把 `pir`、`light`、`dark`、`lamp` 发给 ESP32。 |
| 7 | ESP32 发布 MQTT，Dashboard 卡片实时显示“有人、偏暗、灯已开”。 |

### 现场怎么演示

用手在 PIR 前移动，同时遮住光照传感器。LED 应该亮，网页上 occupancy/light/lamp 状态同步变化。

### 为什么有价值

它不是简单地“有人就开灯”，而是结合了“是否有人”和“是否真的暗”。如果环境已经很亮，系统不会浪费电开灯。

## 4. 功能二：无人超过 10 秒，自动关灯节能

### 这个功能能干嘛

如果 PIR 一段时间没有检测到人，UNO 会在超过 10 秒后关闭教室 LED，进入节能状态。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | PIR 从 HIGH 变成 LOW。 |
| 2 | UNO 记录最后一次有人时间 `lastMotionMs`。 |
| 3 | 主循环用 millis() 非阻塞计时，不使用 delay() 卡死系统。 |
| 4 | 如果当前时间 - lastMotionMs 大于 10 秒，判断为无人。 |
| 5 | UNO 关闭 D5 LED。 |
| 6 | 系统模式可能显示 ENERGY_SAVING。 |
| 7 | Dashboard 收到 telemetry 后显示灯关闭、节能状态。 |

### 现场怎么演示

先触发 PIR 让灯亮，然后人离开或保持静止，等待大约 10 秒，灯会自动熄灭。

### 为什么有价值

真实教室里最常见的浪费就是没人还开灯。这个逻辑直接对应节能场景。

## 5. 功能三：温度升高时风扇逐步增强，而不是一下最大

### 这个功能能干嘛

LM35 温度由 ESP32 ADC 读取，温度超过阈值后，UNO 控制继电器给 12V 风扇上电，并通过 D9 PWM 控制风扇强度。温度越高，PWM 越大；温度下降时，风量也逐步降低。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | LM35 VCC 接 ESP32 5V/VIN，GND 接 ESP32 GND，OUT 接 ESP32 GPIO34。 |
| 2 | ESP32 用 ADC1 读取 GPIO34，并结合 GPIO35 dummy reference 做补偿。 |
| 3 | ESP32 将温度结果随 telemetry 或 UART command 送给 UNO。 |
| 4 | UNO 判断温度是否超过 fanOnC。超过后打开 D6 继电器，12V 风扇通电。 |
| 5 | UNO 根据温度和策略输出 D9 PWM。温度越高，PWM 越大。 |
| 6 | 温度低于 fanOffC 后，UNO 关闭风扇继电器。 |
| 7 | Fan Yellow Tach 接 D3 interrupt，UNO 估算 RPM。 |
| 8 | Dashboard 显示 temperature、fan、pwm、rpm、fan health。 |

### 现场怎么演示

用手靠近 LM35 或改变阈值，让温度高于启动阈值。风扇会启动，网页上 fan/pwm/rpm 变化。降低阈值或等待温度下降，风扇逐步减弱或关闭。

### 为什么有价值

真实环境不应该一超过阈值就满速吹。渐进控制更舒适，也更像商业楼宇里的 HVAC 控制逻辑。

## 6. 功能四：Gas / Flame / Button 触发安全报警

### 这个功能能干嘛

当气体传感器、火焰传感器或 emergency button 触发时，系统进入 SAFETY_ALARM。此时红灯亮，蜂鸣器间歇报警，风扇强制高转，普通节能逻辑让路。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | Gas Sensor AO 接 UNO A1，UNO 读取 gasValue。 |
| 2 | Flame Sensor DO 接 UNO D8，AO 接 UNO A3。UNO 同时读数字和模拟火焰值。 |
| 3 | Emergency Button 接 UNO D4，使用 INPUT_PULLUP，按下为 LOW。 |
| 4 | UNO 判断 `gasDanger || flameDetected || demoEmergency`。 |
| 5 | 一旦为 true，系统模式强制变成 SAFETY_ALARM。 |
| 6 | UNO 控制 D10/D11/D12 让红灯亮。 |
| 7 | UNO 控制 D7 蜂鸣器间歇响，避免持续刺耳。 |
| 8 | UNO 控制 D6 继电器打开风扇，D9 PWM 输出高值。 |
| 9 | ESP32/Dashboard 显示 mode=SAFETY_ALARM，并记录事件。 |

### 现场怎么演示

按 D4 emergency button。红灯亮，蜂鸣器间歇响，风扇强制运行，网页显示 Safety Alarm。

### 为什么有价值

这证明项目不是只读传感器，而是有“优先级状态机”和真实执行器响应。

## 7. 功能五：红黄绿状态灯让现场一眼看懂模式

### 这个功能能干嘛

Traffic Light Module 用红、黄、绿三色表达系统状态。即使不看网页，也能知道系统处于正常、节能/降温、还是报警。

### 状态规则

| 模式 | 灯色 | 直白解释 |
|---|---|---|
| NORMAL | 绿 | 系统正常，没有特别动作。 |
| LIGHTING | 绿 | 有人且暗，正在开灯。 |
| COOLING | 黄 | 温度较高，正在通风降温。 |
| ENERGY_SAVING | 黄 | 无人或节能策略生效。 |
| SAFETY_ALARM | 红 | 安全报警，最高优先级。 |
| SENSOR_ERROR | 红闪 | 传感器异常，需要检查。 |
| Manual Mode | 三灯全亮 | 人工接管，网页正在直接控制设备。 |

## 8. 功能六：Dashboard 手动模式

### 这个功能能干嘛

网页可以切换自动/手动。手动模式下，用户可以控制灯、风扇、PWM、蜂鸣器、红黄绿灯。为了现场可见，手动模式可以让三个状态灯全亮。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | 用户在网页打开 Manual Mode。 |
| 2 | Dashboard 保存 manual settings。 |
| 3 | Dashboard 通过 MQTT 发布 command。 |
| 4 | ESP32 订阅 command topic，收到后通过 UART 发给 UNO。 |
| 5 | UNO 执行命令，控制 D5/D6/D7/D9/D10/D11/D12。 |
| 6 | UNO 回传 ACK。 |
| 7 | ESP32 把 ACK 发布到 MQTT，Dashboard 显示命令是否落地。 |

### 为什么有价值

自动系统一定要保留人工 override。现实教室里，老师或管理员应该能临时接管设备。

## 9. 功能七：Web 配置阈值并永久保存

### 这个功能能干嘛

网页能修改风扇启动温度、停止温度、灯光亮度阈值、状态灯亮度等参数。点击 apply 后，配置立即生效，并保存到本地数据文件，下次启动仍然保留。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | 用户在 Dashboard 输入新阈值。 |
| 2 | Node.js 后端校验数值范围，避免危险或无效配置。 |
| 3 | 后端保存 settings.json。 |
| 4 | 后端将配置命令排入 command queue。 |
| 5 | ESP32 将命令通过 UART 发给 UNO。 |
| 6 | UNO 更新运行参数并 ACK。 |
| 7 | Dashboard 显示最新配置和 ACK。 |

## 10. 功能八：MQTT 网络层

### 这个功能能干嘛

UNO 每秒输出一行 SC2 telemetry，ESP32 解析后发布 MQTT JSON 和多个关键 topic。网页从 MQTT broker 得到实时状态。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | UNO 通过 SoftwareSerial A5/A4 输出 `SC2,mode=...,temp10=...,fan=...`。 |
| 2 | ESP32 Serial2 GPIO16/17 接收。 |
| 3 | ESP32 解析 key=value 字段。 |
| 4 | ESP32 发布完整 JSON 到 `smartclassroom/edge1/telemetry`。 |
| 5 | ESP32 同时发布 mode、temperature、gas、fan、rpm 等关键 topic。 |
| 6 | Node.js MQTT broker 接收消息，Dashboard WebSocket 推送给浏览器。 |
| 7 | 如果 UNO 超过 5 秒无数据，ESP32 发布 `uno_offline`。 |

### 为什么有价值

这体现了真正的 IoT 架构：本地设备、网关、消息总线、Dashboard 分层清晰。

## 11. 功能九：语音控制与 Qwen 多步任务

### 这个功能能干嘛

用户可以在网页按按钮录音，或直接输入文字。faster-whisper 把语音转成文字，Qwen 把自然语言变成结构化任务时间轴，例如“3 分钟后切换手动模式，再把风扇 PWM 调到 180”。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | 手机或电脑浏览器通过 HTTPS microphone page 录音。 |
| 2 | Web 后端把音频传给本地 AI 后端。 |
| 3 | faster-whisper 在 GPU 可用时用 CUDA 转文字，失败时回退 CPU。 |
| 4 | 文本送到 Qwen compatible API。 |
| 5 | Qwen 只返回 JSON，不输出闲聊文字。 |
| 6 | 后端把 JSON 转成 task plan，每个任务都有 action、delaySec、参数。 |
| 7 | Dashboard 显示 timeline。 |
| 8 | 到时间后，后端执行任务，发送 MQTT command。 |
| 9 | ESP32 转发给 UNO，UNO 执行并 ACK。 |
| 10 | 任务全部完成后，timeline 自动清除。 |

### 为什么有价值

AI 不是“聊天机器人挂件”。它把人类语言转换成可执行的设备任务，这才有工程价值。

## 12. 功能十：数据收集与偏好学习

### 这个功能能干嘛

Dashboard 可以收集运行数据和用户调参记录。torch 脚本根据温度、占用、灯光、风扇状态和用户偏好，推荐下一组阈值。

### 逻辑链路

| 步骤 | 发生了什么 |
|---|---|
| 1 | 用户点击 Collect Data。 |
| 2 | 后端把 telemetry 写入 telemetry_samples.jsonl。 |
| 3 | 用户改配置、切换预设、手动控制时，后端写入 preference_events.jsonl。 |
| 4 | Analytics 调用 torch 脚本读取最近样本。 |
| 5 | 脚本计算温度分布、占用比例、风扇工作比例、光照分位数。 |
| 6 | 输出 recommendedAuto。 |
| 7 | 用户可以一键应用推荐。 |

### 为什么有价值

商业系统不能永远靠固定阈值。收集真实使用偏好后，系统可以逐渐变得更适合这个教室。

## 13. 四个人怎么分工讲

| 组员 | 建议负责 | 最重要要讲清楚的话 |
|---|---|---|
| 组员 1 | Use case + 总架构 | 这是一个本地优先的智慧教室，不是传感器堆叠。 |
| 组员 2 | UNO + 硬件控制 | UNO 负责实时状态机、安全优先级和执行器。 |
| 组员 3 | ESP32 + MQTT | ESP32 是网关，负责 UART、Wi-Fi、MQTT 和 ACK。 |
| 组员 4 | Dashboard + AI/数据 | 网页负责运维、配置、图表、语音、Qwen timeline 和偏好学习。 |

## 14. 现场介绍优先级

1. **先演示 Safety Alarm**：按按钮，红灯、蜂鸣器、风扇都动。这最抓人。
2. **再讲本地优先架构**：UNO 不依赖网络也能保证安全。
3. **再演示节能逻辑**：有人且暗才开灯，无人 10 秒关灯。
4. **再演示温控风扇**：温度阈值、PWM、RPM、风扇健康。
5. **再讲 MQTT/Dashboard**：显示实时卡片、图表、ACK、配置保存。
6. **最后讲 AI/数据**：语音命令、Qwen timeline、偏好推荐。

## 15. 最直白的总结话术

如果老师问“你们这个系统到底强在哪里”，可以这样回答：

> 我们不是只把很多传感器接到板子上读数，而是做了一个完整 IoT 闭环。UNO 在本地做实时安全和节能控制，ESP32 做 MQTT 网关，电脑 Dashboard 做运维、配置和数据分析。安全报警优先级最高，网络断了也不影响本地安全。网页和 AI 只是增强能力，不会替代本地控制。

## 16. 现场不要说错的点

- 不要说 ESP32 是主控。主控边缘控制是 UNO，ESP32 是网关。
- 不要说 AI 控制硬件。AI 生成任务，最终仍由后端、ESP32、UNO 执行并 ACK。
- 不要说网页断了系统就不能用。UNO 仍可本地运行。
- 不要说 LM35 接 UNO。当前最终方案是 LM35 由 ESP32 5V/VIN 供电，OUT 到 GPIO34。
- 不要说加了电容。当前实物版本没有安装电容。
