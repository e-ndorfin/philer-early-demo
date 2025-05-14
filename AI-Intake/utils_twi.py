import os
import json
from datetime import datetime
from pathlib import Path
from twilio.rest import Client
from flask import Flask


def make_outgoing_call(twiml: str, to_number: str, from_number: str) -> str:
    """
    Makes a call from a number to a number given TWIML code.

    Args:
        twiml (str): The TwiML code to execute during the call
        to_number (str): The recipient's phone number
        from_number (str): The Twilio number to call from

    Returns:
        call_sid (str): The SID of the created call

    """

    ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

    if not ACCOUNT_SID or not AUTH_TOKEN:
        raise ValueError(
            "Twilio credentials not found in environment variables")

    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    call = client.calls.create(
        # url="http://demo.twilio.com/docs/voice.xml",  # If we want to specify URL containing TwiML code
        twiml=twiml,
        to=to_number,
        from_=from_number,
        record=True
    )

    call_sid = call.sid

    return call_sid


def save_request_data(form_data):
    """
    Saves Twilio request form data to a file organized by CallSID.

    Args:
        form_data: The request.form data from a Twilio webhook

    Returns:
        str: The path where the file was saved
    """
    # Check if CallSID exists
    if 'CallSid' not in form_data:
        raise ValueError("CallSid not found in form data")

    call_sid = form_data['CallSid']

    # Create responses directory if it doesn't exist
    responses_dir = Path("responses")
    responses_dir.mkdir(exist_ok=True)

    # Create directory for this specific call if it doesn't exist
    call_dir = responses_dir / call_sid
    call_dir.mkdir(exist_ok=True)

    # Create a timestamped filename for this interaction
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"interaction_{timestamp}.json"
    file_path = call_dir / filename

    # Convert form data to dict and save as JSON
    # ImmutableMultiDict from Flask needs to be converted
    data_dict = {}
    for key in form_data:
        data_dict[key] = form_data[key]

    # Add timestamp to the data
    data_dict['_timestamp'] = timestamp

    # Write to file
    with open(file_path, 'w') as f:
        json.dump(data_dict, f, indent=2)

    return str(file_path)


def twiml(resp):
    """
    Helper function to convert TwiML objects to Flask responses

    Args:
        resp: A TwiML response object

    Returns:
        A Flask response with the proper mimetype for TwiML
    """
    resp = str(resp)
    response = Flask.response_class(
        response=resp,
        status=200,
        mimetype='text/xml'
    )
    return response
