import os
import json
from flask import Flask, request, jsonify
import requests
from supabase import create_client, Client

app = Flask(__name__)

# 🔐 Haal Supabase credentials uit Render Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔐 Apify
APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN")
ACTOR_ID = os.environ.get("APIFY_ACTOR_ID")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        body = request.get_json()
        steden = body.get("steden", ["Deventer"])  # fallback naar Deventer

        resultaten = []

        for stad in steden:
            # 🎬 Start Apify Actor run
            apify_input = {
                "city": stad,
                "maxPrice": 1000000,
                "maxResults": 100,
                "minPublishDate": "2025-05-20",
                "offerTypes": ["Koop"],
                "propertyTypes": ["Woonhuis", "Appartement"],
                "radiusKm": 10
            }

            run_res = requests.post(
                f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}",
                json={"input": apify_input}
            )
            run_id = run_res.json().get("data", {}).get("id")
            if not run_id:
                resultaten.append({"stad": stad, "status": "Run starten mislukt", "woningen": []})
                continue

            # ⏳ Poll until finished
            while True:
                check = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}")
                status = check.json()["data"]["status"]
                if status in ["SUCCEEDED", "FAILED", "TIMED-OUT"]:
                    break

            if status != "SUCCEEDED":
                resultaten.append({"stad": stad, "status": "Mislukt", "woningen": []})
                continue

            # 📥 Ophalen van dataset items
            dataset_id = check.json()["data"]["defaultDatasetId"]
            items_res = requests.get(f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true")
            woningen = items_res.json()

            # 📤 Stuur woningen naar Supabase
            for woning in woningen:
                supabase.table("woningen").insert(woning).execute()

            resultaten.append({
                "stad": stad,
                "status": "Gelukt",
                "totaal": len(woningen),
                "woningen": woningen
            })

        return jsonify({
            "runs": resultaten,
            "status": "Woningdata succesvol opgehaald",
            "totaal": sum(len(r["woningen"]) for r in resultaten)
        })

    except Exception as e:
        return jsonify({
            "status": "Woningen ophalen: Mislukt",
            "error": str(e),
            "woningen": [],
            "totaal": 0
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
