import os
import json
import time
import requests
from flask import Flask, request, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# Haal Supabase gegevens uit environment variables (zorg dat ze in Render ingesteld staan)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Apify API gegevens uit environment variables
APIFY_ACTOR_ID = os.environ.get("APIFY_ACTOR_ID")
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN")

def run_apify_actor(city):
    url = f"https://api.apify.com/v2/actor-tasks/{APIFY_ACTOR_ID}/runs?token={APIFY_API_TOKEN}"
    payload = {
        "city": city,
        "maxPrice": 1000000,       # Pas dit eventueel aan naar wens
        "maxResults": 100,
        "minPublishDate": "2025-01-01",
        "offerTypes": ["Koop"],
        "propertyTypes": ["Woonhuis", "Appartement"],
        "radiusKm": 10
    }
    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()
    run_id = res.json()["data"]["id"]

    # Wacht tot run klaar is
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(3)
        check_url = f"https://api.apify.com/v2/actor-task-runs/{run_id}?token={APIFY_API_TOKEN}"
        check_res = requests.get(check_url)
        check_res.raise_for_status()
        status = check_res.json()["data"]["status"]

    # Resultaat ophalen
    dataset_url = f"https://api.apify.com/v2/datasets/{run_id}/items?token={APIFY_API_TOKEN}&format=json"
    dataset_res = requests.get(dataset_url)
    dataset_res.raise_for_status()
    woningen = dataset_res.json()
    return status, woningen

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
    runs = []
    totaal = 0

    for stad in steden:
        try:
            status, woningen = run_apify_actor(stad)
        except Exception as e:
            return jsonify({
                "status": "Fout bij ophalen woningen",
                "error": str(e)
            }), 500

        # Insert woningen in Supabase (controleer je tabelnaam en structuur)
        for woning in woningen:
            supabase.table("woningen").insert(woning).execute()

        runs.append({
            "stad": stad,
            "status": status,
            "totaal": len(woningen),
            "woningen": woningen
        })
        totaal += len(woningen)

    return jsonify({
        "runs": runs,
        "status": "Woningen succesvol opgehaald",
        "totaal": totaal
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
