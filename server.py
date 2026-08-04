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
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url: 
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        resolved_url = resolve_share_url(target_url) if 'resolve_share_url' in globals() else target_url
        
        html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        html_content = html_response.text
        
        func_name = 'parseSongHTML' if 'parseSongHTML' in globals() else ('extract_song_info_simple' if 'extract_song_info_simple' in globals() else None)
        parsed_result = globals()[func_name](html_content) if func_name else {"error": "No suitable parser found"}
            
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
        return jsonify(run_diagnostics_suite() if 'run_diagnostics_suite' in globals() else {"status": "ok"})
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
        return jsonify(parse_suno_payload(rsc_result, html_content, resolved_url) if 'parse_suno_payload' in globals() else {})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/classify-url", methods=["POST"])
def api_classify_url():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        resolved_url = resolve_share_url(target_url) if 'resolve_share_url' in globals() else target_url
        url_type = classify_url(resolved_url) if 'classify_url' in globals() else "unknown"
        
        # Extract unique ID based on type
        item_id = None
        if "/song/" in resolved_url:
            item_id = resolved_url.split("/song/")[-1].split("?")[0]
        elif "/playlist/" in resolved_url:
            item_id = resolved_url.split("/playlist/")[-1].split("?")[0]
        elif "/s/" in resolved_url:
            item_id = resolved_url.split("/s/")[-1].split("?")[0]

        return jsonify({
            "status": "success",
            "original_url": target_url,
            "resolved_url": resolved_url,
            "url_type": url_type,
            "item_id": item_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/classify-and-parse", methods=["POST"])
def api_classify_and_parse():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        resolved_url = resolve_share_url(target_url) if 'resolve_share_url' in globals() else target_url
        url_type = classify_url(resolved_url) if 'classify_url' in globals() else "unknown"
        
        # Fetch target HTML content
        html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        html_content = html_response.text
        
        # Heuristic determination if generic or share URL
        heuristic_type = classify_content_heuristic(html_content) if 'classify_content_heuristic' in globals() else "song"
        target_category = "playlist" if "playlist" in url_type or heuristic_type == "playlist" else "song"

        # Apply both HTML parsers
        song_html_res = parse_song_html(html_content) if 'parse_song_html' in globals() else {}
        playlist_html_res = parse_playlist_html(html_content) if 'parse_playlist_html' in globals() else {}

        # Apply RSC parser if available
        rsc_res = {}
        if 'fetch_and_parse_rsc' in globals():
            rsc_res = fetch_and_parse_rsc(resolved_url)

        return jsonify({
            "status": "success",
            "resolved_url": resolved_url,
            "classified_type": target_category,
            "url_type": url_type,
            "heuristic_type": heuristic_type,
            "html_parser_results": {
                "song_parser": song_html_res,
                "playlist_parser": playlist_html_res
            },
            "rsc_parser_result": rsc_res
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
