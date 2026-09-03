# PGAI Voice Challenge — Call Test Scenarios

## Scenario 01 — Basic Greeting
- Objective: Verify the bot answers an outbound call and provides its initial greeting.
- Expected: Call connects and bot speaks the opening prompt.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 02 — Patient Name Recognition
- Objective: Verify the bot recognizes a spoken patient name.
- Expected: Bot correctly captures the caller's spoken name.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 03 — Normal Question and Answer
- Objective: Verify the bot recognizes a normal spoken response and generates an appropriate response.
- Expected: Speech is recognized and the bot responds.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 04 — Follow-Up Question
- Objective: Verify conversational turn-taking across multiple exchanges.
- Expected: Bot continues the conversation without prematurely ending recognition.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 05 — Silence / No Speech
- Objective: Verify behavior when the caller does not respond.
- Expected: Bot handles silence without crashing or entering an infinite loop.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 06 — Short Spoken Response
- Objective: Verify recognition of a short response such as yes or no.
- Expected: Bot recognizes and processes the short response.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 07 — Longer Spoken Response
- Objective: Verify recognition of a longer natural-language response.
- Expected: Complete speech result is processed correctly.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 08 — Echo / Playback Handling
- Objective: Verify the bot does not interpret its own playback as caller speech.
- Expected: Playback completes and recognition resumes without a turn-taking loop.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 09 — Multiple Conversation Turns
- Objective: Verify several consecutive speech and playback cycles.
- Expected: Recognition and playback alternate correctly for multiple turns.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 10 — Call Disconnect
- Objective: Verify clean handling when the caller disconnects.
- Expected: CallDisconnected is handled without an application crash.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 11 — Recognition Completion
- Objective: Verify ACS RecognizeCompleted events are processed correctly.
- Expected: speechResult is extracted and passed into the conversation flow.
- Result: TBD
- Evidence: TBD
- Status: PENDING

## Scenario 12 — Error Handling
- Objective: Verify application behavior when an ACS operation encounters an error.
- Expected: Error is logged and handled without crashing the server.
- Result: TBD
- Evidence: TBD
- Status: PENDING
