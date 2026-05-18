/*
  SmartClassroom_UNO_Phase2.ino
  Smart Classroom Energy-Saving, Safety & Asset Monitoring System

  Phase 2: Safety Alarm Layer on top of the completed Arduino UNO Phase 1 node.

  Safety alarm is the highest-priority local edge-control mode:
  - Gas danger, flame detected, or emergency test button pressed triggers MODE_SAFETY_ALARM.
  - Red traffic light, intermittent buzzer, relay fan forced ON, fan PWM forced high.
  - Normal energy-saving and temperature-control logic resumes only after alarm clears.

  No ESP32, WiFi, MQTT, LCD, gas digital pin, or extra modules in this sketch.
*/

// ---------------- Pin definitions ----------------
#define PIN_PIR        2
#define PIN_FAN_TACH   3
#define PIN_DEMO_BTN   4
#define PIN_LED        5
#define PIN_RELAY_FAN  6
#define PIN_BUZZER     7
#define PIN_FLAME_DO   8
#define PIN_FAN_PWM    9
#define PIN_STATUS_R   10
#define PIN_STATUS_Y   11
#define PIN_STATUS_G   12
#define PIN_LIGHT      A0
#define PIN_GAS        A1
#define PIN_TEMP_LM35  A2
#define PIN_FLAME_AO   A3

// ---------------- Constants and thresholds ----------------
// Current relay behavior appears active HIGH. If yours is active LOW, swap these.
const int RELAY_ON = HIGH;
const int RELAY_OFF = LOW;

const int BUZZER_ON = HIGH;
const int BUZZER_OFF = LOW;

const bool FLAME_ACTIVE_LOW = true;  // If Flame DO logic is reversed, change only this.

const unsigned long SENSOR_INTERVAL_MS = 1000;
const unsigned long SERIAL_INTERVAL_MS = 1000;
const unsigned long NO_MOTION_TIMEOUT_MS = 10000;
const unsigned long BUTTON_DEBOUNCE_MS = 40;
const unsigned long ALARM_BUZZER_PERIOD_MS = 500;
const unsigned long ALARM_BUZZER_ON_MS = 120;
const unsigned long SENSOR_ERROR_BLINK_MS = 500;

const int LIGHT_DARK_ON_THRESHOLD = 330;
const int LIGHT_BRIGHT_OFF_THRESHOLD = 430;

const float FAN_ON_TEMP_C = 28.0;
const float FAN_OFF_TEMP_C = 26.0;

const int GAS_THRESHOLD = 450;       // Adjust after observing clean-air gasValue.
const int FAN_NORMAL_PWM = 200;
const int FAN_ALARM_PWM = 255;

const byte TACH_PULSES_PER_REV = 2;
const byte ADC_REF_AVCC = _BV(REFS0);
const byte ADC_REF_INTERNAL_1V1 = _BV(REFS1) | _BV(REFS0);
const float DEFAULT_ADC_REFERENCE_V = 5.0;
const float TEMP_ADC_REFERENCE_V = 1.265;    // Calibrated internal reference from Phase 1.
const unsigned int TEMP_PWM_QUIET_US = 5000; // Quiet LM35 sampling while fan PWM is running.
const float TEMP_CALIBRATION_SCALE = 1.0;
const float TEMP_CALIBRATION_OFFSET_C = 0.0;

// ---------------- enum SystemMode ----------------
enum SystemMode {
  MODE_NORMAL,
  MODE_LIGHTING,
  MODE_COOLING,
  MODE_ENERGY_SAVING,
  MODE_SAFETY_ALARM,
  MODE_SENSOR_ERROR
};

// ---------------- Global variables ----------------
volatile unsigned long tachPulseCounter = 0;

SystemMode currentMode = MODE_NORMAL;

bool motionDetected = false;
bool occupied = false;
bool isDark = false;
bool classroomLedState = false;
bool fanRelayState = false;
bool temperatureValid = false;

bool gasDanger = false;
bool flameDetected = false;
bool demoEmergency = false;
bool safetyAlarm = false;

int lightValue = 0;
int gasValue = 0;
int flameDigital = HIGH;
int flameAnalog = 0;
int fanPwmValue = 0;
int tempRaw = 0;

float temperatureC = 0.0;
float tempVoltage = 0.0;
float adcReferenceV = DEFAULT_ADC_REFERENCE_V;

bool rawButtonPressed = false;
bool lastRawButtonPressed = false;
bool stableButtonPressed = false;
unsigned long lastButtonChangeMs = 0;

unsigned long lastMotionMs = 0;
unsigned long lastSensorReadMs = 0;
unsigned long lastSerialOutputMs = 0;
unsigned long lastTachPulseCount = 0;

unsigned int estimatedRpm = 0;

// ---------------- Function declarations ----------------
void tachISR();
void setup();
void loop();
void readSensors();
void updateButton();
void updateControlLogic();
void applyActuators();
void updateStatusLight();
void updateBuzzer();
void updateSerialOutput();
const char *modeToString(SystemMode mode);
void setStatusLight(bool red, bool yellow, bool green);
const char *statusLightColor();
byte analogPinToAdcChannel(byte pin);
int readAdcOnce();
int readAdcMedian(byte pin, byte referenceBits, unsigned int settleUs, byte discardCount);
int readLightAverageDefault();
int readLm35QuietInternalMedian();
long readVccMillivolts();

void tachISR() {
  tachPulseCounter++;
}

void setup() {
  pinMode(PIN_RELAY_FAN, OUTPUT);
  digitalWrite(PIN_RELAY_FAN, RELAY_OFF);  // Keep fan off during boot.

  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_FAN_TACH, INPUT_PULLUP);
  pinMode(PIN_DEMO_BTN, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_FLAME_DO, INPUT);
  pinMode(PIN_FAN_PWM, OUTPUT);
  pinMode(PIN_STATUS_R, OUTPUT);
  pinMode(PIN_STATUS_Y, OUTPUT);
  pinMode(PIN_STATUS_G, OUTPUT);

  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, BUZZER_OFF);
  analogWrite(PIN_FAN_PWM, 0);
  setStatusLight(false, false, true);

  Serial.begin(9600);
  while (!Serial) {
    ;  // UNO ignores this, harmless for compatible boards.
  }

  attachInterrupt(digitalPinToInterrupt(PIN_FAN_TACH), tachISR, FALLING);

  const unsigned long now = millis();
  lastSensorReadMs = now;
  lastSerialOutputMs = now;

  Serial.println(F("SmartClassroom_UNO_Phase2 started"));
  Serial.println(F("Safety alarm priority: gasDanger || flameDetected || demoEmergency"));
  Serial.println(F("Fields: mode, pir, occupied, lightValue, isDark, temperatureC, gasValue, gasDanger, flameDigital, flameAnalog, flameDetected, demoEmergency, fanRelayState, fanPwmValue, rpm, classroomLedState, statusLight"));
}

void loop() {
  const unsigned long now = millis();

  updateButton();

  if (now - lastSensorReadMs >= SENSOR_INTERVAL_MS) {
    lastSensorReadMs = now;
    readSensors();
    updateControlLogic();
  }

  applyActuators();
  updateStatusLight();
  updateBuzzer();

  if (now - lastSerialOutputMs >= SERIAL_INTERVAL_MS) {
    lastSerialOutputMs = now;
    updateSerialOutput();
  }
}

void readSensors() {
  const unsigned long now = millis();

  motionDetected = (digitalRead(PIN_PIR) == HIGH);
  if (motionDetected) {
    lastMotionMs = now;
  }
  occupied = (lastMotionMs > 0 && (motionDetected || now - lastMotionMs <= NO_MOTION_TIMEOUT_MS));

  lightValue = readLightAverageDefault();
  if (lightValue <= LIGHT_DARK_ON_THRESHOLD) {
    isDark = true;
  } else if (lightValue >= LIGHT_BRIGHT_OFF_THRESHOLD) {
    isDark = false;
  }

  const long vccMv = readVccMillivolts();
  adcReferenceV = (vccMv > 3500 && vccMv < 5500) ? (vccMv / 1000.0) : DEFAULT_ADC_REFERENCE_V;

  tempRaw = readLm35QuietInternalMedian();
  tempVoltage = tempRaw * (TEMP_ADC_REFERENCE_V / 1023.0);
  temperatureC = ((tempVoltage * 100.0) * TEMP_CALIBRATION_SCALE) + TEMP_CALIBRATION_OFFSET_C;
  temperatureValid = (tempRaw > 1 && tempRaw < 1022 && temperatureC >= -5.0 && temperatureC <= 80.0);

  gasValue = readAdcMedian(PIN_GAS, ADC_REF_AVCC, 250, 1);
  gasDanger = (gasValue >= GAS_THRESHOLD);

  flameDigital = digitalRead(PIN_FLAME_DO);
  flameAnalog = readAdcMedian(PIN_FLAME_AO, ADC_REF_AVCC, 250, 1);
  flameDetected = FLAME_ACTIVE_LOW ? (flameDigital == LOW) : (flameDigital == HIGH);

  noInterrupts();
  const unsigned long pulsesNow = tachPulseCounter;
  interrupts();

  const unsigned long pulseDelta = pulsesNow - lastTachPulseCount;
  lastTachPulseCount = pulsesNow;
  estimatedRpm = (pulseDelta * 60UL) / TACH_PULSES_PER_REV;
}

void updateButton() {
  rawButtonPressed = (digitalRead(PIN_DEMO_BTN) == LOW);
  const unsigned long now = millis();

  if (rawButtonPressed != lastRawButtonPressed) {
    lastRawButtonPressed = rawButtonPressed;
    lastButtonChangeMs = now;
  }

  if (now - lastButtonChangeMs >= BUTTON_DEBOUNCE_MS) {
    stableButtonPressed = rawButtonPressed;
  }

  demoEmergency = stableButtonPressed;
}

void updateControlLogic() {
  safetyAlarm = gasDanger || flameDetected || demoEmergency;

  if (safetyAlarm) {
    currentMode = MODE_SAFETY_ALARM;
    classroomLedState = false;
    fanRelayState = true;
    fanPwmValue = FAN_ALARM_PWM;
    return;
  }

  classroomLedState = occupied && isDark;

  if (temperatureValid) {
    if (temperatureC > FAN_ON_TEMP_C) {
      fanRelayState = true;
    } else if (temperatureC < FAN_OFF_TEMP_C) {
      fanRelayState = false;
    }
  } else {
    fanRelayState = false;
  }

  fanPwmValue = fanRelayState ? FAN_NORMAL_PWM : 0;

  if (!temperatureValid) {
    currentMode = MODE_SENSOR_ERROR;
  } else if (fanRelayState) {
    currentMode = MODE_COOLING;
  } else if (classroomLedState) {
    currentMode = MODE_LIGHTING;
  } else if (!occupied) {
    currentMode = MODE_ENERGY_SAVING;
  } else {
    currentMode = MODE_NORMAL;
  }
}

void applyActuators() {
  digitalWrite(PIN_LED, classroomLedState ? HIGH : LOW);
  digitalWrite(PIN_RELAY_FAN, fanRelayState ? RELAY_ON : RELAY_OFF);
  analogWrite(PIN_FAN_PWM, fanPwmValue);
}

void updateStatusLight() {
  if (currentMode == MODE_SAFETY_ALARM) {
    setStatusLight(true, false, false);
  } else if (currentMode == MODE_SENSOR_ERROR) {
    const bool blinkOn = ((millis() / SENSOR_ERROR_BLINK_MS) % 2) == 0;
    setStatusLight(blinkOn, false, false);
  } else if (currentMode == MODE_ENERGY_SAVING || currentMode == MODE_COOLING) {
    setStatusLight(false, true, false);
  } else {
    setStatusLight(false, false, true);
  }
}

void updateBuzzer() {
  if (currentMode == MODE_SAFETY_ALARM) {
    const unsigned long phase = millis() % ALARM_BUZZER_PERIOD_MS;
    digitalWrite(PIN_BUZZER, phase < ALARM_BUZZER_ON_MS ? BUZZER_ON : BUZZER_OFF);
  } else {
    digitalWrite(PIN_BUZZER, BUZZER_OFF);
  }
}

void updateSerialOutput() {
  Serial.print(F("mode="));
  Serial.print(modeToString(currentMode));
  Serial.print(F(" pir="));
  Serial.print(motionDetected ? F("motion") : F("no_motion"));
  Serial.print(F(" occupied="));
  Serial.print(occupied ? F("true") : F("false"));
  Serial.print(F(" lightValue="));
  Serial.print(lightValue);
  Serial.print(F(" isDark="));
  Serial.print(isDark ? F("true") : F("false"));
  Serial.print(F(" temperatureC="));
  if (temperatureValid) {
    Serial.print(temperatureC, 1);
  } else {
    Serial.print(temperatureC, 1);
    Serial.print(F("(ERROR)"));
  }
  Serial.print(F(" gasValue="));
  Serial.print(gasValue);
  Serial.print(F(" gasDanger="));
  Serial.print(gasDanger ? F("true") : F("false"));
  Serial.print(F(" flameDigital="));
  Serial.print(flameDigital);
  Serial.print(F(" flameAnalog="));
  Serial.print(flameAnalog);
  Serial.print(F(" flameDetected="));
  Serial.print(flameDetected ? F("true") : F("false"));
  Serial.print(F(" demoEmergency="));
  Serial.print(demoEmergency ? F("true") : F("false"));
  Serial.print(F(" fanRelayState="));
  Serial.print(fanRelayState ? F("ON") : F("OFF"));
  Serial.print(F(" fanPwmValue="));
  Serial.print(fanPwmValue);
  Serial.print(F(" rpm="));
  Serial.print(estimatedRpm);
  Serial.print(F(" classroomLedState="));
  Serial.print(classroomLedState ? F("ON") : F("OFF"));
  Serial.print(F(" statusLight="));
  Serial.print(statusLightColor());

  if (currentMode == MODE_SAFETY_ALARM) {
    Serial.print(F(" WARNING=SAFETY_ALARM"));
  }

  Serial.println();
}

const char *modeToString(SystemMode mode) {
  switch (mode) {
    case MODE_NORMAL:
      return "NORMAL";
    case MODE_LIGHTING:
      return "LIGHTING";
    case MODE_COOLING:
      return "COOLING";
    case MODE_ENERGY_SAVING:
      return "ENERGY_SAVING";
    case MODE_SAFETY_ALARM:
      return "SAFETY_ALARM";
    case MODE_SENSOR_ERROR:
      return "SENSOR_ERROR";
    default:
      return "UNKNOWN";
  }
}

void setStatusLight(bool red, bool yellow, bool green) {
  digitalWrite(PIN_STATUS_R, red ? HIGH : LOW);
  digitalWrite(PIN_STATUS_Y, yellow ? HIGH : LOW);
  digitalWrite(PIN_STATUS_G, green ? HIGH : LOW);
}

const char *statusLightColor() {
  if (currentMode == MODE_SAFETY_ALARM) {
    return "RED";
  }
  if (currentMode == MODE_SENSOR_ERROR) {
    return ((millis() / SENSOR_ERROR_BLINK_MS) % 2) == 0 ? "RED_BLINK_ON" : "RED_BLINK_OFF";
  }
  if (currentMode == MODE_ENERGY_SAVING || currentMode == MODE_COOLING) {
    return "YELLOW";
  }
  return "GREEN";
}

byte analogPinToAdcChannel(byte pin) {
  return (pin >= A0) ? (pin - A0) : pin;
}

int readAdcOnce() {
  ADCSRA |= _BV(ADSC);
  while (bit_is_set(ADCSRA, ADSC)) {
    ;
  }
  return ADC;
}

int readAdcMedian(byte pin, byte referenceBits, unsigned int settleUs, byte discardCount) {
  const byte sampleCount = 9;
  int samples[sampleCount];

  ADMUX = referenceBits | (analogPinToAdcChannel(pin) & 0x07);
  delayMicroseconds(settleUs);

  for (byte i = 0; i < discardCount; i++) {
    readAdcOnce();
  }

  for (byte i = 0; i < sampleCount; i++) {
    samples[i] = readAdcOnce();
  }

  for (byte i = 1; i < sampleCount; i++) {
    const int value = samples[i];
    byte j = i;
    while (j > 0 && samples[j - 1] > value) {
      samples[j] = samples[j - 1];
      j--;
    }
    samples[j] = value;
  }

  return samples[sampleCount / 2];
}

int readLightAverageDefault() {
  ADMUX = ADC_REF_AVCC | (analogPinToAdcChannel(PIN_LIGHT) & 0x07);
  delayMicroseconds(250);
  readAdcOnce();

  unsigned int sum = 0;
  const byte sampleCount = 8;
  for (byte i = 0; i < sampleCount; i++) {
    sum += readAdcOnce();
  }
  return sum / sampleCount;
}

int readLm35QuietInternalMedian() {
  const int savedFanPwm = fanPwmValue;

  if (savedFanPwm > 0) {
    analogWrite(PIN_FAN_PWM, 0);
    delayMicroseconds(TEMP_PWM_QUIET_US);
  }

  const int medianRaw = readAdcMedian(PIN_TEMP_LM35, ADC_REF_INTERNAL_1V1, 2500, 4);

  if (savedFanPwm > 0) {
    analogWrite(PIN_FAN_PWM, savedFanPwm);
  }

  return medianRaw;
}

long readVccMillivolts() {
#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
  delayMicroseconds(2000);
  ADCSRA |= _BV(ADSC);
  while (bit_is_set(ADCSRA, ADSC)) {
    ;
  }

  uint16_t result = ADCL;
  result |= ADCH << 8;
  if (result == 0) {
    return (long)(DEFAULT_ADC_REFERENCE_V * 1000.0);
  }
  return 1125300L / result;
#else
  return (long)(DEFAULT_ADC_REFERENCE_V * 1000.0);
#endif
}
