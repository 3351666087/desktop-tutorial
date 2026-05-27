# CW2 Marking Criteria Response

**Project:** Smart Classroom Energy-Saving, Safety & Asset Monitoring System  
**GitHub:** https://github.com/3351666087/desktop-tutorial

This document maps the delivered project directly to the IOT104TC Coursework 2 marking scheme.

## 1. Presentation - 20 Marks

The marking scheme awards 18-20 marks for an outstanding presentation of the idea, design, functions and operations.

| Requirement | Evidence delivered |
|---|---|
| Clear idea | The project solves classroom energy waste, safety alarm response and facility monitoring. |
| Clear design | The slide deck and report explain physical, edge, gateway, service, intelligence and user layers. |
| Clear functions | Lighting, cooling, safety alarm, manual control, mobile voice command, analytics and presets are demonstrated. |
| Clear operations | The system includes live dashboard, MQTT logs, ACK feedback, status lights, fan RPM and physical actuator response. |
| Presentation materials | Final PPTX, PPT PDF, bilingual script, four-person presentation plan and feature guide are included. |

**Why this targets the top band:** The presentation materials are not only descriptive. They are supported by a working physical system, a dashboard, a GitHub repository and a repeatable demo path.

## 2. Technical Knowledge And Operation - 50 Marks

The marking scheme awards 40-50 marks for a perfect technical presentation and operation beyond the design and goal of the group project.

| Technical area | Project evidence |
|---|---|
| Hardware knowledge | Pin-level wiring for UNO, ESP32, sensors, relay, fan, status lights and UART level shifting. |
| Software knowledge | Arduino firmware, ESP32 gateway firmware, Node.js dashboard, MQTT broker, WebSocket live state, Python AI backend. |
| Architecture | Real layered architecture: physical layer, edge control, gateway, service layer, intelligence layer and user layer. |
| Security and privacy | local-first safety, ignored API keys, temporary voice files, validated command schema, LAN-only control prototype. |
| Operations | startup script, self-check script, compile checks, runtime AI check, dashboard health endpoints and onsite wiring checklist. |
| Demonstration depth | Mobile voice command changes the physical fan through ASR, Qwen, MQTT, ESP32 UART and Arduino control. |
| Robustness | UNO remains responsible for safety and actuator control even if dashboard or cloud AI is unavailable. |
| Evidence | `PASS 57 / WARN 0 / FAIL 0`, 11/11 Arduino/ESP32 sketches compiled, AI runtime verified on CUDA. |

**Why this targets the top band:** The system goes beyond a basic Arduino lab task. It integrates embedded control, network gateway, MQTT service architecture, mobile web interaction, AI planning and physical actuation in one demonstrable system.

## 3. Practical Use-Cases - 30 Marks

The marking scheme awards 22-30 marks if the group project can be deployed as a commercial IoT application or service.

| Practical use-case criterion | Project support |
|---|---|
| Real problem | energy waste, classroom safety and facility monitoring are real operational problems. |
| Deployable architecture | separate edge node, gateway and service layers can be maintained or replaced independently. |
| Commercial value | dashboard, logs, status indicators, mobile control and analytics resemble a facility operations product. |
| Cost feasibility | Arduino/ESP32 modules, low-cost sensors and a 12 V fan can be deployed as an affordable prototype. |
| User value | teachers or operators can use presets, mobile dashboard and voice commands instead of technical tools. |
| Safety value | local alarm handling avoids dependence on cloud services. |
| Expandability | MQTT topics support additional rooms, sensors or dashboards. |

**Why this targets the top band:** It is not merely possible to imagine a real application. The prototype already behaves like a small commercial classroom IoT service: it monitors, decides, alarms, logs, accepts remote configuration and responds to natural-language commands.

## 4. Learning Outcomes

| Outcome | Response |
|---|---|
| C: software and hardware in IoT | Arduino, ESP32, sensors, actuators, MQTT, dashboard and AI backend are all explained and implemented. |
| D: security and privacy of IoT | report covers local-first safety, key management, temporary audio, command validation and future hardening. |
| E: layered IoT architecture | the project explicitly separates physical, edge, gateway, service, intelligence and user layers. |
| F: IoT applications | the project implements a smart classroom energy-saving, safety and monitoring service with real hardware. |

## 5. Suggested Examiner-Facing Summary

This project should be evaluated as a complete IoT application/service rather than as a single Arduino circuit. The system has a working edge controller, a network gateway, a local broker, a web operations dashboard, live MQTT telemetry, mobile voice control, AI task planning and physical actuator response. The GitHub repository provides code, documentation, wiring guides, self-check scripts and demonstration materials, showing both technical depth and operational maturity.
