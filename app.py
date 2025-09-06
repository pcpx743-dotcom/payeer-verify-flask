import os, uuid, hashlib, hmac
from flask import Flask, render_template_string, request, abort

app = Flask(__name__)

EPC_MERCHANT_ID = "103045"
EPC_SECRET      = "yrGW2mWFLDjzTpbD"  # SCI/Seller secret (kabinetdagi)
ACTION_URL      = "https://api.epaycore.com/checkout/form"

SUCCESS_URL = "https://payeer-verify-flask.onrender.com/success"
CANCEL_URL  = "https://payeer-verify-flask.onrender.com/fail"
STATUS_URL  = "https://payeer-verify-flask.onrender.com/api/epaycore/webhook"

def sign_md5(amount, currency_code, order_id, merchant_id, secret):
    raw = f"{amount}:{currency_code}:{order_id}:{merchant_id}:{secret}"
    return hashlib.md5(raw.encode()).hexdigest()

def sign_hmac_sha256(amount, currency_code, order_id, merchant_id, secret):
    raw = f"epc_amount={amount}&epc_currency_code={currency_code}&epc_order_id={order_id}&epc_merchant_id={merchant_id}"
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()

@app.get("/pay/<amount>")
def pay(amount):
    # Buyurtma
    order_id = "ORD-" + uuid.uuid4().hex[:10].upper()
    amt = f"{float(amount):.2f}"
    currency_code = "USD"

    # --- SIGN: docs’dagi FORMULAGA mosini TANLANG ---
    epc_sign = sign_md5(amt, currency_code, order_id, EPC_MERCHANT_ID, EPC_SECRET)
    # epc_sign = sign_hmac_sha256(amt, currency_code, order_id, EPC_MERCHANT_ID, EPC_SECRET)

    fields = {
        "epc_merchant_id":  EPC_MERCHANT_ID,
        "epc_commission":   "1",         # 1 = Customer pays fee (siz shuni tanlagansiz)
        "epc_amount":       amt,
        "epc_currency_code": currency_code,
        "epc_order_id":     order_id,
        "epc_success_url":  SUCCESS_URL,
        "epc_cancel_url":   CANCEL_URL,
        "epc_status_url":   STATUS_URL,
        "epc_sign":         epc_sign,
    }

    html = f"""
    <html><body onload="document.forms[0].submit()">
      <h3>Redirecting to ePayCore checkout…</h3>
      <form method="post" action="{ACTION_URL}">
        {''.join(f'<input type="hidden" name="{k}" value="{v}"/>' for k,v in fields.items())}
        <noscript><button type="submit">Continue</button></noscript>
      </form>
    </body></html>
    """
    return render_template_string(html)

@app.post("/api/epaycore/webhook")
def webhook():
    data = request.form.to_dict() or (request.get_json(silent=True) or {})
    # Tipik maydonlar: epc_order_id, epc_amount, epc_currency_code, epc_status, epc_sign, ...
    need = ["epc_order_id","epc_amount","epc_currency_code","epc_status","epc_sign","epc_merchant_id"]
    if not all(k in data for k in need):
        return abort(400, f"missing fields: {need}")

    # SIGN tekshirish — docs’dagi formula bilan BIR XIL bo‘lishi shart:
    expected = sign_md5(data["epc_amount"], data["epc_currency_code"], data["epc_order_id"], data["epc_merchant_id"], EPC_SECRET)
    # expected = sign_hmac_sha256(data["epc_amount"], data["epc_currency_code"], data["epc_order_id"], data["epc_merchant_id"], EPC_SECRET)

    if data["epc_sign"] != expected:
        return abort(403, "bad sign")

    if data["epc_status"].lower() == "success":  # yoki 'paid' — docsdagi aniq qiymatga qarab
        # TODO: orderni paid qilish
        pass

    return "OK"

@app.get("/")
def index():
    return "OK"
