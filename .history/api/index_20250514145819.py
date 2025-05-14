import sys
import os
from pathlib import Path

# Add the AI-Intake directory to Python path
current_dir = Path(__file__).parent.parent
ai_intake_dir = current_dir / 'AI-Intake'
sys.path.append(str(ai_intake_dir))

# Import needed modules from AI-Intake
from flask import Flask, request, jsonify, url_for, send_from_directory
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Hangup
from AI_Intake.utils_twi import save_request_data, twiml
from AI_Intake.core.state import ConversationState
from AI_Intake.core.workflow import intake_workflow
from AI_Intake.twiml_template import introduction
from copy import deepcopy
from langgraph.types import Command, Interrupt
from twilio.rest import Client
from dotenv import load_dotenv
from AI_Intake.airtable.outbound import airtable_to_json, write_json_file
from AI_Intake.airtable.utils import populate_form_data
from AI_Intake.utils.tts import text_to_speech
import tempfile

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Set up cache directory for TTS files
CACHE_DIR = os.path.join(tempfile.gettempdir(), "tts_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Configuration for the workflow
config = {
    "recursion_limit": 500, 
    "configurable": {"thread_id": "intake-thread-1"}
}

# Initial state template for conversations
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

# Dictionary to store active call sessions
call_sessions: dict[str, ConversationState] = {}

@app.route('/')
def home():
    return 'Philer AI Intake System - Vercel Deployment'

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/call')
def call():
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
        "pre-auth token"
    ]
    
    from_number = os.environ.get("TWILIO_PHONE_NUMBER")
    to_number = request.args.get('phone', "+14379882696")  # Allow phone number as a parameter or use default

    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    identifier_field_name = "File Number"
    identifier_value_to_fetch = request.args.get('token')
    data = airtable_to_json(api_key, base_id, table_name, selected_fields, identifier_field_name, identifier_value_to_fetch, view_name=view_name)
    
    if data:
        write_json_file(data, f"{identifier_value_to_fetch}.json")
        form_data = populate_form_data(data)
        state = deepcopy(INITIAL_STATE_TEMPLATE)
        state["form_data"] = form_data

        call = client.calls.create(
            twiml=introduction(),
            to=to_number,
            from_=from_number
        )
        call_sessions[call.sid] = state
        print(f"call id: {call.sid}")
        return jsonify({
            "status": "success", 
            "message": "Call initiated",
            "call_sid": call.sid
        }), 200
    else:
        print("Failed to retrieve data from Airtable.")
        call = client.calls.create(
            twiml=introduction(),
            to=to_number,
            from_=from_number
        )
        return jsonify({
            "status": "warning", 
            "message": "Call initiated but failed to retrieve Airtable data",
            "call_sid": call.sid
        }), 200

@app.route('/in-call', methods=['GET', 'POST'])
def in_call():
    params = request.values  # merged GET + POST params
    call_sid = params.get("CallSid")
    if not call_sid:
        return "Missing CallSid", 400

    # fetch existing state or start fresh
    state: ConversationState = call_sessions.get(call_sid, deepcopy(INITIAL_STATE_TEMPLATE))
    audio_url = ""
    question = ""

    # ─── Digits branch ────────────────────────────────────────────────────
    if 'Digits' in params and params['Digits']:
        # stop as soon as we have TwiML to speak
        print("enter first stream")
        for event in intake_workflow.stream(state, config=config, stream_mode="values"):
            state.update(event)
            print("---- next node ------")
            print(event)
            print("----------------")
            if "__interrupt__" in event:
                interrupt = event["__interrupt__"][0]
                question = interrupt.value
            else:
                question = event["agent_response"]

        audio_url = text_to_speech(question)
        response = VoiceResponse()
        gather = Gather(
            input='speech',
            action=url_for('in_call', _external=True),
            language='en-US',
            method='POST',
            speechTimeout=2
        )
        gather.play(audio_url)
        response.append(gather)
        response.say("We did not receive a response, please try again.")
        response.redirect(url_for('in_call', _external=True), method='POST')
        return twiml(response)

    # ─── SpeechResult branch ──────────────────────────────────────────────
    elif 'SpeechResult' in params and params['SpeechResult']:
        user_response = params['SpeechResult']
        command = Command(resume=user_response)
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
            if "__interrupt__" in event:
                interrupt = event["__interrupt__"][0]
                question = interrupt.value
            else:
                question = event["agent_response"]
        
        call_sessions[call_sid] = state
        response = VoiceResponse()
        if done:
            response.hangup()
        gather = Gather(
            input='speech',
            action=url_for('in_call', _external=True),
            language='en-US',
            method='POST',
            speechTimeout=2
        )
        if question:
            audio_url = text_to_speech(question)
            gather.play(audio_url)
        response.append(gather)
        response.say("We did not receive a response, please try again.")
        response.redirect(url_for('in_call', _external=True), method='POST')
        
        return twiml(response)
    else:
        user_response = "what is the weather"
        command = Command(resume=user_response)
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
            if "__interrupt__" in event:
                interrupt = event["__interrupt__"][0]
                question = interrupt.value
            else:
                question = event["agent_response"]

        call_sessions[call_sid] = state
        response = VoiceResponse()
        gather = Gather(
            input='speech',
            action=url_for('in_call', _external=True),
            language='en-US',
            method='POST',
            speechTimeout=2
        )
        if question:
            audio_url = text_to_speech(question)
            gather.play(audio_url)
        if done:
            print("DONE")
            response.hangup()
        response.append(gather)
        response.say("We did not receive a response, please try again.")
        response.redirect(url_for('in_call', _external=True), method='POST')
        
        return twiml(response)

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
        conditional=True  # adds ETag / range support
    )

# Add route to generate link for making outbound calls
@app.route('/generate-link', methods=['GET'])
def generate_link():
    token = request.args.get('token')
    phone = request.args.get('phone')
    
    if not token or not phone:
        return jsonify({"error": "Missing token or phone parameter"}), 400
    
    # Get the base URL from the request
    host = request.host_url.rstrip('/')
    
    # Generate the call link
    call_link = f"{host}/call?token={token}&phone={phone}"
    
    return jsonify({
        "call_link": call_link,
        "token": token,
        "phone": phone
    }), 200
