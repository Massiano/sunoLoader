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

@app.route("/api/parse-comprehensive", methods=["POST"])
def api_parse_comprehensive():
    data = request.get_json() or {}
    url = data.get("url")
    if not url: return jsonify({"error": "No URL provided"}), 400
    try:
        result = process_suno_comprehensive(url) if 'process_suno_comprehensive' in globals() else (fetch_and_parse_comprehensive(url) if 'fetch_and_parse_comprehensive' in globals() else {})
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
        
        url_type = classify_suno_url(target_url) if 'classify_suno_url' in globals() else 'song'
        if url_type == 'playlist':
            parsed_result = parse_suno_playlist(html_content) if 'parse_suno_playlist' in globals() else {}
        else:
            func = parseSongHTML if 'parseSongHTML' in globals() else extract_song_info_simple
            parsed_result = func(html_content) if func else {}
            
        return jsonify({"url": target_url, "type": url_type, "parsed_result": parsed_result})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/dual-parse", methods=["POST"])
def api_dual_parse():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        resolved_url = resolve_share_url(target_url) if 'resolve_share_url' in globals() else target_url
        
        html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        html_content = html_response.text
        
        html_func = parseSongHTML if 'parseSongHTML' in globals() else extract_song_info_simple
        html_parsed_result = html_func(html_content) if html_func else {}
        
        rsc_parsed_result = None
        if 'fetch_and_parse_rsc' in globals():
            rsc_parsed_result = fetch_and_parse_rsc(resolved_url)
        elif 'parse_suno_clip_from_rsc' in globals():
            rsc_parsed_result = parse_suno_clip_from_rsc(html_content)
            
        return jsonify({
            "status": "success",
            "url": target_url,
            "resolved_url": resolved_url,
            "html_parser_result": html_parsed_result,
            "rsc_parser_result": rsc_parsed_result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
