from twilio.twiml.voice_response import VoiceResponse, Gather
import os
from dotenv import load_dotenv
import re


def introduction() -> str:
    """
    Returns TwiML code for introductory message. 
    """

    DOMAIN = os.environ.get("DOMAIN")

    response = VoiceResponse()
    gather = Gather(
        numDigits=1, action=f"{DOMAIN}/in-call", method="POST")
    gather.say(
        "Press any number to begin answering questions.")
    response.append(gather)

    return str(response)


if __name__ == "__main__":
    load_dotenv()

    # Test the function
    twiml_code = introduction()
    print(twiml_code)
