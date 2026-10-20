"""Local web app. Runs on this computer only, no internet needed.

    python app.py            # then open http://127.0.0.1:7860
"""
import argparse

from flask import Flask, jsonify, render_template, request

from textassist import LANGUAGES, STYLES, TextAssistant

app = Flask(__name__)
assistant = TextAssistant()
MAX_CHARS = 8000


def _text() -> str:
    text = (request.get_json(silent=True) or {}).get("text", "")
    if len(text) > MAX_CHARS:
        raise ValueError(f"ข้อความยาวเกิน {MAX_CHARS} ตัวอักษร")
    return text


@app.errorhandler(Exception)
def handle_error(e):
    return jsonify(error=str(e)), 400


@app.get("/")
def index():
    return render_template("index.html", styles=STYLES, languages=LANGUAGES)


@app.get("/api/status")
def status():
    return jsonify(assistant.status())


@app.post("/api/correct")
def correct():
    return jsonify(assistant.correct(_text()).to_dict())


@app.post("/api/style")
def style():
    body = request.get_json(silent=True) or {}
    styles = body.get("styles") or [body.get("style", "polite")]
    gender = body.get("gender", "neutral")
    text = _text()
    return jsonify({s: assistant.rewrite(text, s, gender).to_dict() for s in styles})


@app.post("/api/translate")
def translate():
    body = request.get_json(silent=True) or {}
    glossary = {}
    for line in (body.get("glossary") or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() and v.strip():
                glossary[k.strip()] = v.strip()
    r = assistant.translate(_text(), target=body.get("target", "en"), source=body.get("source", "auto"),
                            glossary=glossary or None, style=body.get("style") or None,
                            back_translate=bool(body.get("back")))
    return jsonify(r.to_dict())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow other devices on your network")
    args = ap.parse_args()
    print(f"Open http://{args.host}:{args.port}  (models load on first use, ~10-30 s)")
    app.run(host=args.host, port=args.port, threaded=True)
