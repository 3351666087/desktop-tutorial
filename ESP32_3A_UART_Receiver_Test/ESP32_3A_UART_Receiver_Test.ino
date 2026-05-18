/*
  ESP32_3A_UART_Receiver_Test.ino
  Smart Classroom Energy-Saving, Safety & Asset Monitoring System

  Purpose:
  - Test ESP32 Serial2 UART wiring from/to UNO SoftwareSerial.
  - No Wi-Fi, no MQTT.

  Wiring:
  - UNO A5/TX -> resistor divider -> ESP32 GPIO16/RX2
  - ESP32 GPIO17/TX2 -> UNO A4/RX (optional)
  - UNO GND -> ESP32 GND
*/

#define PIN_ESP32_RX2 16
#define PIN_ESP32_TX2 17

const unsigned long UNO_TIMEOUT_MS = 5000;
const unsigned long TIMEOUT_PRINT_INTERVAL_MS = 5000;

String rxLine;
String usbLine;
unsigned long lastUnoRxMs = 0;
unsigned long lastTimeoutPrintMs = 0;

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, PIN_ESP32_RX2, PIN_ESP32_TX2);

  lastUnoRxMs = millis();

  Serial.println();
  Serial.println("ESP32_3A_UART_Receiver_Test started");
  Serial.println("Serial Monitor: 115200 baud");
  Serial.println("Serial2: 9600 baud, RX2=GPIO16, TX2=GPIO17");
  Serial.println("Type PING, BUZZ, DEMO=1, or DEMO=0 in Serial Monitor to send CMD lines to UNO");
}

void loop() {
  readUnoSerial();
  readUsbSerial();
  checkUnoTimeout();
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
        lastUnoRxMs = millis();
        Serial.print("RX from UNO: ");
        Serial.println(rxLine);
      }
      rxLine = "";
      return;
    }

    if (rxLine.length() < 240) {
      rxLine += c;
    } else {
      rxLine = "";
      Serial.println("RX buffer overflow; line dropped");
    }
  }
}

void readUsbSerial() {
  while (Serial.available() > 0) {
    const char c = (char)Serial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      usbLine.trim();
      if (usbLine.length() > 0) {
        String command = usbLine;
        if (!command.startsWith("CMD")) {
          command = "CMD," + command;
        }
        Serial.print("TX to UNO: ");
        Serial.println(command);
        Serial2.print(command);
        Serial2.print('\n');
      }
      usbLine = "";
      return;
    }

    if (usbLine.length() < 120) {
      usbLine += c;
    } else {
      usbLine = "";
      Serial.println("USB command buffer overflow; line dropped");
    }
  }
}

void checkUnoTimeout() {
  const unsigned long now = millis();
  if (now - lastUnoRxMs > UNO_TIMEOUT_MS && now - lastTimeoutPrintMs > TIMEOUT_PRINT_INTERVAL_MS) {
    lastTimeoutPrintMs = now;
    Serial.println("UNO telemetry timeout");
  }
}
