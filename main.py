import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from supabase import create_client

app = Flask(__name__)
CORS(app)

# 🌍 Supabase configuratie
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔐 API sleutels
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")
SECRET_API_KEY = os.getenv("MY_SECRET_API_KEY")

@app.route("/")
def home():
    return "✅ Scraper draait. POST naar /webhook om data te scrapen."

@app.route("/webhook", methods=["POST"])
def run_scraper():
    # ✅ Check API-key
    client_key = request.headers.get("x-api-key")
    if client_key != SECRET_API_KEY:
        return jsonify({"error": "⛔️ Ongeldige API key"}), 403

    data = request.get_json()
    if not data or "steden" not in data:
        return jsonify({"error": "❌ Geen steden opgegeven. Gebruik JSON-body met 'steden': ['...']."}), 400

    steden = data["steden"]
    if not isinstance(steden, list) or not all(isinstance(s, str) for s in steden):
        return jsonify({"error": "❌ 'steden' moet een lijst van strings zijn."}), 400

    all_results = []

    for stad in steden:
        payload = {
            "city": stad,
            "maxConcurrency": 5,
            "minConcurrency": 1,
            "maxRequestRetries": 5,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        print(f"▶️ Start scraping voor: {stad}")
        response = requests.post(
            f"https://api.apify.com/v2/actor-tasks/{ACTOR_ID}/runs?token={APIFY_TOKEN}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 201:
            return jsonify({
                "error": f"❌ Scraper mislukt voor {stad}",
                "details": response.text
            }), 500

        run_id = response.json().get("data", {}).get("id")
        dataset_id = response.json().get("data", {}).get("defaultDatasetId")
        print(f"✅ Scraper gestart voor {stad} met dataset ID {dataset_id}")

        # Ophalen data van dataset
        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true&format=json"
        result = requests.get(dataset_url)
        if result.status_code != 200:
            print(f"❌ Fout bij ophalen dataset voor {stad}")
            continue

        woningen = result.json()

        # ✅ Filtering
        vandaag = datetime.utcnow().date()
        gisteren = vandaag - timedelta(days=1)

        gefilterd = [
            w for w in woningen
            if w.get("offerType") == "Te koop"
            and w.get("price", 0) <= 2000000
            and w.get("dateAdded") in [vandaag.isoformat(), gisteren.isoformat()]
            and w.get("propertyType") in ["Woonhuis", "Appartement"]
        ]

        # Sorteer op winstmarge (bijv. vraagprijs - vraagprijs_per_m2 * opp)
        def potentiële_winst(w):
            try:
                price = w.get("price", 0)
                size = w.get("livingArea", 0)
                if price > 0 and size > 0:
                    return price / size
            except:
                return 0
            return 0

        gesorteerd = sorted(gefilterd, key=potentiële_winst)[:25]

        for woning in gesorteerd:
            woning["stad"] = stad
            woning["scrape_date"] = vandaag.isoformat()

        # ✅ Opslaan in Supabase
        for woning in gesorteerd:
            woning_id = woning.get("externalId")
            existing = supabase.table("woningen").select("id").eq("externalId", woning_id).execute()
            if not existing.data:
                supabase.table("woningen").insert(woning).execute()

        all_results.extend(gesorteerd)

    return jsonify({
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": len(all_results)
    }), 200
