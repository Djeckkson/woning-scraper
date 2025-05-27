from flask import Flask, request, jsonify
import requests
import time
import json
from supabase import create_client
import os

# Config laden
with open("config.json") as f:
    config = json.load(f)

SUPABASE_URL = config["supabase_url"]
SUPABASE_KEY = config["supabase_key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN") or "apify_api_gg0HpMq0fiMJZaRIPRR0Scrs8VzCZe3JEkLC"
ACTOR_ID = "memo23~apify-funda-cheerio-kvstore"

app = Flask(__name__)

def run_apify_actor(stad):
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}"
    payload = {
        "token": APIFY_TOKEN,
        "memory": 1024,
        "timeoutSecs": 300,
        "build": "latest",
        "input": {
            "city": stad,
            "maxPrice": 1000000,
            "maxResults": 100,
            "minPublishDate": "2025-05-20",
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"],
            "radiusKm": 10
        }
    }
    res = requests.post(url, json=payload)
    res.raise_for_status()
    run_id = res.json()["data"]["id"]

    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(5)
        check_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}")
        check_res.raise_for_status()
        status = check_res.json()["data"]["status"]

    if status != "SUCCEEDED":
        return "Mislukt", []

    dataset_id = check_res.json()["data"]["defaultDatasetId"]
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}&format=json"
    items_res = requests.get(items_url)
    items = items_res.json()
    return "Gelukt", items

@app.route("/")
def index():
    return "🏠 Scraper draait"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
    runs = []
    totaal = 0

    for stad in steden:
        status, woningen = run_apify_actor(stad)
        if status == "Gelukt" and woningen:
            for woning in woningen:
                woning["stad"] = stad
                supabase.table("woningen").insert(woning).execute()
        runs.append({
            "stad": stad,
            "status": status,
            "totaal": len(woningen),
            "woningen": woningen
        })
        totaal += len(woningen)

    return jsonify({
        "status": "Woningen verwerkt",
        "totaal": totaal,
        "runs": runs
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=True, host="0.0.0.0", port=port)
