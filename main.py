import os
import requests
from flask import Flask, request, jsonify
from supabase import create_client
from datetime import datetime

app = Flask(__name__)

# 🔐 Environment
SECRET_API_KEY = os.getenv("MY_SECRET_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def home():
    return "✅ Flip Scraper draait - POST naar /webhook om te starten."

@app.route("/webhook", methods=["POST"])
def webhook():
    client_key = request.headers.get("x-api-key")
    if client_key != SECRET_API_KEY:
        return jsonify({"error": "⛔️ Ongeldige API key"}), 403

    data = request.get_json()
    if not data or "datasetUrls" not in data:
        return jsonify({"error": "❌ datasetUrls ontbreekt in JSON-body"}), 400

    results = []
    for url in data["datasetUrls"]:
        try:
            response = requests.get(url)
            woningen = response.json()

            # ✅ Filter op potentieel interessante flip-woningen
            gefilterd = []
            for w in woningen:
                if not w.get("price") or not w.get("livingArea"):
                    continue

                prijs = w["price"]
                m2 = w["livingArea"]
                soort = w.get("kindOfHouse", "").lower()
                sinds = w.get("date", "")
                adres = w.get("location", "")
                url = w.get("url", "")

                # 📅 Alleen woningen van vandaag
                vandaag = datetime.today().date().isoformat()
                if not sinds.startswith(vandaag):
                    continue

                # 🏘️ Alleen woonhuis of appartement
                if "woonhuis" not in soort and "appartement" not in soort:
                    continue

                # 💰 Max. 2 miljoen
                if prijs > 2_000_000:
                    continue

                verbouwkosten = m2 * 1500
                kk = prijs * 0.06
                ovb = prijs * 0.104
                vergunning = prijs * 0.01
                onvoorzien = 0.10 * (prijs + kk + ovb + vergunning)
                totaal = prijs + verbouwkosten + kk + ovb + vergunning + onvoorzien
                verkoopprijs = prijs * 1.25  # ➕ 25% als schatting
                winst = verkoopprijs - totaal

                gefilterd.append({
                    "adres": adres,
                    "vraagprijs": prijs,
                    "aantal_m2": m2,
                    "vraagprijs_per_m2": prijs / m2,
                    "sinds_datum": sinds,
                    "woz_gem_3jr": prijs * 0.9,
                    "uitbouw_mogelijk": "Onbekend",
                    "vergunning_nodig": "Onbekend",
                    "funda_link": url,
                    "verbouwkosten": verbouwkosten,
                    "totale_kosten": totaal,
                    "verkoopprijs_geschat": verkoopprijs,
                    "verwachte_winst": winst,
                    "hypotheek_per_maand": round((prijs * 0.05) / 12, 2),
                    "extra_m2_mogelijk": 0,
                    "lat": w.get("latitude"),
                    "lon": w.get("longitude")
                })

            # 🏆 Top 15 op basis van verwachte winst
            gefilterd = sorted(gefilterd, key=lambda x: x["verwachte_winst"], reverse=True)[:15]

            for woning in gefilterd:
                # 🧽 Verwijder oude records met hetzelfde adres (dupliceervrij)
                supabase.table("woningen").delete().eq("adres", woning["adres"]).execute()
                supabase.table("woningen").insert(woning).execute()
                results.append(woning)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"status": "✅ Flip-woningen succesvol verwerkt", "totaal": len(results)}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
