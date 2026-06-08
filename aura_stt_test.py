import sounddevice as sd
import numpy as np
import whisper
import wave
import os
os.environ["PATH"] += os.pathsep + r"C:\Users\Administrator\Desktop\ROHINI\ffmpeg-2025-10-27-git-68152978b5-full_build\bin"

# --- Step 1: Record your voice ---
samplerate = 16000
duration = 5   #seconds
print("speak now...recording for 5 seconds!")
audio_data = sd.rec(int(duration * samplerate), samplerate = samplerate, channels = 1, dtype = 'int16')
sd.wait()
print("Recording complete!")

# Save as WAV so Whisper can read it
filename = r"C:\Users\Administrator\Desktop\ROHINI\AURA_AI\test_audio.wav"
with wave.open(filename, 'wb') as f:
  f.setnchannels(1)
  f.setsampwidth(2)
  f.setframerate(samplerate)
  f.writeframes(audio_data.tobytes())
print(f"Saved: {filename}")

# --- Step 2: Load Whisper model ---
print("Loading Whisper model...")
model = whisper.load_model("base")

# --- Step 3: Transcribe audio ---
print("Transcribing your voice...")
print("Trying to transcribe file:", filename)

result = model.transcribe(filename)

# --- Step 4: Output ---
print("\n You said:", result["text"])
