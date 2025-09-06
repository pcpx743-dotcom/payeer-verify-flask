
# --- ADD/REPLACE in app.py ---
import os, uuid, hashlib, hmac
from flask import Flask, render_template_string, request, abort

app = Flask(__name__)

EPC_MERCHANT_ID = "104375"
EPC_SECRET      = "yrGW2mWFLDjzTpbD"
ACTION_URL      = "https://api.epaycore.com/checkout/form"

SUCCESS_URL = os.getenv("SUCCESS_URL", "https://payeer-verify-flask.onrender.com/success")
CANCEL_URL  = os.getenv("FAIL_URL",    "https://payeer-verify-flask.onrender.com/fail")
STATUS_URL  = os.getenv("CALLBACK_URL","https://payeer-verify-flask.onrender.com/api/epaycore/webhook")

def sign_md5(amount, currency_code, order_id, merchant_id, secret):
    raw = f"{amount}:{currency_code}:{order_id}:{merchant_id}:{secret}"
    return hashlib.md5(raw.encode()).hexdigest(), raw


def sign_hmac_sha256(merchant_id: str, amount: str, currency_code: str, order_id: str, password: str) -> str:
    # EXACT formula: merchant_id:amount:currency:order_id:password  → sha256 hex (64)
    raw = f"{merchant_id}:{amount}:{currency_code}:{order_id}:{password}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest(), raw

@app.get("/pay/<amount>")
def pay(amount):
    algo = (request.args.get("algo") or "md5").lower()   # md5 | sha256
    order_id = "ORD-" + uuid.uuid4().hex[:10].upper()
    amt = f"{float(amount):.2f}"
    currency_code = "USD"

    if algo == "sha256":
        epc_sign, raw = sign_hmac_sha256(amt, currency_code, order_id, EPC_MERCHANT_ID, EPC_SECRET)
    else:
        epc_sign, raw = sign_md5(amt, currency_code, order_id, EPC_MERCHANT_ID, EPC_SECRET)

    fields = {
        "epc_merchant_id":   EPC_MERCHANT_ID,
        "epc_commission":    "1",           # Customer pays fee
        "epc_amount":        amt,
        "epc_currency_code": currency_code,
        "epc_order_id":      order_id,
        "epc_success_url":   SUCCESS_URL,
        "epc_cancel_url":    CANCEL_URL,
        "epc_status_url":    STATUS_URL,
        "epc_sign":          epc_sign,
    }

    html = f"""
    <html><body onload="document.forms[0].submit()" style="font-family:sans-serif;padding:16px">
      <h3>Redirecting to ePayCore checkout…</h3>
      <p>algo: {algo} | sign: {epc_sign} | raw: {raw}</p>
      <form method="post" action="{ACTION_URL}">
        {''.join(f'<input type="hidden" name="{k}" value="{v}"/>' for k,v in fields.items())}
        <noscript><button type="submit">Continue</button></noscript>
      </form>
    </body></html>
    """
    return render_template_string(html)

@app.get("/sign-preview")
def sign_preview():
    # Tez tekshiruv: siz kiritgan order_id/amount bilan sign satrini ko'rish
    amt = request.args.get("amount","9.99")
    order_id = request.args.get("order_id","ORD-PREVIEW")
    currency = request.args.get("currency","USD").upper()
    m5, raw_m5 = sign_md5(amt, currency, order_id, EPC_MERCHANT_ID, EPC_SECRET)
    s256, raw_s256 = sign_hmac_sha256(amt, currency, order_id, EPC_MERCHANT_ID, EPC_SECRET)
    return {
        "md5": {"raw": raw_m5, "sign": m5},
        "sha256": {"raw": raw_s256, "sign": s256},
        "used": {"merchant": EPC_MERCHANT_ID, "secret_present": bool(EPC_SECRET)}
    }

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


