import os
import sys

from dotenv import load_dotenv

load_dotenv(".env", override=True)

from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
)


def main():
    connection_string = os.getenv("AZURE_COMMUNICATION_CONNECTION_STRING")
    source_number = os.getenv("ACS_PHONE_NUMBER")
    target_number = os.getenv("TARGET_PHONE_NUMBER")
    callback_url = os.getenv("CALLBACK_URL")
    cognitive_endpoint = os.getenv("COGNITIVE_SERVICES_ENDPOINT")

    if not connection_string:
        print("ERROR: AZURE_COMMUNICATION_CONNECTION_STRING is not configured")
        sys.exit(1)

    if not source_number:
        print("ERROR: ACS_PHONE_NUMBER is not configured")
        sys.exit(1)

    if not target_number:
        print("ERROR: TARGET_PHONE_NUMBER is not configured")
        sys.exit(1)

    if not callback_url:
        print("ERROR: CALLBACK_URL is not configured")
        sys.exit(1)

    if not cognitive_endpoint:
        print("ERROR: COGNITIVE_SERVICES_ENDPOINT is not configured")
        sys.exit(1)

    print("=== CREATING OUTBOUND CALL ===")
    print(f"ACS source number configured: {bool(source_number)}")
    print(f"Target number configured: {bool(target_number)}")
    print(f"Callback URL: {callback_url}")
    print(f"Cognitive Services endpoint configured: {bool(cognitive_endpoint)}")

    client = CallAutomationClient.from_connection_string(
        connection_string
    )

    source_participant = PhoneNumberIdentifier(source_number)
    target_participant = PhoneNumberIdentifier(target_number)

    result = client.create_call(
        target_participant=target_participant,
        callback_url=callback_url,
        source_caller_id_number=source_participant,
        cognitive_services_endpoint=cognitive_endpoint,
    )

    print("=== CREATE CALL SUCCEEDED ===")
    print(f"Call connection ID: {result.call_connection_id}")


if __name__ == "__main__":
    main()
