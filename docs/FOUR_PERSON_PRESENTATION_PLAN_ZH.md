# Smart Classroom 四人演示分工说明

这份文件只解决一个问题：**现场 4 个人怎么讲、怎么配合、每个人负责什么功能。**  
建议总时长 8 到 10 分钟。不要四个人平均乱分，每个人都要有清晰角色。

## 总体分工

| 人员 | 角色 | 主要负责 | 建议时间 |
|---|---|---|---|
| Speaker 1 | 项目负责人 / 架构开场 | Use case、系统目标、整体架构、本地优先思想 | 0:00-2:00 |
| Speaker 2 | UNO + 硬件控制 | 传感器、执行器、安全报警、节能和温控逻辑 | 2:00-4:30 |
| Speaker 3 | ESP32 + IoT 网络 | UART、MQTT、ACK、Wi-Fi、温度 ADC、电源/接线关键点 | 4:30-6:30 |
| Speaker 4 | Dashboard + AI + 数据 | Web 控制台、手动模式、图表、Qwen、语音、偏好学习、总结 | 6:30-9:30 |

## Speaker 1：项目目标与总架构

### 你要讲清楚什么

你负责让老师先明白这个项目不是“传感器读数合集”，而是一个完整 IoT classroom service。

### 推荐讲法

1. 我们的项目叫 Smart Classroom Energy-Saving, Safety & Asset Monitoring System。
2. 它解决三个实际问题：节能、安全、设备运维监控。
3. UNO 是本地边缘控制节点，负责实时控制。
4. ESP32 是 IoT Gateway，负责 Wi-Fi、MQTT 和命令转发。
5. Laptop 是运维层，负责 Dashboard、数据、AI 和语音。
6. 最重要的架构思想是 local-first：网络断了，安全和基础控制仍然能工作。

### 你对应的 PPT

- 第 1 页：项目名称和系统亮点。
- 第 2 页：课程要求与 project fit。
- 第 3 页：整体系统架构。

### 你可以说的直白话

> 我们不是把所有东西都堆到网页上控制。真正的安全和节能逻辑在 UNO 本地运行，ESP32 和网页只是增强可视化、配置和远程操作。

### 你交给 Speaker 2 的话

> 下面让我的组员介绍 UNO 这一层，它是我们系统里真正直接控制硬件的部分。

## Speaker 2：UNO、传感器、执行器和 Safety Alarm

### 你要讲清楚什么

你负责证明系统有真实硬件闭环：传感器输入经过 UNO 状态机，最后控制灯、风扇、蜂鸣器和红黄绿灯。

### 推荐讲法

1. 输入包括 PIR、光照、LM35 温度、Gas、Flame、Emergency Button。
2. 输出包括 LED 灯、继电器风扇、PWM、Tach RPM、蜂鸣器、红黄绿状态灯。
3. UNO 主循环不使用长 delay，而是用 millis() 非阻塞运行。
4. UNO 有状态机：NORMAL、LIGHTING、COOLING、ENERGY_SAVING、SAFETY_ALARM、SENSOR_ERROR。
5. Safety Alarm 优先级最高，气体、火焰或按钮触发后，红灯亮、蜂鸣器响、风扇强制开启。
6. 节能逻辑：有人且暗才开灯，无人超过 10 秒关灯。
7. 温控逻辑：温度高风扇启动，PWM 可调，Tach 可读 RPM。

### 现场演示动作

| 演示 | 你做什么 | 正常现象 |
|---|---|---|
| Safety Alarm | 按 emergency button | 红灯亮，蜂鸣器间歇响，风扇强制运行 |
| 自动灯光 | 遮住光照传感器并触发 PIR | LED 亮，Dashboard lamp 状态变化 |
| 节能关灯 | 不触发 PIR 等约 10 秒 | LED 关闭，模式偏 ENERGY_SAVING |
| 温控风扇 | 调低风扇启动阈值或加热 LM35 | 风扇启动，PWM/RPM 变化 |

### 你对应的 PPT

- 第 4 页：硬件输入输出。
- 第 5 页：UNO 状态机。
- 第 6 页：Safety Alarm。
- 第 7 页：Energy saving / comfort。

### 你可以说的直白话

> 这部分最重要的是优先级。只要安全报警触发，普通节能逻辑就必须让路，因为安全比省电更重要。

### 你交给 Speaker 3 的话

> UNO 本地控制已经能独立工作，接下来我们说明 ESP32 怎样把这些状态变成真正的 IoT 网络数据。

## Speaker 3：ESP32、UART、MQTT 和 ACK

### 你要讲清楚什么

你负责证明这个项目有完整 IoT 网络层，而不是只在串口监视器里看数值。

### 推荐讲法

1. UNO 每 1 秒通过 SoftwareSerial 输出 SC2 telemetry。
2. ESP32 用 Serial2 接收 UNO 数据。
3. ESP32 解析 key=value 字段，例如 mode、pir、light、temp、gas、fan、pwm、rpm。
4. ESP32 发布完整 JSON 到 MQTT telemetry topic。
5. ESP32 同时发布关键 topic，例如 mode、temperature、gas、fan、rpm。
6. Dashboard 发出的命令先到 MQTT，再由 ESP32 通过 UART 发给 UNO。
7. UNO 执行后回传 ACK，Dashboard 可以知道命令有没有真正落地。
8. LM35 当前由 ESP32 5V/VIN 供电，OUT 到 GPIO34，解决了之前温度长期偏高的问题。
9. 12V 风扇电源、UNO、ESP32 必须共地，否则 UART、PWM、Tach 可能异常。

### 现场演示动作

| 演示 | 你做什么 | 正常现象 |
|---|---|---|
| MQTT 在线 | 打开 Dashboard 看 MQTT 状态 | 显示 connected / online |
| Telemetry | 观察卡片每秒刷新 | 温度、灯、风扇、模式持续更新 |
| ACK | 点 Dashboard 的 Ping UNO 或 Apply Config | 页面出现 ACK，说明 UNO 收到命令 |
| Offline 说明 | 可以口头说明，不建议现场拔线 | 超过 5 秒无 UNO 数据会显示 uno_offline |

### 你对应的 PPT

- 第 8 页：ESP32 网关。
- 第 9 页：MQTT network layer。
- 第 10 页：Dashboard 截图的一部分。

### 你可以说的直白话

> ESP32 不直接控制继电器，也不直接接大部分传感器。它的职责是网关：把 UNO 的本地控制结果发布到网络，也把网络命令可靠送回 UNO。

### 你交给 Speaker 4 的话

> 有了 MQTT 和 ACK 之后，网页就不仅能看数据，还能作为运维控制台来管理整个系统。

## Speaker 4：Dashboard、AI、语音、数据和总结

### 你要讲清楚什么

你负责展示项目的“服务层”和“智能层”：网页能看、能控、能存、能分析，AI 能把自然语言变成任务。

### 推荐讲法

1. Dashboard 显示实时模式、传感器、执行器状态、图表和日志。
2. 自动模式下，阈值可以在网页修改，Apply 后立即下发给 UNO，并永久保存。
3. 手动模式下，可以直接控制灯、风扇、PWM、蜂鸣器和红黄绿灯。
4. 移动端也能访问，手机在同一局域网可以打开 Dashboard 或 HTTPS microphone page。
5. 数据收集按钮会记录 telemetry 和用户偏好。
6. torch 偏好模型会根据真实数据推荐风扇阈值和亮度策略。
7. 语音路径是 microphone -> faster-whisper -> text -> Qwen -> structured task plan。
8. Qwen 不负责直接控制硬件，它只把自然语言变成 JSON 任务。
9. 任务进入 timeline，到时间后由后端执行，通过 MQTT/ESP32/UNO 落地，完成后自动清除。

### 现场演示动作

| 演示 | 你做什么 | 正常现象 |
|---|---|---|
| Apply Config | 修改风扇启动温度或亮度阈值 | Dashboard 显示保存，ACK 更新 |
| Manual Mode | 打开手动模式，控制状态灯或风扇 | 对应执行器改变 |
| Preset | 点击一键场景 | 阈值和模式按预设更新 |
| Qwen 文本命令 | 输入“3 分钟后切换手动模式”类似指令 | 页面生成 timeline |
| 数据分析 | 打开 analytics | 出现样本数量、偏好事件、推荐策略 |

### 你对应的 PPT

- 第 10 页：Dashboard。
- 第 11 页：Manual / presets / mobile。
- 第 12 页：Data and preference analytics。
- 第 13 页：Qwen and voice.
- 第 14-16 页：商业价值、课程要求、References。

### 你可以说的直白话

> AI 在这里不是聊天，而是把人说的话变成设备可以执行的任务。比如“几分钟后切换模式”会变成带 delaySec 的任务时间轴。

### 你负责结尾

> 总结来说，我们完成的是一个有本地控制、有网络网关、有运维界面、有数据闭环、有 AI 命令层的完整 IoT classroom prototype。它覆盖硬件、软件、架构、安全、运维和实际 use-case。

## 四人现场站位建议

| 人员 | 站位 | 原因 |
|---|---|---|
| Speaker 1 | 靠电脑或投影 | 负责开场和切 PPT。 |
| Speaker 2 | 靠硬件板 | 负责按按钮、遮光、展示风扇/灯/蜂鸣器。 |
| Speaker 3 | 靠电脑和 ESP32 | 负责解释 MQTT、ACK、网络、串口状态。 |
| Speaker 4 | 靠 Dashboard | 负责网页操作、AI 文本/语音、总结。 |

## 如果现场出问题怎么救

| 问题 | 谁处理 | 现场说法 |
|---|---|---|
| 风扇不转 | Speaker 2 | 先说明继电器/12V 是独立负载，检查 12V 和 RELAY_ON/OFF。 |
| Dashboard 不更新 | Speaker 3 | 说明 UNO 本地仍运行，网络层可通过 MQTT/ESP32 恢复。 |
| Qwen 网络不通 | Speaker 4 | 说明 AI 是增强层，本地安全和 Dashboard 手动控制不依赖 Qwen。 |
| 传感器值不稳定 | Speaker 2 + 3 | 说明 LM35 已迁移到 ESP32 供电/ADC，现场以趋势和控制链路为主。 |
| 时间不够 | Speaker 1 | 直接跳到 Safety Alarm、MQTT ACK、Dashboard 手动控制三个最强演示。 |

## 四个人最短版话术

| 人员 | 30 秒版 |
|---|---|
| Speaker 1 | 我们做的是智慧教室 IoT 服务，核心是本地优先：UNO 保证安全和节能，ESP32 做网关，网页做运维。 |
| Speaker 2 | UNO 读取 PIR、光照、温度、气体、火焰和按钮，然后控制灯、风扇、蜂鸣器和红黄绿灯。Safety Alarm 最高优先级。 |
| Speaker 3 | ESP32 把 UNO 每秒 telemetry 转成 MQTT topic，也把网页命令通过 UART 发回 UNO，并用 ACK 证明命令落地。 |
| Speaker 4 | Dashboard 可以看数据、改阈值、手动控制、记录偏好，还能用 Qwen 把语音或文字变成可执行 timeline 任务。 |

