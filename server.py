import os
import requests
from flask import Flask, send_from_directory, request, jsonify
from pythonLibraries.rsc import fetch_and_parse_rsc
from pythonLibraries.suno import resolve_share_url, parse_suno_payload

app = Flask(__name__, static_folder="static", static_url_path="")

@app.route("/")
def serve_index(): return send_from_directory(app.static_folder, "index.html")

@app.route("/process", methods=["POST"])
def process_url():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url: return jsonify({"error": "No URL provided"}), 400
    try:
        resolved_url = resolve_share_url(target_url)
        rsc_result = fetch_and_parse_rsc(resolved_url)
        html_content = ""
        try:
            html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            html_content = html_response.text
        except Exception: pass
        return jsonify(parse_suno_payload(rsc_result, html_content, resolved_url))
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/resolve", methods=["POST"])
def resolve_url_endpoint():
    data = request.get_json() or {}
    share_url = data.get("url")
    if not share_url: return jsonify({"error": "No URL provided"}), 400
    try: return jsonify({"resolved_url": resolve_share_url(share_url)})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
