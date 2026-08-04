import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def classify_suno_url(url):
    if not url or not isinstance(url, str):
        return 'unknown'
    
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    if path.startswith('@'):
        return 'share'
    elif path.startswith('playlist/'):
        return 'playlist'
    elif path.startswith('song/'):
        return 'song'
    else:
        return 'unknown'

def extract_song_info_simple(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, 'html.parser')
    result = {'title': None, 'author': None, 'author_handle': None, 'song_id': None}
    for script in soup.find_all('script'):
        if not script.string: continue
        script_text = script.string
        if 'display_name' in script_text and 'handle' in script_text and 'title' in script_text:
            id_match = re.search(r'"id":"([^"]+?)"', script_text)
            if id_match: result['song_id'] = id_match.group(1)
            title_match = re.search(r'"title":"([^"]+?)"', script_text)
            if title_match: result['title'] = title_match.group(1)
            author_match = re.search(r'"display_name":"([^"]+?)"', script_text)
            if author_match: result['author'] = author_match.group(1)
            handle_match = re.search(r'"handle":"([^"]+?)"', script_text)
            if handle_match: result['author_handle'] = handle_match.group(1)
            if all(result.values()): return result
    if not result['title'] or not result['author']:
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            match = re.match(r'^(.*?)\s+by\s+(.*?)\s*[|•-]', title_tag.string)
            if match:
                result['title'] = result['title'] or match.group(1).strip()
                if not result['author']: result['author'] = match.group(2).strip()
    if not result['title']:
        og_title = soup.find('meta', {'property': 'og:title'})
        if og_title and og_title.get('content'): result['title'] = og_title['content']
    return result

import json
import re
from typing import List, Dict

def parse_suno_playlist(html_content: str) -> List[Dict]:
    songs = []
    
    json_match = re.search(r'{"playlist":\s*{[^}]+(?:{[^}]*}[^}]*)*}}', html_content)
    
    if not json_match:
        return _extract_from_html_fallback(html_content)
    
    try:
        json_str = json_match.group(0).replace('\\"', '"').replace('\\\\', '\\')
        data = json.loads(json_str)
        clips = data.get('playlist', {}).get('playlist_clips', [])
        
        for clip_entry in clips:
            clip = clip_entry.get('clip', {})
            if not clip:
                continue
                
            song = {
                'title': clip.get('title', ''),
                'song_id': clip.get('id', ''),
                'url': f"https://suno.com/song/{clip.get('id', '')}",
                'author': clip.get('display_name', ''),
                'handle': clip.get('handle', ''),
                'duration': clip.get('metadata', {}).get('duration', 0),
                'play_count': clip.get('play_count', 0),
                'upvote_count': clip.get('upvote_count', 0),
                'created_at': clip.get('created_at', ''),
                'model_version': clip.get('major_model_version', ''),
                'tags': clip.get('metadata', {}).get('tags', ''),
                'prompt': clip.get('metadata', {}).get('prompt', ''),
                'is_remix': clip.get('metadata', {}).get('is_remix', False),
                'remix_type': None
            }
            
            badges = clip.get('metadata', {}).get('secondary_badges', [])
            for badge in badges:
                if 'Mashup' in badge.get('display_name', ''):
                    song['remix_type'] = 'Mashup'
                elif 'Cover' in badge.get('display_name', ''):
                    song['remix_type'] = 'Cover'
                    
            if clip.get('audio_url'):
                song['audio_url'] = clip.get('audio_url')
            if clip.get('image_url'):
                song['image_url'] = clip.get('image_url')
                
            songs.append(song)
            
    except json.JSONDecodeError:
        return _extract_from_html_fallback(html_content)
        
    return songs

def _extract_from_html_fallback(html_content: str) -> List[Dict]:
    songs = []
    
    song_ids = re.findall(r'/song/([a-f0-9-]{36})', html_content)
    titles = re.findall(r'<a[^>]*href="/song/[^"]*"[^>]*>([^<]+)</a>', html_content)
    handles = re.findall(r'href="/@([^"]+)"', html_content)
    authors = re.findall(r'<a[^>]*href="/@[^"]*"[^>]*>([^<]+)</a>', html_content)
    
    for i, song_id in enumerate(song_ids):
        if i >= len(titles):
            break
            
        song = {
            'title': titles[i] if i < len(titles) else '',
            'song_id': song_id,
            'url': f"https://suno.com/song/{song_id}",
            'author': authors[i] if i < len(authors) else '',
            'handle': handles[i] if i < len(handles) else '',
        }
        
        durations = re.findall(r'<div[^>]*text-foreground-tertiary[^>]*>(\d+:\d+)</div>', html_content)
        if i < len(durations):
            parts = durations[i].split(':')
            song['duration'] = int(parts[0]) * 60 + int(parts[1])
            
        songs.append(song)
        
    return songs
