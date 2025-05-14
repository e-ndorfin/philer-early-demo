# send_sms.py
import os
from twilio.rest import Client

import os
from dotenv import load_dotenv



if __name__ == '__main__':
    load_dotenv()
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    SMS_FROM    = os.environ.get("TWILIO_PHONE_NUMBER")   # your Twilio SMS-capable number
    USER_PHONE  = '+14379882696'
    DOMAIN = os.environ.get("DOMAIN")                   # the user’s phone

    twilio_client = Client(account_sid, auth_token)

    token = "PL0003"
    link  = f"{DOMAIN}/call?token={token}"

    message = twilio_client.messages.create(
        to=USER_PHONE,
        from_=SMS_FROM,
        body=f"Tap to start your intake process with Philer (expires in 1 h): {link}"
    )


    print(f"LINK to trigger call:  {link}")
    
