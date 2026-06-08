import serial
import cv2
import time

# ---------- Arduino Serial ----------
arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)
print("Arduino connected")

# ---------- ESP32-CAM Stream ----------
ESP32_CAM_URL = "http://192.168.0.104:81/stream"  # CHANGE IP
cap = cv2.VideoCapture(ESP32_CAM_URL)

while True:
    # Read Arduino data
    if arduino.in_waiting:
        line = arduino.readline().decode().strip()
        print("Arduino:", line)

    # Read Camera frame
    ret, frame = cap.read()
    if ret:
        cv2.imshow("ESP32-CAM Feed", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

arduino.close()
cap.release()
cv2.destroyAllWindows()
