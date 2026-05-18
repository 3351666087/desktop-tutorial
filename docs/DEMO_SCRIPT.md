# IoT104TC 10-Minute Demo Script

## 0:00-1:00 - Problem and Value

This project is a smart classroom IoT service. It saves energy, reacts to safety risk, and gives operators a live dashboard for classroom devices.

## 1:00-2:00 - Layered Architecture

Explain:

- UNO = edge control node
- ESP32 = IoT gateway
- Laptop = MQTT broker, dashboard, AI service

Key sentence: safety and real-time actuator control remain on UNO, while the network layer is separated onto ESP32.

## 2:00-3:30 - Hardware Walkthrough

Point to:

- PIR, light, LM35, gas, flame, emergency button
- LED, buzzer, relay fan, fan PWM/tach, traffic light
- UART bridge between UNO and ESP32

## 3:30-5:00 - Energy Saving Demo

Show:

- occupied and dark -> lamp on
- no occupancy or bright light -> lamp off
- temperature threshold -> fan starts

## 5:00-6:30 - Safety Alarm Demo

Press emergency button.

Expected:

- red status light
- intermittent buzzer
- fan forced on
- dashboard shows safety alarm

## 6:30-8:00 - Dashboard and Operations

Show:

- live telemetry cards
- charts
- command ACK
- manual/auto mode
- preset strategy

## 8:00-9:10 - AI Task Planning

Example:

```text
3 minutes later switch to manual mode, set fan PWM to 180, then return to automatic mode 2 minutes later.
```

Explain that Qwen creates structured scheduled tasks. The backend executes them through MQTT commands.

## 9:10-10:00 - Security, Privacy, and Use-Case

Mention:

- API key stored server-side
- credentials ignored by Git
- HTTPS microphone endpoint
- future production: MQTT auth, TLS, account login, asset tags

