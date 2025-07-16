from flask import Flask, render_template, request, jsonify
import requests
import uuid

app = Flask(__name__)

# LIVE credentials (move to .env or config file for production)
X_AUTH = "684fb239dfc9ac0473696f29:fOOH#CY?vX@&Phdi05dYCv#kopHmnuSRBya8"
PAYME_API = "https://checkout.paycom.uz/api"

headers = {
    "X-Auth": X_AUTH,
    "Content-Type": "application/json"
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/pay", methods=["POST"])
def pay():
    data = request.json
    token = data.get("token")
    amount = int(float(data.get("amount")) * 100)  # amount in tiyin
    description = data.get("description", "Payme QR Sale")

    # 1. Create receipt
    receipt_payload = {
        "method": "receipts.create",
        "params": {
            "amount": amount,
            "account": {},
            "description": description
        },
        "id": str(uuid.uuid4())
    }

    r = requests.post(PAYME_API, json=receipt_payload, headers=headers)
    receipt_res = r.json()
    if "result" not in receipt_res:
        return jsonify({"status": "error", "step": "create", "response": receipt_res})

    receipt_id = receipt_res["result"]["receipt"]["_id"]

    # 2. Pay receipt
    pay_payload = {
        "method": "receipts.pay",
        "params": {
            "id": receipt_id,
            "token": token
        },
        "id": str(uuid.uuid4())
    }

    r2 = requests.post(PAYME_API, json=pay_payload, headers=headers)
    pay_res = r2.json()

    if "result" in pay_res:
        return jsonify({"status": "success", "response": pay_res})
    else:
        return jsonify({"status": "error", "step": "pay", "response": pay_res})

if __name__ == "__main__":
    app.run(debug=True)
