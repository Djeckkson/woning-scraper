from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

# Zet hier je geldige Apify token
APIFY_TOKEN = "apify_api_g9OHpMq0fIMJZaRlPRR0Scrs8VzCZ3EkLC"
ACTOR_TASK_ID = "djeckxson~funda-task"

def run_apify_actor(stad):
    print(f"📡 Start Apify actor voor stad: {stad}")
    
    # Stap 1: start actor-task
    url = f"https://api.apify.com/v2/actor-tasks/{ACTOR_TASK_ID}/runs?token={APIFY_TOKEN}"
    payload = {
        "token": APIFY_TOKEN,
        "memory": 1024,
        "timeoutSecs": 300,
        "build": "latest",
        "input": {
            "stad": stad,
            "maxItems": 20
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()
    run_id = res.json()["data"]["id"]
    
    # Stap 2: wachten tot klaar
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(5)
        check_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        check_res = requests.get(check_url)
        check_res.raise_for_status()
        status = check_res.json()["data"]["status"]
        print(f"⌛ Status: {status}")

    # Stap 3: resultaat ophalen
    if status != "SUCCEEDED":
        return "Mislukt", []

    dataset_id = check_res.json()["data"]["defaultDatasetId"]
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}&format=json"
    items_res = requests.get(items_url)
    items_res.raise_for_status()
    items = items_res.json()
    print(f"✅ {len(items)} resultaten opgehaald")
    return "Gelukt", items


@app.route("/")
def index():
    return "Woning scraper draait ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    steden = data.get("steden", [])
    runs = []
    totaal = 0

    for stad in steden:
        status, woningen = run_apify_actor(stad)
        runs.append({
            "stad": stad,
            "totaal": len(woningen),
            "woningen": woningen
        })
        totaal += len(woningen)

    return jsonify({
        "runs": runs,
        "status": "Flip-woningen succesvol verwerkt",
        "totaal": totaal
    })

if __name__ == "__main__":
    app.run(debug=True, port=10000, host="0.0.0.0")
