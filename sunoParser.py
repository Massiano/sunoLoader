import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
from urllib.parse import urlparse

class SunoSongParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })

    def parse_song_url(self, url: str) -> Optional[Dict]:
        song_id = self.extract_song_id(url)
        if not song_id:
            return None
        
        # Attempt both HTML and RSC strategies
        html_result = self._parse_as_html(url, song_id)
        rsc_result = self._parse_as_rsc(url, song_id)

        return {
            'id': song_id,
            'url': url,
            'html_parsed': html_result is not None,
            'rsc_parsed': rsc_result is not None,
            'results': {
                'html': html_result,
                'rsc': rsc_result
            }
        }

    def _parse_as_html(self, url: str, song_id: str) -> Optional[Dict]:
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            song_info = self._get_empty_schema(song_id, url, parse_type="HTML")
            
            title_meta = soup.find('meta', {'property': 'og:title'})
            if title_meta:
                song_info['title'] = re.sub(r'\s*\|\s*Suno$', '', title_meta.get('content', ''))
            
            for prop in ['audio', 'image', 'description']:
                meta = soup.find('meta', {'property': f'og:{prop}'})
                if meta:
                    key = 'audio_url' if prop == 'audio' else ('image_url' if prop == 'image' else 'description')
                    song_info[key] = meta.get('content', '')

            artist_section = soup.find('a', href=re.compile(r'^/@'))
            if artist_section:
                href = artist_section.get('href', '')
                song_info['artist']['handle'] = href.replace('/@', '').split('?')[0]
                song_info['artist']['display_name'] = artist_section.text.strip()
                song_info['artist']['profile_url'] = f"https://suno.com{href}"

            for script in soup.find_all('script'):
                if script.string and ('songId' in script.string or 'clipId' in script.string):
                    self._extract_data_from_text(script.string, song_info)

            return song_info
        except Exception as e:
            return None

    def _parse_as_rsc(self, url: str, song_id: str) -> Optional[Dict]:
        try:
            headers = {'RSC': '1', 'Accept': 'text/x-component'}
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            content = response.text
            
            song_info = self._get_empty_schema(song_id, url, parse_type="RSC")
            if 'songId' in content or 'clipId' in content or 'playCount' in content:
                self._extract_data_from_text(content, song_info)
                return song_info
            return None
        except Exception as e:
            return None

    def _get_empty_schema(self, song_id: str, url: str, parse_type: str) -> Dict:
        return {
            'parse_type': parse_type,
            'id': song_id, 'url': url, 'title': '',
            'artist': {'display_name': '', 'handle': '', 'profile_url': ''},
            'audio_url': '', 'image_url': '', 'duration': '', 'duration_seconds': 0,
            'play_count': 0, 'like_count': 0, 'style': '', 'tags': [],
            'description': '', 'lyrics': '', 'model_version': '', 'is_public': True,
            'created_at': ''
        }

    def _extract_data_from_text(self, content: str, song_info: Dict):
        patterns = {
            'play_count': r'"playCount":\s*(\d+)', 'like_count': r'"likeCount":\s*(\d+)',
            'duration_seconds': r'"duration":\s*(\d+)', 'model_version': r'"modelVersion":\s*"([^"]+)"',
            'created_at': r'"createdAt":\s*"([^"]+)"', 'is_public': r'"isPublic":\s*(true|false)',
            'tags': r'"tags":\s*\[([^\]]+)\]', 'style': r'"style":\s*"([^"]+)"', 'lyrics': r'"lyrics":\s*"([^"]+)"'
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                if key in ('play_count', 'like_count', 'duration_seconds'):
                    val = int(match.group(1))
                    if key == 'duration_seconds':
                        song_info['duration_seconds'] = val
                        song_info['duration'] = f"{val // 60}:{val % 60:02d}"
                    elif key == 'play_count': song_info['play_count'] = val
                    elif key == 'like_count': song_info['like_count'] = val
                elif key == 'is_public':
                    song_info['is_public'] = match.group(1) == 'true'
                elif key == 'tags':
                    song_info['tags'] = re.findall(r'"([^"]+)"', match.group(1))
                elif key == 'lyrics':
                    song_info['lyrics'] = match.group(1).replace('\\n', '\n').replace('\\"', '"')
                else:
                    song_info[key] = match.group(1)

    def extract_song_id(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        match = re.search(r'/song/([a-f0-9-]+)', parsed.path)
        return match.group(1) if match else None

def parse_suno_song(url: str) -> Optional[Dict]:
    return SunoSongParser().parse_song_url(url)
