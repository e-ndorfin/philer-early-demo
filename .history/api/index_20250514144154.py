from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/')
def home():
    return 'Hello, World!'


@app.route('/about')
def about():
    return 'About'


@app.route('/api/data', methods=['POST'])
def process_data():
    if request.is_json:
        data = request.get_json()
        # Process the received data
        response = {
            "message": "Data received successfully",
            "received_data": data
        }
        return jsonify(response), 200
    else:
        return jsonify({"error": "Request must be JSON"}), 400
