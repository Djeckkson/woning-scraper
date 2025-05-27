from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

# 🔐 Apify-instellingen
APIFY_TOKEN = "apify_api_gg0HpMq0fiMJZaRIPRR0Scrs8VzCZe3JEkLC"
ACTOR_ID = "memo23~apify-funda-cheerio-kvstore"

# 🚀 Functie om een Apify actor run te starten en resultaten op te halen
def run_apify_actor(stad):
    print(f"📡 Start Apify actor voor stad: {stad}")
    
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs"
    payload = {
        "memory": 2048,
        "timeoutSecs": 3600,
        "build": "latest",
        "input": {
            "city": stad,
            "maxResults": 20
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": APIFY_TOKEN
    }

    try:
        res = requests.post(url, json=payload, headers=headers)
        res.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"❌ Fout bij starten actor: {e}")
        return "Mislukt", []

    run_id = res.json()["data"]["id"]
    print(f"▶️ Run gestart: {run_id}")

    # ⏳ Pollen tot klaar
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(5)
        check_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
        check_res = requests.get(check_url, headers=headers)
        check_res.raise_for_status()
        status = check_res.json()["data"]["status"]
        print(f"⌛ Status: {status}")

    if status != "SUCCEEDED":
        return "Mislukt", []

    # 📦 Ophalen van resultaten
    dataset_id = check_res.json()["data"]["defaultDatasetId"]
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json"
    items_res = requests.get(items_url, headers=headers)
    items_res.raise_for_status()
    items = items_res.json()
    print(f"✅ {len(items)} resultaten opgehaald voor {stad}")
    return "Gelukt", items

# 🌐 Statuspagina
@app.route("/")
def index():
    return "🏠 Woning scraper draait ✅"

# 📬 Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
    if not steden or not isinstance(steden, list):
        return jsonify({"error": "Verwacht JSON met 'steden': [..]"}), 400

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

# 🚀 App starten
if __name__ == "__main__":
    app.run(debug=True, port=10000, host="0.0.0.0")
