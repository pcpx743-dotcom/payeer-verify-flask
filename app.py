from flask import Flask, Response

app = Flask(__name__)

TOKEN = "payeer_2256083421"       # fayl ichidagi aniq matn
FILENAME = "payeer_2256083421.txt"

@app.get("/")
def home():
    return "ok"

@app.get(f"/{FILENAME}")
def verify():
    return Response(TOKEN, mimetype="text/plain")

if __name__ == "__main__":
    # Render avtomatik PORT o'zgaruvchisidan foydalanadi,
    # lekin lokalda ham ishga tushadi.
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
