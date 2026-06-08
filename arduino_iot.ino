#include <EEPROM.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// -------- PINS --------
#define MIC_PIN A0
#define RAIN_PIN A1
#define RF_PIN A2

#define PIR_PIN 2
#define LED_PIN 8
#define FAN_PIN 7

#define SS_PIN 10
#define RST_PIN 9
#define SERVO_PIN 3

#define EEPROM_ADDR 0
#define FAN_EEPROM_ADDR 1

// -------- OBJECTS --------
MFRC522 rfid(SS_PIN, RST_PIN);
Servo doorServo;
LiquidCrystal_I2C lcd(0x27, 16, 2);

// -------- VARIABLES --------
bool lightState = false;
bool fanState = false;
bool humanDetected = false;

bool lightManualOverride = false;

// ✅ NEW (LCD CONTROL)
unsigned long lcdTimer = 0;
bool showAlert = false;

// ✅ NEW (HUMAN COUNT)
int humanCount = 0;

String uid1 = "73 95 F1 30";
String uid2 = "96 7F ED 96";

// -------- FUNCTION DECLARATIONS --------
void updateLight();
void updateFan();
void handleCommand(String command);

// -------- SETUP --------
void setup() {
  Serial.begin(9600);

  pinMode(LED_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT_PULLUP);

  doorServo.attach(SERVO_PIN);
  doorServo.write(0);

  SPI.begin();
  rfid.PCD_Init();

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("System Ready");

  updateLight();
  updateFan();
}

// -------- LOOP --------
void loop() {

  // -------- SERIAL --------
  while (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    delay(50);
    handleCommand(command);
  }

  int micValue = analogRead(MIC_PIN);
  int rainValue = analogRead(RAIN_PIN);
  int rfValue = analogRead(RF_PIN);
  int pirValue = !digitalRead(PIR_PIN);

  // -------- CLAP DETECTION --------
  static unsigned long lastClap = 0;
  int clapThreshold = 600;
  int clapDelay = 300;

  if (micValue > clapThreshold && (millis() - lastClap > clapDelay)) {
    lightState = !lightState;
    lightManualOverride = true;
    updateLight();
    lastClap = millis();

    lcd.clear();
    lcd.print("Clap Detected");

    lcdTimer = millis();
    showAlert = true;

    Serial.println("CLAP_DETECTED");
  }

  // -------- RAIN AUTO LIGHT --------
  int rainThreshold = 500;

  if (!lightManualOverride) {
    if (rainValue > rainThreshold) {
      lightState = true;
    } else {
      lightState = false;
    }
    updateLight();
  }

  // -------- HUMAN PRIORITY --------
  if (humanDetected) {
    lightState = true;
    fanState = true;
    updateLight();
    updateFan();
  }

  // -------- LCD DEFAULT (ONLY WHEN NO ALERT) --------
  if (!showAlert) {
    lcd.setCursor(0, 0);
    if (lightManualOverride) {
      lcd.print("Mode: MANUAL ");
    } else {
      lcd.print("Mode: AUTO   ");
    }
  }

  // -------- AUTO CLEAR ALERT --------
  if (showAlert && millis() - lcdTimer > 3000) {
    lcd.clear();
    showAlert = false;
  }

  // -------- RFID --------
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {

    String content = "";

    for (byte i = 0; i < rfid.uid.size; i++) {
      content.concat(String(rfid.uid.uidByte[i] < 0x10 ? " 0" : " "));
      content.concat(String(rfid.uid.uidByte[i], HEX));
    }

    content.toUpperCase();
    Serial.println(content);

    lcd.clear();

    String scannedUID = content.substring(1);

    if (scannedUID == uid1 || scannedUID == uid2) {
      lcd.print("Access Granted");
      doorServo.write(90);
      delay(5000);
      doorServo.write(0);
      lcd.clear();
      lcd.print("Door Locked");
    } else {
      lcd.print("Access Denied");
      delay(2000);
    }

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  }

  // -------- SENSOR OUTPUT --------
  Serial.print(micValue);
  Serial.print(",");
  Serial.print(rainValue);
  Serial.print(",");
  Serial.print(rfValue);
  Serial.print(",");
  Serial.println(pirValue);

  delay(100);
}

// -------- COMMAND HANDLER --------
void handleCommand(String command) {

  if (command == "LIGHT_ON") {
    lightManualOverride = true;
    lightState = true;
    EEPROM.write(EEPROM_ADDR, lightState);
    updateLight();

    lcd.clear(); lcd.print("Light ON");
    lcdTimer = millis(); showAlert = true;

    Serial.println("LIGHT_ON_SUCCESS");
  }

  else if (command == "LIGHT_OFF") {
    lightManualOverride = true;
    lightState = false;
    EEPROM.write(EEPROM_ADDR, lightState);
    updateLight();

    lcd.clear(); lcd.print("Light OFF");
    lcdTimer = millis(); showAlert = true;

    Serial.println("LIGHT_OFF_SUCCESS");
  }

  else if (command == "FAN_ON") {
    fanState = true;
    EEPROM.write(FAN_EEPROM_ADDR, fanState);
    updateFan();

    lcd.clear(); lcd.print("Fan ON");
    lcdTimer = millis(); showAlert = true;

    Serial.println("FAN_ON_SUCCESS");
  }

  else if (command == "FAN_OFF") {
    fanState = false;
    EEPROM.write(FAN_EEPROM_ADDR, fanState);
    updateFan();

    lcd.clear(); lcd.print("Fan OFF");
    lcdTimer = millis(); showAlert = true;

    Serial.println("FAN_OFF_SUCCESS");
  }

  // ✅ HUMAN WITH COUNT
  else if (command.startsWith("HUMAN:")) {
    humanDetected = true;

    humanCount = command.substring(6).toInt();

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Human Detected");
    lcd.setCursor(0, 1);
    lcd.print("Humans: ");
    lcd.print(humanCount);

    lcdTimer = millis();
    showAlert = true;

    Serial.println("HUMAN_ON");
  }

  else if (command == "N") {
    humanDetected = false;
    Serial.println("HUMAN_OFF");
  }

  else if (command == "RAIN") {
    lcd.clear();
    lcd.print("Rain Detected");

    lcdTimer = millis();
    showAlert = true;
  }

  else if (command == "INTRUDER") {
    lcd.clear();
    lcd.print("Intruder Alert!");

    lcdTimer = millis();
    showAlert = true;
  }

  else if (command == "RF_ALERT") {
    lcd.clear();
    lcd.print("RF Signal Alert");

    lcdTimer = millis();
    showAlert = true;
  }
}

// -------- LIGHT CONTROL --------
void updateLight() {
  digitalWrite(LED_PIN, lightState ? LOW : HIGH);
}

// -------- FAN CONTROL --------
void updateFan() {
  digitalWrite(FAN_PIN, fanState ? LOW : HIGH);
}