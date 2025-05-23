import os
import requests
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dateutil.parser import parse as parse_date
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
    vandaag = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

    for stad in steden:
        payload = {
            "city": stad,
            "maxPrice": 2000000,
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"],
            "maxResults": 100,
            "radiusKm": 5,
            "minPublishDate": vandaag.strftime("%Y-%m-%d"),
        }

        print(f"▶️ Scrapen gestart voor: {stad} met payload: {payload}")

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
        print(f"⬇️ Dataset ophalen van: {dataset_url}")

        woningen = []
        for poging in range(5):
            try:
                dataset_response = requests.get(dataset_url)
                woningen = dataset_response.json()
                if isinstance(woningen, list) and len(woningen) > 0:
                    break
            except Exception as e:
                print(f"⏳ Wachten op dataset... poging {poging+1}")
                time.sleep(3)

        unieke_woningen = []
        for w in woningen:
            try:
                if (
                    w.get("price") is not None
                    and w.get("externalId") is not None
                    and w.get("propertyType") in ["Woonhuis", "Appartement"]
                    and parse_date(w.get("dateAdded", "")) >= vandaag
                ):
                    nieuwe = {
                        "externalId": w["externalId"],
                        "price": w["price"],
                        "propertyType": w.get("propertyType", ""),
                        "offerType": w.get("offerType", ""),
                        "dateAdded": w.get("dateAdded", ""),
                        "livingArea": w.get("livingArea", 0),
                        "stad": stad,
                        "scrape_date": vandaag.strftime("%Y-%m-%d"),
                        "adres": w.get("adres", ""),
                        "woz_gemiddeld": w.get("wozWaardeGemiddeld"),
                        "uitbouw_mogelijk": w.get("uitbouwMogelijk"),
                        "vergunning_nodig": w.get("vergunningNodig"),
                    }
                    unieke_woningen.append(nieuwe)
            except Exception as e:
                print(f"⚠️ Skipped woning vanwege parse-fout: {e}")

        print(f"✅ {len(unieke_woningen)} woningen gevonden voor {stad}")

        if unieke_woningen:
            try:
                supabase.table("woningen").upsert(unieke_woningen, on_conflict="externalId").execute()
                print(f"📥 {len(unieke_woningen)} woningen opgeslagen in Supabase voor {stad}")
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
