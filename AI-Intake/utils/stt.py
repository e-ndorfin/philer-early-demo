"""
Speech-to-Text Utility

This module provides functionality to convert speech to text using Groq with Whisper models.
"""

import os
import tempfile
import pyaudio
import wave
import time
from groq import Groq
from dotenv import load_dotenv
from utils.tts import get_speaking_status

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

# Initialize the Groq client
client = Groq(api_key=groq_api_key)

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
SILENCE_THRESHOLD = 500  
SILENCE_DURATION = 2.0 
# Cooldown period after TTS finishes before starting to record
TTS_COOLDOWN = 0.5

def record_audio():
    """
    Record audio from the microphone until silence is detected.
    Waits for TTS to finish before starting to record.
    
    Returns:
        str: Path to the recorded audio file
    """
    # Wait for TTS to finish if it's currently speaking
    while get_speaking_status():
        time.sleep(0.1)
    
    # Add a cooldown period to avoid any TTS echo
    time.sleep(TTS_COOLDOWN)
    
    print("\nListening... (speak now, pause when done)")
    
    p = pyaudio.PyAudio()
    
    # Open stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    frames = []
    silent_chunks = 0
    required_silent_chunks = int(SILENCE_DURATION * RATE / CHUNK)
    
    # Start recording
    try:
        while True:
            # Check again if TTS started speaking (should not happen, but just in case)
            if get_speaking_status():
                # If TTS started speaking, clear the frames and wait
                frames = []
                silent_chunks = 0
                print("\nDetected system speech, resetting recording...")
                
                while get_speaking_status():
                    time.sleep(0.1)
                
                # Add cooldown after TTS finishes
                time.sleep(TTS_COOLDOWN)
                print("\nListening again... (speak now, pause when done)")
                continue
            
            data = stream.read(CHUNK)
            frames.append(data)
            
            # Check if this chunk is silent
            amplitude = max(abs(int.from_bytes(data[i:i+2], byteorder='little', signed=True)) 
                          for i in range(0, len(data), 2))
            
            if amplitude < SILENCE_THRESHOLD:
                silent_chunks += 1
                if silent_chunks >= required_silent_chunks:
                    break  
            else:
                silent_chunks = 0 
                
    except KeyboardInterrupt:
        print("Recording stopped manually.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    # Save the recorded audio to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = temp_file.name
    
    wf = wave.open(temp_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print("Recording complete.")
    return temp_path

def transcribe_audio(audio_file_path):
    """
    Transcribe the audio file using Groq with Whisper model.
    
    Args:
        audio_file_path (str): Path to the audio file to transcribe
        
    Returns:
        str: Transcribed text
    """
    try:
        # Use Groq client directly
        with open(audio_file_path, "rb") as audio_file:
            # Using the fastest model: distil-whisper-large-v3-en (English only)
            # If multilingual support is needed, use whisper-large-v3-turbo instead
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="distil-whisper-large-v3-en",  # Fastest model (English only)
                temperature=0.0
            )
            return transcription.text
            
    except Exception as e:
        print(f"Transcription Error: {e}")
        # Fallback to whisper-large-v3-turbo (multilingual) if needed
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",  # Multilingual fallback
                    temperature=0.0
                )
                return transcription.text
        except Exception as e2:
            print(f"Fallback transcription error: {e2}")
            text = input("Fallback - Type what you said: ")
            return text
    finally:
        try:
            os.unlink(audio_file_path)
        except:
            pass

def speech_to_text():
    """
    Record audio from the microphone and transcribe it using Groq.
    Makes sure to wait for any TTS playback to finish before recording.
    
    Returns:
        str: Transcribed text
    """
    audio_path = record_audio()
    print("Transcribing...")
    
    transcribed_text = transcribe_audio(audio_path)
    
    if transcribed_text:
        print(f"Transcribed: {transcribed_text}")
    else:
        print("Transcription failed or empty.")
        transcribed_text = "[Transcription failed]"
        
    return transcribed_text 