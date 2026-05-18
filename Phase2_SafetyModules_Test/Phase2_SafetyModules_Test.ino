/*
  Phase2_SafetyModules_Test.ino
  Smart Classroom Energy-Saving, Safety & Asset Monitoring System

  Purpose:
  - Test only Phase 2 safety modules.
  - Does not touch the Phase 1 fan, LED, PIR, light, or LM35 control logic.

  Tested modules:
  - Analog Gas Sensor AO -> A1
  - Flame Sensor DO -> D8, AO -> A3
  - Emergency Test Button -> D4, INPUT_PULLUP
  - Traffic Light R/Y/G -> D10/D11/D12
  - Active Buzzer -> D7, short non-blocking beep
*/

// ---------------- Pin definitions ----------------
#define PIN_DEMO_BTN   4
#define PIN_BUZZER     7
#define PIN_FLAME_DO   8
#define PIN_STATUS_R   10
#define PIN_STATUS_Y   11
#define PIN_STATUS_G   12
#define PIN_GAS        A1
#define PIN_FLAME_AO   A3

// ---------------- Constants and thresholds ----------------
const int BUZZER_ON = HIGH;
const int BUZZER_OFF = LOW;

const bool FLAME_ACTIVE_LOW = true;  // If Flame DO logic is reversed, change only this.
const int GAS_THRESHOLD = 450;       // Adjust after observing clean-air gasValue.

const unsigned long SERIAL_INTERVAL_MS = 500;
const unsigned long DEBOUNCE_MS = 40;
const unsigned long BEEP_DURATION_MS = 90;

// ---------------- Global variables ----------------
int gasValue = 0;
int flameAnalog = 0;
int flameDigital = HIGH;
bool gasDanger = false;
bool flameDetected = false;

bool buttonPressed = false;
bool lastRawButtonPressed = false;
bool stableButtonPressed = false;
bool previousStableButtonPressed = false;
unsigned long lastButtonChangeMs = 0;

bool buzzerActive = false;
unsigned long buzzerOffAtMs = 0;
unsigned long lastSerialMs = 0;

// ---------------- Function declarations ----------------
void setStatusLight(bool red, bool yellow, bool green);
void readSafetySensors();
void updateButton();
void updateBuzzer();
void requestBeep(unsigned long durationMs);
void updateSerialOutput();

void setup() {
  pinMode(PIN_DEMO_BTN, INPUT_PULLUP);
  pinMode(PIN_FLAME_DO, INPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_STATUS_R, OUTPUT);
  pinMode(PIN_STATUS_Y, OUTPUT);
  pinMode(PIN_STATUS_G, OUTPUT);

  digitalWrite(PIN_BUZZER, BUZZER_OFF);
  setStatusLight(false, false, true);

  Serial.begin(9600);
  while (!Serial) {
    ;  // UNO ignores this, harmless for compatible boards.
  }

  Serial.println(F("Phase2_SafetyModules_Test started"));
  Serial.println(F("Fields: gasValue, gasDanger, flameDigital, flameAnalog, flameDetected, buttonPressed, statusLight"));
  requestBeep(120);
}

void loop() {
  readSafetySensors();
  updateButton();

  if (stableButtonPressed && !previousStableButtonPressed) {
    requestBeep(BEEP_DURATION_MS);
  }
  previousStableButtonPressed = stableButtonPressed;

  if (stableButtonPressed || flameDetected) {
    setStatusLight(true, false, false);
  } else if (gasDanger) {
    setStatusLight(false, true, false);
  } else {
    setStatusLight(false, false, true);
  }

  updateBuzzer();

  if (millis() - lastSerialMs >= SERIAL_INTERVAL_MS) {
    lastSerialMs = millis();
    updateSerialOutput();
  }
}

void readSafetySensors() {
  gasValue = analogRead(PIN_GAS);
  gasDanger = (gasValue >= GAS_THRESHOLD);

  flameDigital = digitalRead(PIN_FLAME_DO);
  flameAnalog = analogRead(PIN_FLAME_AO);
  flameDetected = FLAME_ACTIVE_LOW ? (flameDigital == LOW) : (flameDigital == HIGH);
}

void updateButton() {
  const bool rawPressed = (digitalRead(PIN_DEMO_BTN) == LOW);
  const unsigned long now = millis();

  if (rawPressed != lastRawButtonPressed) {
    lastRawButtonPressed = rawPressed;
    lastButtonChangeMs = now;
  }

  if (now - lastButtonChangeMs >= DEBOUNCE_MS) {
    stableButtonPressed = rawPressed;
  }

  buttonPressed = stableButtonPressed;
}

void setStatusLight(bool red, bool yellow, bool green) {
  digitalWrite(PIN_STATUS_R, red ? HIGH : LOW);
  digitalWrite(PIN_STATUS_Y, yellow ? HIGH : LOW);
  digitalWrite(PIN_STATUS_G, green ? HIGH : LOW);
}

void requestBeep(unsigned long durationMs) {
  digitalWrite(PIN_BUZZER, BUZZER_ON);
  buzzerActive = true;
  buzzerOffAtMs = millis() + durationMs;
}

void updateBuzzer() {
  if (buzzerActive && (long)(millis() - buzzerOffAtMs) >= 0) {
    buzzerActive = false;
    digitalWrite(PIN_BUZZER, BUZZER_OFF);
  }
}

void updateSerialOutput() {
  const char *statusLight = "GREEN";
  if (stableButtonPressed || flameDetected) {
    statusLight = "RED";
  } else if (gasDanger) {
    statusLight = "YELLOW";
  }

  Serial.print(F("gasValue="));
  Serial.print(gasValue);
  Serial.print(F(" gasDanger="));
  Serial.print(gasDanger ? F("true") : F("false"));
  Serial.print(F(" flameDigital="));
  Serial.print(flameDigital);
  Serial.print(F(" flameAnalog="));
  Serial.print(flameAnalog);
  Serial.print(F(" flameDetected="));
  Serial.print(flameDetected ? F("true") : F("false"));
  Serial.print(F(" buttonState="));
  Serial.print(stableButtonPressed ? F("pressed") : F("released"));
  Serial.print(F(" statusLight="));
  Serial.println(statusLight);
}
