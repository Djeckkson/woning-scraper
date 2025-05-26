from flask import Flask, request, jsonify
import requests
import time
import os

app = Flask(__name__)

# Apify configuratie
APIFY_TOKEN = "apify_api_g9OHpMqOfiMJZaRIPRR0Scrs8VvCZ3EJekLC"
ACTOR_ID = "djeckxson~funda-task"
BASE_URL = "https://api.apify.com/v2/actor-tasks"

@app.route('/')
def home():
    return "✅ De woning scraper is live!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
    results = []

    print(f"🚀 Webhook ontvangen voor steden: {steden}")

    for stad in steden:
        print(f"📦 Start scraping voor: {stad}")

        # Start de Apify actor taak
        run_url = f"{BASE_URL}/{ACTOR_ID}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
        payload = {
            "zoekterm": stad
        }

        response = requests.post(run_url, json=payload)
        if response.status_code != 200:
            print(f"❌ Error bij ophalen van {stad}: {response.text}")
            results.append({"stad": stad, "totaal": 0})
            continue

        woningen = response.json()
        print(f"✅ Ontvangen woningen voor {stad}: {len(woningen)} items")

        results.append({
            "stad": stad,
            "totaal": len(woningen),
            "woningen": woningen
        })

    return jsonify({
        "status": "✅ Flip-woningen succesvol verwerkt",
        "runs": results,
        "totaal": sum(r["totaal"] for r in results)
    })

if __name__ == '__main__':
    app.run(debug=True)
