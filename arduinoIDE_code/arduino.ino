#include <LiquidCrystal.h>
#include <DHT.h>

// ---------- Pins ----------
// LCD
const int LCD_RS = 7;
const int LCD_EN = 8;
const int LCD_D4 = 9;
const int LCD_D5 = 10;
const int LCD_D6 = 11;
const int LCD_D7 = 12;

// Sensors & actuators
const int SOIL_PIN   = A0;  // Soil moisture sensor
const int DHT_PIN    = 6;   // Temp & humidity sensor
const int RELAY_PIN  = 5;   // Relay -> pump

// Ultrasonic water level
const int TRIG_PIN   = 2;
const int ECHO_PIN   = 3;

// Water level LED
const int WATER_LED_PIN = 4;

// LCD
LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);

// DHT Sensor
#define DHTTYPE DHT11
DHT dht(DHT_PIN, DHTTYPE);

// Settings
// Below this soil moisture % pump gets activated
const int moistureThreshold = 40;

// Above this distance (cm), water is considered too low
const int waterLowDistance = 10;

// Pump timing
const unsigned long pumpOnDuration   = 5000;  // 5 seconds
const unsigned long waitAfterPump    = 30000; // 30 seconds

void setup() {
  Serial.begin(9600);

  lcd.begin(16, 2);
  lcd.print("Watering System");
  delay(1500);
  lcd.clear();

  dht.begin();

  pinMode(SOIL_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  pinMode(WATER_LED_PIN, OUTPUT);
  digitalWrite(WATER_LED_PIN, LOW);
}

// soil moisture to %
int readSoilMoisturePercent() {
  int raw = analogRead(SOIL_PIN);  // 0–1023

  // Assumes: 0 (wet) -> 100%, 1023 (dry) -> 0%
  int percent = map(raw, 1023, 0, 0, 100);
  if (percent < 0)   percent = 0;
  if (percent > 100) percent = 100;

  return percent;
}

//ultrasonic distance in cm
long readWaterDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return -1;
  }

  long distance = duration * 0.0343 / 2;
  return distance;
}

// Pump cycle: run pump 5s, then 30s countdown
void runPumpCycle() {
  // 5-seconds pump running
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Watering...");
  lcd.setCursor(0, 1);
  lcd.print("Pump: 5s");

  digitalWrite(RELAY_PIN, HIGH);
  delay(pumpOnDuration);
  digitalWrite(RELAY_PIN, LOW);

  //  30-seconds countdown
  for (int i = waitAfterPump / 1000; i > 0; i--) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Wait: ");
    lcd.print(i);
    lcd.print("s");

    lcd.setCursor(0, 1);
    lcd.print("Recheck soil...");
    delay(1000);
  }
}

//Main Loop
void loop() {
  //  Read sensors
  float h = dht.readHumidity();
  float t = dht.readTemperature();   // °C
  int   soilPercent   = readSoilMoisturePercent();
  long  waterDistance = readWaterDistanceCm();

  // Send data to Python app
  Serial.print("M:");
  Serial.print(soilPercent);
  Serial.print(",T:");
  Serial.print((int)t);
  Serial.print(",H:");
  Serial.println((int)h);

  // If DHT failed, show error
  if (isnan(h) || isnan(t)) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("DHT error...");
    delay(2000);
    return;
  }

  //  Water level LED
  bool waterLow = false;
  if (waterDistance == -1) {
    // no echo -> we just say "??" but don't block pump
    waterLow = false;
  } else if (waterDistance > waterLowDistance) {
    waterLow = true;
  }

  if (waterLow) {
    digitalWrite(WATER_LED_PIN, HIGH);
  } else {
    digitalWrite(WATER_LED_PIN, LOW);
  }

  // Debug to Serial
  Serial.print("Temp: "); Serial.print(t); Serial.print(" *C  ");
  Serial.print("Humidity: "); Serial.print(h); Serial.print(" %  ");
  Serial.print("Soil: "); Serial.print(soilPercent); Serial.print(" %  ");
  Serial.print("WaterDist: "); Serial.print(waterDistance); Serial.print(" cm  ");
  Serial.print("WaterLowLED: "); Serial.println(waterLow ? "ON" : "OFF");

  // Decide: water or just display?
  if (soilPercent < moistureThreshold) {
    // SOIL IS "DRY" ACCORDING TO THRESHOLD -> run one watering cycle
    runPumpCycle();
    // After this finishes, loop() repeats, reads sensors again,
    // and will decide if we water again or not.
  } else {
    // Soil moist enough: show normal screen, pump OFF
    digitalWrite(RELAY_PIN, LOW);

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("T:");
    lcd.print(t, 1);
    lcd.print("C ");
    lcd.print("H:");
    lcd.print((int)h);
    lcd.print("%");

    lcd.setCursor(0, 1);
    lcd.print("Soil:");
    lcd.print(soilPercent);
    lcd.print("% ");

    if (waterDistance > 0 && waterDistance < 999) {
      lcd.print("W:");
      lcd.print(waterDistance);
      lcd.print("cm");
    } else {
      lcd.print("W:??");
    }

    delay(2000);
  }
}
