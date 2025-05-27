from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import requests
import os

app = Flask(__name__)
CORS(app)

# Haal Supabase credentials uit environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])

    if not steden:
        return jsonify({"status": "Fout", "bericht": "Geen steden opgegeven"}), 400

    resultaten = []

    for stad in steden:
        run_input = {
            "city": stad,
            "maxPrice": 1000000,
            "maxResults": 100,
            "minPublishDate": "2025-05-20",
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"],
            "radiusKm": 10,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}"
        run_response = requests.post(run_url, json=run_input).json()
        run_id = run_response.get("data", {}).get("id")

        if not run_id:
            resultaten.append({
                "stad": stad,
                "status": "Mislukt",
                "woningen": [],
                "totaal": 0
            })
            continue

        dataset_url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_TOKEN}&clean=true"
        woningen = []
        for _ in range(40):  # maximaal 40 seconden wachten
            r = requests.get(dataset_url)
            if r.status_code == 200 and r.json():
                woningen = r.json()
                break
            import time
            time.sleep(1)

        resultaten.append({
            "stad": stad,
            "status": "Gelukt" if woningen else "Mislukt",
            "woningen": woningen,
            "totaal": len(woningen)
        })

        # Opslaan in Supabase
        for woning in woningen:
            supabase.table("woningen").insert(woning).execute()

    return jsonify({
        "status": "Woningdata opgehaald",
        "runs": resultaten,
        "totaal": sum(len(r["woningen"]) for r in resultaten)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
