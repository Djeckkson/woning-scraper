import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔐 Haal tokens op uit environment variables
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
TASK_ID = "djeckkson/funda-task"  # Jouw task-ID

@app.route('/')
def home():
    return "✅ Scraper draait! POST naar /webhook met stedenlijst om te starten."

@app.route('/webhook', methods=['POST'])
def run_scraper():
    data = request.get_json()

    if not data or "steden" not in data:
        return jsonify({"error": "❌ Geen steden opgegeven. Stuur JSON zoals {'steden': ['Amsterdam', 'Utrecht']}"}), 400

    steden = data["steden"]
    all_runs = []

    for stad in steden:
        payload = {
            "city": stad,
            "maxConcurrency": 10,
            "minConcurrency": 5,
            "maxRequestRetries": 10,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        print(f"▶️ Start scraping voor: {stad}")

        response = requests.post(
            f"https://api.apify.com/v2/actor-tasks/{TASK_ID}/runs?token={APIFY_TOKEN}",
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

    return jsonify({
        "status": "✅ Scraper gestart voor alle steden",
        "runs": all_runs
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
