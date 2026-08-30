import os
import sys

from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
)


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"ERROR: {name} is not configured")
        sys.exit(1)
    return value


def main():
    connection_string = required("AZURE_COMMUNICATION_CONNECTION_STRING")
    source_number = required("ACS_PHONE_NUMBER")
    target_number = required("TARGET_PHONE_NUMBER")
    callback_url = required("CALLBACK_URL")

    print("=== CREATING OUTBOUND CALL ===")
    print(f"ACS source number configured: {bool(source_number)}")
    print(f"Target number configured: {bool(target_number)}")
    print(f"Callback URL: {callback_url}")

    client = CallAutomationClient.from_connection_string(
        connection_string
    )

    source = PhoneNumberIdentifier(source_number)
    target = PhoneNumberIdentifier(target_number)

    result = client.create_call(
        target_participant=target,
        source_caller_id_number=source,
        callback_url=callback_url,
    )

    print("=== CREATE CALL SUCCEEDED ===")
    print(f"Call connection ID: {result.call_connection_id}")


if __name__ == "__main__":
    main()
