from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

# 🔐 Apify-instellingen
APIFY_TOKEN = "apify_api_gg0HpMq0fiMJZaRIPRR0Scrs8VzCZe3JEkLC"
ACTOR_ID = "memo23~apify-funda-cheerio-kvstore"

# 🚀 Actor aanroepen en data ophalen
def run_apify_actor(stad):
    print(f"📡 Start Apify actor voor stad: {stad}")
    
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs"
    payload = {
        "memory": 2048,
        "timeoutSecs": 3600,
        "build": "latest",
        "input": {
            "city": stad,
            "maxResults": 20,
            "radiusKm": 15,
            "offerTypes": ["Koop"],
            "propertyTypes": ["Woonhuis", "Appartement"]
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": APIFY_TOKEN
    }

    # 👉 Start de actor-run
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code != 201:
        print(f"❌ Fout bij starten actor-run (status: {res.status_code})")
        print(f"📨 Response: {res.text}")
        return "Mislukt", []

    run_id = res.json()["data"]["id"]
    print(f"▶️ Actor-run ID: {run_id}")

    # ⏳ Pollen tot de run klaar is
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(5)
        check_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
        check_res = requests.get(check_url, headers=headers)
        check_res.raise_for_status()
        status = check_res.json()["data"]["status"]
        print(f"⌛ Status: {status}")

    if status != "SUCCEEDED":
        print(f"❌ Run mislukt met status: {status}")
        return "Mislukt", []

    # ✅ Resultaten ophalen
    dataset_id = check_res.json()["data"]["defaultDatasetId"]
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json"
    items_res = requests.get(items_url, headers=headers)
    items_res.raise_for_status()
    items = items_res.json()
    print(f"✅ {len(items)} resultaten opgehaald voor {stad}")
    return "Gelukt", items

# 🌐 Root-route
@app.route("/")
def index():
    return "🏠 Woning scraper draait ✅"

# 📬 Webhook voor POST met steden
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
    if not steden or not isinstance(steden, list):
        return jsonify({"error": "Gebruik JSON met 'steden': [..]"}), 400

    runs = []
    totaal = 0

    for stad in steden:
        status, woningen = run_apify_actor(stad)
        runs.append({
            "stad": stad,
            "status": status,
            "totaal": len(woningen),
            "woningen": woningen
        })
        totaal += len(woningen)

    return jsonify({
        "status": "Woningdata opgehaald",
        "totaal": totaal,
        "runs": runs
    })

# 🚀 Server starten
if __name__ == "__main__":
    app.run(debug=True, port=10000, host="0.0.0.0")
