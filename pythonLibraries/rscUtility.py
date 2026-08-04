import json
import re
import requests

def parse_rsc_payload(text):
    lines = text.split("\n")
    parsed_chunks = []
    rsc_pattern = re.compile(r"^([0-9a-f]+):(.*)$")
    for line in lines:
        match = rsc_pattern.match(line.strip())
        if match:
            chunk_id, content = match.groups()
            try: parsed_content = json.loads(content)
            except json.JSONDecodeError: parsed_content = content
            parsed_chunks.append({"id": chunk_id, "content": parsed_content})
    return parsed_chunks

def fetch_and_parse_rsc(target_url):
    headers = {"RSC": "1", "User-Agent": "Mozilla/5.0"}
    response = requests.get(target_url, headers=headers, timeout=10)
    response.raise_for_status()
    content = response.text
    content_type = response.headers.get("Content-Type", "")
    is_direct_rsc = "text/x-component" in content_type or bool(re.search(r"^[0-9a-f]+:", content, re.MULTILINE))
    if is_direct_rsc:
        return {"success": True, "is_rsc": True, "source": "direct_stream", "message": "Direct RSC stream successfully detected and parsed!", "chunks": parse_rsc_payload(content)}
    embedded_matches = re.findall(r'__next_f\.push\(\s*\[\s*\d+,\s*"(.*?)"\s*\]\s*\)', content)
    if embedded_matches:
        combined_rsc_text = "".join([m.encode().decode('unicode-escape') + "\n" for m in embedded_matches])
        parsed_data = parse_rsc_payload(combined_rsc_text)
        if parsed_data:
            return {"success": True, "is_rsc": True, "source": "embedded_html", "message": "Embedded RSC payload found inside HTML and parsed!", "chunks": parsed_data}
    return {"success": True, "is_rsc": False, "message": "Fetched successfully, but no direct or embedded RSC blob was found.", "raw_preview": content[:500]}
