import os
import requests
from flask import Flask, send_from_directory, request, jsonify
from pythonLibraries.rsc import *
from pythonLibraries.suno import *

app = Flask(__name__, static_folder="static", static_url_path="")

@app.route("/")
def serve_index(): return send_from_directory(app.static_folder, "index.html")

@app.route("/api/parse-song", methods=["POST"])
def api_parse_song():
    """Proper workhorse endpoint to parse a Suno song URL using parseSongHTML."""
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url: 
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        resolved_url = resolve_share_url(target_url) if 'resolve_share_url' in globals() else target_url
        
        html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        html_content = html_response.text
        
        # Invoke the workhorse function imported from pythonLibraries.suno
        parsed_result = parseSongHTML(html_content)
            
        return jsonify({
            "status": "success",
            "url": target_url,
            "resolved_url": resolved_url,
            "data": parsed_result
        })
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/diagnostics", methods=["GET"])
def diagnostics():
    try:
        return jsonify(run_diagnostics_suite())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/process", methods=["POST"])
def process_url():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url: return jsonify({"error": "No URL provided"}), 400
    try:
        resolved_url = resolve_share_url(target_url) if 'resolve_share_url' in globals() else target_url
        rsc_result = fetch_and_parse_rsc(resolved_url) if 'fetch_and_parse_rsc' in globals() else {}
        html_content = ""
        try:
            html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            html_content = html_response.text
        except Exception: pass
        return jsonify(parse_suno_payload(rsc_result, html_content, resolved_url))
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/parse-comprehensive", methods=["POST"])
def api_parse_comprehensive():
    data = request.get_json() or {}
    url = data.get("url")
    if not url: return jsonify({"error": "No URL provided"}), 400
    try:
        result = process_suno_comprehensive(url) if 'process_suno_comprehensive' in globals() else fetch_and_parse_comprehensive(url)
        return jsonify(result)
    except Exception as e: return jsonify({"error": str(e)}), 500
        
@app.route("/test-parser-song-html", methods=["POST"])
def test_parser_song_html():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url: return jsonify({"error": "No URL provided"}), 400
    try:
        html_response = requests.get(target_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        html_content = html_response.text
        
        # Utilize the new suno.py functions depending on URL type classification
        url_type = classify_suno_url(target_url)
        if url_type == 'playlist':
            parsed_result = parse_suno_playlist(html_content)
        else:
            parsed_result = extract_song_info_simple(html_content)
            
        return jsonify({"url": target_url, "type": url_type, "parsed_result": parsed_result})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
