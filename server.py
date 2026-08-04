import os
from flask import Flask, send_from_directory, request, jsonify
from pythonLibraries.sunoUtility import parse_suno_content, resolve_share_url

app = Flask(__name__, static_folder="static", static_url_path="")

@app.route("/")
def serve_index(): return send_from_directory(app.static_folder, "index.html")

@app.route("/process", methods=["POST"])
def process_url():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url: return jsonify({"error": "No URL provided"}), 400
    try: return jsonify(parse_suno_content(target_url))
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
