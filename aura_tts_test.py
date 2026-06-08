from gtts import gTTS
from playsound3 import playsound

playsound("aura_response.mp3")
import os

# Step 1: Write what you want AURA to say
response_text = "Hello, I am AURA. How can I assist you today?"

# Step 2: Convert text to speech 
tts = gTTS(text=response_text, lang='en')
tts.save("aura_response.mp3")

# Step 3: Play the audio file
print("Playing AURA's voice...")
playsound("aura_response.mp3")
