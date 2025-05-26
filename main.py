from flask import Flask, request, jsonify
from scraper import scrape_flip_woningen
import time

app = Flask(__name__)

API_KEY = "Maluku123"

@app.route("/")
def home():
    return "🏠 Flip-scraper API is live!"

@app.route("/webhook", methods=["POST"])
def webhook():
    # 🔒 API-key check
    if request.headers.get("x-api-key") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or "steden" not in data:
        return jsonify({"error": "Missing 'steden' in request"}), 400

    steden = data["steden"]
    resultaten = []
    totaal = 0

    for stad in steden:
        print(f"\n🚀 Start scraping voor stad: {stad}")
        pogingen = 0
        woningen = []

        while pogingen < 5 and not woningen:
            print(f"🔄 Poging {pogingen + 1} om data op te halen voor {stad}...")
            woningen = scrape_flip_woningen(stad, dagen=7)  # 👈 7 dagen filter
            print(f"📦 Ontvangen woningen voor {stad}: {len(woningen)} items")
            time.sleep(2)  # iets langere pauze
            pogingen += 1

        resultaten.append({
            "stad": stad,
            "totaal": len(woningen)
        })
        totaal += len(woningen)

    print(f"\n✅ Scrape afgerond voor {len(steden)} steden. Totaal gevonden: {totaal} woningen.")

    return jsonify({
        "runs": resultaten,
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": totaal
    })

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
