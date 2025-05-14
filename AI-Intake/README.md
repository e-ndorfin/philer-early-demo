# AI-Intake

## Setup and Installation

### 1. Install Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

### 2. Start the Flask Server

Run the Flask server in one terminal:

```bash
python app.py
```

### 2.5 Install ngrok 

Follow instructions on [ngrok](https://dashboard.ngrok.com/get-started/setup/macos)

### 3. Expose Local Server with ngrok

In a separate terminal, start ngrok to expose your local server:

```bash
# Explicit port number (might have to edit port number in Flask if you are doing this manually)
ngrok http 5000

# Or use same port as .env, which Flask uses too
source .env && ngrok http $PORT
```

Where `$PORT` is the port specified in your `.env` file.

### 4. Run the Application

In a third terminal, with the virtual environment activated, run below to make phone call:

```bash
python main.py
```