import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
  print("Connected with result code", rc)

client = mqtt.Client()
client.on_connect = on_connect
client.connect("test.mosquitto.org", 1883, 60)
client.loop_start()