from flask import Flask, request, render_template, jsonify, redirect
import requests
import time
import base64

app = Flask(__name__)

POSTER_DOMAIN = 'coffee-n-1.joinposter.com'
POSTER_TOKEN = '664212:0943952407a90a0dffb58c7903984f19'

PAYME_MERCHANT_ID = '684fb239dfc9ac0473696f29'
PAYME_MERCHANT_KEY = 'fOOH#CY?vX@&Phdi05dYCv#kopHmnuSRBya8'

@app.route('/')
def index():
    return render_template('scan.html')

@app.route('/pay', methods=['POST'])
def pay():
    data = request.json
    token = data['token']         # From Payme QR
    order_id = data['order_id']   # From Poster.orders.getActive()
    amount = int(float(data['amount']) * 100)  # Convert to tiyin

    # Step 1: Prepare
    prepare_payload = {
        "id": str(int(time.time())),
        "method": "cards.prepare",
        "params": {
            "token": token,
            "amount": amount,
            "merchant_id": PAYME_MERCHANT_ID
        }
    }

    auth_string = base64.b64encode(f"Paycom:{PAYME_MERCHANT_KEY}".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_string}"
    }

    r1 = requests.post("https://checkout.paycom.uz/api", json=prepare_payload, headers=headers)
    prepare_result = r1.json()

    if 'result' not in prepare_result:
        return jsonify({"error": "Prepare failed", "details": prepare_result}), 400

    transaction_id = prepare_result['result']['_id']

    # Step 2: Perform
    perform_payload = {
        "id": str(int(time.time())),
        "method": "cards.perform",
        "params": {
            "id": transaction_id
        }
    }

    r2 = requests.post("https://checkout.paycom.uz/api", json=perform_payload, headers=headers)
    perform_result = r2.json()

    if 'result' not in perform_result:
        return jsonify({"error": "Perform failed", "details": perform_result}), 400

    # Step 3: Close Poster Order
    close_url = f"https://{POSTER_DOMAIN}/api/orders.close"
    close_data = {
        "token": POSTER_TOKEN,
        "order_id": order_id
    }

    r3 = requests.post(close_url, data=close_data)
    close_result = r3.json()

    return jsonify({"success": True, "payment": perform_result, "close_result": close_result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

