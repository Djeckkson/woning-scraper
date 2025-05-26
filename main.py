import requests
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ Jouw vaste Apify gegevens
APIFY_TOKEN = "apify_api_bBAe9vPd4r9NnhxHtRXkquKjxfGx2A0cHt"  # Dit is jouw werkende token
SCRAPER_ACTOR_ID = "bA9PazxMRX4aN5F1m"  # Dit is je actor task ID

def start_apify_scraper(stad):
    print(f"▶️ Start Apify scraper voor: {stad}")
    url = f"https://api.apify.com/v2/actor-tasks/{SCRAPER_ACTOR_ID}/runs?token={APIFY_TOKEN}"

    # Input data naar je scraper zoals je die eerder had ingesteld
    payload = {
        "city": stad,
        "maxPrice": 2000000,
        "offerTypes": ["Koop"],
        "propertyTypes": ["Woonhuis", "Appartement"],
        "maxResults": 100,
        "radiusKm": 5
    }

    # Start scraper run
    run_response = requests.post(url, json=payload)
    if run_response.status_code != 201:
        print(f"❌ Scraper start fout voor {stad}: {run_response.text}")
        return []

    run_data = run_response.json()["data"]
    dataset_id = run_data["defaultDatasetId"]

    # Wacht en probeer resultaten op te halen
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true&format=json"
    woningen = []
    for attempt in range(10):
        print(f"⌛️ Poging {attempt + 1} om data op te halen...")
        res = requests.get(dataset_url)
        try:
            woningen = res.json()
            if woningen:
                break
        except Exception:
            pass
        time.sleep(6)

    print(f"📦 Ontvangen woningen voor {stad}: {len(woningen)} items")
    return woningen

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])

    resultaten = []
    totaal = 0

    for stad in steden:
        woningen = start_apify_scraper(stad)
        resultaten.append({
            "stad": stad,
            "totaal": len(woningen)
        })
        totaal += len(woningen)

    return jsonify({
        "runs": resultaten,
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": totaal
    })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)
