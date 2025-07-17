from flask import Flask, render_template, request, redirect, jsonify
import requests
import base64
import time

app = Flask(__name__)

# === CONFIG ===
POSTER_TOKEN = '664212:0943952407a90a0dffb58c7903984f19'
POSTER_DOMAIN = 'coffee-n-1.joinposter.com'
PAYME_ID = '684fb239dfc9ac0473696f29'
PAYME_SECRET = 'fOOH#CY?vX@&Phdi05dYCv#kopHmnuSRBya8'
PAYME_URL = 'https://checkout.test.paycom.uz/api'  # Change to production URL if needed
PAYME_PAYMENT_METHOD_ID = 17


# === ROUTES ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pay')
def pay_redirect():
    order_id = request.args.get('order_id')
    if not order_id:
        return redirect('/')
    return redirect(f'/pay/{order_id}')

@app.route('/pay/<order_id>')
def pay(order_id):
    return render_template('scan.html', order_id=order_id)

@app.route('/charge', methods=['POST'])
def charge():
    order_id = request.form['order_id']
    token = request.form['token']

    # Get order total from Poster
    order_url = f'https://{POSTER_DOMAIN}/api/incomingOrders.getOne'
    order_res = requests.get(order_url, params={'token': POSTER_TOKEN, 'incoming_order_id': order_id})
    order_data = order_res.json()
    if 'response' not in order_data:
        return '❌ Order not found in Poster.'

    total = int(float(order_data['response']['full_sum']) * 100)  # convert to tiyin

    # Prepare Payme request
    headers = {
        'X-Auth': base64.b64encode(f"{PAYME_ID}:{PAYME_SECRET}".encode()).decode(),
        'Content-Type': 'application/json'
    }

    payload = {
        "id": str(int(time.time() * 1000)),
        "method": "receipts.create",
        "params": {
            "amount": total,
            "account": {
                "token": token
            }
        }
    }

    res = requests.post(PAYME_URL, json=payload, headers=headers)
    r = res.json()
    if 'error' in r:
        return f"❌ Payme error: {r['error']['message']}"

    receipt_id = r['result']['_id']

    # Pay the receipt
    pay_payload = {
        "id": str(int(time.time() * 1000)) + "1",
        "method": "receipts.pay",
        "params": {
            "id": receipt_id
        }
    }
    pay_res = requests.post(PAYME_URL, json=pay_payload, headers=headers)
    pay_data = pay_res.json()

    if 'error' in pay_data:
        return f"❌ Payme payment error: {pay_data['error']['message']}"

    # Mark as paid in Poster
    poster_url = f"https://{POSTER_DOMAIN}/api/incomingOrders.pay"
    poster_res = requests.post(poster_url, data={
        'token': POSTER_TOKEN,
        'incoming_order_id': order_id,
        'payments': f'[{{"payment_method_id":{PAYME_PAYMENT_METHOD_ID},"sum":{total / 100}}}]'
    })

    if poster_res.status_code != 200 or 'error' in poster_res.text:
        return '✅ Charged on Payme but failed to update Poster POS.'

    return '✅ Payment successful and order marked paid!'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
