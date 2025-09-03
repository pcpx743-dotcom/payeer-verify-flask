from flask import Flask, Response
import os

app = Flask(__name__)

TOKEN = "payeer_2256083421"
FILENAME = "payeer_2256083421.txt"

@app.get("/")
def home():
    return "ok"

@app.get(f"/{FILENAME}")
def verify():
    return Response(TOKEN, mimetype="text/plain")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render PORT muhit o'zgaruvchisini oladi
    app.run(host="0.0.0.0", port=port)

