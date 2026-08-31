from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "pgai-voice-challenge"})

@app.route("/api/callbacks", methods=["POST"])
def callbacks():
    event = request.get_json(silent=True)

    print("\n=== ACS CALLBACK ===")
    print(event)

    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    print("=== PAI VOICE CALLBACK SERVER ===")
    print("Listening on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000)
