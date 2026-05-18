#define _SS_MAX_RX_BUFF 128
#include <SoftwareSerial.h>

/*
  UNO_Phase3_TelemetryPatch.ino
  Smart Classroom Energy-Saving, Safety & Asset Monitoring System

  Phase 3 UNO Edge Node:
  - Phase 1 union: PIR occupancy, TEMT6000 light gate, LM35 temperature, LED lighting,
    relay fan power, 4-wire fan PWM, fan tach, buzzer, serial telemetry.
  - Phase 2 union: gas sensor, flame sensor, emergency test button, traffic light,
    safety alarm priority.
  - Phase 3 patch: SoftwareSerial telemetry to ESP32 gateway on A4/A5.
  - Mixed features:
    1. Air-quality warning ventilation before full alarm.
    2. Gas-warning + suspicious flame analog escalates to safety alarm.
    3. Safety alarm turns on classroom LED in dark/occupied conditions for evacuation.
    4. Occupied rooms use a faster alarm buzzer cadence than vacant rooms.
    5. Fan tach health checks report stuck/no-tach faults.
    6. LM35 uses quiet internal-reference ADC sampling to reduce fan/PWM coupling.
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
#define PIN_ESP_RX     A4
#define PIN_ESP_TX     A5

SoftwareSerial espSerial(PIN_ESP_RX, PIN_ESP_TX);

// ---------------- Constants and thresholds ----------------
// Current relay behavior appears active HIGH. If yours is active LOW, swap these.
const int RELAY_ON = HIGH;
const int RELAY_OFF = LOW;

const int BUZZER_ON = HIGH;
const int BUZZER_OFF = LOW;

const bool PIR_ACTIVE_HIGH = true;        // Most PIR modules output HIGH when motion is detected.
const bool FLAME_ACTIVE_LOW = true;       // Change only this if Flame DO logic is reversed.
const bool FLAME_AO_ACTIVE_LOW = true;    // Most flame modules read lower AO near flame.

const unsigned long SENSOR_INTERVAL_MS = 1000;
const unsigned long SERIAL_INTERVAL_MS = 1000;
const unsigned long FAN_RAMP_INTERVAL_MS = 250;
const unsigned long NO_MOTION_TIMEOUT_MS = 10000;
const unsigned long BUTTON_DEBOUNCE_MS = 40;
const unsigned long SENSOR_ERROR_BLINK_MS = 500;
const unsigned long FAN_TACH_FAULT_TIMEOUT_MS = 7000;
const unsigned long WARNING_CHIRP_INTERVAL_MS = 10000;
const unsigned long WARNING_CHIRP_MS = 60;
const unsigned long REMOTE_DEMO_HOLD_MS = 10000;
const byte ESP_CMD_BUFFER_SIZE = 96;
const unsigned int STATUS_PWM_PERIOD_US = 4096;

const int LIGHT_DARK_ON_THRESHOLD = 330;
const int LIGHT_BRIGHT_OFF_THRESHOLD = 430;

const float FAN_START_TEMP_C = 26.0;
const float FAN_STOP_TEMP_C = 25.0;
const float FAN_MAX_TEMP_C = 33.0;

const byte FAN_MIN_PWM = 85;
const byte FAN_AIR_QUALITY_PWM = 170;
const byte FAN_ALARM_PWM = 255;
const byte FAN_RAMP_UP_STEP = 8;
const byte FAN_RAMP_DOWN_STEP = 4;
const bool FAN_PWM_INVERTED = false;

const int GAS_DANGER_THRESHOLD = 450;      // Adjust after observing gasValue in clean air.
const int GAS_WARNING_DELTA = 80;          // gasValue above baseline for warning ventilation.
const int GAS_DANGER_DELTA = 160;          // gasValue above baseline for safety alarm.
const int GAS_BASELINE_MIN = 80;
const float GAS_BASELINE_ALPHA = 0.02;

const int FLAME_AO_SUSPICIOUS_LOW = 450;   // If AO logic differs, tune with Serial values.
const int FLAME_AO_SUSPICIOUS_HIGH = 650;

const byte TACH_PULSES_PER_REV = 2;
const byte ADC_REF_AVCC = _BV(REFS0);
const byte ADC_REF_INTERNAL_1V1 = _BV(REFS1) | _BV(REFS0);
const float DEFAULT_ADC_REFERENCE_V = 5.0;
const float TEMP_ADC_REFERENCE_V = 1.265;  // Calibrated internal ADC reference from Phase 1.
const unsigned int TEMP_PWM_QUIET_US = 5000;
const float TEMP_CALIBRATION_SCALE = 1.0;
const float TEMP_CALIBRATION_OFFSET_C = 0.0;

const float TEMP_OBSERVER_OFF_ALPHA = 0.45;
const float TEMP_OBSERVER_ON_RISE_ALPHA = 0.06;
const float TEMP_OBSERVER_ON_FALL_ALPHA = 0.35;
const float FAN_BIAS_LEARN_ALPHA = 0.70;
const float FAN_BIAS_RELEASE_ALPHA = 0.18;
const unsigned long ESP32_TEMP_TIMEOUT_MS = 7000;
const float ESP32_TEMP_MIN_C = 5.0;
const float ESP32_TEMP_MAX_C = 60.0;

// ---------------- enum SystemMode ----------------
enum SystemMode {
  MODE_NORMAL,
  MODE_LIGHTING,
  MODE_COOLING,
  MODE_AIR_QUALITY_WARNING,
  MODE_ENERGY_SAVING,
  MODE_SAFETY_ALARM,
  MODE_SENSOR_ERROR,
  MODE_MANUAL
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
bool fanTachFault = false;

bool gasBaselineReady = false;
bool gasWarning = false;
bool gasDanger = false;
bool flameDetected = false;
bool flameSuspicious = false;
bool demoEmergency = false;
bool remoteDemoEmergency = false;
bool safetyAlarm = false;
bool airQualityVentilation = false;
bool buzzerPulseActive = false;
bool manualMode = false;
bool manualLampState = false;
bool manualFanRelayState = false;
bool manualBuzzerState = false;
bool manualStatusR = true;
bool manualStatusY = true;
bool manualStatusG = true;
bool statusRState = false;
bool statusYState = false;
bool statusGState = true;

int lightValue = 0;
int gasValue = 0;
int gasBaseline = 0;
int flameDigital = HIGH;
int flameAnalog = 0;
int tempRaw = 0;

float tempVoltage = 0.0;
float adcReferenceV = DEFAULT_ADC_REFERENCE_V;
float temperatureSensorC = 0.0;
float temperatureCalibratedC = 0.0;
float temperatureC = 0.0;
float esp32TemperatureC = 0.0;
float ambientEstimateC = 0.0;
float fanBiasEstimateC = 0.0;
bool esp32TemperatureValid = false;
bool usingEsp32Temperature = false;

byte fanPwmTarget = 0;
byte fanPwmOutput = 0;
byte manualFanPwm = 0;
byte ledBrightnessMax = 255;
byte statusBrightnessMax = 255;

int lightDarkOnThreshold = LIGHT_DARK_ON_THRESHOLD;
int lightBrightOffThreshold = LIGHT_BRIGHT_OFF_THRESHOLD;

float fanStartTempC = FAN_START_TEMP_C;
float fanStopTempC = FAN_STOP_TEMP_C;

bool rawButtonPressed = false;
bool lastRawButtonPressed = false;
bool stableButtonPressed = false;
unsigned long lastButtonChangeMs = 0;

unsigned long lastMotionMs = 0;
unsigned long lastSensorReadMs = 0;
unsigned long lastSerialOutputMs = 0;
unsigned long lastFanRampMs = 0;
unsigned long lastTachPulseCount = 0;
unsigned long fanNoTachSinceMs = 0;
unsigned long buzzerPulseOffAtMs = 0;
unsigned long lastWarningChirpMs = 0;
unsigned long remoteDemoUntilMs = 0;
unsigned long lastEsp32TemperatureMs = 0;

unsigned int estimatedRpm = 0;
const char *tempSource = "QUIET";
const char *safetyReason = "NONE";
char espCommandBuffer[ESP_CMD_BUFFER_SIZE];
byte espCommandLength = 0;

// ---------------- Function declarations ----------------
void tachISR();
void setup();
void loop();
void readSensors();
void updatePirOccupancy();
void updateButton();
void updateControlLogic();
void applyActuators();
void updateStatusLight();
void updateBuzzer();
void applyStatusLightSoftPwm();
void updateSerialOutput();
void readCommandsFromESP32();
void handleEspCommand(char *line);
void sendCommandAck(const char *command, const char *result);
bool commandHas(char *line, const char *key);
bool readIntCommandValue(char *line, const char *key, int *out);
bool readFloatCommandValue(char *line, const char *key, float *out);
void applyCommandConfig(char *line);
void applyManualCommand(char *line);
bool applyRemoteTemperatureCommand(char *line);
void sendTelemetryToESP32();
void printSc2Telemetry(Print &out);
const char *modeToString(SystemMode mode);
void setStatusLight(bool red, bool yellow, bool green);
const char *statusLightColor();
char statusLightShort();
const char *fanHealthText();
byte calculateFanTargetPwm(float tempC);
void requestBuzzerPulse(unsigned long durationMs);
byte analogPinToAdcChannel(byte pin);
int readAdcOnce();
int readAdcMedian(byte pin, byte referenceBits, unsigned int settleUs, byte discardCount);
int readAverageAvcc(byte pin, byte sampleCount);
int readLm35QuietInternalMedian();
long readVccMillivolts();
void setupFanPwm25kHz();
void setFanPwmValue(byte value);

void tachISR() {
  tachPulseCounter++;
}

void setup() {
  pinMode(PIN_RELAY_FAN, OUTPUT);
  digitalWrite(PIN_RELAY_FAN, RELAY_OFF);

  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_FAN_TACH, INPUT_PULLUP);
  pinMode(PIN_DEMO_BTN, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_FLAME_DO, INPUT);
  pinMode(PIN_STATUS_R, OUTPUT);
  pinMode(PIN_STATUS_Y, OUTPUT);
  pinMode(PIN_STATUS_G, OUTPUT);

  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, BUZZER_OFF);
  setStatusLight(false, false, true);
  setupFanPwm25kHz();
  setFanPwmValue(0);

  Serial.begin(9600);
  espSerial.begin(9600);
  espSerial.listen();
  while (!Serial) {
    ;
  }

  attachInterrupt(digitalPinToInterrupt(PIN_FAN_TACH), tachISR, FALLING);

  const unsigned long now = millis();
  lastSensorReadMs = now;
  lastSerialOutputMs = now;
  lastFanRampMs = now;

  requestBuzzerPulse(120);

  Serial.println(F("UNO_Phase3_TelemetryPatch started"));
  Serial.println(F("Union: Phase1 energy/comfort + Phase2 safety alarm + ESP32 SC2 telemetry"));
  Serial.println(F("Serial fields include: mode, pir, occupied, lightValue, temperatureC, gas, flame, emergency, fan, rpm, LED, statusLight, safetyReason"));
  Serial.println(F("ESP32 telemetry on SoftwareSerial A5(TX) / A4(RX), 9600 baud, SC2 CSV"));
}

void loop() {
  const unsigned long now = millis();

  readCommandsFromESP32();
  updateButton();
  updatePirOccupancy();

  if (now - lastSensorReadMs >= SENSOR_INTERVAL_MS) {
    lastSensorReadMs = now;
    readSensors();
  }

  updateControlLogic();
  applyActuators();
  updateStatusLight();
  updateBuzzer();
  applyStatusLightSoftPwm();

  if (now - lastSerialOutputMs >= SERIAL_INTERVAL_MS) {
    lastSerialOutputMs = now;
    updateSerialOutput();
    sendTelemetryToESP32();
  }
}

void readSensors() {
  lightValue = readAverageAvcc(PIN_LIGHT, 8);
  if (lightValue <= lightDarkOnThreshold) {
    isDark = true;
  } else if (lightValue >= lightBrightOffThreshold) {
    isDark = false;
  }

  const long vccMv = readVccMillivolts();
  adcReferenceV = (vccMv > 3500 && vccMv < 5500) ? (vccMv / 1000.0) : DEFAULT_ADC_REFERENCE_V;

  tempRaw = readLm35QuietInternalMedian();
  tempVoltage = tempRaw * (TEMP_ADC_REFERENCE_V / 1023.0);
  temperatureSensorC = tempVoltage * 100.0;
  temperatureCalibratedC = (temperatureSensorC * TEMP_CALIBRATION_SCALE) + TEMP_CALIBRATION_OFFSET_C;
  const bool localTemperatureValid = (tempRaw > 1 && tempRaw < 1022 && temperatureCalibratedC >= -5.0 && temperatureCalibratedC <= 80.0);
  const unsigned long now = millis();
  const bool remoteTempFresh = esp32TemperatureValid && (now - lastEsp32TemperatureMs <= ESP32_TEMP_TIMEOUT_MS);

  if (remoteTempFresh) {
    usingEsp32Temperature = true;
    temperatureValid = true;
    fanBiasEstimateC += (0.0 - fanBiasEstimateC) * FAN_BIAS_RELEASE_ALPHA;
    if (ambientEstimateC == 0.0) {
      ambientEstimateC = esp32TemperatureC;
    } else {
      const float alpha = (fanRelayState || fanPwmOutput > 0 || fanPwmTarget > 0) ? 0.28 : TEMP_OBSERVER_OFF_ALPHA;
      ambientEstimateC += (esp32TemperatureC - ambientEstimateC) * alpha;
    }
    temperatureC = ambientEstimateC;
    tempSource = "ESP32_ADC";
  } else if (localTemperatureValid) {
    usingEsp32Temperature = false;
    temperatureValid = true;
    if (ambientEstimateC == 0.0) {
      ambientEstimateC = temperatureCalibratedC;
      fanBiasEstimateC = 0.0;
      tempSource = "QUIET";
    } else if (fanRelayState || fanPwmOutput > 0 || fanPwmTarget > 0) {
      const float apparentBiasC = max(0.0, temperatureCalibratedC - ambientEstimateC);
      fanBiasEstimateC += (apparentBiasC - fanBiasEstimateC) * FAN_BIAS_LEARN_ALPHA;
      const float correctedTempC = temperatureCalibratedC - fanBiasEstimateC;
      const float alpha = (correctedTempC < ambientEstimateC) ? TEMP_OBSERVER_ON_FALL_ALPHA : TEMP_OBSERVER_ON_RISE_ALPHA;
      ambientEstimateC += (correctedTempC - ambientEstimateC) * alpha;
      tempSource = "ADAPTIVE";
    } else {
      fanBiasEstimateC += (0.0 - fanBiasEstimateC) * FAN_BIAS_RELEASE_ALPHA;
      ambientEstimateC += (temperatureCalibratedC - ambientEstimateC) * TEMP_OBSERVER_OFF_ALPHA;
      tempSource = "QUIET";
    }
    temperatureC = ambientEstimateC;
  } else {
    usingEsp32Temperature = false;
    temperatureValid = false;
    temperatureC = temperatureCalibratedC;
  }

  gasValue = readAverageAvcc(PIN_GAS, 8);
  if (!gasBaselineReady) {
    gasBaseline = max(gasValue, GAS_BASELINE_MIN);
    gasBaselineReady = true;
  } else if (!gasDanger) {
    gasBaseline = (int)((gasBaseline * (1.0 - GAS_BASELINE_ALPHA)) + (gasValue * GAS_BASELINE_ALPHA));
  }

  gasWarning = (gasValue >= gasBaseline + GAS_WARNING_DELTA);
  gasDanger = (gasValue >= GAS_DANGER_THRESHOLD) || (gasValue >= gasBaseline + GAS_DANGER_DELTA);

  flameDigital = digitalRead(PIN_FLAME_DO);
  flameAnalog = readAverageAvcc(PIN_FLAME_AO, 8);
  flameDetected = FLAME_ACTIVE_LOW ? (flameDigital == LOW) : (flameDigital == HIGH);
  flameSuspicious = FLAME_AO_ACTIVE_LOW ? (flameAnalog <= FLAME_AO_SUSPICIOUS_LOW) : (flameAnalog >= FLAME_AO_SUSPICIOUS_HIGH);

  noInterrupts();
  const unsigned long pulsesNow = tachPulseCounter;
  interrupts();

  const unsigned long pulseDelta = pulsesNow - lastTachPulseCount;
  lastTachPulseCount = pulsesNow;
  estimatedRpm = (pulseDelta * 60UL) / TACH_PULSES_PER_REV;
}

void updatePirOccupancy() {
  const unsigned long now = millis();
  const bool rawPirHigh = (digitalRead(PIN_PIR) == HIGH);

  motionDetected = PIR_ACTIVE_HIGH ? rawPirHigh : !rawPirHigh;
  if (motionDetected) {
    lastMotionMs = now;
  }

  occupied = (lastMotionMs > 0 && (motionDetected || now - lastMotionMs <= NO_MOTION_TIMEOUT_MS));
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

  remoteDemoEmergency = (remoteDemoUntilMs > 0 && (long)(remoteDemoUntilMs - now) > 0);
  demoEmergency = stableButtonPressed || remoteDemoEmergency;
}

void updateControlLogic() {
  safetyReason = "NONE";
  if (gasDanger) {
    safetyReason = "GAS";
  } else if (flameDetected) {
    safetyReason = "FLAME";
  } else if (stableButtonPressed) {
    safetyReason = "BUTTON";
  } else if (remoteDemoEmergency) {
    safetyReason = "REMOTE_DEMO";
  } else if (gasWarning && flameSuspicious) {
    safetyReason = "GAS_FLAME_FUSION";
  }

  safetyAlarm = gasDanger || flameDetected || demoEmergency || (gasWarning && flameSuspicious);
  airQualityVentilation = gasWarning && !safetyAlarm;

  if (safetyAlarm) {
    currentMode = MODE_SAFETY_ALARM;
    classroomLedState = occupied || isDark;  // Evacuation visibility.
    fanPwmTarget = FAN_ALARM_PWM;
    fanRelayState = true;
    return;
  }

  if (manualMode) {
    currentMode = MODE_MANUAL;
    classroomLedState = manualLampState;
    fanRelayState = manualFanRelayState;
    fanPwmTarget = manualFanRelayState ? manualFanPwm : 0;
    fanTachFault = false;
    return;
  }

  classroomLedState = occupied && isDark;

  byte thermalFanTarget = 0;
  if (temperatureValid) {
    thermalFanTarget = calculateFanTargetPwm(temperatureC);
  }

  if (airQualityVentilation) {
    fanPwmTarget = max(thermalFanTarget, FAN_AIR_QUALITY_PWM);
  } else {
    fanPwmTarget = thermalFanTarget;
  }

  if (fanRelayState && fanPwmOutput >= FAN_MIN_PWM && estimatedRpm == 0) {
    if (fanNoTachSinceMs == 0) {
      fanNoTachSinceMs = millis();
    }
    fanTachFault = (millis() - fanNoTachSinceMs >= FAN_TACH_FAULT_TIMEOUT_MS);
  } else {
    fanNoTachSinceMs = 0;
    fanTachFault = false;
  }

  if (fanTachFault || !temperatureValid) {
    currentMode = MODE_SENSOR_ERROR;
  } else if (airQualityVentilation) {
    currentMode = MODE_AIR_QUALITY_WARNING;
  } else if (fanPwmTarget > 0 || fanPwmOutput > 0) {
    currentMode = MODE_COOLING;
  } else if (classroomLedState) {
    currentMode = MODE_LIGHTING;
  } else if (!occupied) {
    currentMode = MODE_ENERGY_SAVING;
  } else {
    currentMode = MODE_NORMAL;
  }

  if (airQualityVentilation && millis() - lastWarningChirpMs >= WARNING_CHIRP_INTERVAL_MS) {
    lastWarningChirpMs = millis();
    requestBuzzerPulse(WARNING_CHIRP_MS);
  }
}

void applyActuators() {
  const unsigned long now = millis();

  if (currentMode == MODE_SAFETY_ALARM) {
    fanPwmOutput = FAN_ALARM_PWM;
  } else if (currentMode == MODE_MANUAL) {
    fanPwmOutput = manualFanRelayState ? manualFanPwm : 0;
  } else if (now - lastFanRampMs >= FAN_RAMP_INTERVAL_MS) {
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

  if (currentMode == MODE_MANUAL) {
    fanRelayState = manualFanRelayState;
  } else {
    fanRelayState = (fanPwmOutput > 0);
  }

  analogWrite(PIN_LED, classroomLedState ? ledBrightnessMax : 0);
  digitalWrite(PIN_RELAY_FAN, fanRelayState ? RELAY_ON : RELAY_OFF);
  setFanPwmValue(fanRelayState ? fanPwmOutput : 0);
}

void updateStatusLight() {
  if (currentMode == MODE_MANUAL) {
    setStatusLight(manualStatusR, manualStatusY, manualStatusG);
  } else if (currentMode == MODE_SAFETY_ALARM) {
    setStatusLight(true, false, false);
  } else if (currentMode == MODE_SENSOR_ERROR) {
    const bool blinkOn = ((millis() / SENSOR_ERROR_BLINK_MS) % 2) == 0;
    setStatusLight(blinkOn, false, false);
  } else if (currentMode == MODE_AIR_QUALITY_WARNING) {
    const bool blinkOn = ((millis() / 350) % 2) == 0;
    setStatusLight(false, blinkOn, false);
  } else if (currentMode == MODE_COOLING) {
    setStatusLight(false, true, false);
  } else {
    setStatusLight(false, false, true);
  }
}

void updateBuzzer() {
  if (currentMode == MODE_SAFETY_ALARM) {
    const unsigned long period = occupied ? 360 : 650;
    const unsigned long onTime = occupied ? 130 : 90;
    const unsigned long phase = millis() % period;
    digitalWrite(PIN_BUZZER, phase < onTime ? BUZZER_ON : BUZZER_OFF);
    buzzerPulseActive = false;
    return;
  }

  if (currentMode == MODE_MANUAL) {
    digitalWrite(PIN_BUZZER, manualBuzzerState ? BUZZER_ON : BUZZER_OFF);
    buzzerPulseActive = false;
    return;
  }

  if (buzzerPulseActive && (long)(millis() - buzzerPulseOffAtMs) >= 0) {
    buzzerPulseActive = false;
    digitalWrite(PIN_BUZZER, BUZZER_OFF);
  }

  if (!buzzerPulseActive) {
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
  Serial.print(F(" sensorTempC="));
  Serial.print(temperatureCalibratedC, 1);
  Serial.print(F(" tempComp="));
  Serial.print(fanBiasEstimateC, 1);
  Serial.print(F(" tempSource="));
  Serial.print(tempSource);
  Serial.print(F(" espTempC="));
  if (esp32TemperatureValid) {
    Serial.print(esp32TemperatureC, 1);
  } else {
    Serial.print(F("NA"));
  }
  Serial.print(F(" espTempFresh="));
  Serial.print(usingEsp32Temperature ? F("true") : F("false"));
  Serial.print(F(" gasValue="));
  Serial.print(gasValue);
  Serial.print(F(" gasBaseline="));
  Serial.print(gasBaseline);
  Serial.print(F(" gasWarning="));
  Serial.print(gasWarning ? F("true") : F("false"));
  Serial.print(F(" gasDanger="));
  Serial.print(gasDanger ? F("true") : F("false"));
  Serial.print(F(" flameDigital="));
  Serial.print(flameDigital);
  Serial.print(F(" flameAnalog="));
  Serial.print(flameAnalog);
  Serial.print(F(" flameSuspicious="));
  Serial.print(flameSuspicious ? F("true") : F("false"));
  Serial.print(F(" flameDetected="));
  Serial.print(flameDetected ? F("true") : F("false"));
  Serial.print(F(" demoEmergency="));
  Serial.print(demoEmergency ? F("true") : F("false"));
  Serial.print(F(" safetyAlarm="));
  Serial.print(safetyAlarm ? F("true") : F("false"));
  Serial.print(F(" safetyReason="));
  Serial.print(safetyReason);
  Serial.print(F(" fanRelayState="));
  Serial.print(fanRelayState ? F("ON") : F("OFF"));
  Serial.print(F(" fanPwmValue="));
  Serial.print(fanPwmOutput);
  Serial.print(F(" fanTarget="));
  Serial.print(fanPwmTarget);
  Serial.print(F(" fanStartC="));
  Serial.print(fanStartTempC, 1);
  Serial.print(F(" fanStopC="));
  Serial.print(fanStopTempC, 1);
  Serial.print(F(" ledMax="));
  Serial.print(ledBrightnessMax);
  Serial.print(F(" statusMax="));
  Serial.print(statusBrightnessMax);
  Serial.print(F(" manual="));
  Serial.print(manualMode ? F("true") : F("false"));
  Serial.print(F(" rpm="));
  Serial.print(estimatedRpm);
  Serial.print(F(" fanHealth="));
  Serial.print(fanHealthText());
  Serial.print(F(" classroomLedState="));
  Serial.print(classroomLedState ? F("ON") : F("OFF"));
  Serial.print(F(" statusLight="));
  Serial.print(statusLightColor());

  if (currentMode == MODE_SAFETY_ALARM) {
    Serial.print(F(" WARNING=SAFETY_ALARM"));
  }

  Serial.println();
}

void readCommandsFromESP32() {
  while (espSerial.available() > 0) {
    const char c = (char)espSerial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      espCommandBuffer[espCommandLength] = '\0';
      if (espCommandLength > 0) {
        handleEspCommand(espCommandBuffer);
      }
      espCommandLength = 0;
      return;
    }

    if (espCommandLength < ESP_CMD_BUFFER_SIZE - 1) {
      espCommandBuffer[espCommandLength++] = c;
    } else {
      espCommandLength = 0;
      sendCommandAck("BUFFER", "overflow");
    }
  }
}

void handleEspCommand(char *line) {
  Serial.print(F("espRx="));
  Serial.println(line);

  char *cmdStart = strstr(line, "CMD");
  if (cmdStart != NULL && cmdStart != line) {
    memmove(line, cmdStart, strlen(cmdStart) + 1);
  }

  if (strncmp(line, "CMD", 3) != 0) {
    sendCommandAck("UNKNOWN", "bad_prefix");
    return;
  }

  if (strstr(line, "PING") != NULL) {
    sendCommandAck("PING", "PONG");
    return;
  }

  if (strstr(line, "TEMP10=") != NULL) {
    sendCommandAck("TEMP", applyRemoteTemperatureCommand(line) ? "ok" : "bad_value");
    return;
  }

  if (strstr(line, "BUZZ=") != NULL) {
    int durationMs = 120;
    char *value = strstr(line, "BUZZ=");
    if (value != NULL) {
      durationMs = constrain(atoi(value + 5), 30, 500);
    }
    requestBuzzerPulse((unsigned long)durationMs);
    sendCommandAck("BUZZ", "ok");
    return;
  }

  if (strstr(line, "DEMO=1") != NULL) {
    remoteDemoUntilMs = millis() + REMOTE_DEMO_HOLD_MS;
    remoteDemoEmergency = true;
    sendCommandAck("DEMO", "on");
    return;
  }

  if (strstr(line, "DEMO=0") != NULL) {
    remoteDemoUntilMs = 0;
    remoteDemoEmergency = false;
    sendCommandAck("DEMO", "off");
    return;
  }

  if (strstr(line, "CFG") != NULL || strstr(line, "FAN_ON=") != NULL || strstr(line, "LED_MAX=") != NULL || strstr(line, "STATUS_MAX=") != NULL) {
    applyCommandConfig(line);
    sendCommandAck("CFG", "ok");
    return;
  }

  if (strstr(line, "MANUAL") != NULL || strstr(line, "AUTO") != NULL || strstr(line, "LAMP=") != NULL || strstr(line, "FAN=") != NULL || strstr(line, "PWM=") != NULL || strstr(line, "STATUS=") != NULL || strstr(line, "BUZZER=") != NULL) {
    applyManualCommand(line);
    sendCommandAck("MANUAL", manualMode ? "on" : "off");
    return;
  }

  sendCommandAck("UNKNOWN", "ignored");
}

bool commandHas(char *line, const char *key) {
  return strstr(line, key) != NULL;
}

bool readIntCommandValue(char *line, const char *key, int *out) {
  char *pos = strstr(line, key);
  if (pos == NULL) {
    return false;
  }
  *out = atoi(pos + strlen(key));
  return true;
}

bool readFloatCommandValue(char *line, const char *key, float *out) {
  char *pos = strstr(line, key);
  if (pos == NULL) {
    return false;
  }
  *out = atof(pos + strlen(key));
  return true;
}

void applyCommandConfig(char *line) {
  int intValue = 0;
  float floatValue = 0.0;

  if (readFloatCommandValue(line, "FAN_ON=", &floatValue)) {
    fanStartTempC = constrain(floatValue, 15.0, 45.0);
  }
  if (readFloatCommandValue(line, "FAN_OFF=", &floatValue)) {
    fanStopTempC = constrain(floatValue, 10.0, 44.0);
  }
  if (fanStopTempC >= fanStartTempC) {
    fanStopTempC = fanStartTempC - 0.5;
  }

  if (readIntCommandValue(line, "LED_MAX=", &intValue)) {
    ledBrightnessMax = (byte)constrain(intValue, 0, 255);
  }
  if (readIntCommandValue(line, "STATUS_MAX=", &intValue)) {
    statusBrightnessMax = (byte)constrain(intValue, 0, 255);
  }
  if (readIntCommandValue(line, "LIGHT_DARK=", &intValue)) {
    lightDarkOnThreshold = constrain(intValue, 0, 1023);
  }
  if (readIntCommandValue(line, "LIGHT_BRIGHT=", &intValue)) {
    lightBrightOffThreshold = constrain(intValue, 0, 1023);
  }
  if (lightBrightOffThreshold <= lightDarkOnThreshold) {
    lightBrightOffThreshold = min(1023, lightDarkOnThreshold + 50);
  }
}

void applyManualCommand(char *line) {
  int intValue = 0;

  if (commandHas(line, "MANUAL=1")) {
    manualMode = true;
    manualStatusR = true;
    manualStatusY = true;
    manualStatusG = true;
  } else if (commandHas(line, "MANUAL=0") || commandHas(line, "AUTO")) {
    manualMode = false;
    manualBuzzerState = false;
    return;
  }

  if (readIntCommandValue(line, "LAMP=", &intValue)) {
    manualLampState = (intValue != 0);
  }
  if (readIntCommandValue(line, "FAN=", &intValue)) {
    manualFanRelayState = (intValue != 0);
    if (manualFanRelayState && manualFanPwm == 0) {
      manualFanPwm = FAN_MIN_PWM;
    }
  }
  if (readIntCommandValue(line, "PWM=", &intValue)) {
    manualFanPwm = (byte)constrain(intValue, 0, 255);
    manualFanRelayState = (manualFanPwm > 0);
  }
  if (readIntCommandValue(line, "BUZZER=", &intValue)) {
    manualBuzzerState = (intValue != 0);
  }

  char *status = strstr(line, "STATUS=");
  if (status != NULL) {
    status += 7;
    if (strncmp(status, "ALL", 3) == 0) {
      manualStatusR = true;
      manualStatusY = true;
      manualStatusG = true;
    } else if (strncmp(status, "OFF", 3) == 0) {
      manualStatusR = false;
      manualStatusY = false;
      manualStatusG = false;
    } else {
      manualStatusR = (status[0] == 'R');
      manualStatusY = (status[0] == 'Y');
      manualStatusG = (status[0] == 'G');
    }
  }
}

bool applyRemoteTemperatureCommand(char *line) {
  int temp10 = 0;
  if (!readIntCommandValue(line, "TEMP10=", &temp10)) {
    return false;
  }

  const float tempC = temp10 / 10.0;
  if (tempC < ESP32_TEMP_MIN_C || tempC > ESP32_TEMP_MAX_C) {
    esp32TemperatureValid = false;
    return false;
  }

  esp32TemperatureC = tempC;
  esp32TemperatureValid = true;
  lastEsp32TemperatureMs = millis();
  return true;
}

void sendCommandAck(const char *command, const char *result) {
  espSerial.print(F("ACK,cmd="));
  espSerial.print(command);
  espSerial.print(F(",result="));
  espSerial.println(result);

  Serial.print(F("espAck=ACK,cmd="));
  Serial.print(command);
  Serial.print(F(",result="));
  Serial.println(result);

  espSerial.listen();
}

void sendTelemetryToESP32() {
  printSc2Telemetry(espSerial);
  espSerial.listen();
  Serial.print(F("espTx="));
  printSc2Telemetry(Serial);
}

void printSc2Telemetry(Print &out) {
  const int temp10 = (int)(temperatureC * 10.0);

  out.print(F("SC2"));
  out.print(F(",mode="));
  out.print(modeToString(currentMode));
  out.print(F(",pir="));
  out.print(occupied ? 1 : 0);
  out.print(F(",light="));
  out.print(lightValue);
  out.print(F(",dark="));
  out.print(isDark ? 1 : 0);
  out.print(F(",temp10="));
  out.print(temp10);
  out.print(F(",tempRemote="));
  out.print(usingEsp32Temperature ? 1 : 0);
  out.print(F(",espTemp10="));
  out.print(esp32TemperatureValid ? (int)(esp32TemperatureC * 10.0) : -999);
  out.print(F(",tempSrc="));
  out.print(usingEsp32Temperature ? F("ESP32") : F("UNO"));
  out.print(F(",gas="));
  out.print(gasValue);
  out.print(F(",gasD="));
  out.print(gasDanger ? 1 : 0);
  out.print(F(",flameD="));
  out.print(flameDigital);
  out.print(F(",flameA="));
  out.print(flameAnalog);
  out.print(F(",flame="));
  out.print(flameDetected ? 1 : 0);
  out.print(F(",demo="));
  out.print(demoEmergency ? 1 : 0);
  out.print(F(",fan="));
  out.print(fanRelayState ? 1 : 0);
  out.print(F(",pwm="));
  out.print(fanPwmOutput);
  out.print(F(",rpm="));
  out.print(estimatedRpm);
  out.print(F(",lamp="));
  out.print(classroomLedState ? 1 : 0);
  out.print(F(",status="));
  out.print(statusLightShort());
  out.print(F(",manual="));
  out.print(manualMode ? 1 : 0);
  out.print(F(",fanOn10="));
  out.print((int)(fanStartTempC * 10.0));
  out.print(F(",fanOff10="));
  out.print((int)(fanStopTempC * 10.0));
  out.print(F(",ledMax="));
  out.print(ledBrightnessMax);
  out.print(F(",statusMax="));
  out.print(statusBrightnessMax);
  out.println();
}

const char *modeToString(SystemMode mode) {
  switch (mode) {
    case MODE_NORMAL:
      return "NORMAL";
    case MODE_LIGHTING:
      return "LIGHTING";
    case MODE_COOLING:
      return "COOLING";
    case MODE_AIR_QUALITY_WARNING:
      return "AIR_QUALITY_WARNING";
    case MODE_ENERGY_SAVING:
      return "ENERGY_SAVING";
    case MODE_SAFETY_ALARM:
      return "SAFETY_ALARM";
    case MODE_SENSOR_ERROR:
      return "SENSOR_ERROR";
    case MODE_MANUAL:
      return "MANUAL";
    default:
      return "UNKNOWN";
  }
}

void setStatusLight(bool red, bool yellow, bool green) {
  statusRState = red;
  statusYState = yellow;
  statusGState = green;
}

void applyStatusLightSoftPwm() {
  if (statusBrightnessMax >= 255) {
    digitalWrite(PIN_STATUS_R, statusRState ? HIGH : LOW);
    digitalWrite(PIN_STATUS_Y, statusYState ? HIGH : LOW);
    digitalWrite(PIN_STATUS_G, statusGState ? HIGH : LOW);
    return;
  }

  if (statusBrightnessMax == 0) {
    digitalWrite(PIN_STATUS_R, LOW);
    digitalWrite(PIN_STATUS_Y, LOW);
    digitalWrite(PIN_STATUS_G, LOW);
    return;
  }

  const unsigned int onTime = (unsigned long)statusBrightnessMax * STATUS_PWM_PERIOD_US / 255UL;
  const unsigned int phase = micros() % STATUS_PWM_PERIOD_US;
  const bool pwmOn = (phase < onTime);
  digitalWrite(PIN_STATUS_R, statusRState && pwmOn ? HIGH : LOW);
  digitalWrite(PIN_STATUS_Y, statusYState && pwmOn ? HIGH : LOW);
  digitalWrite(PIN_STATUS_G, statusGState && pwmOn ? HIGH : LOW);
}

const char *statusLightColor() {
  if (currentMode == MODE_MANUAL) {
    return "MANUAL";
  }
  if (currentMode == MODE_SAFETY_ALARM) {
    return "RED";
  }
  if (currentMode == MODE_SENSOR_ERROR) {
    return ((millis() / SENSOR_ERROR_BLINK_MS) % 2) == 0 ? "RED_BLINK_ON" : "RED_BLINK_OFF";
  }
  if (currentMode == MODE_AIR_QUALITY_WARNING) {
    return ((millis() / 350) % 2) == 0 ? "YELLOW_BLINK_ON" : "YELLOW_BLINK_OFF";
  }
  if (currentMode == MODE_COOLING) {
    return "YELLOW";
  }
  return "GREEN";
}

char statusLightShort() {
  if (currentMode == MODE_MANUAL) {
    return 'M';
  }
  if (currentMode == MODE_SAFETY_ALARM || currentMode == MODE_SENSOR_ERROR) {
    return 'R';
  }
  if (currentMode == MODE_AIR_QUALITY_WARNING || currentMode == MODE_COOLING) {
    return 'Y';
  }
  return 'G';
}

const char *fanHealthText() {
  if (fanTachFault) {
    return "NO_TACH";
  }
  if (fanRelayState && estimatedRpm > 0) {
    return "RUNNING";
  }
  if (fanRelayState) {
    return "STARTING";
  }
  return "STANDBY";
}

byte calculateFanTargetPwm(float tempC) {
  if (!temperatureValid || tempC < fanStopTempC) {
    return 0;
  }
  if (tempC <= fanStartTempC) {
    return 0;
  }
  if (tempC >= FAN_MAX_TEMP_C) {
    return FAN_ALARM_PWM;
  }

  const float ratio = (tempC - fanStartTempC) / (FAN_MAX_TEMP_C - fanStartTempC);
  const int pwm = FAN_MIN_PWM + (int)((FAN_ALARM_PWM - FAN_MIN_PWM) * ratio);
  return constrain(pwm, FAN_MIN_PWM, FAN_ALARM_PWM);
}

void requestBuzzerPulse(unsigned long durationMs) {
  if (currentMode == MODE_SAFETY_ALARM) {
    return;
  }
  digitalWrite(PIN_BUZZER, BUZZER_ON);
  buzzerPulseActive = true;
  buzzerPulseOffAtMs = millis() + durationMs;
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

int readAverageAvcc(byte pin, byte sampleCount) {
  ADMUX = ADC_REF_AVCC | (analogPinToAdcChannel(pin) & 0x07);
  delayMicroseconds(250);
  readAdcOnce();

  unsigned int sum = 0;
  for (byte i = 0; i < sampleCount; i++) {
    sum += readAdcOnce();
  }
  return sum / sampleCount;
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
