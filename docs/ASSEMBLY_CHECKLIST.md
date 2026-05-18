# Smart Classroom 现场组装清单

给组员现场搭建演示硬件使用。本文档按“图片内 48 件套模块”和“额外元件”分开列出，接口精确到 UNO / ESP32 引脚。

当前版本特别说明：**没有安装电容**。如果现场看到电路图里有人提到电容，这不是当前实物版本的一部分。

## A. 图片内 48 件套模块

| 图片编号 | 模块名称 | 当前状态 | 精确接口 |
|---:|---|---|---|
| #4 | Traffic Light Module 红黄绿灯模块 | 已使用 | R -> UNO D10；Y -> UNO D11；G -> UNO D12；GND -> UNO GND |
| #5 | Active Buzzer Module 有源蜂鸣器 | 已使用 | S / Signal -> UNO D7；+ / VCC -> UNO 5V；- / GND -> UNO GND |
| #16 | Flame Sensor 火焰传感器 | 已使用 | VCC -> UNO 5V；GND -> UNO GND；DO / D0 -> UNO D8；AO / A0 -> UNO A3 |
| #18 | PIR Motion Sensor 人体红外传感器 | 已使用 | VCC -> UNO 5V；GND -> UNO GND；OUT -> UNO D2 |
| #25 | Analog Gas Sensor 气体传感器 | 已使用 | VCC -> UNO 5V；GND -> UNO GND；AO -> UNO A1；DO 不接 |
| #30 | TEMT6000 Light Sensor 光照传感器 | 已使用 | VCC -> UNO 5V；GND -> UNO GND；SIG -> UNO A0 |
| #39 | LM35 Temperature Sensor 温度传感器 | 已使用 | VCC -> ESP32 5V/VIN；GND -> ESP32 GND；OUT/S -> ESP32 GPIO34 |
| #38 | 5V Single Relay Module 单路继电器 | 未使用 | 当前实物使用外置 6 口继电器模块替代 |
| #7 | Digital Push Button Module 按键模块 | 未使用 | 当前实物使用裸四脚轻触按钮替代 |

## B. 图片外额外元件

| 元件 | 精确接口 |
|---|---|
| KS0001 Keyestudio UNO R3 | 边缘控制主控，负责传感器读取、状态机、继电器、蜂鸣器、红绿灯 |
| ESP32 开发板 | MQTT 网关，同时负责 LM35 ADC 读取 |
| 外置 6 口继电器模块 | 控制侧：DC+ -> UNO 5V；DC- -> UNO GND；IN -> UNO D6 |
| 12V 四线风扇 | Red -> 继电器 NO/ON；Black -> 12V 电源负极；Yellow Tach -> UNO D3；Blue PWM -> UNO D9 |
| 12V 2A 电源适配器 | + -> 继电器 COM；- -> 风扇 Black，并与 UNO GND / ESP32 GND 共地 |
| 单颗 LED 模拟教室灯 | UNO D5 -> 220 ohm 电阻 -> LED 长脚；LED 短脚 -> GND |
| 裸四脚轻触按钮 | 一侧任意脚 -> UNO D4；对侧任意脚 -> UNO GND；代码使用 INPUT_PULLUP |
| UART 分压电阻 | UNO A5 -> 10k ohm -> ESP32 GPIO16；ESP32 GPIO16 -> 20k ohm -> GND |
| ESP32 指令回传线 | ESP32 GPIO17 -> UNO A4 |
| 公共地线 | UNO GND -> ESP32 GND -> 12V adapter - |
| LM35 ADC 下拉 | ESP32 GPIO34 -> 100k ohm -> GND |
| Dummy ADC 下拉 | ESP32 GPIO35 -> 100k ohm -> GND |

## C. Arduino UNO 引脚总表

| UNO 引脚 | 连接对象 |
|---|---|
| D2 | #18 PIR OUT |
| D3 | 风扇 Yellow Tach |
| D4 | Emergency Button 到 GND |
| D5 | 教室灯 LED，经 220 ohm 电阻 |
| D6 | 6 口继电器模块 IN |
| D7 | #5 有源蜂鸣器 S |
| D8 | #16 火焰传感器 DO |
| D9 | 风扇 Blue PWM |
| D10 | #4 红绿灯 R |
| D11 | #4 红绿灯 Y |
| D12 | #4 红绿灯 G |
| A0 | #30 TEMT6000 SIG |
| A1 | #25 气体传感器 AO |
| A2 | 旧版 UNO LM35 输入，当前不是主温度源 |
| A3 | #16 火焰传感器 AO |
| A4 | SoftwareSerial RX，接 ESP32 GPIO17 |
| A5 | SoftwareSerial TX，经 10k/20k 分压后接 ESP32 GPIO16 |

## D. ESP32 引脚总表

| ESP32 引脚 | 连接对象 |
|---|---|
| GPIO16 RX2 | 接收 UNO A5 telemetry，必须经过 10k/20k 分压 |
| GPIO17 TX2 | 发送 dashboard / MQTT 指令到 UNO A4 |
| GPIO34 ADC1 | LM35 OUT/S 主温度输入 |
| GPIO35 ADC1 | Dummy ADC reference，接 100k ohm 到 GND |
| 5V / VIN | 给 LM35 VCC 供电 |
| GND | 接 LM35 GND、UNO GND、12V adapter -，必须共地 |

## E. 继电器和风扇负载侧

| 接口 | 接线 |
|---|---|
| 继电器 COM | 12V adapter + |
| 继电器 ON / NO | 风扇 Red |
| 继电器 NC | 不接 |
| 风扇 Black | 12V adapter - |
| 风扇 Yellow | UNO D3，可按需要加 10k ohm 上拉到 5V |
| 风扇 Blue | UNO D9 |

注意：继电器板上如果标的是 `ON / COM / NC`，这里的 `ON` 大概率等价于 `NO`。如果风扇逻辑反了，只改代码里的 `RELAY_ON` / `RELAY_OFF`，不要乱换整套引脚。

## F. 推荐上电顺序

1. 先确认所有 GND 已经共地：UNO GND、ESP32 GND、12V adapter -。
2. 先给 ESP32 上电，确认 dashboard / MQTT gateway online。
3. 再给 UNO 上电。
4. 最后接入 12V 风扇电源。
5. 等待 10-20 秒，让 telemetry 和温度滤波稳定。

这样做可以降低 LM35 长时间高电位或 ADC 漂移的概率。

## G. Dashboard 预期现象

| 项目 | 正常现象 |
|---|---|
| ESP32 status | online |
| UNO telemetry | 大约每 1 秒更新一次 |
| temperature source | 稳定后显示 ESP32 |
| safety alarm | 正常无报警时为 0 / OFF |
| status light | NORMAL / LIGHTING 为绿；COOLING / ENERGY_SAVING 为黄；SAFETY_ALARM 为红 |
| command ACK | 点击 dashboard 或 Qwen 指令后会更新 ACK |
| fan rpm | Tach 接线正确时显示非 0；为 0 不影响继电器开关 |

## H. 常见错误排查

| 现象 | 优先检查 |
|---|---|
| ESP32 收不到 UNO 数据 | UNO A5 是否经过分压到 ESP32 GPIO16；UNO / ESP32 是否共地；UNO 是否已烧录 Phase3 |
| ESP32 可以收但 UNO 不响应指令 | ESP32 GPIO17 是否接 UNO A4；不要接到 GPIO16 分压中点 |
| 温度长期偏高 | LM35 VCC 应接 ESP32 5V/VIN；OUT 接 GPIO34；GPIO34 / GPIO35 的 100k ohm 下拉是否存在 |
| 拔掉温度传感器后 GPIO34 仍有电压 | GPIO34 是高阻 ADC 输入，必须检查 100k ohm 下拉和周围跳线漏接 |
| 风扇不转 | 12V adapter + -> 继电器 COM；继电器 NO/ON -> 风扇 Red；风扇 Black -> 12V - |
| 风扇一直转 | 继电器触发极性反了，或负载侧误接 NC；先改 `RELAY_ON` / `RELAY_OFF` |
| Tach RPM 一直为 0 | 风扇 Yellow 是否到 UNO D3；是否共地；必要时 Yellow 加 10k ohm 上拉 |
| 红黄绿灯颜色不对 | R/Y/G 是否分别接 D10/D11/D12 |
| 按钮一直 pressed | 四脚按钮必须跨面包板中间沟槽；D4 到按钮，按钮对侧到 GND |
| Gas 数值异常高 | 气体传感器需要预热；AO 接 A1；阈值可在代码或 dashboard 中调整 |
| Flame AO 有变化但 DO 不变 | 调整火焰模块电位器；如果 DO 逻辑反了，改 `FLAME_ACTIVE_LOW` |
| MQTT offline | 电脑热点 / 路由器 IP 是否改变；ESP32 `credentials.h` 里的 MQTT host 是否正确 |

## I. 现场分工建议

| 角色 | 负责内容 |
|---|---|
| 硬件同学 | 按本清单接线，重点确认共地、继电器、风扇和 LM35 |
| UNO 同学 | 解释传感器读取、状态机、安全优先级、继电器控制 |
| ESP32 同学 | 解释 UART、Wi-Fi、MQTT、LM35 ADC 路由 |
| Dashboard 同学 | 展示网页、图表、手动/自动、ACK、Qwen timeline |
| Use-case 同学 | 讲商业应用、节能、安全、隐私和后续扩展 |
