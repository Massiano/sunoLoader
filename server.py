import os
import requests
from flask import Flask, send_from_directory, request, jsonify
from pythonLibraries.rsc import parse_rsc_payload, extract_html_header_data, fetch_and_parse_comprehensive
from pythonLibraries.suno import (
    classify_suno_url,
    extract_suno_id,
    parseSongHTML,
    parse_suno_clip_from_rsc,
    parsePlaylistHTML,
    parsePlaylistRSC
)

# Aliases for consistent naming conventions across modules
classify_url = classify_suno_url
parse_song_html = parseSongHTML
parse_playlist_html = parsePlaylistHTML

app = Flask(__name__, static_folder="static", static_url_path="")

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/classify-url", methods=["POST"])
def api_classify_url():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        url_type = classify_url(target_url)
        item_id = extract_suno_id(target_url)

        return jsonify({
            "status": "success",
            "original_url": target_url,
            "url_type": url_type,
            "item_id": item_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/parse-song", methods=["POST"])
def api_parse_song():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        # Use comprehensive fetch from rsc.py to get metadata and RSC chunks
        comp_data = fetch_and_parse_comprehensive(target_url, page_type="song")
        html_content = comp_data.get("html_dom", "")
        
        # Parse standard HTML elements
        html_parsed = parse_song_html(html_content)
        
        # Parse RSC payload for advanced clip data if available
        rsc_clip_data = None
        for chunk in comp_data.get("rsc_payload", []):
            content_str = str(chunk.get("content", ""))
            if '"clip":' in content_str:
                res = parse_suno_clip_from_rsc(content_str)
                if res:
                    rsc_clip_data = res
                    break

        return jsonify({
            "status": "success",
            "url": target_url,
            "html_data": html_parsed,
            "rsc_clip_data": rsc_clip_data,
            "header_meta": comp_data.get("html_header")
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
        url_type = classify_url(target_url)
        
        # Fetch comprehensive payload via rsc.py
        page_type = "playlist" if url_type == "playlist" else "song"
        comp_data = fetch_and_parse_comprehensive(target_url, page_type=page_type)
        html_content = comp_data.get("html_dom", "")

        # Run HTML Parsers
        song_html_res = parse_song_html(html_content)
        playlist_html_res = parse_playlist_html(html_content)

        # Run RSC Parsers depending on content type
        rsc_result = {}
        for chunk in comp_data.get("rsc_payload", []):
            content_str = str(chunk.get("content", ""))
            if page_type == "playlist" and '"playlist":' in content_str:
                rsc_result = parsePlaylistRSC(content_str)
                break
            elif page_type == "song" and '"clip":' in content_str:
                rsc_result = parse_suno_clip_from_rsc(content_str)
                break

        return jsonify({
            "status": "success",
            "resolved_url": target_url,
            "classified_type": page_type,  # <--- Ensured this key is explicitly sent
            "url_type": url_type,
            "html_parser_results": {
                "song_parser": song_html_res,
                "playlist_parser": playlist_html_res
            },
            "rsc_parser_result": rsc_result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/diagnostics", methods=["GET"])
def diagnostics():
    return jsonify({"status": "ok", "message": "Server components running smoothly."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
