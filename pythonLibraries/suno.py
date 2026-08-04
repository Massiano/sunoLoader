import json
import re
import requests
from bs4 import BeautifulSoup

def classify_url(url: str) -> str:
    if not url: return "unknown"
    if "suno.com/s/" in url: return "share_url"
    elif "suno.com/playlist/" in url: return "playlist_url"
    elif "suno.com/song/" in url: return "song_url"
    elif "suno.com" in url: return "suno_url"
    return "unknown"

def classify_content_heuristic(text: str) -> str:
    if not text: return "unknown"
    lower_text = text.lower()
    if "playlist" in lower_text or "clips" in lower_text or "playlist-container" in lower_text: return "playlist"
    elif "lyrics" in lower_text or "audio_url" in lower_text or "song-content" in lower_text: return "song"
    return "unknown"

def parse_song_html(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    data = {"title": None, "author": None, "lyrics": None, "metadata": {}}
    if soup.title and soup.title.string: data["title"] = soup.title.string.strip()
    else:
        h1_tag = soup.find("h1")
        if h1_tag: data["title"] = h1_tag.get_text(strip=True)
    author_meta = soup.find("meta", attrs={"name": ["author", "artist", "music:musician"]})
    if author_meta and author_meta.get("content"): data["author"] = author_meta["content"].strip()
    else:
        author_tag = soup.find(class_=lambda x: x and any(term in x.lower() for term in ["artist", "author", "singer"]))
        if author_tag: data["author"] = author_tag.get_text(strip=True)
    lyrics_container = soup.find(class_=lambda x: x and any(term in x.lower() for term in ["lyrics", "song-content", "body"]))
    if lyrics_container: data["lyrics"] = lyrics_container.get_text(separator="\n", strip=True)
    for meta in soup.find_all("meta"):
        name = meta.get("name") or meta.get("property")
        content = meta.get("content")
        if name and content: data["metadata"][name] = content
    return data

def parse_playlist_html(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    data = {"title": None, "description": None, "tracks": [], "metadata": {}}
    if soup.title and soup.title.string: data["title"] = soup.title.string.strip()
    else:
        h1_tag = soup.find("h1")
        if h1_tag: data["title"] = h1_tag.get_text(strip=True)
    desc_meta = soup.find("meta", attrs={"name": ["description"], "property": ["og:description"]})
    if desc_meta and desc_meta.get("content"): data["description"] = desc_meta["content"].strip()
    track_elements = soup.find_all(class_=lambda x: x and any(term in x.lower() for term in ["track", "song-item", "playlist-item"]))
    for track in track_elements:
        track_title = track.get_text(strip=True)
        if track_title: data["tracks"].append({"title": track_title})
    for meta in soup.find_all("meta"):
        name = meta.get("name") or meta.get("property")
        content = meta.get("content")
        if name and content: data["metadata"][name] = content
    return data

def resolve_share_url(share_url):
    try:
        response = requests.head(share_url, allow_redirects=True, timeout=10)
        return response.url
    except Exception: return share_url

def parse_suno_payload(rsc_result, html_content, resolved_url):
    url_type = classify_url(resolved_url)
    heuristic_type = classify_content_heuristic(html_content)
    
    html_metadata = {}
    if html_content:
        if url_type == "playlist_url" or heuristic_type == "playlist":
            html_metadata = parse_playlist_html(html_content)
        else:
            html_metadata = parse_song_html(html_content)

    if not rsc_result.get("is_rsc"):
        return {"resolved_url": resolved_url, "url_type": url_type, "heuristic_type": heuristic_type, "type": "unknown", "html_metadata": html_metadata, "raw": rsc_result}

    chunks = rsc_result.get("chunks", [])
    suno_data = {"resolved_url": resolved_url, "songs": [], "playlists": []}
    for chunk in chunks:
        content = chunk.get("content")
        if isinstance(content, dict):
            if "id" in content and "audio_url" in content: suno_data["songs"].append(content)
            elif "id" in content and "clips" in content: suno_data["playlists"].append(content)

    content_type = "playlist" if url_type == "playlist_url" or suno_data["playlists"] else ("song" if url_type == "song_url" or suno_data["songs"] else heuristic_type)
    return {"resolved_url": resolved_url, "url_type": url_type, "heuristic_type": heuristic_type, "type": content_type, "success": True, "html_metadata": html_metadata, "parsed_data": suno_data}
