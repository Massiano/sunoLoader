import json
import requests
from bs4 import BeautifulSoup
from pythonLibraries.rsc import fetch_and_parse_rsc

def parse_suno_song_html(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    metadata = {"title": None, "description": None, "audio_url": None, "image_url": None, "canonical_url": None}
    title_tag = soup.find("title")
    if title_tag: metadata["title"] = title_tag.get_text(strip=True)
    og_mappings = {"og:title": "title", "og:description": "description", "og:audio": "audio_url", "og:audio:secure_url": "audio_url", "og:image": "image_url", "og:url": "canonical_url"}
    for tag in soup.find_all("meta"):
        prop = tag.get("property") or tag.get("name")
        if prop in og_mappings: metadata[og_mappings[prop]] = tag.get("content", "").strip()
    next_data_script = soup.find("script", id="__NEXT_DATA__")
    if next_data_script:
        try: metadata["next_js_payload"] = json.loads(next_data_script.string)
        except (json.JSONDecodeError, TypeError): pass
    return metadata

def resolve_share_url(share_url):
    try:
        response = requests.head(share_url, allow_redirects=True, timeout=10)
        return response.url
    except Exception: return share_url

def parse_suno_content(target_url):
    resolved_url = resolve_share_url(target_url)
    
    # Use rsc.py to handle the heavy lifting of fetching and parsing the RSC/HTML payload
    rsc_result = fetch_and_parse_rsc(resolved_url)
    
    # Fetch raw HTML separately just for BeautifulSoup metadata parsing
    html_metadata = {}
    try:
        html_response = requests.get(resolved_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        html_metadata = parse_suno_song_html(html_response.text)
    except Exception: pass

    if not rsc_result.get("is_rsc"):
        return {"resolved_url": resolved_url, "type": "unknown", "html_metadata": html_metadata, "raw": rsc_result}
    
    chunks = rsc_result.get("chunks", [])
    suno_data = {"resolved_url": resolved_url, "songs": [], "playlists": []}
    
    for chunk in chunks:
        content = chunk.get("content")
        if isinstance(content, dict):
            if "id" in content and "audio_url" in content: suno_data["songs"].append(content)
            elif "id" in content and "clips" in content: suno_data["playlists"].append(content)
            
    content_type = "song" if "/song/" in resolved_url else ("playlist" if "/playlist/" in resolved_url else "generic")
    return {"resolved_url": resolved_url, "type": content_type, "success": True, "html_metadata": html_metadata, "parsed_data": suno_data}
