import os
import sys
os.environ["PATH"] += os.pathsep + r"C:\Desktop\Major Project\ffmpeg\ffmpeg-8.1-essentials_build\bin"

import whisper
import sounddevice as sd
import wave
from gtts import gTTS
from playsound3 import playsound
import serial
import time
import numpy as np
import pandas as pd
from anomaly_detection import AnomalyDetector
from cloud_sync import send_sensor_data, send_status, send_alert
from firebase_admin import db

# ✅ CAMERA IMPORTS
from flask import Flask, Response
import cv2
from ultralytics import YOLO
import threading

# ---------------- CAMERA SERVER ----------------
app = Flask(__name__)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
yolo_model = YOLO("yolov8n.pt")

camera_active = True
latest_human_count = 0
last_sent_state = None  # ✅ prevent spam

def generate_frames():
    global camera_active, latest_human_count

    while camera_active:
        success, frame = cap.read()

        if not success:
            continue

        results = yolo_model(frame, verbose=False)

        human_count = 0

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])

                if cls == 0:
                    human_count += 1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, "Human", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        latest_human_count = human_count

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def start_camera_server():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


# ---------------- SERIAL SETUP ----------------
try:
    arduino = serial.Serial('COM3', 9600, timeout=1)
    time.sleep(2)
    print("✅ Connected to Arduino")
except:
    print("❌ Could not connect to Arduino. Exiting program.")
    sys.exit()

# ---------------- LOAD MODELS ----------------
print("Loading Whisper model...")
model = whisper.load_model("base")

print("Loading YOLO model...")
print("✅ System Ready.")

# ---------------- DATASET ----------------
dataset = pd.read_csv("aura_normal_dataset.csv")
training_data = dataset[['mic', 'rain', 'rf', 'pir']].values

detector = AnomalyDetector()
detector.train(training_data)

# ---------------- SPEAK ----------------
def speak(text):
    print("AURA:", text)
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("aura_reply.mp3")
        playsound("aura_reply.mp3")
    except:
        print("⚠ Audio playback error")

# ---------------- ALERT CONTROL ----------------
last_alert = None
last_camera_alert_time = 0

# ---------------- ANOMALY ----------------
def check_anomaly():
    global last_alert

    if arduino.in_waiting:
        try:
            line = arduino.readline().decode().strip()
            values = line.split(",")

            if len(values) != 4:
                return

            mic, rain, rf, pir = map(int, values)

            print(f"Sensors → Mic:{mic} Rain:{rain} RF:{rf} PIR:{pir}")
            send_sensor_data(mic, rain, rf, pir)

            # -------- 🔊 MIC / PIR --------
            if pir == 1 or mic > 150:
                if last_alert != "intruder":
                    speak("Motion or loud sound detected. Possible intruder")

                    send_alert("Intruder detected")

                    arduino.write(b'INTRUDER\n')
                    arduino.write(b'LIGHT_ON\n')   # ✅ FORCE LIGHT ON

                    send_status("ON", fan_state)   # ✅ DASHBOARD

                    last_alert = "intruder"

            # -------- 🌧 RAIN --------
            elif rain > 200:   # adjust if needed
                if last_alert != "rain":
                    speak("Rain detected. Please check the windows")

                    send_alert("Rain detected")

                    arduino.write(b'RAIN\n')
                    arduino.write(b'LIGHT_ON\n')   # ✅ FORCE LIGHT

                    send_status("ON", fan_state)

                    last_alert = "rain"

            # -------- 📡 RF --------
            elif rf > 600:
                if last_alert != "rf":
                    speak("Unknown signal activity detected")

                    send_alert("RF detected")

                    arduino.write(b'RF_ALERT\n')
                    arduino.write(b'LIGHT_ON\n')

                    send_status("ON", fan_state)

                    last_alert = "rf"

            else:
                last_alert = None

        except:
            pass

# ---------------- VOICE ----------------
def listen_command(duration=4):
    try:
        samplerate = 16000
        print("\n🎤 Speak now...")

        audio_data = sd.rec(int(duration * samplerate),
                            samplerate=samplerate,
                            channels=1,
                            dtype='int16')
        sd.wait()

        filename = "user_audio.wav"
        with wave.open(filename, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(samplerate)
            f.writeframes(audio_data.tobytes())

        result = model.transcribe(filename)
        user_text = result["text"].lower()

        print("You said:", user_text)
        time.sleep(2)   # prevent fast looping
        return user_text

    except Exception as e:
        print("⚠ Whisper Error:", e)
        return ""

# ---------------- CONVERSATION ----------------
conversations = {
    "how are you": "I am good, thank you. How about you?",
    "i am good": "Great to hear that!",
    "i am fine": "Glad to hear that!",
    "hello": "Hello! How can I help you?",
    "hi": "Hi there! What can I do for you?",
}

# ---------------- START ----------------
speak("Hi, I am AURA. How can I help you today?")
conversation_active = True

light_state = "OFF"
fan_state = "OFF"

# ✅ START CAMERA SERVER
camera_thread = threading.Thread(target=start_camera_server)
camera_thread.daemon = True
camera_thread.start()

while conversation_active:

    for _ in range(5):
        check_anomaly()

    # ✅ HUMAN DETECTION FIXED
    try:
        if latest_human_count > 0:
            count = latest_human_count

            if last_sent_state != "H":
                speak(f"{count} human detected in camera.")
                send_alert(f"{count} human detected")

                arduino.write(b'H\n')
                arduino.write(b'LIGHT_ON\n')

                last_sent_state = "H"

        else:
            if last_sent_state != "N":
                arduino.write(b'N\n')
                last_sent_state = "N"

    except:
        print("⚠ Camera error")

    time.sleep(0.2)

    # -------- VOICE --------
    user_text = listen_command()

    if not user_text:
        continue  # ✅ NO SPAM

    # -------- EXIT --------
    if any(word in user_text for word in ["bye", "bye aura", "goodbye", "stop", "exit", "quit"]):
        speak("Goodbye! Turning off all devices.")
        arduino.write(b'LIGHT_OFF\n')
        arduino.write(b'FAN_OFF\n')
        conversation_active = False
        break

    # -------- CONVERSATION --------
    response_given = False
    for key in conversations:
        if key in user_text:
            speak(conversations[key])
            response_given = True
            break

    # -------- LIGHT --------
    if "light" in user_text:

        if "on" in user_text:
            command = "LIGHT_ON"
            success_msg = "Light turned on successfully."
        elif "off" in user_text:
            command = "LIGHT_OFF"
            success_msg = "Light turned off successfully."
        else:
            command = None

        if command:
            arduino.reset_input_buffer()
            arduino.write((command + "\n").encode())

            start = time.time()

        while time.time() - start < 5:
            if arduino.in_waiting:
                reply = arduino.readline().decode().strip()

                if "," in reply:
                    continue

                if reply == "LIGHT_ON_SUCCESS":
                    light_state = "ON"
                    send_status(light_state, fan_state)
                    speak(success_msg)
                    response_given = True
                    break

                elif reply == "LIGHT_OFF_SUCCESS":
                    light_state = "OFF"
                    send_status(light_state, fan_state)
                    speak(success_msg)
                    response_given = True
                    break

    # -------- FAN --------
    if "fan" in user_text:

        if "on" in user_text:
            command = "FAN_ON"
            success_msg = "Fan turned on successfully."
        elif "off" in user_text:
            command = "FAN_OFF"
            success_msg = "Fan turned off successfully."
        else:
            command = None

        if command:
            arduino.reset_input_buffer()
            arduino.write((command + "\n").encode())

            start = time.time()

        while time.time() - start < 5:
            if arduino.in_waiting:
                reply = arduino.readline().decode().strip()

                if "," in reply:
                    continue

                if reply == "FAN_ON_SUCCESS":
                    fan_state = "ON"
                    send_status(light_state, fan_state)
                    speak(success_msg)
                    response_given = True
                    break

                elif reply == "FAN_OFF_SUCCESS":
                    fan_state = "OFF"
                    send_status(light_state, fan_state)
                    speak(success_msg)
                    response_given = True
                    break

    # -------- UNKNOWN --------
    if not response_given:
        speak("I didn't understand, can you repeat?")
