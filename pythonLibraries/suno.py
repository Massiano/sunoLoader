import json
import re
import requests
from pythonLibraries.rscUtilities import fetch_and_parse_rsc

def resolve_share_url(share_url):
    try:
        response = requests.head(share_url, allow_redirects=True, timeout=10)
        return response.url
    except Exception:
        return share_url

def parse_suno_content(target_url):
    resolved_url = resolve_share_url(target_url)
    result = fetch_and_parse_rsc(resolved_url)
    if not result.get("is_rsc"): return {"resolved_url": resolved_url, "type": "unknown", "raw": result}
    
    chunks = result.get("chunks", [])
    suno_data = {"resolved_url": resolved_url, "songs": [], "playlists": []}
    
    for chunk in chunks:
        content = chunk.get("content")
        if isinstance(content, dict):
            if "id" in content and "audio_url" in content: suno_data["songs"].append(content)
            elif "id" in content and "clips" in content: suno_data["playlists"].append(content)
            
    content_type = "song" if "/song/" in resolved_url else ("playlist" if "/playlist/" in resolved_url else "generic")
    return {"resolved_url": resolved_url, "type": content_type, "success": True, "parsed_data": suno_data}
