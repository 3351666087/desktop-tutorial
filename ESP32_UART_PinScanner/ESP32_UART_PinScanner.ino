/*
  ESP32_UART_PinScanner.ino

  Temporary scanner for finding which ESP32 GPIO receives the UNO A5 SoftwareSerial TX signal.
  Keep UNO running UNO_Phase3_TelemetryPatch.
*/

const byte WATCH_PINS[] = {
  4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33, 34, 35
};
const byte PIN_COUNT = sizeof(WATCH_PINS) / sizeof(WATCH_PINS[0]);

volatile unsigned long edgeCounts[PIN_COUNT];
unsigned long lastCounts[PIN_COUNT];
unsigned long lastReportMs = 0;

void IRAM_ATTR edgeISR(void *arg) {
  const byte index = (byte)(uintptr_t)arg;
  if (index < PIN_COUNT) {
    edgeCounts[index]++;
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("ESP32_UART_PinScanner started");
  Serial.println("Looking for UNO A5 TX edges. Pins with activity will be printed once per second.");

  for (byte i = 0; i < PIN_COUNT; i++) {
    pinMode(WATCH_PINS[i], INPUT);
    attachInterruptArg(digitalPinToInterrupt(WATCH_PINS[i]), edgeISR, (void *)(uintptr_t)i, CHANGE);
  }
}

void loop() {
  const unsigned long now = millis();
  if (now - lastReportMs < 1000) {
    return;
  }
  lastReportMs = now;

  bool any = false;
  Serial.print("scan ");
  for (byte i = 0; i < PIN_COUNT; i++) {
    noInterrupts();
    const unsigned long count = edgeCounts[i];
    interrupts();

    const unsigned long delta = count - lastCounts[i];
    lastCounts[i] = count;

    if (delta > 0) {
      any = true;
      Serial.print(" GPIO");
      Serial.print(WATCH_PINS[i]);
      Serial.print("=");
      Serial.print(delta);
      Serial.print(" level");
      Serial.print(digitalRead(WATCH_PINS[i]));
    }
  }

  if (!any) {
    Serial.print("no_edges");
  }
  Serial.println();
}
