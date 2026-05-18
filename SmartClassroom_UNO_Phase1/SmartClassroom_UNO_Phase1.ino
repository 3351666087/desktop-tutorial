/*
  SmartClassroom_UNO_Phase1.ino
  Smart Classroom Energy-Saving, Safety & Asset Monitoring System

  Arduino UNO Edge Control Node v1 hardware integration only.
  No ESP32, WiFi, MQTT, LCD, gas, flame, or accelerometer code in this phase.

  Temperature sensor:
  - LM35 VCC -> UNO 5V
  - LM35 GND -> UNO GND
  - LM35 OUT/SIG -> UNO A2

  Humanized phase-1 behavior:
  - Bright-room lockout: if the room is bright enough, the LED stays off even when PIR sees motion.
  - Dark-room occupancy lighting: when the room is dark, PIR motion enables the LED for a grace period.
  - Progressive cooling: above 26 C, the fan target PWM rises with temperature instead of jumping to max.
  - Soft fan ramp: actual fan PWM ramps up/down gradually as temperature changes.
  - Tach health check: RPM is monitored when the fan is commanded on, without blocking cooling control.
  - Buzzer is used only for short event feedback, never as a continuous alarm.

  If the fan relay behavior is reversed, only swap these two constants:
    const int RELAY_ON  = LOW;
    const int RELAY_OFF = HIGH;
*/

// ---------------- Pin definitions ----------------
#define PIN_PIR        2
#define PIN_FAN_TACH   3
#define PIN_TEMP_LM35  A2
#define PIN_LED        5
#define PIN_RELAY_FAN  6
#define PIN_BUZZER     7
#define PIN_FAN_PWM    9
#define PIN_LIGHT      A0

// ---------------- Thresholds and constants ----------------
// Current relay behavior appears active HIGH. If yours is active LOW, swap these.
const int RELAY_ON  = HIGH;
const int RELAY_OFF = LOW;

const unsigned long SERIAL_INTERVAL_MS = 1000;
const unsigned long SENSOR_INTERVAL_MS = 1000;
const unsigned long FAN_RAMP_INTERVAL_MS = 250;
const unsigned long NO_MOTION_TIMEOUT_MS = 10000;
const unsigned long SENSOR_ALERT_INTERVAL_MS = 30000;
const unsigned long TACH_FAULT_TIMEOUT_MS = 7000;
const unsigned long FAN_VERIFY_MIN_RUN_MS = 12000;
const unsigned long FAN_VERIFY_PAUSE_MS = 3500;
const unsigned long FAN_VERIFY_COOLDOWN_MS = 20000;

const int LIGHT_DARK_ON_THRESHOLD = 330;     // Below this, lighting is allowed.
const int LIGHT_BRIGHT_OFF_THRESHOLD = 430;  // Above this, lighting is locked out.

const float FAN_START_TEMP_C = 26.0;         // Fan starts to assist above this.
const float FAN_STOP_TEMP_C = 25.0;          // Fan softly ramps down below this.
const float FAN_MAX_TEMP_C = 33.0;           // Full fan command at/above this.

const byte FAN_MIN_PWM = 85;                 // Reliable low-speed command.
const byte FAN_MAX_PWM = 255;
const byte FAN_RAMP_UP_STEP = 8;             // Every FAN_RAMP_INTERVAL_MS.
const byte FAN_RAMP_DOWN_STEP = 4;
const bool FAN_PWM_INVERTED = false;         // Set true only if your fan interprets PWM backwards.

const byte TACH_PULSES_PER_REV = 2;          // Most 4-wire PC fans output 2 pulses/rev.
const byte ADC_REF_AVCC = _BV(REFS0);
const byte ADC_REF_INTERNAL_1V1 = _BV(REFS1) | _BV(REFS0);
const float DEFAULT_ADC_REFERENCE_V = 5.0;   // Fallback if Vcc measurement fails.
const float TEMP_ADC_REFERENCE_V = 1.265;    // Calibrated INTERNAL reference: raw 202 at 25.0 C.
const unsigned int TEMP_PWM_QUIET_US = 5000; // Pause D9 PWM briefly while sampling LM35.
const float TEMP_CALIBRATION_SCALE = 1.0;    // Fine tune only after comparing with a room thermometer.
const float TEMP_CALIBRATION_OFFSET_C = 0.0;
const float TEMP_OBSERVER_OFF_ALPHA = 0.45;      // Trust LM35 more when the fan is electrically quiet.
const float TEMP_OBSERVER_ON_RISE_ALPHA = 0.06;  // Hotter readings during fan run are treated cautiously.
const float TEMP_OBSERVER_ON_FALL_ALPHA = 0.35;  // Cooler corrected readings are allowed to settle quickly.
const float FAN_BIAS_LEARN_ALPHA = 0.70;         // Learns fan-induced LM35 uplift quickly.
const float FAN_BIAS_RELEASE_ALPHA = 0.18;       // Releases learned bias after the fan winds down.
const float FAN_BIAS_VERIFY_THRESHOLD_C = 1.0;   // Above this, run an active fan-off verification sample.

// ---------------- Global variables ----------------
volatile unsigned long tachPulseCounter = 0;

bool motionDetected = false;
bool occupied = false;
bool wasOccupied = false;
bool isDark = false;
bool ledOn = false;
bool wasLedOn = false;
bool fanRelayOn = false;
bool wasFanRelayOn = false;
bool temperatureValid = false;
bool fanTachFault = false;
bool fanVerifyActive = false;
bool tempObserverReady = false;
bool buzzerActive = false;

int lightValue = 0;
int tempRaw = 0;
float tempVoltage = 0.0;
float adcReferenceV = DEFAULT_ADC_REFERENCE_V;
float temperatureSensorC = 0.0;
float temperatureCalibratedC = 0.0;
float temperatureC = 0.0;
float ambientEstimateC = 0.0;
float fanBiasEstimateC = 0.0;

byte fanPwmTarget = 0;
byte fanPwmOutput = 0;

unsigned long lastMotionMs = 0;
unsigned long lastSensorReadMs = 0;
unsigned long lastSerialOutputMs = 0;
unsigned long lastFanRampMs = 0;
unsigned long lastTachPulseCount = 0;
unsigned long fanNoTachSinceMs = 0;
unsigned long fanRunStartedMs = 0;
unsigned long fanVerifyUntilMs = 0;
unsigned long lastFanVerifyMs = 0;
unsigned long buzzerOffAtMs = 0;
unsigned long lastAlertBeepMs = 0;

unsigned int estimatedRpm = 0;
const char *currentMode = "NORMAL";
const char *tempSource = "QUIET";

// ---------------- Function declarations ----------------
void readSensors();
void updateControlLogic();
void applyActuators();
void updateSerialOutput();
void tachISR();
void setupFanPwm25kHz();
void setFanPwmValue(byte value);
byte calculateFanTargetPwm(float tempC);
byte analogPinToAdcChannel(byte pin);
int readAdcOnce();
int readAdcMedian(byte pin, byte referenceBits, unsigned int settleUs, byte discardCount);
int readLm35QuietInternalMedian();
int readLightAverageDefault();
long readVccMillivolts();
void requestBeep(unsigned long durationMs);
void updateBuzzer();
const char *fanHealthText();

void setup() {
  pinMode(PIN_RELAY_FAN, OUTPUT);
  digitalWrite(PIN_RELAY_FAN, RELAY_OFF);  // Keep fan off during boot.

  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_FAN_TACH, INPUT_PULLUP);     // External 10k pull-up is still recommended.
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, LOW);
  setupFanPwm25kHz();
  setFanPwmValue(0);

  Serial.begin(9600);
  while (!Serial) {
    ;  // UNO ignores this, harmless for compatible boards.
  }

  attachInterrupt(digitalPinToInterrupt(PIN_FAN_TACH), tachISR, FALLING);

  const unsigned long now = millis();
  lastSensorReadMs = now;
  lastSerialOutputMs = now;
  lastFanRampMs = now;

  requestBeep(140);

  Serial.println(F("SmartClassroom_UNO_Phase1 started"));
  Serial.println(F("Temperature sensor=LM35 on A2"));
  Serial.println(F("Fan PWM=D9 Timer1 25kHz soft-ramp; LM35 uses quiet INTERNAL 1.1V ADC sampling"));
  Serial.println(F("Serial fields: PIR, occupancy, lightValue, light, lightGate, temperatureC, sensorTempC, tempComp, tempSource, tempRaw, tempVoltage, vcc, fanRelay, LED, fanPWM, fanTarget, tachPulses, estimatedRPM, fanHealth, mode"));
}

void loop() {
  const unsigned long now = millis();

  if (now - lastSensorReadMs >= SENSOR_INTERVAL_MS) {
    lastSensorReadMs = now;
    readSensors();
    updateControlLogic();
  }

  applyActuators();
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

  wasOccupied = occupied;
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
  temperatureSensorC = tempVoltage * 100.0;
  temperatureCalibratedC = (temperatureSensorC * TEMP_CALIBRATION_SCALE) + TEMP_CALIBRATION_OFFSET_C;
  temperatureValid = (tempRaw > 1 && tempRaw < 1022 && temperatureCalibratedC >= -5.0 && temperatureCalibratedC <= 80.0);

  if (temperatureValid) {
    if (!tempObserverReady) {
      ambientEstimateC = temperatureCalibratedC;
      fanBiasEstimateC = 0.0;
      tempObserverReady = true;
      tempSource = "QUIET";
    } else if (fanRelayOn || fanPwmOutput > 0 || fanPwmTarget > 0) {
      const float apparentBiasC = max(0.0, temperatureCalibratedC - ambientEstimateC);
      fanBiasEstimateC += (apparentBiasC - fanBiasEstimateC) * FAN_BIAS_LEARN_ALPHA;

      const float correctedTempC = temperatureCalibratedC - fanBiasEstimateC;
      const float observerAlpha = (correctedTempC < ambientEstimateC) ? TEMP_OBSERVER_ON_FALL_ALPHA : TEMP_OBSERVER_ON_RISE_ALPHA;
      ambientEstimateC += (correctedTempC - ambientEstimateC) * observerAlpha;
      tempSource = fanVerifyActive ? "VERIFYING" : "ADAPTIVE";
    } else {
      fanBiasEstimateC += (0.0 - fanBiasEstimateC) * FAN_BIAS_RELEASE_ALPHA;
      ambientEstimateC += (temperatureCalibratedC - ambientEstimateC) * TEMP_OBSERVER_OFF_ALPHA;
      tempSource = fanVerifyActive ? "VERIFYING" : "QUIET";
    }
    temperatureC = ambientEstimateC;
  } else {
    temperatureC = temperatureCalibratedC;
  }

  noInterrupts();
  const unsigned long pulsesNow = tachPulseCounter;
  interrupts();

  const unsigned long pulseDelta = pulsesNow - lastTachPulseCount;
  lastTachPulseCount = pulsesNow;
  estimatedRpm = (pulseDelta * 60UL) / TACH_PULSES_PER_REV;
}

void updateControlLogic() {
  const unsigned long now = millis();

  ledOn = occupied && isDark;

  if (fanVerifyActive && now >= fanVerifyUntilMs) {
    fanVerifyActive = false;
    lastFanVerifyMs = now;
    fanRunStartedMs = 0;
  }

  if (temperatureValid) {
    fanPwmTarget = calculateFanTargetPwm(temperatureC);
  } else {
    fanPwmTarget = 0;
  }

  const bool fanIsRunningOrCommanded = fanRelayOn || fanPwmOutput > 0 || fanPwmTarget > 0;
  if (fanIsRunningOrCommanded && fanRunStartedMs == 0) {
    fanRunStartedMs = now;
  } else if (!fanIsRunningOrCommanded) {
    fanRunStartedMs = 0;
  }

  if (!fanVerifyActive &&
      fanRunStartedMs > 0 &&
      now - fanRunStartedMs >= FAN_VERIFY_MIN_RUN_MS &&
      now - lastFanVerifyMs >= FAN_VERIFY_COOLDOWN_MS &&
      fanBiasEstimateC >= FAN_BIAS_VERIFY_THRESHOLD_C) {
    fanVerifyActive = true;
    fanVerifyUntilMs = now + FAN_VERIFY_PAUSE_MS;
    fanPwmTarget = 0;
    requestBeep(45);
  }

  if (fanVerifyActive) {
    fanPwmTarget = 0;
  }

  if (fanRelayOn && fanPwmOutput >= FAN_MIN_PWM && estimatedRpm == 0) {
    if (fanNoTachSinceMs == 0) {
      fanNoTachSinceMs = now;
    }
    fanTachFault = (now - fanNoTachSinceMs >= TACH_FAULT_TIMEOUT_MS);
  } else {
    fanNoTachSinceMs = 0;
    fanTachFault = false;
  }

  if (ledOn && !wasLedOn) {
    requestBeep(35);
  }

  if (fanRelayOn && !wasFanRelayOn) {
    requestBeep(70);
  }

  if ((fanTachFault || !temperatureValid) && now - lastAlertBeepMs >= SENSOR_ALERT_INTERVAL_MS) {
    lastAlertBeepMs = now;
    requestBeep(110);
  }

  if (!temperatureValid || fanTachFault) {
    currentMode = "SENSOR_ERROR";
  } else if (fanVerifyActive) {
    currentMode = "VERIFYING";
  } else if (fanPwmTarget > 0 || fanPwmOutput > 0) {
    currentMode = "COOLING";
  } else if (ledOn) {
    currentMode = "LIGHTING";
  } else if (!occupied) {
    currentMode = "ENERGY_SAVING";
  } else {
    currentMode = "NORMAL";
  }

  wasLedOn = ledOn;
  wasFanRelayOn = fanRelayOn;
}

void applyActuators() {
  const unsigned long now = millis();

  if (fanVerifyActive) {
    fanPwmOutput = 0;
    fanRelayOn = false;
    digitalWrite(PIN_LED, ledOn ? HIGH : LOW);
    digitalWrite(PIN_RELAY_FAN, RELAY_OFF);
    setFanPwmValue(0);
    return;
  }

  if (now - lastFanRampMs >= FAN_RAMP_INTERVAL_MS) {
    lastFanRampMs = now;

    if (fanPwmTarget > 0 && fanPwmOutput == 0) {
      fanPwmOutput = FAN_MIN_PWM;
    } else if (fanPwmOutput < fanPwmTarget) {
      const int nextValue = fanPwmOutput + FAN_RAMP_UP_STEP;
      fanPwmOutput = (nextValue > fanPwmTarget) ? fanPwmTarget : nextValue;
    } else if (fanPwmOutput > fanPwmTarget) {
      const int nextValue = fanPwmOutput - FAN_RAMP_DOWN_STEP;
      fanPwmOutput = (nextValue < fanPwmTarget) ? fanPwmTarget : nextValue;
    }
  }

  fanRelayOn = temperatureValid && (fanPwmTarget > 0 || fanPwmOutput > 0);

  digitalWrite(PIN_LED, ledOn ? HIGH : LOW);
  digitalWrite(PIN_RELAY_FAN, fanRelayOn ? RELAY_ON : RELAY_OFF);
  setFanPwmValue(fanRelayOn ? fanPwmOutput : 0);
}

void updateSerialOutput() {
  noInterrupts();
  const unsigned long pulsesTotal = tachPulseCounter;
  interrupts();

  Serial.print(F("PIR="));
  Serial.print(motionDetected ? F("motion") : F("no_motion"));
  Serial.print(F(" occupancy="));
  Serial.print(occupied ? F("occupied") : F("vacant"));
  Serial.print(F(" lightValue="));
  Serial.print(lightValue);
  Serial.print(F(" light="));
  Serial.print(isDark ? F("dark") : F("bright"));
  Serial.print(F(" lightGate="));
  Serial.print(isDark ? F("enabled") : F("blocked"));
  Serial.print(F(" temperatureC="));
  if (temperatureValid) {
    Serial.print(temperatureC, 1);
  } else {
    Serial.print(temperatureC, 1);
    Serial.print(F("(ERROR)"));
  }
  Serial.print(F(" sensorTempC="));
  Serial.print(temperatureCalibratedC, 1);
  Serial.print(F(" tempComp="));
  Serial.print(fanBiasEstimateC, 1);
  Serial.print(F(" tempSource="));
  Serial.print(tempSource);
  Serial.print(F(" tempRaw="));
  Serial.print(tempRaw);
  Serial.print(F(" tempVoltage="));
  Serial.print(tempVoltage, 3);
  Serial.print(F(" vcc="));
  Serial.print(adcReferenceV, 2);
  Serial.print(F(" fanRelay="));
  Serial.print(fanRelayOn ? F("ON") : F("OFF"));
  Serial.print(F(" LED="));
  Serial.print(ledOn ? F("ON") : F("OFF"));
  Serial.print(F(" fanPWM="));
  Serial.print(fanPwmOutput);
  Serial.print(F(" fanTarget="));
  Serial.print(fanPwmTarget);
  Serial.print(F(" tachPulses="));
  Serial.print(pulsesTotal);
  Serial.print(F(" estimatedRPM="));
  Serial.print(estimatedRpm);
  Serial.print(F(" fanHealth="));
  Serial.print(fanHealthText());
  Serial.print(F(" mode="));
  Serial.println(currentMode);
}

void tachISR() {
  tachPulseCounter++;
}

void setupFanPwm25kHz() {
  pinMode(PIN_FAN_PWM, OUTPUT);

  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;

  ICR1 = 639;  // 16 MHz / (1 * (639 + 1)) = 25 kHz.
  OCR1A = 0;

  TCCR1A = _BV(COM1A1) | _BV(WGM11);
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS10);
}

void setFanPwmValue(byte value) {
  const byte logicalValue = FAN_PWM_INVERTED ? (255 - value) : value;
  OCR1A = ((unsigned long)logicalValue * ICR1) / 255;
}

byte calculateFanTargetPwm(float tempC) {
  if (tempC < FAN_STOP_TEMP_C) {
    return 0;
  }

  if (tempC <= FAN_START_TEMP_C) {
    return 0;
  }

  if (tempC >= FAN_MAX_TEMP_C) {
    return FAN_MAX_PWM;
  }

  const float ratio = (tempC - FAN_START_TEMP_C) / (FAN_MAX_TEMP_C - FAN_START_TEMP_C);
  const int pwm = FAN_MIN_PWM + (int)((FAN_MAX_PWM - FAN_MIN_PWM) * ratio);
  return constrain(pwm, FAN_MIN_PWM, FAN_MAX_PWM);
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

int readLm35QuietInternalMedian() {
  const byte savedFanPwm = fanPwmOutput;

  if (savedFanPwm > 0) {
    setFanPwmValue(0);
    delayMicroseconds(TEMP_PWM_QUIET_US);
  }

  const int medianRaw = readAdcMedian(PIN_TEMP_LM35, ADC_REF_INTERNAL_1V1, 2500, 4);

  if (savedFanPwm > 0) {
    setFanPwmValue(savedFanPwm);
  }

  return medianRaw;
}

int readLightAverageDefault() {
  ADMUX = ADC_REF_AVCC | (analogPinToAdcChannel(PIN_LIGHT) & 0x07);
  delayMicroseconds(250);
  readAdcOnce();  // Discard first read after reference/channel switching.

  unsigned int lightSampleSum = 0;
  const byte lightSampleCount = 8;
  for (byte i = 0; i < lightSampleCount; i++) {
    lightSampleSum += readAdcOnce();
  }
  return lightSampleSum / lightSampleCount;
}

long readVccMillivolts() {
#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
  delay(2);  // Short ADC reference settling pause, once per second.
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

void requestBeep(unsigned long durationMs) {
  digitalWrite(PIN_BUZZER, HIGH);
  buzzerActive = true;
  buzzerOffAtMs = millis() + durationMs;
}

void updateBuzzer() {
  if (buzzerActive && (long)(millis() - buzzerOffAtMs) >= 0) {
    buzzerActive = false;
    digitalWrite(PIN_BUZZER, LOW);
  }
}

const char *fanHealthText() {
  if (fanTachFault) {
    return "NO_TACH";
  }
  if (fanRelayOn && estimatedRpm > 0) {
    return "RUNNING";
  }
  if (fanRelayOn) {
    return "STARTING";
  }
  return "STANDBY";
}
