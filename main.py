
import os
import json
import requests
from flask import Flask, request, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# Haal Supabase config uit environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Apify credentials en endpoint
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")
APIFY_URL = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])

    resultaten = []
    totaal_woningen = 0

    for stad in steden:
        input_config = {
            "city": stad,
            "maxPrice": 1000000,
            "maxResults": 100,
            "minPublishDate": "2025-05-20",
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"],
            "radiusKm": 10
        }

        run_response = requests.post(APIFY_URL, json={"input": input_config})
        if run_response.status_code != 201:
            resultaten.append({
                "stad": stad,
                "status": "Mislukt",
                "woningen": [],
                "totaal": 0
            })
            continue

        run_id = run_response.json()["data"]["id"]

        # Wacht op scraping result
        dataset_url = f"https://api.apify.com/v2/datasets/{run_id}/items?clean=true"
        woningen_response = requests.get(dataset_url)
        woningen = woningen_response.json() if woningen_response.ok else []

        totaal_woningen += len(woningen)

        # Voeg toe aan Supabase
        for woning in woningen:
            supabase.table("woningen").insert(woning).execute()

        resultaten.append({
            "stad": stad,
            "status": "Gelukt" if woningen else "Mislukt",
            "woningen": woningen,
            "totaal": len(woningen)
        })

    return jsonify({
        "runs": resultaten,
        "status": "Woningdata opgehaald",
        "totaal": totaal_woningen
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
