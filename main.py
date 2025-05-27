from flask import Flask, request, jsonify
import requests
import time
import os

app = Flask(__name__)

# 🔐 Apify configuratie
APIFY_TOKEN = "apify_api_gg0HpMq0fiMJZaRIPRR0Scrs8VzCZe3JEkLC"
TASK_ID = "djeckxson~funda-task2"

def run_apify_task():
    print(f"📡 Start Apify task: {TASK_ID}")

    # ✅ Start de task via URL-token
    url = f"https://api.apify.com/v2/actor-tasks/{TASK_ID}/runs?token={APIFY_TOKEN}"
    res = requests.post(url)

    if res.status_code != 201:
        print(f"❌ Task starten mislukt: {res.status_code}")
        return "Mislukt", []

    run_id = res.json()["data"]["id"]
    print(f"▶️ Task gestart met run ID: {run_id}")

    # ⏳ Poll de status
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(5)
        check_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        status_res = requests.get(check_url)
        status = status_res.json()["data"]["status"]
        print(f"⌛ Status: {status}")

    if status != "SUCCEEDED":
        print("❌ Task eindigde zonder succes")
        return "Mislukt", []

    # ✅ Resultaten ophalen
    dataset_id = status_res.json()["data"]["defaultDatasetId"]
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}&format=json"
    items_res = requests.get(items_url)
    woningen = items_res.json()
    print(f"✅ {len(woningen)} woningen opgehaald")
    return "Gelukt", woningen

@app.route("/")
def index():
    return "🏠 Woning scraper draait ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    status, woningen = run_apify_task()
    return jsonify({
        "status": f"Woningen ophalen: {status}",
        "totaal": len(woningen),
        "woningen": woningen
    })

# ✅ Zorg dat Render de juiste poort pakt
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=True, host="0.0.0.0", port=port)

