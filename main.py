from flask import Flask, request, jsonify
from scraper import scrape_flip_woningen
import time

app = Flask(__name__)

@app.route("/")
def home():
    return "🏡 Woning scraper draait!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
    
    print(f"📨 Ontvangen POST-verzoek voor steden: {steden}")
    
    resultaten = []
    totaal = 0

    for stad in steden:
        print(f"🔍 Start scraping voor: {stad}")
        
        woningen = []
        pogingen = 0
        while pogingen < 5 and not woningen:
            print(f"⏱️ Poging {pogingen+1} om data op te halen voor {stad}...")
            woningen = scrape_flip_woningen(stad, dagen=7)
            if woningen:
                break
            pogingen += 1
            time.sleep(3)  # Wacht 3 seconden tussen pogingen

        print(f"📦 Ontvangen woningen voor {stad}: {len(woningen)} items")
        resultaten.append({
            "stad": stad,
            "totaal": len(woningen)
        })
        totaal += len(woningen)

    response = {
        "runs": resultaten,
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": totaal
    }

    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=False, port=10000, host="0.0.0.0")
