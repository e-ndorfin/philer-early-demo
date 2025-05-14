from .core import ConversationState, intake_workflow
from .utils import introduction, text_to_speech, convert_to_twiml
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    url_for,
    send_from_directory
)
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Hangup
from twilio.rest import Client
from copy import deepcopy
from langgraph.types import Command, Interrupt
from dotenv import load_dotenv
import tempfile
import os
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


load_dotenv()
app = Flask(__name__)

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

call_sessions: dict[str, ConversationState] = {}


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/call', methods=['POST'])
def call():
    from_number = os.environ.get("TWILIO_PHONE_NUMBER")
    # Get the phone number from the request
    to_number = request.form.get('phone_number')

    if not to_number:
        return jsonify({"error": "Phone number is required"}), 400

    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    call = client.calls.create(
        twiml=introduction(),
        to=to_number,
        from_=from_number
    )

    # print(f"call id: {call.sid}")
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
        return convert_to_twiml(response)

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

        return convert_to_twiml(response)

    # persist for the next webhook hit
    call_sessions[call_sid] = state

    twiml_xml = state.get("twiml")
    if not twiml_xml:
        return "No TwiML generated", 500

    return convert_to_twiml(str(twiml_xml))


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
    app.run(debug=True)
