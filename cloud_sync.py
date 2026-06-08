import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate("firebase_key.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://aura-ai-dfd1a-default-rtdb.firebaseio.com/'
})

# Send sensor data
def send_sensor_data(mic, rain, rf, pir):
    ref = db.reference("aura/sensors")
    ref.set({
        "mic": mic,
        "rain": rain,
        "rf": rf,
        "pir": pir
    })

# Send device status
def send_status(light, fan):
    ref = db.reference("aura/status")
    ref.set({
        "light": light,
        "fan": fan
    })

# Send alert
def send_alert(message):
    ref = db.reference("aura/alerts")
    ref.push({
        "message": message
    })