import requests
from pythonLibraries.rsc import fetch_and_parse_comprehensive, parse_rsc_payload

def classify_suno_url(url: str) -> str:
    if not url: return "song"
    if "playlist" in url: return "playlist"
    return "song"

def process_suno_comprehensive(target_url):
    page_type = classify_suno_url(target_url)
    return fetch_and_parse_comprehensive(target_url, page_type)
