import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from supabase import create_client

app = Flask(__name__)
CORS(app)

# 🔐 Omgevingsvariabelen
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID")
SECRET_API_KEY = os.getenv("MY_SECRET_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def home():
    return "✅ Flip-scraper draait. POST naar /webhook om te scrapen en op te slaan."

@app.route("/webhook", methods=["POST"])
def run_scraper():
    if request.headers.get("x-api-key") != SECRET_API_KEY:
        return jsonify({"error": "⛔️ Ongeldige API key"}), 403

    body = request.get_json()
    if not body or "datasetUrls" not in body:
        return jsonify({"error": "❌ Ontbrekende datasetUrls in body"}), 400

    total_inserted = 0
    for url in body["datasetUrls"]:
        try:
            response = requests.get(url)
            response.raise_for_status()
            items = response.json()
        except Exception as e:
            return jsonify({"error": f"❌ Fout bij ophalen van dataset: {e}"}), 500

        vandaag = datetime.utcnow().date()
        gisteren = vandaag - timedelta(days=1)
        geldig_types = ["Woonhuis", "Appartement"]

        gefilterd = []
        unieke_ids = set()

        for item in items:
            externalId = str(item.get("externalId"))
            if externalId in unieke_ids:
                continue

            try:
                datum = datetime.strptime(item.get("dateAdded"), "%Y-%m-%d").date()
            except:
                continue

            if datum < gisteren:
                continue
            if item.get("offerType") != "Koop":
                continue
            if item.get("propertyType") not in geldig_types:
                continue

            gefilterd.append({
                "externalId": externalId,
                "price": item.get("price"),
                "propertyType": item.get("propertyType"),
                "offerType": item.get("offerType"),
                "dateAdded": datum.isoformat(),
                "livingArea": item.get("livingArea"),
                "stad": item.get("city"),
                "scrape_date": vandaag.isoformat(),
                "adres": item.get("adres"),
                "woz_gemiddeld": item.get("wozAvg"),
                "uitbouw_mogelijk": item.get("uitbouwMogelijk"),
                "vergunning_nodig": item.get("vergunningNodig"),
            })
            unieke_ids.add(externalId)

        for woning in gefilterd:
            try:
                supabase.table("woningen").insert(woning).execute()
                total_inserted += 1
            except Exception:
                continue  # Dubbele of fout → negeren

    return jsonify({
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": total_inserted
    }), 200
