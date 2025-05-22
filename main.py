import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# 🔐 Gevoelige gegevens via omgevingsvariabelen
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")
SECRET_API_KEY = os.getenv("MY_SECRET_API_KEY")  # Verwachte waarde: 'Maluku123'

@app.route("/")
def home():
    return "✅ Scraper draait. POST naar /webhook om flipwoningen op te halen."

@app.route("/webhook", methods=["POST"])
def run_scraper():
    client_key = request.headers.get("x-api-key")
    if client_key != SECRET_API_KEY:
        return jsonify({"error": "⛔️ Ongeldige API key"}), 403

    data = request.get_json()
    if not data or "steden" not in data:
        return jsonify({"error": "❌ Geen steden opgegeven. Gebruik JSON-body met 'steden': ['...']."}), 400

    steden = data["steden"]
    if not isinstance(steden, list) or not all(isinstance(s, str) for s in steden):
        return jsonify({"error": "Steden moeten een lijst van strings zijn."}), 400

    vandaag = datetime.now().strftime("%Y-%m-%d")
    all_results = []

    for stad in steden:
        payload = {
            "city": stad,
            "radiusKm": 5,
            "maxConcurrency": 5,
            "minConcurrency": 1,
            "maxRequestRetries": 3,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        print("Payload:", payload)

        response = requests.post(
            f"https://api.apify.com/v2/actor-tasks/{ACTOR_ID}/runs?token={APIFY_TOKEN}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 201:
            print(f"Scraper mislukt voor {stad}:", response.text)
            return jsonify({"error": f"Scraper mislukt voor {stad}", "details": response.text}), 500

        run_info = response.json()
        all_results.append({"stad": stad, "run": run_info})

    return jsonify({"status": "✅ Flip-scraper gestart", "runs": all_results}), 200

# 📊 (optioneel) Functie om filterregels toe te passen op woningdata

def is_potentiele_flipwoning(woning):
    vandaag = datetime.now().strftime("%Y-%m-%d")
    return (
        woning.get("listed_date") == vandaag and
        woning.get("price", 0) <= 2_000_000 and
        woning.get("type") in ["Woonhuis", "Appartement"]
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
