from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

APIFY_TOKEN = "apify_api_gg0HpMq0fiMJZaRIPRR0Scrs8VzCZe3JEkLC"
TASK_ID = "djeckxson~funda-task2"

def run_apify_task():
    print(f"📡 Start Apify task {TASK_ID}")

    # Start task
    start_url = f"https://api.apify.com/v2/actor-tasks/{TASK_ID}/runs"
    res = requests.post(start_url, json={"token": APIFY_TOKEN})
    if res.status_code != 201:
        print(f"❌ Start mislukt: {res.status_code}")
        return "Mislukt", []

    run_id = res.json()["data"]["id"]
    print(f"▶️ Task gestart, run ID: {run_id}")

    # Poll tot klaar
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(5)
        status_res = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}",
            headers={"Authorization": f"Bearer {APIFY_TOKEN}"}
        )
        status = status_res.json()["data"]["status"]
        print(f"⌛ Status: {status}")

    if status != "SUCCEEDED":
        return "Mislukt", []

    dataset_id = status_res.json()["data"]["defaultDatasetId"]
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json"
    items_res = requests.get(items_url)
    woningen = items_res.json()
    print(f"✅ {len(woningen)} woningen opgehaald")
    return "Gelukt", woningen

@app.route("/")
def index():
    return "🏠 Scraper draait ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    status, woningen = run_apify_task()
    return jsonify({
        "status": f"Woningen ophalen: {status}",
        "totaal": len(woningen),
        "woningen": woningen
    })

if __name__ == "__main__":
    app.run(debug=True, port=10000, host="0.0.0.0")
