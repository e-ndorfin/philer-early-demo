from twilio.twiml.voice_response import VoiceResponse, Gather
import os
from dotenv import load_dotenv
import re
from tts import text_to_speech
def introduction() -> str:
    """
    Returns TwiML code for introductory message. 
    """

    DOMAIN = os.environ.get("DOMAIN")

    response = VoiceResponse()
    gather = Gather(
        numDigits=1, action=f"{DOMAIN}/in-call", method="POST")
    welcome_message = "Hi there! I'm your virtual assistant. I'm here to guide you through the intake process for your real estate closing. I'll be asking you a few questions — this should take about 5 minutes. Before we begin, please make sure you're in a quiet place and make sure to speak slowly and clearly. Don't worry if you are not able to answer some questions. We will send you a summary of the information you provide to us to your email and you will be able to adjust anything using the philer platform. Press any button to start!"
    audio_url = text_to_speech(welcome_message)
    gather.play(audio_url)
    response.append(gather)

    return str(response)


if __name__ == "__main__":
    load_dotenv()

    # Test the function
    twiml_code = introduction()
    print(twiml_code)
