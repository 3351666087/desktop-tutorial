/*
  ESP32_UART_RXPinDecode.ino

  Temporary decoder scanner. It tries to receive UNO SC2 telemetry on several ESP32 pins.
  Keep UNO running UNO_Phase3_TelemetryPatch.
*/

const byte RX_CANDIDATES[] = {16, 17, 27, 5, 14, 15, 4, 21, 22, 23};
const byte RX_COUNT = sizeof(RX_CANDIDATES) / sizeof(RX_CANDIDATES[0]);

const byte UNUSED_TX_PIN = 25;
const unsigned long PIN_WINDOW_MS = 3500;

String rxLine;
byte activeIndex = 0;
unsigned long windowStartMs = 0;

void beginCandidate(byte index) {
  Serial2.end();
  delay(30);
  rxLine = "";
  activeIndex = index % RX_COUNT;
  const byte rxPin = RX_CANDIDATES[activeIndex];
  Serial2.begin(9600, SERIAL_8N1, rxPin, UNUSED_TX_PIN);
  windowStartMs = millis();
  Serial.print("Listening RX GPIO");
  Serial.println(rxPin);
}

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("ESP32_UART_RXPinDecode started");
  Serial.println("Trying to decode UNO SC2 telemetry at 9600 baud");
  beginCandidate(0);
}

void loop() {
  while (Serial2.available() > 0) {
    const char c = (char)Serial2.read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      rxLine.trim();
      if (rxLine.length() > 0) {
        Serial.print("RX GPIO");
        Serial.print(RX_CANDIDATES[activeIndex]);
        Serial.print(": ");
        Serial.println(rxLine);
      }
      rxLine = "";
      continue;
    }
    if (rxLine.length() < 260) {
      rxLine += c;
    } else {
      Serial.print("Overflow on GPIO");
      Serial.println(RX_CANDIDATES[activeIndex]);
      rxLine = "";
    }
  }

  if (millis() - windowStartMs >= PIN_WINDOW_MS) {
    beginCandidate(activeIndex + 1);
  }
}
