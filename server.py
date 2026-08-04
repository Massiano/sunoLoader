import json
import re
from flask import Flask, send_from_directory, request, jsonify
import requests

app = Flask(__name__, static_folder="static", static_url_path="")

def parse_rsc_payload(text):
    """
    Basic parser for React Server Components (RSC) payload.
    """
    lines = text.split("\n")
    parsed_chunks = []
    rsc_pattern = re.compile(r"^([0-9a-f]+):(.*)$")
    
    for line in lines:
        match = rsc_pattern.match(line.strip())
        if match:
            chunk_id, content = match.groups()
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError:
                parsed_content = content
                
            parsed_chunks.append({
                "id": chunk_id,
                "content": parsed_content
            })
            
    return parsed_chunks

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/process", methods=["POST"])
def process_url():
    data = request.get_json()
    target_url = data.get("url")
    
    if not target_url:
        return jsonify({"error": "No URL provided"}), 400
        
    try:
        headers = {"RSC": "1"}
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        content = response.text
        is_rsc = "text/x-component" in response.headers.get("Content-Type", "") or bool(re.search(r"^[0-9a-f]+:", content, re.MULTILINE))
        
        if not is_rsc:
            return jsonify({
                "success": True,
                "is_rsc": False,
                "message": "Fetched successfully, but no RSC blob signature was detected.",
                "raw_preview": content[:500]
            })
            
        parsed_data = parse_rsc_payload(content)
        
        return jsonify({
            "success": True,
            "is_rsc": True,
            "message": "RSC blob successfully detected and parsed!",
            "chunks": parsed_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
