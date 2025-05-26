from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

# ✅ Correcte Apify-token zonder prefix
APIFY_TOKEN = "g9OHpMq0fIMJZaRlPRR0Scrs8VzCZ3EkLC"
ACTOR_ID = "djeckxson~funda-task"

def run_apify_actor(stad):
    url = f"https://api.apify.com/v2/actor-tasks/{ACTOR_ID}/runs?token={APIFY_TOKEN}"
    payload = {
        "token": APIFY_TOKEN,
        "memory": 2048,
        "timeoutSecs": 1200,
        "build": "latest",
        "input": {
            "stad": stad,
            "maxItems": 20
        }
    }

    print("📡 Start Apify actor...")
    res = requests.post(url, json=payload)
    res.raise_for_status()
    run_id = res.json().get("data", {}).get("id")
    if not run_id:
        return None, []

    # 🕒 Wachten tot de actor klaar is
    for _ in range(30):
        run_status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        run_status_res = requests.get(run_status_url)
        run_status_res.raise_for_status()
        status = run_status_res.json().get("data", {}).get("status")
        if status == "SUCCEEDED":
            break
        time.sleep(2)
    else:
        return None, []

    # 📥 Ophalen van resultaat
    items_url = f"https://api.apify.com/v2/datasets/{run_id}/items?token={APIFY_TOKEN}&clean=true&format=json"
    items_res = requests.get(items_url)
    items_res.raise_for_status()
    woningen = items_res.json()

    return "✅ Flip-woningen succesvol verwerkt", woningen

@app.route("/")
def index():
    return "🏠 Woning scraper is live."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
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
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": totaal
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
