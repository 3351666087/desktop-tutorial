/*
  Relay_Fan_Test.ino
  Smart Classroom Energy-Saving, Safety & Asset Monitoring System

  Purpose:
  - Test only the relay-controlled 12V fan power path.
  - Toggle the relay every 2 seconds.
  - Keep the 4-wire fan PWM input on D9 at a fixed duty value.

  If the fan relay behavior is reversed, only swap these two constants:
    const int RELAY_ON  = HIGH;
    const int RELAY_OFF = LOW;
*/

#define PIN_RELAY_FAN 6
#define PIN_FAN_PWM   9

// Current relay behavior appears active HIGH. If yours is active LOW, swap these.
const int RELAY_ON  = HIGH;
const int RELAY_OFF = LOW;

const unsigned long TOGGLE_INTERVAL_MS = 2000;
const int FAN_PWM_VALUE = 255;  // 0-255. Use 255 for full/high fan command.

bool fanRelayOn = false;
unsigned long lastToggleMs = 0;

void setup() {
  pinMode(PIN_RELAY_FAN, OUTPUT);
  digitalWrite(PIN_RELAY_FAN, RELAY_OFF);  // Keep fan off during boot.

  pinMode(PIN_FAN_PWM, OUTPUT);
  analogWrite(PIN_FAN_PWM, FAN_PWM_VALUE);

  Serial.begin(9600);
  while (!Serial) {
    ;  // UNO ignores this, harmless for compatible boards.
  }

  Serial.println(F("Relay_Fan_Test started"));
  Serial.println(F("Relay toggles every 2 seconds; D9 outputs fixed PWM."));
  Serial.println(F("If ON/OFF is reversed, swap RELAY_ON and RELAY_OFF at the top."));
}

void loop() {
  const unsigned long now = millis();

  analogWrite(PIN_FAN_PWM, FAN_PWM_VALUE);

  if (now - lastToggleMs >= TOGGLE_INTERVAL_MS) {
    lastToggleMs = now;
    fanRelayOn = !fanRelayOn;

    digitalWrite(PIN_RELAY_FAN, fanRelayOn ? RELAY_ON : RELAY_OFF);

    Serial.print(F("fanRelay="));
    Serial.print(fanRelayOn ? F("ON") : F("OFF"));
    Serial.print(F(" relayPinLevel="));
    Serial.print(fanRelayOn ? RELAY_ON : RELAY_OFF);
    Serial.print(F(" fanPWM="));
    Serial.println(FAN_PWM_VALUE);
  }
}
