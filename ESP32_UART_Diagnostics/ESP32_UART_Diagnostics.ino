/*
  ESP32_UART_Diagnostics.ino

  Temporary diagnostic sketch for UNO A5 -> ESP32 RX2 UART.
  It reports:
  - GPIO16 logic level
  - GPIO16 edge count
  - Serial2 decoded lines at 9600 baud

  Keep UNO running UNO_Phase3_TelemetryPatch while this sketch runs.
*/

#define PIN_RX2 16
#define PIN_TX2 17

volatile unsigned long edgeCount = 0;

String rxLine;
unsigned long lastReportMs = 0;
unsigned long lastRxMs = 0;
unsigned long lastEdgeSnapshot = 0;

void IRAM_ATTR rxEdgeISR() {
  edgeCount++;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_RX2, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_RX2), rxEdgeISR, CHANGE);

  Serial2.begin(9600, SERIAL_8N1, PIN_RX2, PIN_TX2);

  Serial.println();
  Serial.println("ESP32_UART_Diagnostics started");
  Serial.println("Watching GPIO16/RX2 at 9600 baud");
  Serial.println("Expected: GPIO16 edges should increase when UNO sends espTx=SC2 lines");
}

void loop() {
  readSerial2();
  reportPinState();
}

void readSerial2() {
  while (Serial2.available() > 0) {
    const char c = (char)Serial2.read();
    lastRxMs = millis();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      rxLine.trim();
      if (rxLine.length() > 0) {
        Serial.print("RX LINE: ");
        Serial.println(rxLine);
      }
      rxLine = "";
      return;
    }

    if (rxLine.length() < 260) {
      rxLine += c;
    } else {
      Serial.println("RX overflow; clearing line");
      rxLine = "";
    }
  }
}

void reportPinState() {
  const unsigned long now = millis();
  if (now - lastReportMs < 1000) {
    return;
  }

  noInterrupts();
  const unsigned long edges = edgeCount;
  interrupts();

  const unsigned long deltaEdges = edges - lastEdgeSnapshot;
  lastEdgeSnapshot = edges;
  lastReportMs = now;

  Serial.print("GPIO16 level=");
  Serial.print(digitalRead(PIN_RX2));
  Serial.print(" edgesPerSec=");
  Serial.print(deltaEdges);
  Serial.print(" totalEdges=");
  Serial.print(edges);
  Serial.print(" serial2Available=");
  Serial.print(Serial2.available());
  Serial.print(" msSinceRx=");
  Serial.println(lastRxMs == 0 ? -1 : (long)(now - lastRxMs));
}
