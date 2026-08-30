import logging
import os

from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pgai-voice")

app = FastAPI(title="PG-AI Voice Challenge")


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

    if isinstance(events, list):
        for event in events:
            event_type = event.get("type")
            logger.info("Event type: %s", event_type)

            if event_type == "Microsoft.Communication.CreateCallFailed":
                data = event.get("data", {})
                result = data.get("resultInformation", {})

                logger.error("=== CREATE CALL FAILED ===")
                logger.error("Code: %s", result.get("code"))
                logger.error("SubCode: %s", result.get("subCode"))
                logger.error("Message: %s", result.get("message"))

            elif event_type == "Microsoft.Communication.CallDisconnected":
                data = event.get("data", {})
                result = data.get("resultInformation", {})

                logger.info("=== CALL DISCONNECTED ===")
                logger.info("Call connection: %s", data.get("callConnectionId"))
                logger.info("Result information: %s", result)

            elif event_type == "Microsoft.Communication.CallConnected":
                data = event.get("data", {})
                logger.info("=== CALL CONNECTED ===")
                logger.info("Call connection: %s", data.get("callConnectionId"))

    return {"received": True}
