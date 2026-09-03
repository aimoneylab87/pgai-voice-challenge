# Architecture

## System Overview

The application uses Azure Communication Services for telephone connectivity, Azure Speech for speech recognition and text-to-speech, FastAPI for event callbacks, and Azure OpenAI for conversational responses.

## Flow

```text
Patient
  |
  v
Azure Communication Services
  |
  v
FastAPI Callback Server
  |
  v
Azure Speech Recognition
  |
  v
Python Conversation Logic
  |
  v
Azure OpenAI / GPT-5-mini
  |
  v
Text-to-Speech
  |
  v
Azure Communication Services
  |
  v
Patient
```

## Components

### Azure Communication Services
Handles the outbound telephone call and call-control events.

### FastAPI
Receives ACS callbacks and coordinates call state, speech recognition, playback, and conversation processing.

### Azure Speech
Provides speech recognition and text-to-speech capabilities.

### Azure OpenAI
Generates the conversational response using the GPT-5-mini deployment.

### Python Application
Maintains call state, tracks recognition and playback, detects duplicate recognition, and filters likely bot-audio echoes.

## Reliability

The application protects against disconnected calls, duplicate recognition, recognition overlap, and recognition of the assistant's own audio.

## Security

Credentials are supplied through environment variables and are excluded from source control. The public repository contains only configuration examples, not production secrets.
