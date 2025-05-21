import os
import requests
import json
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Tokens via environment
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")

@app.route('/')
def home():
    return "✅ Scraper draait! POST naar /webhook om data te scrapen."

@app.route('/webhook', methods=['POST'])
def run_scraper():
    data = request.get_json()

    if not data or "steden" not in data:
        return jsonify({"error": "❌ Geen steden opgegeven. Stuur een JSON-body met 'steden': ['...']."}), 400

    steden = data["steden"]
    all_runs = []

    for stad in steden:
        payload = {
            "city": stad,
            "maxConcurrency": 10,
            "minConcurrency": 5,
            "maxRequestRetries": 5,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        response = requests.post(
            f"https://api.apify.com/v2/actor-tasks/{ACTOR_ID}/runs?token={APIFY_TOKEN}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 201:
            run_info = response.json()
            all_runs.append({stad: run_info})

            # 📝 Resultaat lokaal opslaan
            os.makedirs("data", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"data/scraper_{stad}_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump(run_info, f, indent=2)

            print(f"✅ Data opgeslagen voor {stad} in {filename}")
        else:
            print(f"❌ Scraper mislukt voor {stad}")
            return jsonify({
                "error": f"Scraper mislukt voor {stad}",
                "details": response.text
            }), 500

    return jsonify({"status": "✅ Scraper gestart voor alle steden", "runs": all_runs}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
