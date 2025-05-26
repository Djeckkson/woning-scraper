from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

APIFY_TOKEN = "apify_api_g9OHpMq0fIMJZaRlPRR0Scrs8VzCZ3EkLC"  # jouw echte token
ACTOR_ID = "djeckxson~funda-task"  # actor-id uit je screenshot

def run_apify_actor(stad):
    url = f"https://api.apify.com/v2/actor-tasks/{ACTOR_ID}/runs?token={APIFY_TOKEN}"
    payload = {
        "startUrls": [f"https://www.funda.nl/koop/{stad.lower()}/"],
        "maxItems": 20,
    }

    print("📡 Start Apify actor...")
    res = requests.post(url, json=payload)
    res.raise_for_status()
    run_id = res.json().get("data", {}).get("id")
    if not run_id:
        return None, []

    # Wachten op voltooiing
    for _ in range(30):  # maximaal 30 seconden
        status_res = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        )
        status_res.raise_for_status()
        status = status_res.json().get("data", {}).get("status")
        if status == "SUCCEEDED":
            print("✅ Apify-run succesvol afgerond.")
            break
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            print(f"❌ Apify-run gefaald met status: {status}")
            return status, []
        time.sleep(1)
    else:
        print("⏳ Timeout: Apify-run duurde te lang.")
        return "TIMEOUT", []

    # Data ophalen
    dataset_id = status_res.json().get("data", {}).get("defaultDatasetId")
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}&clean=true"
    dataset_res = requests.get(dataset_url)
    dataset_res.raise_for_status()
    woningen = dataset_res.json()

    return "SUCCEEDED", woningen

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
        "status": "Flip-woningen succesvol verwerkt",
        "totaal": totaal,
        "runs": runs
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
