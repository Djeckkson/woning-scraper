# main.py

import os
import json
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

APIFY_ACTOR_ID = "djdeckson~funda-task"
APIFY_TOKEN = "apify_api_g9OHpMq0fIMJZaRIPRR0Scrs8VzCZe3JEkLC"

def run_apify_task(stad):
    url = f"https://api.apify.com/v2/actor-tasks/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}"
    payload = {
        "startUrls": [
            {
                "url": f"https://www.funda.nl/koop/{stad}/0-1000000/"
            }
        ]
    }

    response = requests.post(url, json=payload)
    if response.status_code != 201:
        print(f"❌ Apify run failed: {response.text}")
        return []

    run_id = response.json()["data"]["id"]

    # Wacht op voltooien
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        check = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()
        status = check["data"]["status"]

    # Haal dataset items op
    dataset_id = check["data"]["defaultDatasetId"]
    items_response = requests.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
    )

    if items_response.status_code != 200:
        print(f"❌ Failed to get dataset: {items_response.text}")
        return []

    return items_response.json()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    steden = data.get('steden', [])
    output = []

    for stad in steden:
        woningen = run_apify_task(stad)
        output.append({
            "stad": stad,
            "totaal": len(woningen),
            "woningen": woningen
        })

    return jsonify({
        "status": "✅ Flip-woningen succesvol verwerkt",
        "totaal": sum([len(x["woningen"]) for x in output]),
        "runs": output
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
