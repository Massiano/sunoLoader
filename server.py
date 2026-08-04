import os
import requests
from flask import Flask, send_from_directory, request, jsonify
from bs4 import BeautifulSoup
from pythonLibraries.rsc import fetch_and_parse_rsc
from pythonLibraries.suno import resolve_share_url, parse_suno_payload, run_diagnostics_suite

app = Flask(__name__, static_folder="static", static_url_path="")

@app.route("/")
def serve_index(): return send_from_directory(app.static_folder, "index.html")

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
        resolved_url = resolve_share_url(target_url)
        rsc_result = fetch_and_parse_rsc(resolved_url)
        html_content = ""
        try:
            html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            html_content = html_response.text
        except Exception: pass
        return jsonify(parse_suno_payload(rsc_result, html_content, resolved_url))
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/test-parser-song-html", methods=["POST"])
def test_parser_song_html():
    data = request.get_json() or {}
    target_url = data.get("url")
    if not target_url: return jsonify({"error": "No URL provided"}), 400
    try:
        resolved_url = resolve_share_url(target_url)
        html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        html_content = html_response.text
        
        soup = BeautifulSoup(html_content, "html.parser")
        songs_data = []
        for item in soup.find_all("li"):
            title_elem = item.select_one(".clip-title-wrapper a")
            title = title_elem.get_text(strip=True) if title_elem else None
            song_id = title_elem["href"].split("/song/")[-1] if title_elem and title_elem.has_attr("href") and "/song/" in title_elem["href"] else None
            author_elem = item.select_one("a[href^='/@']")
            author = author_elem.get_text(strip=True) if author_elem else None
            genre_elem = item.select_one("a[href^='/style/']")
            genre_prompt = genre_elem.get_text(strip=True) if genre_elem else None
            plays = next((span.get_text(strip=True) for span in item.find_all("span") if span.find("svg") and span.get_text(strip=True).isdigit()), None)
            songs_data.append({"title": title, "author": author, "genre_or_prompt": genre_prompt, "song_id": song_id, "plays": plays})
            
        return jsonify({"url": resolved_url, "parsed_result": songs_data})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
```[cite: 1, 2, 3]
