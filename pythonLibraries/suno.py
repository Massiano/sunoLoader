import json
import re
import requests
from bs4 import BeautifulSoup
from pythonLibraries.rsc import parse_rsc_payload

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

def parse_suno_song_HTML(html):
    soup = BeautifulSoup(html, "html.parser")
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
    return songs_data

def parse_song_html(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    data = {"title": None, "author": None, "lyrics": None, "body_text_sample": None, "metadata": {}}
    
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
    
    body_tag = soup.find("body")
    if body_tag:
        full_text = body_tag.get_text(separator=" ", strip=True)
        data["body_text_sample"] = full_text[:1000]
        
    for meta in soup.find_all("meta"):
        name = meta.get("name") or meta.get("property")
        content = meta.get("content")
        if name and content: data["metadata"][name] = content
    return data

def parse_playlist_html(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    data = {"title": None, "description": None, "tracks": [], "body_text_sample": None, "metadata": {}}
    
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
        
    body_tag = soup.find("body")
    if body_tag:
        full_text = body_tag.get_text(separator=" ", strip=True)
        data["body_text_sample"] = full_text[:1000]
        
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

def run_diagnostics_suite() -> dict:
    test_results = {}
    try:
        sample_url_class = classify_url("https://suno.com/s/My0OwL2naY5TSYkD")
        test_results["url_classifier"] = "PASS" if sample_url_class == "share_url" else "FAIL"
    except Exception as e: test_results["url_classifier"] = f"FAIL: {str(e)}"

    try:
        sample_heuristic = classify_content_heuristic("<html><body><div class='lyrics'>Hello world</div></body></html>")
        test_results["heuristic_classifier"] = "PASS" if sample_heuristic == "song" else "FAIL"
    except Exception as e: test_results["heuristic_classifier"] = f"FAIL: {str(e)}"

    try:
        sample_rsc_text = '0:{"id":"test-123","audio_url":"https://cdn.suno.ai/test.mp3"}'
        parsed = parse_rsc_payload(sample_rsc_text)
        test_results["rsc_payload_parser"] = "PASS" if len(parsed) == 1 and parsed[0]["id"] == "0" else "FAIL"
    except Exception as e: test_results["rsc_payload_parser"] = f"FAIL: {str(e)}"

    try:
        sample_html = "<html><head><title>Test Song</title><meta name='author' content='Test Artist'></head><body><h1>Heading</h1><div class='lyrics'>Test Lyrics Body Content</div></body></html>"
        song_parsed = parse_song_html(sample_html)
        test_results["song_html_parser"] = "PASS" if song_parsed["title"] == "Test Song" and song_parsed["body_text_sample"] is not None else "FAIL"
    except Exception as e: test_results["song_html_parser"] = f"FAIL: {str(e)}"

    try:
        sample_playlist_html = "<html><head><title>Test Playlist</title></head><body><div class='track'>Track 1</div></body></html>"
        playlist_parsed = parse_playlist_html(sample_playlist_html)
        test_results["playlist_html_parser"] = "PASS" if playlist_parsed["title"] == "Test Playlist" and len(playlist_parsed["tracks"]) == 1 else "FAIL"
    except Exception as e: test_results["playlist_html_parser"] = f"FAIL: {str(e)}"

    try:
        sample_list_html = "<html><body><ul><li><div class='clip-title-wrapper'><a href='/song/123'>Test</a></div><a href='/@artist'>Author</a><a href='/style/pop'>Pop</a><span><svg></svg>100</span></li></ul></body></html>"
        list_parsed = parse_suno_song_HTML(sample_list_html)
        test_results["suno_song_html_parser"] = "PASS" if len(list_parsed) == 1 and list_parsed[0]["song_id"] == "123" else "FAIL"
    except Exception as e: test_results["suno_song_html_parser"] = f"FAIL: {str(e)}"

    overall_status = "healthy" if all(v == "PASS" for v in test_results.values()) else "degraded"
    return {"status": overall_status, "live_tests": test_results}
```[cite: 4]
