import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 👈 Belangrijk om CORS-fouten te vermijden bij frontend requests

# 🔐 Omgevingsvariabelen
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")
SECRET_API_KEY = os.getenv("MY_SECRET_API_KEY")  # voorbeeld: 'Maluku123'

@app.route("/")
def home():
    return "✅ Scraper draait. POST naar /webhook om data te scrapen."

@app.route("/webhook", methods=["POST"])
def run_scraper():
    # ✅ Beveiliging
    client_key = request.headers.get("x-api-key")
    if client_key != SECRET_API_KEY:
        return jsonify({"error": "⛔️ Ongeldige API key"}), 403

    data = request.get_json()

    # ✅ Validatie: check of JSON correct is
    if not data or "steden" not in data:
        return jsonify({"error": "❌ Geen steden opgegeven. Gebruik JSON-body met 'steden': ['...']."}), 400

    steden = data["steden"]

    # ✅ Extra validatie: steden moet een lijst van strings zijn
    if not isinstance(steden, list) or not all(isinstance(s, str) for s in steden):
        return jsonify({"error": "❌ 'steden' moet een lijst van strings zijn."}), 400

    all_runs = []

    for stad in steden:
        payload = {
            "city": stad,
            "maxConcurrency": 5,
            "minConcurrency": 1,
            "maxRequestRetries": 5,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        print("▶️ Payload:", payload)  # 👈 Debug output om te zien wat er wordt gestuurd

        response = requests.post(
            f"https://api.apify.com/v2/actor-tasks/{ACTOR_ID}/runs?token={APIFY_TOKEN}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 201:
            run_info = response.json()
            all_runs.append({stad: run_info})
            print(f"✅ Scraper gestart voor: {stad}")
        else:
            print(f"❌ Scraper mislukt voor: {stad}")
            print(response.text)
            return jsonify({
                "error": f"Scraper mislukt voor {stad}",
                "details": response.text
            }), 500

    return jsonify({"status": "✅ Scraper gestart voor alle steden", "runs": all_runs}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
