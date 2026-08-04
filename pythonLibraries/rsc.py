import json, re, requests
from bs4 import BeautifulSoup

def parse_rsc_payload(text):
    lines, parsed_chunks, rsc_pattern = text.split("\n"), [], re.compile(r"^([0-9a-f]+):(.*)$")
    for line in lines:
        match = rsc_pattern.match(line.strip())
        if match:
            chunk_id, content = match.groups()
            try: parsed_content = json.loads(content)
            except json.JSONDecodeError: parsed_content = content
            parsed_chunks.append({"id": chunk_id, "content": parsed_content})
    return parsed_chunks

def extract_html_header_data(soup):
    header_data = {"title": soup.title.string.strip() if soup.title and soup.title.string else None, "meta": {}}
    for meta in soup.find_all("meta"):
        name, prop, content = meta.get("name"), meta.get("property"), meta.get("content")
        key = name or prop
        if key and content: header_data["meta"][key] = content.strip()
    return header_data

def extract_html_dom_data(soup, page_type="song"):
    dom_data = {"page_type": page_type, "headings": [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])], "text_content": soup.get_text(separator=" ", strip=True)}
    if page_type == "playlist":
        dom_data["items"] = [item.get_text(strip=True) for item in soup.find_all(class_=lambda x: x and any(t in x.lower() for t in ["track", "song-item", "playlist-item"]))]
    else:
        lyrics_elem = soup.find(class_=lambda x: x and any(t in x.lower() for t in ["lyrics", "song-content"]))
        dom_data["lyrics"] = lyrics_elem.get_text(separator="\n", strip=True) if lyrics_elem else None
    return dom_data

def fetch_and_parse_comprehensive(target_url, page_type="song"):
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(target_url, headers=headers, timeout=10)
    resp.raise_for_status()
    html_text = resp.text
    soup = BeautifulSoup(html_text, "html.parser")
    
    html_header = extract_html_header_data(soup)
    html_dom = extract_html_dom_data(soup, page_type)
    
    # Extract RSC if present via embedded Next.js or direct stream
    rsc_chunks = []
    embedded_matches = re.findall(r'__next_f\.push\(\s*\[\s*\d+,\s*"(.*?)"\s*\]\s*\)', html_text)
    if embedded_matches:
        combined = "".join([m.encode().decode('unicode-escape') + "\n" for m in embedded_matches])
        rsc_chunks = parse_rsc_payload(combined)
    elif "text/x-component" in resp.headers.get("Content-Type", ""):
        rsc_chunks = parse_rsc_payload(html_text)

    return {"url": target_url, "page_type": page_type, "html_header": html_header, "html_dom": html_dom, "rsc_payload": rsc_chunks}
