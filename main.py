from flask import Flask, request, jsonify
import requests
import time
from datetime import date, timedelta

app = Flask(__name__)

APIFY_TOKEN = "apify_api_gg0HpMq0fiMJZaRIPRR0Scrs8VzCZe3JEkLC"
ACTOR_ID = "memo23~apify-funda-cheerio-kvstore"

def run_apify_actor(stad):
    print(f"📡 Start Apify actor voor stad: {stad}")

    today = date.today()
    three_days_ago = today - timedelta(days=3)

    payload = {
        "memory": 2048,
        "timeoutSecs": 3600,
        "build": "latest",
        "input": {
            "city": stad,
            "maxPrice": 300000,
            "maxResults": 100,
            "minPublishDate": three_days_ago.isoformat(),
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"],
            "radiusKm": 10,
            "maxConcurrency": 10,
            "minConcurrency": 1,
            "maxRequestRetries": 100,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": APIFY_TOKEN
    }

    res = requests.post(f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs", json=payload, headers=headers)
    if res.status_code != 201:
        print(f"❌ Kon actor niet starten. Status: {res.status_code}")
        print(f"Response: {res.text}")
        return "Mislukt", []

    run_id = res.json()["data"]["id"]
    print(f"▶️ Actor gestart met ID: {run_id}")

    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(5)
        status_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}", headers=headers)
        status_res.raise_for_status()
        status = status_res.json()["data"]["status"]
        print(f"⌛ Status: {status}")

    if status != "SUCCEEDED":
        print(f"❌ Run mislukt met status: {status}")
        return "Mislukt", []

    dataset_id = status_res.json()["data"]["defaultDatasetId"]
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json"
    items_res = requests.get(items_url, headers=headers)
    items = items_res.json()
    print(f"✅ {len(items)} woningen opgehaald uit {stad}")
    return "Gelukt", items

@app.route("/")
def index():
    return "🏠 Scraper draait ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
    if not steden or not isinstance(steden, list):
        return jsonify({"error": "Gebruik JSON met 'steden': [..]"}), 400

    runs = []
    totaal = 0

    for stad in steden:
        status, woningen = run_apify_actor(stad)
        runs.append({
            "stad": stad,
            "status": status,
            "totaal": len(woningen),
            "woningen": woningen
        })
        totaal += len(woningen)

    return jsonify({
        "status": "Woningen succesvol opgehaald",
        "totaal": totaal,
        "runs": runs
    })

if __name__ == "__main__":
    app.run(debug=True, port=10000, host="0.0.0.0")
