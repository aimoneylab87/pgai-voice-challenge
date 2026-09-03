# Bug Report

## Bug: Assistant Audio Recognized as Patient Speech

### Description

During early voice testing, Azure Speech recognition sometimes captured the AI assistant's own text-to-speech output as if it were patient speech.

### Impact

The problem could cause the assistant to respond to itself and create a conversational feedback loop.

### Observed Behavior

```text
Assistant speaks
      |
      v
Speech recognition captures assistant audio
      |
      v
Conversation logic processes the text
      |
      v
Assistant generates another response
```

### Root Cause

The speech-recognition pipeline could receive audio containing the assistant's own playback. An immediate-last-utterance comparison was not sufficient for every observed case because recognized bot audio was not always identical to the immediately preceding stored phrase.

### Fixes Implemented

- Bot-audio echo detection
- Character similarity comparison
- Word similarity comparison
- Shared-phrase detection
- Duplicate-recognition protection
- Recognition-in-progress protection
- Call-active state checks

### Validation

Testing demonstrated cases where assistant-generated speech was recognized and subsequently rejected by echo detection.

### Remaining Risk

Echo detection is heuristic. Real patient speech that closely resembles the assistant response could potentially be rejected. Additional testing with interruptions and natural patient responses is recommended.

## Other Tested Conditions

- Call connection
- Participant identification
- Text-to-speech playback
- Speech recognition
- GPT response generation
- Call disconnection
