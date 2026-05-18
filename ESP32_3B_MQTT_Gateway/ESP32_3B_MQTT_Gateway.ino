/*
  ESP32_3B_MQTT_Gateway.ino
  Smart Classroom Energy-Saving, Safety & Asset Monitoring System

  ESP32 role:
  - Receive UNO SC2 telemetry over Serial2 RX.
  - Forward MQTT command messages to UNO over Serial2 TX.
  - Connect to Wi-Fi.
  - Publish MQTT telemetry and key topics.

  Wi-Fi target:
  - Windows laptop hotspot SSID: SmartClassroom-IoT
  - Password: 12345678

  MQTT broker:
  - Default: 192.168.137.1:1883
  - If your Windows hotspot adapter IP differs, update MQTT_HOST after checking ipconfig.
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <Preferences.h>

#if __has_include("credentials.h")
#include "credentials.h"
#endif

#define PIN_ESP32_RX2 16
#define PIN_ESP32_TX2 17
#define PIN_ESP32_UNUSED_TX 25
#define PIN_LM35_ADC 34
#define PIN_LM35_DUMMY_ADC 35

const char *WIFI_SSID =
#ifdef SMARTCLASSROOM_WIFI_SSID
  SMARTCLASSROOM_WIFI_SSID;
#else
  "SmartClassroom-IoT";
#endif
const char *WIFI_PASSWORD =
#ifdef SMARTCLASSROOM_WIFI_PASSWORD
  SMARTCLASSROOM_WIFI_PASSWORD;
#else
  "change-me";
#endif

const char *MQTT_HOST =
#ifdef SMARTCLASSROOM_MQTT_HOST
  SMARTCLASSROOM_MQTT_HOST;
#else
  "192.168.137.1";
#endif
const uint16_t MQTT_PORT = 1883;
const char *MQTT_CLIENT_ID = "smartclassroom-esp32-edge1";

const char *FALLBACK_WIFI_SSID =
#ifdef SMARTCLASSROOM_FALLBACK_WIFI_SSID
  SMARTCLASSROOM_FALLBACK_WIFI_SSID;
#else
  "";
#endif
const char *FALLBACK_WIFI_PASSWORD =
#ifdef SMARTCLASSROOM_FALLBACK_WIFI_PASSWORD
  SMARTCLASSROOM_FALLBACK_WIFI_PASSWORD;
#else
  "";
#endif
const char *FALLBACK_MQTT_HOST =
#ifdef SMARTCLASSROOM_FALLBACK_MQTT_HOST
  SMARTCLASSROOM_FALLBACK_MQTT_HOST;
#else
  "192.168.137.1";
#endif

struct WifiProfile {
  const char *ssid;
  const char *password;
  const char *mqttHost;
};

const WifiProfile WIFI_PROFILES[] = {
  {WIFI_SSID, WIFI_PASSWORD, MQTT_HOST},
  {FALLBACK_WIFI_SSID, FALLBACK_WIFI_PASSWORD, FALLBACK_MQTT_HOST}
};
const byte WIFI_PROFILE_COUNT = sizeof(WIFI_PROFILES) / sizeof(WIFI_PROFILES[0]);

const char *TOPIC_TELEMETRY = "smartclassroom/edge1/telemetry";
const char *TOPIC_STATUS = "smartclassroom/edge1/status";
const char *TOPIC_MODE = "smartclassroom/edge1/mode";
const char *TOPIC_SAFETY_ALARM = "smartclassroom/edge1/safety/alarm";
const char *TOPIC_OCCUPANCY = "smartclassroom/edge1/sensors/occupancy";
const char *TOPIC_LIGHT = "smartclassroom/edge1/sensors/light";
const char *TOPIC_TEMPERATURE = "smartclassroom/edge1/sensors/temperature";
const char *TOPIC_GAS = "smartclassroom/edge1/sensors/gas";
const char *TOPIC_FLAME = "smartclassroom/edge1/sensors/flame";
const char *TOPIC_LAMP = "smartclassroom/edge1/actuators/lamp";
const char *TOPIC_FAN = "smartclassroom/edge1/actuators/fan";
const char *TOPIC_RPM = "smartclassroom/edge1/actuators/rpm";
const char *TOPIC_STATUS_LIGHT = "smartclassroom/edge1/actuators/status_light";
const char *TOPIC_COMMAND = "smartclassroom/edge1/command";
const char *TOPIC_COMMAND_ACK = "smartclassroom/edge1/command_ack";

const unsigned long WIFI_RECONNECT_INTERVAL_MS = 8000;
const unsigned long MQTT_RECONNECT_INTERVAL_MS = 3000;
const unsigned long UNO_TIMEOUT_MS = 5000;
const unsigned long OFFLINE_PUBLISH_INTERVAL_MS = 5000;
const unsigned long SERIAL_HEARTBEAT_INTERVAL_MS = 10000;
const uint16_t MQTT_PACKET_BUFFER_SIZE = 2048;
const unsigned long LM35_SAMPLE_INTERVAL_MS = 1000;
const unsigned long LM35_COMMAND_INTERVAL_MS = 2500;
const unsigned long LM35_COMMAND_DELAY_AFTER_TELEMETRY_MS = 90;
const unsigned long LM35_COMMAND_GAP_MAX_MS = 700;
const unsigned long LM35_PAUSE_AFTER_EXTERNAL_COMMAND_MS = 7000;
const unsigned long UNO_COMMAND_DELAY_AFTER_TELEMETRY_MS = 130;
const unsigned long UNO_COMMAND_GAP_MAX_MS = 720;
const unsigned long UNO_COMMAND_MIN_SPACING_MS = 620;
const byte UNO_COMMAND_QUEUE_SIZE = 12;
const int LM35_VALID_MIN_MV = 100;
const int LM35_VALID_MAX_MV = 600;
const byte LM35_STABLE_REQUIRED = 3;
const byte LM35_SAMPLE_COUNT = 17;
const byte LM35_TRIM_COUNT = 4;
const float LM35_FILTER_ALPHA = 0.22;
const float LM35_AMBIENT_MAX_RISE_C_PER_SEC = 0.12;
const float LM35_AMBIENT_MAX_FALL_C_PER_SEC = 0.35;
const float LM35_SPIKE_RATE_C_PER_SEC = 1.0;
const int LM35_SPIKE_DELTA_MV = 70;
const int LM35_TRUSTED_MIN_MV = 150;
const int LM35_TRUSTED_MAX_MV = 380;
const int LM35_DEFAULT_AMBIENT_MV = 260;
const unsigned long LM35_TRUSTED_STORE_INTERVAL_MS = 60000;
const int LM35_DUMMY_VALID_MAX_MV = 220;
const int LM35_DUMMY_COMP_NOISE_FLOOR_MV = 6;
const int LM35_DUMMY_COMP_LIMIT_MV = 180;
const float LM35_DUMMY_FILTER_ALPHA = 0.22;
const float LM35_DUMMY_COMP_GAIN = 0.85;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
HardwareSerial commandSerial(1);
Preferences preferences;

struct Telemetry {
  bool valid = false;
  String mode = "UNKNOWN";
  int pir = 0;
  int light = 0;
  int dark = 0;
  int temp10 = 0;
  int tempRemote = 0;
  int espTemp10 = -999;
  int gas = 0;
  int gasD = 0;
  int flameD = 1;
  int flameA = 0;
  int flame = 0;
  int demo = 0;
  int fan = 0;
  int pwm = 0;
  int rpm = 0;
  int lamp = 0;
  int manual = 0;
  int fanOn10 = 280;
  int fanOff10 = 260;
  int ledMax = 255;
  int statusMax = 255;
  String tempSrc = "UNO";
  String status = "G";
  String raw = "";
};

Telemetry telemetry;
String rxLine;

unsigned long lastUnoRxMs = 0;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;
unsigned long lastOfflinePublishMs = 0;
unsigned long lastHeartbeatMs = 0;
unsigned long lastLm35SampleMs = 0;
unsigned long lastLm35CommandMs = 0;
unsigned long lastExternalCommandMs = 0;
unsigned long lastTelemetryPublishWarnMs = 0;

bool unoOfflinePublished = false;
byte profileAttemptIndex = 0;
byte activeProfileIndex = 0;
int lm35Mv = 0;
int lm35RawMv = 0;
int lm35CorrectedMv = 0;
int lm35DummyRawMv = 0;
int lm35DummyMv = 0;
int lm35DummyBaselineMv = 0;
int lm35DummyCompensationMv = 0;
int lm35AmbientMv = 0;
int lm35Temp10 = 0;
byte lm35StableCount = 0;
bool lm35Valid = false;
bool lm35DummyValid = false;
bool lm35DummyReady = false;
bool lm35DummyCompActive = false;
bool lm35FilterReady = false;
bool pendingLm35Command = false;
bool lm35AmbientReady = false;
bool lm35SpikeGuardActive = false;
bool lm35TrustedReady = false;
float lm35FilteredMv = 0.0;
float lm35DummyFilteredMv = 0.0;
int lm35LastRawMv = 0;
int lm35TrustedAmbientMv = LM35_DEFAULT_AMBIENT_MV;
unsigned long lastLm35AcceptedMs = 0;
unsigned long lastLm35TrustedStoreMs = 0;
String unoCommandQueue[UNO_COMMAND_QUEUE_SIZE];
byte unoCommandQueueCount = 0;
unsigned long lastUnoCommandWriteMs = 0;

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, PIN_ESP32_RX2, PIN_ESP32_UNUSED_TX);
  pinMode(PIN_ESP32_TX2, INPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_LM35_ADC, ADC_0db);
  analogSetPinAttenuation(PIN_LM35_DUMMY_ADC, ADC_0db);
  preferences.begin("smartcls", false);
  lm35TrustedAmbientMv = preferences.getInt("lm35GoodMv", LM35_DEFAULT_AMBIENT_MV);
  lm35DummyBaselineMv = preferences.getInt("lm35DummyBase", 0);
  if (lm35DummyBaselineMv < 0 || lm35DummyBaselineMv > LM35_DUMMY_VALID_MAX_MV) {
    lm35DummyBaselineMv = 0;
  }
  if (lm35TrustedAmbientMv < LM35_TRUSTED_MIN_MV || lm35TrustedAmbientMv > LM35_TRUSTED_MAX_MV) {
    lm35TrustedAmbientMv = LM35_DEFAULT_AMBIENT_MV;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  mqtt.setServer(WIFI_PROFILES[activeProfileIndex].mqttHost, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  if (!mqtt.setBufferSize(MQTT_PACKET_BUFFER_SIZE)) {
    Serial.println("WARNING: MQTT buffer allocation failed; telemetry JSON may not publish");
  }

  lastUnoRxMs = millis();

  Serial.println();
  Serial.println("ESP32_3B_MQTT_Gateway started");
  Serial.println("Serial Monitor: 115200 baud");
  Serial.println("UNO RX UART: 9600 baud, RX=GPIO16, unused TX=GPIO25");
  Serial.println("UNO command TX: GPIO17 only while sending commands");
  Serial.println("LM35 ADC: GPIO34 ADC1, 0 dB attenuation, sends CMD,TEMP10 to UNO when stable");
  Serial.println("LM35 dummy ADC: GPIO35 ADC1 reference channel, use 100k pulldown to GND");
  Serial.print("LM35 trusted ambient startup mV: ");
  Serial.println(lm35TrustedAmbientMv);
  Serial.print("LM35 dummy baseline startup mV: ");
  Serial.println(lm35DummyBaselineMv);
  Serial.println("ESP32 GPIO17 must be wired only to UNO A4/RX, not to GPIO16 or the divider midpoint");
  Serial.print("Primary Wi-Fi SSID: ");
  Serial.println(WIFI_SSID);
  Serial.print("Primary MQTT broker: ");
  Serial.print(MQTT_HOST);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  Serial.print("Fallback Wi-Fi SSID: ");
  Serial.println(FALLBACK_WIFI_SSID);
  Serial.print("Fallback MQTT broker: ");
  Serial.print(FALLBACK_MQTT_HOST);
  Serial.print(":");
  Serial.println(MQTT_PORT);
}

void loop() {
  maintainWiFi();
  maintainMqtt();

  if (mqtt.connected()) {
    mqtt.loop();
  }

  readUnoSerial();
  updateLm35Temperature();
  sendPendingLm35Temperature();
  processUnoCommandQueue();
  checkUnoTimeout();
  printHeartbeat();
}

void maintainWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  const unsigned long now = millis();
  if (lastWifiAttemptMs != 0 && now - lastWifiAttemptMs < WIFI_RECONNECT_INTERVAL_MS) {
    return;
  }

  lastWifiAttemptMs = now;
  activeProfileIndex = profileAttemptIndex;
  profileAttemptIndex = (profileAttemptIndex + 1) % WIFI_PROFILE_COUNT;
  const WifiProfile &profile = WIFI_PROFILES[activeProfileIndex];

  mqtt.disconnect();
  mqtt.setServer(profile.mqttHost, MQTT_PORT);

  Serial.print("Connecting Wi-Fi: ");
  Serial.println(profile.ssid);
  WiFi.disconnect(false);
  WiFi.begin(profile.ssid, profile.password);
}

void maintainMqtt() {
  if (WiFi.status() != WL_CONNECTED || mqtt.connected()) {
    return;
  }

  const unsigned long now = millis();
  if (now - lastMqttAttemptMs < MQTT_RECONNECT_INTERVAL_MS) {
    return;
  }

  lastMqttAttemptMs = now;
  Serial.print("Connecting MQTT: ");
  Serial.println(WIFI_PROFILES[activeProfileIndex].mqttHost);

  if (mqtt.connect(MQTT_CLIENT_ID, TOPIC_STATUS, 0, true, "esp32_offline")) {
    Serial.println("MQTT connected");
    mqtt.publish(TOPIC_STATUS, "esp32_online", true);
    mqtt.subscribe(TOPIC_COMMAND);
    Serial.print("Subscribed command topic: ");
    Serial.println(TOPIC_COMMAND);
    if (millis() - lastUnoRxMs > UNO_TIMEOUT_MS) {
      publishUnoOffline();
    }
  } else {
    Serial.print("MQTT connect failed, rc=");
    Serial.println(mqtt.state());
  }
}

void mqttCallback(char *topic, byte *payload, unsigned int length) {
  String message;
  message.reserve(length + 8);
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  message.trim();

  if (String(topic) == TOPIC_COMMAND) {
    forwardCommandToUno(message);
  }
}

void forwardCommandToUno(const String &message) {
  if (message.length() == 0) {
    publishCommandAck("empty_command");
    return;
  }

  String command = message;
  if (!command.startsWith("CMD")) {
    command = "CMD," + command;
  }

  lastExternalCommandMs = millis();
  pendingLm35Command = false;
  enqueueUnoCommand(command);

  String ack = "queued:";
  ack += command;
  publishCommandAck(ack);
}

void enqueueUnoCommand(const String &command) {
  if (unoCommandQueueCount >= UNO_COMMAND_QUEUE_SIZE) {
    for (byte i = 1; i < UNO_COMMAND_QUEUE_SIZE; i++) {
      unoCommandQueue[i - 1] = unoCommandQueue[i];
    }
    unoCommandQueueCount = UNO_COMMAND_QUEUE_SIZE - 1;
    Serial.println("UNO command queue full; oldest command dropped");
  }

  unoCommandQueue[unoCommandQueueCount++] = command;
  Serial.print("Queued UNO command: ");
  Serial.println(command);
}

bool safeToSendUnoCommand() {
  const unsigned long now = millis();
  const unsigned long ageSinceTelemetry = now - lastUnoRxMs;
  return rxLine.length() == 0 &&
         ageSinceTelemetry >= UNO_COMMAND_DELAY_AFTER_TELEMETRY_MS &&
         ageSinceTelemetry <= UNO_COMMAND_GAP_MAX_MS &&
         now - lastUnoCommandWriteMs >= UNO_COMMAND_MIN_SPACING_MS;
}

void processUnoCommandQueue() {
  if (unoCommandQueueCount == 0 || !safeToSendUnoCommand()) {
    return;
  }

  const String command = unoCommandQueue[0];
  for (byte i = 1; i < unoCommandQueueCount; i++) {
    unoCommandQueue[i - 1] = unoCommandQueue[i];
  }
  unoCommandQueueCount--;
  lastUnoCommandWriteMs = millis();
  writeCommandToUno(command);
}

void writeCommandToUno(const String &command) {
  Serial.print("TX to UNO: ");
  Serial.println(command);
  commandSerial.begin(9600, SERIAL_8N1, -1, PIN_ESP32_TX2);
  commandSerial.print(command);
  commandSerial.print('\n');
  commandSerial.flush();
  commandSerial.end();
  pinMode(PIN_ESP32_TX2, INPUT);
  rxLine = "";
}

void publishCommandAck(const String &message) {
  if (mqtt.connected()) {
    mqtt.publish(TOPIC_COMMAND_ACK, message.c_str(), false);
  }
  Serial.print("Command ack: ");
  Serial.println(message);
}

void updateLm35Temperature() {
  const unsigned long now = millis();
  if (now - lastLm35SampleMs < LM35_SAMPLE_INTERVAL_MS) {
    return;
  }
  lastLm35SampleMs = now;

  lm35RawMv = readTrimmedAdcMilliVolts(PIN_LM35_ADC);
  updateLm35DummyReference();
  lm35CorrectedMv = calculateLm35CorrectedMv();

  const bool inRange = (lm35CorrectedMv >= LM35_VALID_MIN_MV && lm35CorrectedMv <= LM35_VALID_MAX_MV);
  if (inRange) {
    if (!lm35FilterReady) {
      lm35FilteredMv = lm35CorrectedMv;
      lm35FilterReady = true;
    } else {
      lm35FilteredMv += (lm35CorrectedMv - lm35FilteredMv) * LM35_FILTER_ALPHA;
    }
    if (lm35StableCount < LM35_STABLE_REQUIRED) {
      lm35StableCount++;
    }
  } else {
    lm35StableCount = 0;
    lm35FilterReady = false;
  }

  lm35Mv = lm35FilterReady ? (int)(lm35FilteredMv + 0.5) : lm35CorrectedMv;
  lm35Valid = (lm35StableCount >= LM35_STABLE_REQUIRED);
  updateLm35AmbientEstimate(now);
  if (lm35Valid) {
    pendingLm35Command = true;
  }
}

int readTrimmedAdcMilliVolts(byte pin) {
  int samples[LM35_SAMPLE_COUNT];
  for (byte i = 0; i < LM35_SAMPLE_COUNT; i++) {
    samples[i] = analogReadMilliVolts(pin);
    delayMicroseconds(350);
  }
  for (byte i = 1; i < LM35_SAMPLE_COUNT; i++) {
    const int value = samples[i];
    byte j = i;
    while (j > 0 && samples[j - 1] > value) {
      samples[j] = samples[j - 1];
      j--;
    }
    samples[j] = value;
  }

  long sum = 0;
  byte used = 0;
  for (byte i = LM35_TRIM_COUNT; i < LM35_SAMPLE_COUNT - LM35_TRIM_COUNT; i++) {
    sum += samples[i];
    used++;
  }

  return used > 0 ? (int)(sum / used) : samples[LM35_SAMPLE_COUNT / 2];
}

void updateLm35DummyReference() {
  lm35DummyRawMv = readTrimmedAdcMilliVolts(PIN_LM35_DUMMY_ADC);
  lm35DummyValid = (lm35DummyRawMv >= 0 && lm35DummyRawMv <= LM35_DUMMY_VALID_MAX_MV);

  if (!lm35DummyValid) {
    lm35DummyReady = false;
    lm35DummyCompensationMv = 0;
    lm35DummyCompActive = false;
    return;
  }

  if (!lm35DummyReady) {
    lm35DummyFilteredMv = lm35DummyRawMv;
    lm35DummyMv = lm35DummyRawMv;
    lm35DummyReady = true;
    if (lm35DummyBaselineMv == 0 || lm35DummyMv < lm35DummyBaselineMv) {
      lm35DummyBaselineMv = lm35DummyMv;
      preferences.putInt("lm35DummyBase", lm35DummyBaselineMv);
    }
  } else {
    lm35DummyFilteredMv += (lm35DummyRawMv - lm35DummyFilteredMv) * LM35_DUMMY_FILTER_ALPHA;
    lm35DummyMv = (int)(lm35DummyFilteredMv + 0.5);
    if (lm35DummyMv < lm35DummyBaselineMv || lm35DummyMv <= lm35DummyBaselineMv + 12) {
      lm35DummyBaselineMv = (int)(lm35DummyBaselineMv + (lm35DummyMv - lm35DummyBaselineMv) * 0.04 + 0.5);
    }
  }

  const int noiseMv = max(0, lm35DummyMv - lm35DummyBaselineMv - LM35_DUMMY_COMP_NOISE_FLOOR_MV);
  lm35DummyCompensationMv = constrain((int)(noiseMv * LM35_DUMMY_COMP_GAIN + 0.5), 0, LM35_DUMMY_COMP_LIMIT_MV);
  lm35DummyCompActive = lm35DummyCompensationMv > 0;
}

int calculateLm35CorrectedMv() {
  if (!lm35DummyValid || !lm35DummyReady) {
    lm35DummyCompensationMv = 0;
    lm35DummyCompActive = false;
    return lm35RawMv;
  }
  return max(0, lm35RawMv - lm35DummyCompensationMv);
}

void updateLm35AmbientEstimate(unsigned long now) {
  if (!lm35Valid) {
    lm35AmbientReady = false;
    lm35SpikeGuardActive = false;
    lm35Temp10 = lm35TrustedAmbientMv;
    return;
  }

  const float dtSec = lastLm35AcceptedMs == 0 ? 1.0 : max(0.2, (now - lastLm35AcceptedMs) / 1000.0);
  const float rawRateCPerSec = lastLm35AcceptedMs == 0 ? 0.0 : ((lm35CorrectedMv - lm35LastRawMv) / 10.0) / dtSec;
  const bool trustedRange = (lm35Mv >= LM35_TRUSTED_MIN_MV && lm35Mv <= LM35_TRUSTED_MAX_MV);

  if (!lm35AmbientReady) {
    lm35AmbientMv = trustedRange ? lm35Mv : lm35TrustedAmbientMv;
    lm35AmbientReady = true;
    lm35SpikeGuardActive = !trustedRange;
  } else {
    const int rawDeltaFromAmbient = lm35Mv - lm35AmbientMv;
    lm35SpikeGuardActive = (abs(rawRateCPerSec) >= LM35_SPIKE_RATE_C_PER_SEC)
      || (rawDeltaFromAmbient >= LM35_SPIKE_DELTA_MV && rawRateCPerSec > 0.35)
      || !trustedRange;

    const int targetMv = lm35SpikeGuardActive ? lm35TrustedAmbientMv : lm35Mv;
    const float maxRiseMv = max(1.0, LM35_AMBIENT_MAX_RISE_C_PER_SEC * 10.0 * dtSec);
    const float maxFallMv = max(1.0, LM35_AMBIENT_MAX_FALL_C_PER_SEC * 10.0 * dtSec);
    float deltaMv = targetMv - lm35AmbientMv;

    if (deltaMv > 0) {
      const float guardedRiseMv = lm35SpikeGuardActive ? maxRiseMv * 0.35 : maxRiseMv;
      deltaMv = min(deltaMv, guardedRiseMv);
    } else {
      deltaMv = max(deltaMv, -maxFallMv);
    }

    lm35AmbientMv = (int)(lm35AmbientMv + deltaMv + (deltaMv >= 0 ? 0.5 : -0.5));
  }

  if (!lm35SpikeGuardActive && trustedRange) {
    lm35TrustedAmbientMv = lm35AmbientMv;
    if (now - lastLm35TrustedStoreMs >= LM35_TRUSTED_STORE_INTERVAL_MS) {
      lastLm35TrustedStoreMs = now;
      preferences.putInt("lm35GoodMv", lm35TrustedAmbientMv);
    }
  }

  lm35LastRawMv = lm35CorrectedMv;
  lastLm35AcceptedMs = now;
  lm35Temp10 = lm35AmbientMv;  // LM35 is 10 mV per C, so mV equals C * 10.
}

void sendPendingLm35Temperature() {
  if (!pendingLm35Command || !lm35Valid) {
    return;
  }

  const unsigned long now = millis();
  if (now - lastExternalCommandMs < LM35_PAUSE_AFTER_EXTERNAL_COMMAND_MS) {
    return;
  }
  if (lastLm35CommandMs != 0 && now - lastLm35CommandMs < LM35_COMMAND_INTERVAL_MS) {
    return;
  }
  if (unoCommandQueueCount > 0) {
    return;
  }

  pendingLm35Command = false;
  lastLm35CommandMs = now;

  String command = "CMD,TEMP10=";
  command += String(lm35Temp10);
  enqueueUnoCommand(command);
}

void readUnoSerial() {
  while (Serial2.available() > 0) {
    const char c = (char)Serial2.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      rxLine.trim();
      if (rxLine.length() > 0) {
        handleUnoLine(rxLine);
      }
      rxLine = "";
      return;
    }

    if (rxLine.length() < 420) {
      rxLine += c;
    } else {
      rxLine = "";
      Serial.println("RX buffer overflow; line dropped");
    }
  }
}

void handleUnoLine(const String &line) {
  Serial.print("RX from UNO: ");
  Serial.println(line);

  if (line.startsWith("ACK")) {
    publishCommandAck(line);
    return;
  }

  if (!parseTelemetry(line)) {
    Serial.println("Ignored malformed telemetry");
    return;
  }

  lastUnoRxMs = millis();
  unoOfflinePublished = false;

  if (mqtt.connected()) {
    publishTelemetry();
  }
}

bool parseTelemetry(const String &line) {
  if (!line.startsWith("SC2")) {
    return false;
  }

  Telemetry next;
  next.valid = true;
  next.raw = line;

  int start = 4;  // skip "SC2,"
  while (start < line.length()) {
    int comma = line.indexOf(',', start);
    if (comma < 0) {
      comma = line.length();
    }

    String token = line.substring(start, comma);
    token.trim();
    const int eq = token.indexOf('=');
    if (eq > 0) {
      const String key = token.substring(0, eq);
      const String value = token.substring(eq + 1);
      assignField(next, key, value);
    }

    start = comma + 1;
  }

  telemetry = next;
  return true;
}

void assignField(Telemetry &t, const String &key, const String &value) {
  if (key == "mode") {
    t.mode = value;
  } else if (key == "pir") {
    t.pir = value.toInt();
  } else if (key == "light") {
    t.light = value.toInt();
  } else if (key == "dark") {
    t.dark = value.toInt();
  } else if (key == "temp10") {
    t.temp10 = value.toInt();
  } else if (key == "tempRemote") {
    t.tempRemote = value.toInt();
  } else if (key == "espTemp10") {
    t.espTemp10 = value.toInt();
  } else if (key == "tempSrc") {
    t.tempSrc = value;
  } else if (key == "gas") {
    t.gas = value.toInt();
  } else if (key == "gasD") {
    t.gasD = value.toInt();
  } else if (key == "flameD") {
    t.flameD = value.toInt();
  } else if (key == "flameA") {
    t.flameA = value.toInt();
  } else if (key == "flame") {
    t.flame = value.toInt();
  } else if (key == "demo") {
    t.demo = value.toInt();
  } else if (key == "fan") {
    t.fan = value.toInt();
  } else if (key == "pwm") {
    t.pwm = value.toInt();
  } else if (key == "rpm") {
    t.rpm = value.toInt();
  } else if (key == "lamp") {
    t.lamp = value.toInt();
  } else if (key == "manual") {
    t.manual = value.toInt();
  } else if (key == "fanOn10") {
    t.fanOn10 = value.toInt();
  } else if (key == "fanOff10") {
    t.fanOff10 = value.toInt();
  } else if (key == "ledMax") {
    t.ledMax = value.toInt();
  } else if (key == "statusMax") {
    t.statusMax = value.toInt();
  } else if (key == "status") {
    t.status = value;
  }
}

void publishTelemetry() {
  const float temperatureC = telemetry.temp10 / 10.0;
  const bool safetyAlarm = telemetry.gasD || telemetry.flame || telemetry.demo || telemetry.mode == "SAFETY_ALARM";

  String json = "{";
  json.reserve(1600);
  json += "\"device\":\"edge1\"";
  json += ",\"mode\":\"" + telemetry.mode + "\"";
  json += ",\"pir\":" + String(telemetry.pir);
  json += ",\"occupied\":" + String(telemetry.pir);
  json += ",\"light\":" + String(telemetry.light);
  json += ",\"dark\":" + String(telemetry.dark);
  json += ",\"temperatureC\":" + String(temperatureC, 1);
  json += ",\"temp10\":" + String(telemetry.temp10);
  json += ",\"temperatureSource\":\"" + telemetry.tempSrc + "\"";
  json += ",\"tempRemote\":" + String(telemetry.tempRemote);
  json += ",\"espTemp10\":" + String(telemetry.espTemp10);
  json += ",\"esp32AdcTempC\":" + String(lm35Temp10 / 10.0, 1);
  json += ",\"esp32AdcMv\":" + String(lm35Mv);
  json += ",\"esp32AdcRawMv\":" + String(lm35RawMv);
  json += ",\"esp32AdcCorrectedMv\":" + String(lm35CorrectedMv);
  json += ",\"esp32AdcAmbientMv\":" + String(lm35AmbientMv);
  json += ",\"esp32AdcRawTempC\":" + String(lm35RawMv / 10.0, 1);
  json += ",\"esp32AdcSuspect\":" + String(lm35SpikeGuardActive ? 1 : 0);
  json += ",\"esp32AdcTrustedMv\":" + String(lm35TrustedAmbientMv);
  json += ",\"esp32AdcDummyRawMv\":" + String(lm35DummyRawMv);
  json += ",\"esp32AdcDummyMv\":" + String(lm35DummyMv);
  json += ",\"esp32AdcDummyBaselineMv\":" + String(lm35DummyBaselineMv);
  json += ",\"esp32AdcDummyCompMv\":" + String(lm35DummyCompensationMv);
  json += ",\"esp32AdcDummyValid\":" + String(lm35DummyValid ? 1 : 0);
  json += ",\"esp32AdcDummyCompActive\":" + String(lm35DummyCompActive ? 1 : 0);
  json += ",\"esp32AdcValid\":" + String(lm35Valid ? 1 : 0);
  json += ",\"gas\":" + String(telemetry.gas);
  json += ",\"gasDanger\":" + String(telemetry.gasD);
  json += ",\"flameDigital\":" + String(telemetry.flameD);
  json += ",\"flameAnalog\":" + String(telemetry.flameA);
  json += ",\"flameDetected\":" + String(telemetry.flame);
  json += ",\"demoEmergency\":" + String(telemetry.demo);
  json += ",\"safetyAlarm\":" + String(safetyAlarm ? 1 : 0);
  json += ",\"fan\":" + String(telemetry.fan);
  json += ",\"pwm\":" + String(telemetry.pwm);
  json += ",\"rpm\":" + String(telemetry.rpm);
  json += ",\"lamp\":" + String(telemetry.lamp);
  json += ",\"manual\":" + String(telemetry.manual);
  json += ",\"fanOn10\":" + String(telemetry.fanOn10);
  json += ",\"fanOff10\":" + String(telemetry.fanOff10);
  json += ",\"fanOnC\":" + String(telemetry.fanOn10 / 10.0, 1);
  json += ",\"fanOffC\":" + String(telemetry.fanOff10 / 10.0, 1);
  json += ",\"ledMax\":" + String(telemetry.ledMax);
  json += ",\"statusMax\":" + String(telemetry.statusMax);
  json += ",\"statusLight\":\"" + telemetry.status + "\"";
  json += ",\"raw\":\"" + telemetry.raw + "\"";
  json += "}";

  const bool telemetryPublished = mqtt.publish(TOPIC_TELEMETRY, json.c_str(), false);
  if (!telemetryPublished && millis() - lastTelemetryPublishWarnMs >= 5000) {
    Serial.print("MQTT telemetry publish failed, jsonBytes=");
    Serial.print(json.length());
    Serial.print(", mqttBuffer=");
    Serial.println(MQTT_PACKET_BUFFER_SIZE);
    lastTelemetryPublishWarnMs = millis();
  }
  mqtt.publish(TOPIC_STATUS, "online", true);
  mqtt.publish(TOPIC_MODE, telemetry.mode.c_str(), true);
  mqtt.publish(TOPIC_SAFETY_ALARM, safetyAlarm ? "1" : "0", true);
  mqtt.publish(TOPIC_OCCUPANCY, String(telemetry.pir).c_str(), true);
  mqtt.publish(TOPIC_LIGHT, String(telemetry.light).c_str(), true);
  mqtt.publish(TOPIC_TEMPERATURE, String(temperatureC, 1).c_str(), true);
  mqtt.publish(TOPIC_GAS, String(telemetry.gas).c_str(), true);
  mqtt.publish(TOPIC_FLAME, String(telemetry.flame).c_str(), true);
  mqtt.publish(TOPIC_LAMP, String(telemetry.lamp).c_str(), true);
  mqtt.publish(TOPIC_FAN, String(telemetry.fan).c_str(), true);
  mqtt.publish(TOPIC_RPM, String(telemetry.rpm).c_str(), true);
  mqtt.publish(TOPIC_STATUS_LIGHT, telemetry.status.c_str(), true);
}

void checkUnoTimeout() {
  if (millis() - lastUnoRxMs <= UNO_TIMEOUT_MS) {
    return;
  }

  if (!mqtt.connected()) {
    return;
  }

  if (!unoOfflinePublished || millis() - lastOfflinePublishMs >= OFFLINE_PUBLISH_INTERVAL_MS) {
    publishUnoOffline();
  }
}

void publishUnoOffline() {
  lastOfflinePublishMs = millis();
  unoOfflinePublished = true;
  mqtt.publish(TOPIC_STATUS, "uno_offline", true);
  Serial.println("Published status: uno_offline");
}

void printHeartbeat() {
  const unsigned long now = millis();
  if (now - lastHeartbeatMs < SERIAL_HEARTBEAT_INTERVAL_MS) {
    return;
  }

  lastHeartbeatMs = now;
  Serial.print("Heartbeat wifi=");
  Serial.print(WiFi.status() == WL_CONNECTED ? "connected" : "disconnected");
  Serial.print(" ip=");
  Serial.print(WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "-");
  Serial.print(" mqtt=");
  Serial.print(mqtt.connected() ? "connected" : "disconnected");
  Serial.print(" unoAgeMs=");
  Serial.print(now - lastUnoRxMs);
  Serial.print(" lm35Mv=");
  Serial.print(lm35Mv);
  Serial.print(" rawMv=");
  Serial.print(lm35RawMv);
  Serial.print(" correctedMv=");
  Serial.print(lm35CorrectedMv);
  Serial.print(" dummyMv=");
  Serial.print(lm35DummyMv);
  Serial.print(" dummyBase=");
  Serial.print(lm35DummyBaselineMv);
  Serial.print(" dummyComp=");
  Serial.print(lm35DummyCompensationMv);
  Serial.print(" dummyValid=");
  Serial.print(lm35DummyValid ? "true" : "false");
  Serial.print(" ambientMv=");
  Serial.print(lm35AmbientMv);
  Serial.print(" lm35TempC=");
  Serial.print(lm35Temp10 / 10.0, 1);
  Serial.print(" spikeGuard=");
  Serial.print(lm35SpikeGuardActive ? "true" : "false");
  Serial.print(" lm35Valid=");
  Serial.println(lm35Valid ? "true" : "false");
}
