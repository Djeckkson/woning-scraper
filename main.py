import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from supabase import create_client, Client

# 🔐 Omgevingsvariabelen
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")
SECRET_API_KEY = os.getenv("MY_SECRET_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "✅ Flip-scraper draait. POST naar /webhook om te starten."

@app.route("/webhook", methods=["POST"])
def run_scraper():
    # ✅ Beveiliging
    client_key = request.headers.get("x-api-key")
    if client_key != SECRET_API_KEY:
        return jsonify({"error": "⛔️ Ongeldige API key"}), 403

    data = request.get_json()
    if not data or "steden" not in data:
        return jsonify({"error": "❌ Geen steden opgegeven."}), 400

    steden = data["steden"]
    if not isinstance(steden, list) or not all(isinstance(s, str) for s in steden):
        return jsonify({"error": "❌ 'steden' moet een lijst van strings zijn."}), 400

    all_runs = []
    for stad in steden:
        payload = {
            "city": stad,
            "maxPrice": 2000000,
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"],
            "maxResults": 100,
            "radiusKm": 5,
            "minPublishDate": datetime.today().strftime("%Y-%m-%d"),
        }

        print("▶️ Payload:", payload)

        response = requests.post(
            f"https://api.apify.com/v2/actor-tasks/{ACTOR_ID}/runs?token={APIFY_TOKEN}",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code != 201:
            return jsonify({
                "error": f"❌ Scraper mislukt voor {stad}",
                "details": response.text,
            }), 500

        run_data = response.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data["defaultDatasetId"]

        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true&format=json"
        print(f"⬇️ Dataset ophalen van: {dataset_url}")

        # Wacht even totdat dataset klaar is (optioneel: retry logic)
        try:
            items_response = requests.get(dataset_url)
            woningen = items_response.json()
        except Exception as e:
            return jsonify({"error": f"❌ Fout bij ophalen dataset: {e}"}), 500

        unieke_woningen = []
        vandaag = datetime.today().strftime("%Y-%m-%d")

        for w in woningen:
            if (
                w.get("dateAdded", "") >= vandaag
                and w.get("price") is not None
                and w.get("externalId") is not None
                and w.get("propertyType") in ["Woonhuis", "Appartement"]
            ):
                nieuwe = {
                    "externalId": w["externalId"],
                    "price": w["price"],
                    "propertyType": w.get("propertyType", ""),
                    "offerType": w.get("offerType", ""),
                    "dateAdded": w.get("dateAdded", ""),
                    "livingArea": w.get("livingArea", 0),
                    "stad": stad,
                    "scrape_date": vandaag,
                    "adres": w.get("adres", ""),
                    "woz_gemiddeld": w.get("wozWaardeGemiddeld"),
                    "uitbouw_mogelijk": w.get("uitbouwMogelijk"),
                    "vergunning_nodig": w.get("vergunningNodig"),
                }
                unieke_woningen.append(nieuwe)

        if unieke_woningen:
            supabase.table("woningen").upsert(unieke_woningen, on_conflict="externalId").execute()

        all_runs.append({"stad": stad, "totaal": len(unieke_woningen)})

    totaal = sum(r["totaal"] for r in all_runs)
    return jsonify({
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": totaal,
        "runs": all_runs
    }), 200


# 🔁 Start de app voor Render (poortbinding)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
