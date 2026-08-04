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
    
    h1_tag = soup.find('h1', class_=lambda c: c and 'text-[2.5rem]' in c and 'text-foreground-primary' in c)
    if h1_tag and h1_tag.string:
        result['title'] = h1_tag.string.strip()
    
    if not result['title']:
        h1_fallback = soup.find('h1')
        if h1_fallback and h1_fallback.string:
            result['title'] = h1_fallback.string.strip()

    container = soup.select_one('#main-container div div div.flex.flex-row.items-start.justify-stretch')
    if container:
        author_tag = container.select_one('a[href^="/@"]')
        if author_tag:
            result['author'] = author_tag.get_text(strip=True)
            href = author_tag.get('href', '')
            if href.startswith('/@'):
                result['author_handle'] = href[2:]

    if not result['author']:
        author_tag = soup.find('a', href=re.compile(r'^/@'))
        if author_tag:
            result['author'] = author_tag.get_text(strip=True)
            href = author_tag.get('href', '')
            if href.startswith('/@'):
                result['author_handle'] = href[2:]

    for script in soup.find_all('script'):
        if not script.string: continue
        script_text = script.string
        if 'id' in script_text:
            id_match = re.search(r'"id":"([a-f0-9-]{36})"', script_text)
            if id_match: 
                result['song_id'] = id_match.group(1)
                break

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
