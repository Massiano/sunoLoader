import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def classify_suno_url(url):
    if not url or not isinstance(url, str):
        return 'unknown'
    
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    
    if 'suno.com' not in host and 'suno.ai' not in host:
        return 'unknown'
    
    path = parsed.path.strip('/')
    
    if path.startswith('@'):
        return 'share'
    if path.startswith('playlist/'):
        return 'playlist'
    if path.startswith('song/'):
        return 'song'
    if path.startswith('s/'):
        return 'short_link'
    if path == 'create':
        return 'create'
    if path == 'me':
        return 'library'
    if path == 'explore':
        return 'explore'
    if path == 'search':
        return 'search'
    
    return 'unknown'

def extract_suno_id(url):
    if not url or not isinstance(url, str):
        return None
    
    path = urlparse(url).path.strip('/')
    
    if path.startswith('song/'):
        return path[5:].split('/')[0]
    if path.startswith('playlist/'):
        return path[9:].split('/')[0]
    if path.startswith('s/'):
        return path[2:].split('/')[0]
    if path.startswith('@'):
        return path[1:].split('/')[0]
    
    return None

def parseSongHTML(html_string):
  soup = BeautifulSoup(html_string, "html.parser")

  og_title = soup.find("meta", property="og:title")
  title = og_title["content"] if og_title else None

  canonical_link = soup.find("link", rel="canonical")
  song_url = canonical_link["href"] if canonical_link else None
  song_id = song_url.split("/")[-1] if song_url else None

  og_image = soup.find("meta", property="og:image")
  cover_image = og_image["content"] if og_image else None

  meta_desc = soup.find("meta", attrs={"name": "description"})
  desc_text = meta_desc["content"] if meta_desc else ""

  author_name = None
  author_handle = None

  if desc_text:
    match = re.search(r"by\s+(.*?)\s+\((@[\w\d_]+)\)", desc_text)
    if match:
      author_name = match.group(1).strip()
      author_handle = match.group(2).strip()

  page_title = soup.find("title")
  page_title_text = page_title.text.strip() if page_title else None

  return {      "title": title,      "author": author_name,      "author_handle": author_handle,      "song_id": song_id,      "song_url": song_url,      "cover_image": cover_image,      "page_title": page_title_text,  }

def parse_suno_clip_from_rsc(rsc_payload_string):
    try:
        lines = rsc_payload_string.split('\n')
        for line in lines:
            if '"clip":' in line:
                json_start_index = line.find('{')
                if json_start_index != -1:
                    json_str = line[json_start_index:]
                    parsed_data = json.loads(json_str)
                    clip = parsed_data.get('clip') or parsed_data
                    
                    if clip and 'id' in clip:
                        result = {
                            "id": clip.get("id"),"title": clip.get("title"),"duration": clip.get("duration"),"caption": clip.get("metadata", {}).get("prompt") or clip.get("caption"),
                            "tags": clip.get("metadata", {}).get("tags"),"modelName": clip.get("model_name"),"isExplicit": clip.get("is_explicit"),"createdAt": clip.get("created_at"),
                            "artist": {"displayName": clip.get("display_name"),"handle": clip.get("handle"),"userId": clip.get("user_id"),"avatarUrl": clip.get("image_url")},
                            "assets": {"audioUrl": clip.get("audio_url"),"videoUrl": clip.get("video_url"),"imageUrl": clip.get("image_url") },
                            "stats": { "playCount": clip.get("play_count"), "upvoteCount": clip.get("upvote_count"), "commentCount": clip.get("comment_count") }
                        }
                        return json.dumps(result, separators=(',', ':'))
        
        match = re.search(r'"clip"\s*:\s*({.+?})\s*,\s*"action_config"', rsc_payload_string, re.DOTALL)
        if match:
            clip = json.loads(match.group(1))
            return json.dumps(clip, separators=(',', ':'))
            
        return None
    except Exception as error:
        print(f"Failed to parse RSC payload for clip info: {error}")
        return None

def parsePlaylistHTML( string ):
    return

def parsePlaylistRSC ( string ):
    return
