import os, uuid, hashlib, hmac
from urllib.parse import urlencode
from flask import Flask, request, render_template_string, redirect, url_for, abort
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

SCI_MERCHANT  = os.getenv("SCI_MERCHANT")
SCI_NAME      = os.getenv("SCI_NAME")
SCI_PASSWORD  = os.getenv("SCI_PASSWORD")
SCI_ACTION    = os.getenv("SCI_ACTION_URL", "https://pay.epaycore.com/sci").rstrip("/")
SIGN_ALGO     = (os.getenv("SCI_SIGN_ALGO") or "md5").lower()

SUCCESS_URL   = os.getenv("SUCCESS_URL")
FAIL_URL      = os.getenv("FAIL_URL")
CALLBACK_URL  = os.getenv("CALLBACK_URL")

assert SCI_MERCHANT and SCI_NAME and SCI_PASSWORD, "SCI env larini to'ldiring (.env)"
assert SUCCESS_URL and FAIL_URL and CALLBACK_URL,  "SUCCESS/FAIL/CALLBACK URL larni .env da to'ldiring"

# Demo uchun oddiy "order storage" (prod-da DB ishlating)
ORDERS = {}  # order_id -> {"amount": "...", "currency": "usd", "status": "new|paid|fail"}

def sign_md5(amount, currency, order_id, merchant, sci_name, secret):
    # Ko'p SCI larda shunday formula bo'ladi: md5("amount:currency:order_id:merchant:sci_name:secret")
    s = f"{amount}:{currency}:{order_id}:{merchant}:{sci_name}:{secret}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def sign_sha256_hmac(params: dict, secret: str):
    # Ayrim SCI larda sorted query-string + HMAC-SHA256 ishlatiladi
    items = sorted(params.items(), key=lambda x: x[0])
    qs = urlencode(items)
    return hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()

def make_sign_for_request(params: dict) -> str:
    if SIGN_ALGO == "md5":
        return sign_md5(params["amount"], params["currency"], params["order_id"],
                        params["merchant"], params["sci_name"], SCI_PASSWORD)
    else:
        # sha256/hmac
        return sign_sha256_hmac({
            "amount":   params["amount"],
            "callback_url": params["callback_url"],
            "currency": params["currency"],
            "description": params.get("description",""),
            "fail_url": params["fail_url"],
            "merchant": params["merchant"],
            "order_id": params["order_id"],
            "sci_name": params["sci_name"],
            "success_url": params["success_url"],
        }, SCI_PASSWORD)

def make_sign_for_webhook(data: dict) -> str:
    # Webhook uchun ham Integrationdagi formula bilan BIR XIL bo'lishi kerak.
    # md5 varianti:
    if SIGN_ALGO == "md5":
        return sign_md5(data["amount"], data["currency"], data["order_id"],
                        SCI_MERCHANT, SCI_NAME, SCI_PASSWORD)
    else:
        # sha256/hmac varianti: webhookdan kelgan maydonlarni xuddi yuqoridagi tartibda yig'ing
        src = {
            "amount":   data["amount"],
            "currency": data["currency"],
            "order_id": data["order_id"],
            "merchant": SCI_MERCHANT,
            "sci_name": SCI_NAME,
        }
        return sign_sha256_hmac(src, SCI_PASSWORD)

@app.get("/")
def index():
    return "OK: /pay/9.99 ni sinab ko'ring"

@app.get("/pay/<amount>")
def start_payment(amount):
    # 1) order yaratamiz
    order_id = "ORD-" + uuid.uuid4().hex[:10].upper()
    currency = "usd"
    description = "BigoLive Diamond"

    ORDERS[order_id] = {"amount": f"{float(amount):.2f}", "currency": currency, "status": "new"}

    # 2) SCI post parametrlari
    params = {
        "merchant": SCI_MERCHANT,
        "sci_name": SCI_NAME,
        "amount": ORDERS[order_id]["amount"],
        "currency": currency,
        "order_id": order_id,
        "description": description,
        "success_url": SUCCESS_URL,
        "fail_url": FAIL_URL,
        "callback_url": CALLBACK_URL,
        # "email": "client@example.com",  # ixtiyoriy
    }
    params["sign"] = make_sign_for_request(params)

    # 3) Auto-submit form (POST to SCI_ACTION)
    html = f"""
    <html><body onload="document.forms[0].submit()">
      <form action="{SCI_ACTION}" method="post">
        {"".join(f'<input type="hidden" name="{k}" value="{v}"/>' for k,v in params.items())}
        <noscript><button type="submit">Continue</button></noscript>
      </form>
    </body></html>
    """
    return render_template_string(html)

@app.route("/success")
def success():
    # Foydalanuvchi shu yerga qaytadi (brauzer)
    # order_id query/body orqali kelmasligi ham mumkin — agar Integration da qaytarilsa, ko'rsatamiz.
    order_id = request.args.get("order_id") or request.form.get("order_id")
    status = ORDERS.get(order_id, {}).get("status") if order_id else "unknown"
    return f"SUCCESS page. order_id={order_id}, local_status={status}"

@app.route("/fail")
def fail():
    order_id = request.args.get("order_id") or request.form.get("order_id")
    if order_id in ORDERS:
        ORDERS[order_id]["status"] = "fail"
    return f"FAIL page. order_id={order_id}"

@app.post("/api/epaycore/webhook")
def epaycore_webhook():
    # ePayCore server-to-server: form-encoded yoki JSON bo'lishi mumkin
    data = request.form.to_dict() or (request.get_json(silent=True) or {})
    # kutiladigan maydonlar nomi SCI'ga qarab farq qiladi; odatda: order_id, amount, currency, status, sign
    required = ["order_id", "amount", "currency", "status", "sign"]
    if not all(k in data for k in required):
        return abort(400, f"missing fields: need {required}, got {list(data.keys())}")

    # SIGN tekshiruv
    expected = make_sign_for_webhook(data)
    if data.get("sign") != expected:
        return abort(403, "bad sign")

    oid = data["order_id"]
    if oid not in ORDERS:
        # Agar orderni oldindan yaratmagan bo'lsak ham OK; prod-da DB dan qidiriladi
        ORDERS[oid] = {"amount": data["amount"], "currency": data["currency"], "status": "new"}

    if data["status"].lower() == "paid":
        ORDERS[oid]["status"] = "paid"
    elif data["status"].lower() in ("failed", "canceled", "cancelled"):
        ORDERS[oid]["status"] = "fail"

    return "OK"

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))



