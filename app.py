import os, re
from flask import Flask, send_from_directory, abort, Response

app = Flask(__name__)

# 1) Sog'liq tekshiruvi
@app.get("/")
def home():
    return "OK"

# 2) Domen-verifikatsiya fayllarini ildizda xizmat qilish
#    /enot_xxxxxxxx.html kabi so'rovlarni ./verifications/<file> dan beradi
@app.get("/<path:filename>")
def serve_verification(filename: str):
    # Faqat HTML fayllar va xavfsiz nomlar
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.html", filename):
        abort(404)

    base_dir = os.path.join(app.root_path, "verifications")
    file_path = os.path.join(base_dir, filename)

    # Variant A: repoga qo'yilgan faylni berish
    if os.path.isfile(file_path):
        return send_from_directory(base_dir, filename, mimetype="text/html")

    # Variant B: ENV orqali berish (mas: ENOT_2C0329D0_HTML="<html>...</html>")
    env_key = filename.upper().replace(".", "_")
    content = os.getenv(env_key)
    if content:
        return Response(content, mimetype="text/html")

    abort(404)


if __name__ == "__main__":
    # Render PORT env bilan ishlaydi
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
