import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔐 Haal tokens op uit environment variables
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")

# 🔍 Check of de tokens bestaan, anders log dit
if not APIFY_TOKEN or not ACTOR_ID:
    print("❌ Environment variables niet ingesteld:")
    print(f"APIFY_API_TOKEN: {APIFY_TOKEN}")
    print(f"APIFY_ACTOR_ID: {ACTOR_ID}")

@app.route('/')
def home():
    return "✅ Scraper draait! POST naar /webhook om data te scrapen."

@app.route('/webhook', methods=['POST'])
def run_scraper():
    data = request.get_json()

    if not data or "steden" not in data:
        return jsonify({
            "error": "❌ Geen steden opgegeven. Stuur een JSON-body met 'steden': ['...']"
        }), 400

    steden = data["steden"]
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

        print(f"▶️ Scraper starten voor: {stad}")
        print(f"📦 Payload: {payload}")

        try:
            response = requests.post(
                f"https://api.apify.com/v2/actor-tasks/{ACTOR_ID}/runs?token={APIFY_TOKEN}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            print(f"❌ Fout bij verzoek naar Apify voor {stad}: {str(e)}")
            return jsonify({"error": f"Scraper request error voor {stad}: {str(e)}"}), 500

        print(f"📬 Status code: {response.status_code}")
        print(f"📨 Response content: {response.text}")

        if response.status_code == 201:
            run_info = response.json()
            all_runs.append({stad: run_info})
            print(f"✅ Scraper succesvol gestart voor: {stad}")
        else:
            print(f"❌ Scraper mislukt voor {stad} met status {response.status_code}")
            return jsonify({
                "error": f"Scraper mislukt voor {stad}",
                "details": response.text
            }), 500

    return jsonify({
        "status": "✅ Scraper gestart voor alle steden",
        "runs": all_runs
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

