"""
Text-to-Speech Utility

This module provides functionality to convert text to speech using OpenAI's TTS API.
Optimized for low latency conversation flow.
"""

import os
import tempfile
import subprocess
import random
import hashlib
import threading
import time
from openai import OpenAI
from dotenv import load_dotenv

from flask import url_for
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Hangup
# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)

OPENAI_VOICES = ["alloy"]

CACHE_DIR = os.path.join(tempfile.gettempdir(), "tts_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Default speed increased for faster response
DEFAULT_SPEED = 1

# Global flag to indicate when TTS is active
# This will be used by the STT module to avoid recording the bot's voice
IS_SPEAKING = False

# # Commented out Groq implementation
# """
# import os
# import tempfile
# import subprocess
# from groq import Groq
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# groq_api_key = os.getenv("GROQ_API_KEY")

# # Initialize the Groq client
# client = Groq(api_key=groq_api_key)

# # Track if we've already shown the terms acceptance message
# _showed_terms_message = False
# """

def get_cache_key(text, voice, speed):
    """Generate a cache key based on text, voice and speed"""
    hash_obj = hashlib.md5(f"{text}_{voice}_{speed}".encode())
    return hash_obj.hexdigest()

def get_speaking_status():
    """Get the current speaking status for STT module"""
    global IS_SPEAKING
    return IS_SPEAKING

def set_speaking_status(status):
    """Set the speaking status"""
    global IS_SPEAKING
    IS_SPEAKING = status

def play_audio_async(file_path):
    """Play audio asynchronously without blocking the main thread"""
    def _play():
        global IS_SPEAKING
        try:
            # Signal that TTS is active
            set_speaking_status(True)
            
            if os.name == 'posix':  # For macOS and Linux
                subprocess.run(["afplay", file_path], 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
            else:  # For Windows
                import winsound
                winsound.PlaySound(file_path, winsound.SND_FILENAME)
        finally:
            # Signal that TTS is complete
            set_speaking_status(False)
            # Add a small delay to ensure the microphone doesn't pick up trailing audio
            time.sleep(0.2)
    
    # Start playback in a separate thread
    thread = threading.Thread(target=_play)
    thread.daemon = True  # Thread will exit when main program exits
    thread.start()
    
    # Wait a small amount of time to make sure speaking flag is set
    # before returning control to the main program
    time.sleep(0.1)

def text_to_speech(text, voice=None, speed=DEFAULT_SPEED):
    """
    Convert text to speech using OpenAI's TTS API with minimal latency.
    
    Args:
        text (str): Text to convert to speech
        voice (str): Voice to use for TTS (default: random OpenAI voice)
        speed (float): Speed of speech playback (default: 1.5)
        
    Returns:
        voice reponse (str): TwiML for mp3
    """
    
    # Choose a random voice if not specified
    if voice is None or voice.endswith("-PlayAI"):
        voice = random.choice(OPENAI_VOICES)
    elif voice not in OPENAI_VOICES:
        voice = "alloy"  
    
    try:
        # Check cache first
        cache_key = get_cache_key(text, voice, speed)
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
        
        if not os.path.exists(cache_path):
            # Generate speech using OpenAI API
 
           with client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice=voice,
                input=text,
                speed=speed
            ) as response:
                response.stream_to_file(cache_path)
        
        # Play audio asynchronously - doesn't block execution
        # play_audio_async(cache_path)
        audio_url = url_for("serve_audio",
                        filename=f"{cache_key}.mp3",
                        _external=True)   # absolute HTTPS URL
        
        

            
    except Exception as e:
        print(f"TTS Error: {e}")
        # TTS failed but we still printed the text
    return audio_url

# Commented out Groq implementation
"""
def text_to_speech(text, voice="Celeste-PlayAI"):
    \"""
    Convert text to speech using Groq's TTS API.
    
    Args:
        text (str): Text to convert to speech
        voice (str): Voice to use for TTS (default: "Celeste-PlayAI")
        
    Returns:
        None: Plays the audio and prints text to terminal
    \"""
    # Print text to terminal
    print(text)
    
    global _showed_terms_message
    
    try:
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
            
        # Generate speech using Groq API
        response = client.audio.speech.create(
            model="playai-tts",
            voice=voice,
            input=text,
            response_format="wav"
        )
        
        # Write to temporary file
        response.write_to_file(temp_path)
        
        # Play the audio file using system's default player
        if os.name == 'posix':  # For macOS and Linux
            subprocess.run(["afplay", temp_path], check=True)
        else:  # For Windows
            import winsound
            winsound.PlaySound(temp_path, winsound.SND_FILENAME)
            
        # Clean up the temporary file
        os.unlink(temp_path)
            
    except Exception as e:
        # Check if this is a terms acceptance error
        error_str = str(e)
        if "terms acceptance" in error_str and not _showed_terms_message:
            print("\nNOTE: Text-to-speech is disabled until terms are accepted.")
            print("To enable TTS, please visit: https://console.groq.com/playground?model=playai-tts")
            print("and accept the terms for the playai-tts model.\n")
            _showed_terms_message = True
        else:
            # Only print detailed error if it's not the terms acceptance error or we haven't shown the message
            if "terms acceptance" not in error_str or not _showed_terms_message:
                print(f"TTS Error: {e}")
        
        # TTS failed but we still printed the text
""" 