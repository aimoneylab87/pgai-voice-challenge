# PG-AI Voice Challenge

AI-powered healthcare voice bot built with Python, Azure Communication Services, Azure Speech, and Azure OpenAI.

## Overview

This project demonstrates an automated telephone conversation between a patient and an AI voice assistant.

Supported scenarios include appointment scheduling, rescheduling, cancellation, medication refills, office hours, location, insurance, ambiguous requests, multi-step conversations, interruptions, turn-taking, and bot-audio echo detection.

## Architecture

Patient -> Azure Communication Services -> Speech Recognition -> FastAPI Callback Server -> Python Conversation Logic -> Azure OpenAI -> Text-to-Speech -> Azure Communication Services -> Patient

## Technologies

- Python 3.12
- FastAPI
- Uvicorn
- Azure Communication Services
- Azure Speech
- Azure OpenAI
- GPT-5-mini
- ngrok
- Git/GitHub

## Installation

```bash
git clone https://github.com/aimoneylab87/pgai-voice-challenge.git
cd pgai-voice-challenge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy .env.example to .env and configure the required Azure values. Never commit .env or credentials.

## Run

Start the callback server with:

```bash
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
```

Start ngrok in another terminal:

```bash
ngrok http 8000
```

Start the outbound call:

```bash
python src/outbound_call.py
```

## Reliability Controls

- Call-active state tracking
- Recognition-in-progress protection
- Patient participant targeting
- Duplicate recognition detection
- Bot-audio echo detection
- Playback exception handling
- Disconnected-call protection

## Known Bug

Early testing showed that Azure Speech could recognize the assistant's own TTS audio as patient speech, creating a feedback loop. Echo detection and duplicate-recognition protection were added to reduce this failure mode.

## Testing

Testing covered call connection, participant identification, TTS playback, speech recognition, GPT responses, turn taking, duplicate recognition, bot-audio echo, and call disconnection.

## Security

Secrets are stored through environment variables and excluded from Git. Any credential exposed during development should be rotated before public submission.

## Project Structure

```text
pgai-voice-challenge/
├── src/
│   ├── __init__.py
│   ├── app.py
│   └── outbound_call.py
├── .env.example
├── .gitignore
├── requirements.txt
├── ARCHITECTURE.md
├── BUG_REPORT.md
└── README.md
```

## Challenge Evidence

- Public GitHub repository
- Architecture documentation
- Bug report
- 10+ real test calls
- Recordings and transcripts
- Scenario coverage
- Project walkthrough video
- AI debugging screen recording

## Author

PG-AI Voice Challenge project by Ajibola.
