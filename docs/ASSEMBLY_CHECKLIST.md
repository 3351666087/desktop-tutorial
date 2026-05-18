# Smart Classroom On-Site Assembly Checklist

This checklist is for group members assembling the demo hardware on-site.

Current build note: **no capacitors are installed**.

## A. Modules From the 48-Piece Kit Photo

| Photo No. | Module | Current Use | Interface |
|---:|---|---|---|
| #4 | Traffic Light Module | Used | R -> UNO D10, Y -> UNO D11, G -> UNO D12, GND -> UNO GND |
| #5 | Active Buzzer Module | Used | S -> UNO D7, + -> UNO 5V, - -> UNO GND |
| #16 | Flame Sensor | Used | VCC -> UNO 5V, GND -> UNO GND, DO -> UNO D8, AO -> UNO A3 |
| #18 | PIR Motion Sensor | Used | VCC -> UNO 5V, GND -> UNO GND, OUT -> UNO D2 |
| #25 | Analog Gas Sensor | Used | VCC -> UNO 5V, GND -> UNO GND, AO -> UNO A1, DO not connected |
| #30 | TEMT6000 Light Sensor | Used | VCC -> UNO 5V, GND -> UNO GND, SIG -> UNO A0 |
| #39 | LM35 Temperature Sensor | Used | VCC -> ESP32 5V/VIN, GND -> ESP32 GND, OUT -> ESP32 GPIO34 |
| #38 | 5V Single Relay Module | Not used | replaced by external 6-port relay module |
| #7 | Digital Push Button Module | Not used | current build uses a bare 4-leg tactile button |

## B. Extra Components Not From the Photo

| Component | Interface |
|---|---|
| KS0001 Keyestudio UNO R3 | main edge controller |
| ESP32 dev board | MQTT gateway and LM35 ADC reader |
| 6-port relay module | DC+ -> UNO 5V, DC- -> UNO GND, IN -> UNO D6 |
| 12V 4-wire fan | Red -> relay NO/ON, Black -> 12V adapter -, Yellow -> UNO D3, Blue -> UNO D9 |
| 12V 2A adapter | + -> relay COM, - -> fan black and common ground |
| discrete classroom LED | UNO D5 -> 220 ohm resistor -> LED long leg, LED short leg -> GND |
| emergency 4-leg button | one side -> UNO D4, opposite side -> UNO GND, code uses INPUT_PULLUP |
| UART divider | UNO A5 -> 10k -> ESP32 GPIO16; ESP32 GPIO16 -> 20k -> GND |
| ESP32 command TX | ESP32 GPIO17 -> UNO A4 |
| common ground | UNO GND -> ESP32 GND -> 12V adapter - |
| ADC pulldown | ESP32 GPIO34 -> 100k -> GND |
| dummy ADC pulldown | ESP32 GPIO35 -> 100k -> GND |

## C. UNO Pin Table

| UNO Pin | Connected Device |
|---|---|
| D2 | PIR OUT |
| D3 | fan yellow tach |
| D4 | emergency button to GND |
| D5 | classroom LED through 220 ohm |
| D6 | relay module IN |
| D7 | active buzzer S |
| D8 | flame sensor DO |
| D9 | fan blue PWM |
| D10 | traffic light R |
| D11 | traffic light Y |
| D12 | traffic light G |
| A0 | TEMT6000 SIG |
| A1 | gas sensor AO |
| A2 | legacy UNO LM35 input, currently not main temperature source |
| A3 | flame sensor AO |
| A4 | SoftwareSerial RX from ESP32 GPIO17 |
| A5 | SoftwareSerial TX to ESP32 GPIO16 through divider |

## D. ESP32 Pin Table

| ESP32 Pin | Connected Device |
|---|---|
| GPIO16 RX2 | receives UNO A5 telemetry through 10k/20k divider |
| GPIO17 TX2 | sends commands to UNO A4 |
| GPIO34 ADC1 | LM35 OUT |
| GPIO35 ADC1 | dummy reference channel with 100k pulldown to GND |
| 5V/VIN | LM35 VCC |
| GND | LM35 GND, UNO GND, 12V adapter - common ground |

## E. Power-On Order

Recommended for stable LM35 readings:

1. Connect all grounds first.
2. Power ESP32 and verify dashboard/gateway is online.
3. Power UNO.
4. Power 12V adapter for fan.
5. Wait 10-20 seconds for telemetry and temperature filter to stabilize.

## F. Expected Dashboard Signals

| Item | Expected |
|---|---|
| ESP32 status | online |
| UNO telemetry | updates roughly once per second |
| temperature source | ESP32 after stable LM35 ADC |
| safety alarm | 0 during normal mode |
| status light | green for normal/lighting, yellow for cooling/energy-saving, red for safety alarm |
| command ACK | updates after dashboard/Qwen/manual commands |

## G. Common Assembly Mistakes

| Symptom | Check |
|---|---|
| ESP32 receives no UNO data | A5 divider to GPIO16, common GND, UNO firmware flashed |
| ESP32 command not reaching UNO | GPIO17 -> UNO A4, no accidental connection to GPIO16 divider midpoint |
| temperature too high | LM35 VCC should be ESP32 5V/VIN, OUT to GPIO34, GPIO34/GPIO35 pulldowns present |
| temperature floats with sensor unplugged | GPIO34 is high impedance; check 100k pulldown |
| fan not spinning | 12V adapter + -> relay COM, relay NO/ON -> fan red, fan black -> 12V - |
| fan always spinning | relay trigger polarity or wrong NO/NC terminal |
| tach is zero | fan yellow -> UNO D3, common ground, tach pullup if needed |
| red/yellow/green wrong | swap R/Y/G wires on D10/D11/D12 |
| button always pressed | button must straddle breadboard gap; D4 uses INPUT_PULLUP |
| MQTT offline | laptop IP/MQTT host mismatch or hotspot/router changed |

