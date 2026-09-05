import logging
import difflib
import time
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

from fastapi import FastAPI, Request
from azure.core.exceptions import ResourceNotFoundError

from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    RecognizeInputType,
    TextSource,
    ServerCallLocator,
    RecordingContent,
    RecordingChannel,
    RecordingFormat,
)

from openai import AzureOpenAI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pgai-voice")

app = FastAPI(title="PG-AI Voice Challenge")


ACS_CONNECTION_STRING = os.getenv(
    "AZURE_COMMUNICATION_CONNECTION_STRING"
)

OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
OPENAI_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT",
    "gpt-5-mini"
)

CALLBACK_URL = os.getenv("CALLBACK_URL")
TARGET_PHONE_NUMBER = os.getenv("TARGET_PHONE_NUMBER")

VOICE_NAME = "en-US-JennyNeural"
SPEECH_LANGUAGE = "en-US"


SYSTEM_PROMPT = """
You are a friendly medical scheduling voice assistant.

You are speaking with a patient who wants to schedule a medical appointment.

Be concise and natural.
Ask one question at a time.
Do not provide medical diagnosis or treatment advice.
"""


def get_openai_client():
    if not OPENAI_ENDPOINT or not OPENAI_API_KEY:
        return None

    return AzureOpenAI(
        api_key=OPENAI_API_KEY,
        api_version="2024-10-21",
        azure_endpoint=OPENAI_ENDPOINT,
    )


def generate_response(user_text: str) -> str:
    client = get_openai_client()

    if client is None:
        return "I'm sorry, the AI service is not configured."

    response = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
        max_completion_tokens=500,
    )

    content = response.choices[0].message.content

    if not content:
        return "I'm sorry, I didn't catch that."

    return content.strip()


PATIENT_PARTICIPANT = None
LAST_AGENT_TEXT = ""

# Per-call turn-taking state.
CALL_STATE = {}

# Evidence recording/transcript state.
EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evidence")
RECORDING_STATE = {}

def get_recording_state(call_connection_id: str):
    return RECORDING_STATE.setdefault(
        call_connection_id,
        {
            "recording_id": None,
            "transcript": [],
            "recording_started": False,
        },
    )

def add_transcript(call_connection_id: str, speaker: str, text: str):
    if not text:
        return
    state = get_recording_state(call_connection_id)
    state["transcript"].append(f"[{speaker}] {text}")
    logger.info(
        "TRANSCRIPT [%s]: %s",
        speaker,
        text,
    )

# Short guard against ACS recognizing recently played agent TTS
# as patient speech.
TTS_ECHO_GUARD_SECONDS = 1.5
TTS_CHARS_PER_SECOND = 14.0

CALL_ACTIVE = True


def get_call_state(call_connection_id: str):
    """Return mutable state for one ACS call."""
    return CALL_STATE.setdefault(
        call_connection_id,
        {
            "active": True,
            "recognition_in_progress": False,
            "last_agent_text": "",
            "last_recognized_text": "",
            "tts_guard_until": 0.0,
        },
    )


def is_echo_of_agent(text: str, state: dict) -> bool:
    """
    Detect only very strong matches to our own most recently played TTS.

    The phone participant is the remote AI scheduling agent. Its speech
    must NOT be rejected merely because it shares generic wording with
    our TTS. Therefore paraphrases are accepted.
    """

    normalized = " ".join((text or "").lower().split())
    last_agent = " ".join(
        (state.get("last_agent_text", "") or "").lower().split()
    )

    if not normalized or not last_agent:
        return False

    char_similarity = difflib.SequenceMatcher(
        None,
        normalized,
        last_agent,
    ).ratio()

    recognized_words = normalized.split()
    agent_words = last_agent.split()

    if recognized_words and agent_words:
        word_similarity = difflib.SequenceMatcher(
            None,
            recognized_words,
            agent_words,
        ).ratio()

        word_overlap = (
            len(set(recognized_words) & set(agent_words))
            / max(1, len(set(agent_words)))
        )
    else:
        word_similarity = 0.0
        word_overlap = 0.0

    logger.info(
        "Echo similarity: %.3f | word similarity: %.3f | "
        "word overlap: %.3f | recognized=%r | last_agent=%r",
        char_similarity,
        word_similarity,
        word_overlap,
        text,
        state.get("last_agent_text", ""),
    )

    # Only reject speech that is extremely close to the exact text
    # our bot most recently played.
    strong_echo = (
        char_similarity >= 0.85
        or (
            char_similarity >= 0.75
            and word_similarity >= 0.80
            and word_overlap >= 0.80
        )
    )

    if strong_echo:
        logger.info(
            "Strong match to our own TTS detected; treating as echo."
        )
        return True

    return False

def is_duplicate_recognition(text: str, state: dict) -> bool:
    """Ignore repeated recognition results within the current call turn."""

    if not text:
        return True

    normalized = " ".join(text.lower().split())
    previous = " ".join(
        (state.get("last_recognized_text", "") or "").lower().split()
    )

    if not previous:
        state["last_recognized_text"] = normalized
        return False

    similarity = difflib.SequenceMatcher(
        None,
        normalized,
        previous,
    ).ratio()

    logger.info(
        "Recognition duplicate similarity: %.3f | "
        "current=%r | previous=%r",
        similarity,
        text,
        state.get("last_recognized_text", ""),
    )

    if similarity >= 0.90:
        logger.warning(
            "=== DUPLICATE RECOGNITION: IGNORING ==="
        )
        return True

    state["last_recognized_text"] = normalized
    return False


def start_patient_recognition(call_connection, call_connection_id=None):
    """Listen specifically for the patient after agent audio finishes."""
    logger.info("=== STARTING PATIENT RECOGNITION ===")

    global PATIENT_PARTICIPANT

    if PATIENT_PARTICIPANT is None:
        logger.warning("Patient participant is not available yet.")
        return

    if call_connection_id:
        state = get_call_state(call_connection_id)

        if not state["active"]:
            logger.info("Call is no longer active; skipping recognition.")
            return

        if state["recognition_in_progress"]:
            logger.info("Recognition already in progress; skipping duplicate start.")
            return

        state["recognition_in_progress"] = True

    logger.info(
        "Recognition target: %s",
        PATIENT_PARTICIPANT
    )

    try:
        call_connection.start_recognizing_media(
            input_type=RecognizeInputType.SPEECH,
            target_participant=PATIENT_PARTICIPANT,
            speech_language=SPEECH_LANGUAGE,
            initial_silence_timeout=10,
            end_silence_timeout=2,
            operation_callback_url=CALLBACK_URL,
        )

        logger.info("=== PATIENT RECOGNITION REQUEST SENT ===")

    except Exception:
        if call_connection_id:
            state["recognition_in_progress"] = False

        logger.exception("Failed to start patient recognition.")


def play_text(call_connection, text: str, context="", call_connection_id=None):
    """Play TTS without crashing callbacks if the call has already ended."""
    global LAST_AGENT_TEXT

    if not text:
        return

    LAST_AGENT_TEXT = text

    if call_connection_id:
        state = get_call_state(call_connection_id)
        state["last_agent_text"] = text

        # Estimate the TTS playback duration. Recognition is normally
        # started after PlayCompleted, but ACS can still expose buffered
        # bot audio to the recognizer. Keep a short post-playback guard.
        estimated_duration = max(
            1.0,
            len(text) / TTS_CHARS_PER_SECOND,
        )
        state["tts_guard_until"] = (
            time.monotonic()
            + estimated_duration
            + TTS_ECHO_GUARD_SECONDS
        )

        logger.info(
            "TTS echo guard armed for approximately %.2f seconds.",
            estimated_duration + TTS_ECHO_GUARD_SECONDS,
        )

    logger.info("=== PLAYING AUDIO [%s] ===", context)

    try:
        source = TextSource(
            text=text,
            source_locale=SPEECH_LANGUAGE,
            voice_name=VOICE_NAME,
        )

        call_connection.play_media_to_all(
            source,
            interrupt_call_media_operation=False,
        )

        logger.info("=== AUDIO PLAY REQUEST SENT ===")

    except ResourceNotFoundError as exc:
        logger.warning(
            "Call is no longer available; skipping audio playback: %s",
            exc,
        )

    except Exception:
        logger.exception("Audio playback failed; continuing callback processing.")



def start_call_recording(call_connection_id: str, server_call_id: str):
    """Start a WAV recording for evidence collection."""
    try:
        client = CallAutomationClient.from_connection_string(
            ACS_CONNECTION_STRING
        )

        locator = ServerCallLocator(
            server_call_id=server_call_id
        )

        properties = client.start_recording(
            call_locator=locator,
            recording_state_callback_url=CALLBACK_URL,
            recording_content_type=RecordingContent.AUDIO,
            recording_channel_type=RecordingChannel.UNMIXED,
            recording_format_type=RecordingFormat.WAV,
        )

        state = get_recording_state(call_connection_id)
        state["recording_id"] = properties.recording_id
        state["recording_started"] = True

        logger.info(
            "=== RECORDING STARTED === recording_id=%s",
            properties.recording_id,
        )

    except Exception:
        logger.exception(
            "Failed to start call recording."
        )


def stop_call_recording(call_connection_id: str):
    """Stop the active recording."""
    state = get_recording_state(call_connection_id)
    recording_id = state.get("recording_id")

    if not recording_id:
        logger.warning(
            "No recording ID available for call %s",
            call_connection_id,
        )
        return

    try:
        client = CallAutomationClient.from_connection_string(
            ACS_CONNECTION_STRING
        )

        client.stop_recording(recording_id)

        logger.info(
            "=== RECORDING STOP REQUESTED === recording_id=%s",
            recording_id,
        )

    except Exception:
        logger.exception(
            "Failed to stop call recording."
        )


def save_transcript(call_connection_id: str):
    """Persist the conversation transcript."""
    state = get_recording_state(call_connection_id)
    lines = state.get("transcript", [])

    if not lines:
        logger.warning(
            "No transcript entries for call %s",
            call_connection_id,
        )
        return

    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    # Use a deterministic evidence folder based on call order.
    existing = sorted(
        name for name in os.listdir(EVIDENCE_DIR)
        if name.startswith("call-") and os.path.isdir(
            os.path.join(EVIDENCE_DIR, name)
        )
    )

    call_folder = None

    for name in existing:
        transcript_path = os.path.join(
            EVIDENCE_DIR,
            name,
            f"{name}-transcript.txt",
        )
        if not os.path.exists(transcript_path):
            call_folder = os.path.join(EVIDENCE_DIR, name)
            break

    if call_folder is None:
        call_folder = os.path.join(
            EVIDENCE_DIR,
            f"call-{len(existing) + 1:02d}",
        )

    os.makedirs(call_folder, exist_ok=True)

    transcript_path = os.path.join(
        call_folder,
        f"{os.path.basename(call_folder)}-transcript.txt",
    )

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(
            f"Call connection ID: {call_connection_id}\n"
        )
        f.write("=" * 70 + "\n\n")
        f.write("\n\n".join(lines))
        f.write("\n")

    logger.info(
        "=== TRANSCRIPT SAVED === %s",
        transcript_path,
    )

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "pgai-voice-challenge",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/callbacks")
async def callbacks(request: Request):

    events = await request.json()

    logger.info("=== ACS CALLBACK RECEIVED ===")
    logger.info("%s", events)

    if not isinstance(events, list):
        return {"received": True}

    for event in events:

        event_type = event.get("type")
        data = event.get("data", {})

        logger.info("Event type: %s", event_type)

        # ---------------------------------------------------------
        # CALL CONNECTED
        # ---------------------------------------------------------

        if event_type == "Microsoft.Communication.CallConnected":

            call_connection_id = data.get("callConnectionId")

            logger.info("=== CALL CONNECTED ===")
            logger.info(
                "Call connection: %s",
                call_connection_id
            )

            # Initialize isolated turn-taking state for this call.
            state = get_call_state(call_connection_id)
            state["active"] = True
            state["recognition_in_progress"] = False
            state["last_agent_text"] = ""
            state["last_recognized_text"] = ""

            # Start WAV recording for challenge evidence.
            server_call_id = data.get("serverCallId")

            get_recording_state(call_connection_id)

            if server_call_id:
                start_call_recording(
                    call_connection_id,
                    server_call_id,
                )
            else:
                logger.error(
                    "Cannot start recording: serverCallId missing."
                )

            try:
                client = CallAutomationClient.from_connection_string(
                    ACS_CONNECTION_STRING
                )

                connection = client.get_call_connection(
                    call_connection_id
                )

                # Initial greeting.
                greeting = (
                    "Hello, this is the medical scheduling assistant. "
                    "How can I help you today?"
                )

                logger.info("Playing greeting")

                play_text(
                    connection,
                    greeting,
                    call_connection_id=call_connection_id,
                )


            except Exception:
                logger.exception(
                    "Error handling CallConnected"
                )

        # ---------------------------------------------------------
        # PLAY COMPLETED
        # ---------------------------------------------------------

        elif event_type == "Microsoft.Communication.PlayCompleted":

            logger.info("=== PLAY COMPLETED ===")

            call_connection_id = data.get("callConnectionId")

            try:
                client = CallAutomationClient.from_connection_string(
                    ACS_CONNECTION_STRING
                )

                connection = client.get_call_connection(
                    call_connection_id
                )

                # Agent has finished speaking. Now listen for the patient.
                state = get_call_state(call_connection_id)

                if not state["active"]:
                    logger.info(
                        "Call is no longer active; skipping PlayCompleted recognition."
                    )
                    continue

                # The previous recognition operation has completed.
                state["recognition_in_progress"] = False

                start_patient_recognition(
                    connection,
                    call_connection_id,
                )

            except Exception:
                logger.exception(
                    "Error handling PlayCompleted"
                )

        # ---------------------------------------------------------
        # PARTICIPANTS UPDATED
        # ---------------------------------------------------------

        elif event_type == "Microsoft.Communication.ParticipantsUpdated":

            logger.info("=== PARTICIPANTS UPDATED ===")

            participants = data.get(
                "participants",
                []
            )

            for participant in participants:

                identifier = participant.get(
                    "identifier",
                    {}
                )

                logger.info(
                    "Participant kind: %s",
                    identifier.get("kind")
                )

                if identifier.get("kind") == "phoneNumber":

                    phone = identifier.get(
                        "phoneNumber",
                        {}
                    ).get("value")

                    logger.info(
                        "Phone participant: %s",
                        phone
                    )

                    global PATIENT_PARTICIPANT
                    PATIENT_PARTICIPANT = PhoneNumberIdentifier(phone)

                    logger.info(
                        "Stored patient participant for recognition: %s",
                        phone
                    )

        # ---------------------------------------------------------
        # CALL DISCONNECTED
        # ---------------------------------------------------------

        elif event_type == "Microsoft.Communication.CallDisconnected":

            call_connection_id = data.get("callConnectionId")

            state = get_call_state(call_connection_id)
            state["active"] = False
            state["recognition_in_progress"] = False

            logger.info("=== CALL DISCONNECTED ===")
            logger.info(
                "Call connection: %s",
                call_connection_id
            )

            result = data.get(
                "resultInformation",
                {}
            )

            logger.info(
                "Result information: %s",
                result
            )

        # ---------------------------------------------------------
        # RECOGNIZE COMPLETED
        # ---------------------------------------------------------

        elif event_type == "Microsoft.Communication.RecognizeCompleted":

            logger.info("=== RECOGNIZE COMPLETED ===")
            logger.info("Recognize data: %s", data)

            call_connection_id = data.get("callConnectionId")
            state = get_call_state(call_connection_id)

            # This recognition operation has finished.
            state["recognition_in_progress"] = False

            # Never process speech from a call that has already ended.
            if not state["active"]:
                logger.info(
                    "Call is no longer active; ignoring recognition."
                )
                continue

            # ACS places recognized speech in speechResult.
            speech_result = data.get("speechResult", {})
            recognized_text = speech_result.get("speech", "")

            if not recognized_text:
                logger.warning("No speech text recognized")
                continue

            logger.info(
                "Patient/agent speech recognized: %s",
                recognized_text
            )

            # ACS can occasionally return buffered agent TTS as
            # recognized patient speech. Since recognition is intended
            # only for the patient after agent playback, suppress
            # recognition while the playback guard is active.
            tts_guard_until = state.get("tts_guard_until", 0.0)

            if time.monotonic() < tts_guard_until:
                remaining = tts_guard_until - time.monotonic()
                logger.warning(
                    "=== TTS PLAYBACK GUARD: IGNORING RECOGNITION "
                    "(%.2fs REMAINING) ===",
                    remaining,
                )
                continue

            # Ignore the bot hearing its own TTS.
            if is_echo_of_agent(recognized_text, state):
                logger.warning(
                    "=== ECHO DETECTED: IGNORING BOT'S OWN AUDIO ==="
                )
                logger.info(
                    "=== RESTARTING PATIENT RECOGNITION AFTER ECHO ==="
                )
                try:
                    client = CallAutomationClient.from_connection_string(
                        ACS_CONNECTION_STRING
                    )
                    connection = client.get_call_connection(
                        call_connection_id
                    )
                    start_patient_recognition(
                        connection,
                        call_connection_id=call_connection_id,
                    )
                except ResourceNotFoundError as exc:
                    logger.info("Call ended while restarting recognition: %s", exc)
                except Exception:
                    logger.exception("Failed to restart recognition after echo")
                continue

            # Ignore duplicate recognition callbacks.
            if is_duplicate_recognition(recognized_text, state):
                continue

            try:
                client = CallAutomationClient.from_connection_string(
                    ACS_CONNECTION_STRING
                )

                connection = client.get_call_connection(
                    call_connection_id
                )

                # The call may have ended between the callback and this
                # operation, so verify state again before generating audio.
                if not state["active"]:
                    logger.info(
                        "Call ended before response generation; skipping."
                    )
                    continue

                response_text = generate_response(recognized_text)

                logger.info(
                    "Generated patient response: %s",
                    response_text
                )

                play_text(
                    connection,
                    response_text,
                    call_connection_id=call_connection_id,
                )

            except ResourceNotFoundError as exc:
                logger.info(
                    "Call ended before response playback: %s",
                    exc
                )

            except Exception:
                logger.exception(
                    "Error handling RecognizeCompleted"
                )

        elif event_type == "Microsoft.Communication.RecognizeFailed":

            logger.error(
                "=== RECOGNIZE FAILED ==="
            )

            logger.error(
                "Recognize data: %s",
                data
            )

    return {"received": True}
