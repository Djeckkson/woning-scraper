import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔐 Jouw Apify API-token (niet delen met anderen!)
APIFY_TOKEN = "apify_api_g9OHpMqQfiMJZaRlPRR8Scrs8VvCZ3EJEkLC"

# 🏙️ Steden die je wilt scrapen
STEDEN = ["Amsterdam", "Deventer", "Rotterdam", "Utrecht"]

# 🔧 Funda Actor ID (voor de gekozen scraper)
ACTOR_ID = "memo23/apify-funda-cheerio-kvstore"

@app.route('/')
def home():
    return "✅ Scraper draait! POST naar /webhook om data toe te voegen."

@app.route('/webhook', methods=['POST'])
def run_scraper():
    all_runs = []

    for stad in STEDEN:
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
