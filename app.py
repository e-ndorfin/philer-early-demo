# from agents.intent_classifier import classify_intent
# from agents.question_asker import ask_question_node
from flask import (
    request,
    url_for,
    jsonify
)
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Hangup
from flask import Flask, send_from_directory
from flask_cors import CORS
from utils_twi import save_request_data, twiml
from core.state import ConversationState
from core.workflow import intake_workflow
from twiml_template import introduction
from copy import deepcopy
from langgraph.types import Command, Interrupt
from twilio.rest import Client
from dotenv import load_dotenv
from airtable.outbound import airtable_to_json, write_json_file
from airtable.utils import populate_form_data
from utils.tts import text_to_speech
import tempfile

import os


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

CACHE_DIR = os.path.join(tempfile.gettempdir(), "tts_cache")
CACHE_DIR = os.path.join(tempfile.gettempdir(), "tts_cache")

config = {
    "recursion_limit": 500,
    "configurable": {"thread_id": "intake-thread-1"}
}
INITIAL_STATE_TEMPLATE: ConversationState = {
    "form_data": {},
    "conversation_history": [],
    "current_question_id": "welcome",
    "user_response": None,
    "intent": None,
    "agent_response": None,
    "twiml": None,
    "is_done": False
}


@app.route('/print-data', methods=['POST'])
def print_data():
    """Simple endpoint that just prints received Twilio data."""
    print('hi')
    print("---- Received Twilio Data ----")
    for key, value in request.form.items():
        print(f"{key}: {value}")
    print("-----------------------------")

    return {"status": "success"}, 200


call_sessions: dict[str, ConversationState] = {}


@app.route('/call', methods=['POST'])
def call():
    request_data = request.get_json()

    to_number = request_data.get('to_number')
    identifier_value_to_fetch = request_data.get('token')

    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    table_name = os.environ.get('FILES_TABLE_NAME')
    view_name = "Intake View"
    selected_fields = [
        "File Number",
        "Main Applicant",
        "Second Applicant",
        "Third Applicant",
        "Fourth Applicant",
        "Transaction Type",
        "Full Address",
        "Pre Con?",
        "Property Type",
        "Intent of Use",
        "Holding Title As",
        "Current Address",
        "Closing Date",
        "Mortgage Agent",
        "Realtor",
        "Insurance Agent",
        "pre-auth token"]
    record_id_to_fetch = None
    identifier_field_name = "File Number"  # The field to use for identification

    # updated_form_data[current_question_id]
    data = airtable_to_json(api_key, base_id, table_name, selected_fields,
                            identifier_field_name, identifier_value_to_fetch, view_name=view_name)
    if data:
        write_json_file(data, f"{identifier_value_to_fetch}.json")
        form_data = populate_form_data(data)
        state = deepcopy(INITIAL_STATE_TEMPLATE)
        state["form_data"] = form_data
        call_sessions[call.sid] = state
        print(data)
    else:
        print("Failed to retrieve data from Airtable.")

    from_number = os.environ.get("TWILIO_PHONE_NUMBER")
    print(f"to_number: {to_number}")

    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    call = client.calls.create(
        twiml=introduction(),
        to=to_number,
        from_=from_number
    )

    print(f"call id: {call.sid}")
    return jsonify({"status": "success",
                    "message": "Calling {to_number} now..."}), 200


@app.route('/in-call', methods=['POST'])
def in_call():
    if request.method != 'POST':
        return "Method not allowed", 405

    call_sid = request.form.get("CallSid")
    if not call_sid:
        return "Missing CallSid", 400

    # fetch existing state or start fresh
    state: ConversationState = call_sessions.get(
        call_sid, deepcopy(INITIAL_STATE_TEMPLATE))
    audio_url = ""
    question = ""
    if 'Digits' in request.form and request.form['Digits']:

        # stop as soon as we have TwiML to speak
        twiml_xml = None

        print("enter first stream")
        for event in intake_workflow.stream(state, config=config, stream_mode="values"):
            state.update(event)
            print("---- next node ------")
            print(event)
            print("----------------")
            if "__interrupt__" in event:                      # ← interrupt fired
                # first (and only) Interrupt
                interrupt = event["__interrupt__"][0]
                question = interrupt.value
            else:
                question = event["agent_response"]

            print(question)

        audio_url = text_to_speech(question)
        response = VoiceResponse()
        gather = Gather(
            input='speech',
            action=url_for('in_call'),
            language='en-US',
            method='POST',
            speechTimeout=2
        )
        # gather.say(question)
        gather.play(audio_url)
        response.append(gather)
        return twiml(response)

    elif 'SpeechResult' in request.form and request.form['SpeechResult']:
        user_reponse = request.form['SpeechResult']
        command = Command(resume=user_reponse)
        done = False

        if state["current_question_id"] == 'farewell':
            command = Command(resume="okay")

        for event in intake_workflow.stream(command, config=config, stream_mode="values"):
            print("---- next node ------")
            print(event)
            print("----------------")
            state.update(event)
            if event.get("is_done"):
                done = True
            if "__interrupt__" in event:                      # ← interrupt fired
                # first (and only) Interrupt
                interrupt = event["__interrupt__"][0]
                question = interrupt.value
            else:
                question = event["agent_response"]

        call_sessions[call_sid] = state
        response = VoiceResponse()
        gather = Gather(
            input='speech',
            action=url_for('in_call'),
            language='en-US',
            method='POST',
            speechTimeout=2
        )
        # gather.say(question)
        if question:
            audio_url = text_to_speech(question)
            gather.play(audio_url)
        response.append(gather)
        response.redirect(url_for('in_call', _external=True), method='POST')

        if done:
            response.hangup()

        return twiml(response)

    # persist for the next webhook hit
    call_sessions[call_sid] = state

    twiml_xml = state.get("twiml")
    if not twiml_xml:
        return "No TwiML generated", 500

    return twiml(str(twiml_xml))


@app.route("/audio/<path:filename>")
def serve_audio(filename):
    """
    Twilio issues a GET to this endpoint when it sees <Play>...</Play>.
    We stream back the MP3 from CACHE_DIR.
    """
    return send_from_directory(
        CACHE_DIR,
        filename,
        mimetype="audio/mpeg",
        conditional=True            # adds ETag / range support
    )


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    load_dotenv()
    PORT = int(os.environ.get("PORT"))

    app.run(debug=True, port=PORT, host='0.0.0.0')
