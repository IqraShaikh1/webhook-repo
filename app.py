from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os

# -----------------------------------
# Load environment variables
# -----------------------------------
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise Exception("❌ MONGO_URI not found in .env file")

# -----------------------------------
# MongoDB Connection
# -----------------------------------
client = MongoClient(MONGO_URI)
db = client.github_events
collection = db.events

print("✅ Connected to MongoDB Atlas")
print("📦 Databases:", client.list_database_names())

# -----------------------------------
# Flask App
# -----------------------------------
app = Flask(__name__)

# -----------------------------------
# Home Route
# -----------------------------------
@app.route("/")
def home():
    return "GitHub Webhook Receiver is running"

# -----------------------------------
# Debug Route (MongoDB Check)
# -----------------------------------
@app.route("/check")
def check():
    docs = list(collection.find({}, {"_id": 0}))
    return jsonify({
        "count": len(docs),
        "data": docs
    })

# -----------------------------------
# UI Route
# -----------------------------------
@app.route("/ui")
def ui():
    return render_template("index.html")

# -----------------------------------
# Webhook Receiver
# -----------------------------------
@app.route("/webhook", methods=["POST"])
def github_webhook():
    payload = request.json
    event_type = request.headers.get("X-GitHub-Event")

    # ✅ GitHub ping event (MANDATORY)
    if event_type == "ping":
        print("✅ GitHub webhook ping received")
        return jsonify({"msg": "pong"}), 200

    if event_type == "push":
        handle_push(payload)

    elif event_type == "pull_request":
        handle_pull_request(payload)

    return jsonify({"status": "event processed"}), 200


# -----------------------------------
# Handle PUSH Event
# -----------------------------------
def handle_push(payload):
    author = payload["pusher"]["name"]
    to_branch = payload["ref"].split("/")[-1]
    request_id = payload["after"]

    collection.insert_one({
        "request_id": request_id,
        "author": author,
        "action": "PUSH",
        "from_branch": None,
        "to_branch": to_branch,
        "timestamp": datetime.utcnow()
    })

    print(f"📌 PUSH stored | Author: {author} | Branch: {to_branch}")

# -----------------------------------
# Handle PULL REQUEST & MERGE Event
# -----------------------------------
def handle_pull_request(payload):
    pr = payload["pull_request"]

    author = pr["user"]["login"]
    from_branch = pr["head"]["ref"]
    to_branch = pr["base"]["ref"]
    request_id = pr["id"]

    # Store Pull Request
    collection.insert_one({
        "request_id": request_id,
        "author": author,
        "action": "PULL_REQUEST",
        "from_branch": from_branch,
        "to_branch": to_branch,
        "timestamp": datetime.utcnow()
    })

    print(f"📌 PULL REQUEST stored | Author: {author}")

    # Store Merge (Bonus)
    if pr["merged"]:
        collection.insert_one({
            "request_id": request_id,
            "author": author,
            "action": "MERGE",
            "from_branch": from_branch,
            "to_branch": to_branch,
            "timestamp": datetime.utcnow()
        })

        print(f"🏆 MERGE stored | Author: {author}")

# -----------------------------------
# API for UI Polling (15 sec)
# -----------------------------------
@app.route("/events", methods=["GET"])
def get_events():
    events = list(
        collection.find({}, {"_id": 0}).sort("timestamp", -1)
    )
    return jsonify(events)

# -----------------------------------
# Run App
# -----------------------------------
if __name__ == "__main__":
    app.run(debug=True)
