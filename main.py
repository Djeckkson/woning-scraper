import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ Lees tokens uit de Environment Variables van Render
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")

@app.route('/')
def home():
    return "✅ Scraper draait! POST naar /webhook om data toe te voegen."

@app.route('/webhook', methods=['POST'])
def run_scraper():
    data = request.get_json()
    steden = data.get("steden", [])
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

        print(f"▶️ Start scraping voor: {stad}")

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
            print(f"❌ Fout bij starten scraper voor: {stad}")
            print(response.text)
            return jsonify({"error": f"Scraper mislukt voor {stad}"}), 500

    return jsonify({"status": "✅ Scraper gestart voor alle steden", "runs": all_runs}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
