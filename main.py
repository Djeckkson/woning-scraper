import os
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
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
    vandaag = datetime.today().strftime("%Y-%m-%d")
    zeven_dagen_terug = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")

    for stad in steden:
        print(f"🚀 Start scraper voor {stad}...")

        payload = {
            "city": stad,
            "maxPrice": 2000000,
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"],
            "maxResults": 100,
            "radiusKm": 5,
            "minPublishDate": zeven_dagen_terug,
        }

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
        dataset_id = run_data["defaultDatasetId"]
        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true&format=json"

        woningen = []
        for attempt in range(5):
            print(f"⏳ Poging {attempt + 1} om dataset op te halen voor {stad}...")
            try:
                response = requests.get(dataset_url)
                woningen = response.json()
                if woningen:
                    break
                time.sleep(8)
            except Exception as e:
                print(f"⚠️ Fout bij ophalen dataset: {e}")
                time.sleep(8)

        print(f"📦 Ontvangen woningen voor {stad}: {len(woningen)} items")

        unieke_woningen = []

        for item in woningen:
            s = item.get("search_item", {}).get("_source", {})
            address = s.get("address", {})
            price = s.get("price", {}).get("selling_price", [None])[0]
            woonopp = s.get("floor_area", [0])[0]
            publish_date = s.get("publish_date", "")[:10]

            if not price or not publish_date:
                continue

            nieuwe = {
                "externalId": str(item.get("_id", "")),
                "price": price,
                "propertyType": "Appartement" if s.get("object_type") == "apartment" else "Woonhuis",
                "offerType": "Koop",
                "dateAdded": publish_date,
                "livingArea": woonopp,
                "stad": stad,
                "scrape_date": vandaag,
                "adres": f'{address.get("street_name", "")} {address.get("house_number", "")}, {address.get("postal_code", "")}',
                "woz_gemiddeld": None,
                "uitbouw_mogelijk": None,
                "vergunning_nodig": None,
            }

            unieke_woningen.append(nieuwe)

        if unieke_woningen:
            try:
                supabase.table("woningen").upsert(unieke_woningen, on_conflict="externalId").execute()
            except Exception as e:
                return jsonify({"error": f"❌ Fout bij opslaan in Supabase: {str(e)}"}), 500

        all_runs.append({"stad": stad, "totaal": len(unieke_woningen)})

    totaal = sum(r["totaal"] for r in all_runs)
    return jsonify({
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": totaal,
        "runs": all_runs
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
