from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

APIFY_TOKEN = "apify_api_gg0HpMq0fiMJZaRIPRR0Scrs8VzCZe3JEkLC"
ACTOR_ID = "memo23~apify-funda-cheerio-kvstore"

def run_apify_actor(stad):
    print(f"▶️ Start scraping voor stad: {stad}")

    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}"

    payload = {
        "token": APIFY_TOKEN,
        "memory": 1024,
        "timeoutSecs": 300,
        "build": "latest",
        "input": {
            "city": stad,
            "maxPrice": 1000000,
            "maxResults": 50,
            "minPublishDate": "2025-05-20",
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"],
            "radiusKm": 10
        }
    }

    res = requests.post(url, json=payload)
    res.raise_for_status()
    run_id = res.json()["data"]["id"]

    # Wachten tot scraper klaar is
    while True:
        status_check = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}")
        status_check.raise_for_status()
        data = status_check.json()["data"]
        if data["status"] not in ["RUNNING", "READY"]:
            break
        time.sleep(5)

    if data["status"] != "SUCCEEDED":
        return "Mislukt", []

    dataset_id = data["defaultDatasetId"]
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}&format=json"
    items = requests.get(dataset_url).json()
    return "Gelukt", items

@app.route("/")
def index():
    return "✅ Woning scraper draait"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
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
        "status": "Woningen opgehaald",
        "totaal": totaal,
        "runs": runs
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
