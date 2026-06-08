import serial
import time
import numpy as np
from sklearn.ensemble import IsolationForest

# ----------------------------
# SERIAL CONNECTION
# ----------------------------

arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)
print("✅ Connected to Arduino")

# ----------------------------
# TRAIN ANOMALY MODEL
# ----------------------------

normal_data = np.array([
    [0, 300, 27],
    [0, 320, 26.5],
    [1, 350, 28],
    [0, 310, 27.2],
    [1, 330, 27.8],
    [0, 305, 26.9]
])

model = IsolationForest(contamination=0.1)
model.fit(normal_data)

print("✅ Anomaly model trained")

# ----------------------------
# DATA PARSER FUNCTION
# ----------------------------

def parse_data(line):
    data = {}
    parts = line.split(',')
    for part in parts:
        key, value = part.split(':')
        data[key] = float(value)
    return data

# ----------------------------
# MAIN LOOP
# ----------------------------

while True:
    try:
        line = arduino.readline().decode().strip()

        if not line:
            continue

        print("📩 Received:", line)

        data = parse_data(line)

        X = np.array([[data["MOTION"], data["LDR"], data["TEMP"]]])
        result = model.predict(X)

        if result[0] == -1:
            print("⚠️ Anomaly detected!")
            arduino.write(b'BUZZER_ON\n')
        else:
            print("✅ Normal condition")
            arduino.write(b'BUZZER_OFF\n')

    except Exception as e:
        print("Error:", e)
