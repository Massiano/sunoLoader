import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
from urllib.parse import urlparse

class SunoSongParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate, br', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none', 'Sec-Fetch-User': '?1', 'Cache-Control': 'max-age=0'})

    def parse_song_url(self, url: str) -> Optional[Dict]:
        song_id = self.extract_song_id(url)
        if not song_id:
            return None
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return self.parse_song_page(soup, song_id, url)
        except requests.RequestException as e:
            print(f"Error fetching URL: {e}")
            return None
        except Exception as e:
            print(f"Error parsing page: {e}")
            return None

    def parse_song_page(self, soup: BeautifulSoup, song_id: str, url: str) -> Dict:
        song_info = {'id': song_id, 'url': url, 'title': '', 'artist': {'display_name': '', 'handle': '', 'profile_url': ''}, 'audio_url': '', 'image_url': '', 'duration': '', 'duration_seconds': 0, 'play_count': 0, 'like_count': 0, 'style': '', 'tags': [], 'description': '', 'lyrics': '', 'model_version': '', 'is_public': True, 'created_at': '', 'raw_data': {}}
        title_meta = soup.find('meta', {'property': 'og:title'})
        if title_meta:
            title = title_meta.get('content', '')
            song_info['title'] = re.sub(r'\s*\|\s*Suno$', '', title)
        audio_meta = soup.find('meta', {'property': 'og:audio'})
        if audio_meta:
            song_info['audio_url'] = audio_meta.get('content', '')
        image_meta = soup.find('meta', {'property': 'og:image'})
        if image_meta:
            song_info['image_url'] = image_meta.get('content', '')
        desc_meta = soup.find('meta', {'property': 'og:description'})
        if desc_meta:
            song_info['description'] = desc_meta.get('content', '')
        artist_section = soup.find('a', href=re.compile(r'^/@'))
        if artist_section:
            href = artist_section.get('href', '')
            song_info['artist']['handle'] = href.replace('/@', '').split('?')[0]
            song_info['artist']['display_name'] = artist_section.text.strip()
            song_info['artist']['profile_url'] = f"https://suno.com{href}"
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                content = script.string
                if 'songId' in content or 'clipId' in content:
                    self.extract_data_from_script(content, song_info)
        self.extract_visible_data(soup, song_info)
        return song_info

    def extract_data_from_script(self, content: str, song_info: Dict):
        patterns = {'play_count': r'"playCount":\s*(\d+)', 'like_count': r'"likeCount":\s*(\d+)', 'duration_seconds': r'"duration":\s*(\d+)', 'model_version': r'"modelVersion":\s*"([^"]+)"', 'created_at': r'"createdAt":\s*"([^"]+)"', 'is_public': r'"isPublic":\s*(true|false)', 'tags': r'"tags":\s*\[([^\]]+)\]', 'style': r'"style":\s*"([^"]+)"', 'lyrics': r'"lyrics":\s*"([^"]+)"'}
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                if key in ('play_count', 'like_count', 'duration_seconds'):
                    value = int(match.group(1))
                    if key == 'duration_seconds':
                        song_info['duration_seconds'] = value
                        minutes = value // 60
                        seconds = value % 60
                        song_info['duration'] = f"{minutes}:{seconds:02d}"
                    elif key == 'play_count':
                        song_info['play_count'] = value
                    elif key == 'like_count':
                        song_info['like_count'] = value
                elif key == 'is_public':
                    song_info['is_public'] = match.group(1) == 'true'
                elif key == 'tags':
                    tags_str = match.group(1)
                    tags = re.findall(r'"([^"]+)"', tags_str)
                    song_info['tags'] = tags
                elif key == 'lyrics':
                    lyrics = match.group(1)
                    lyrics = lyrics.replace('\\n', '\n').replace('\\"', '"')
                    song_info['lyrics'] = lyrics
                else:
                    song_info[key] = match.group(1)

    def extract_visible_data(self, soup: BeautifulSoup, song_info: Dict):
        duration_el = soup.find('span', class_=re.compile(r'text.*?duration'))
        if duration_el:
            song_info['duration'] = duration_el.text.strip()
        play_el = soup.find(text=re.compile(r'\d+ plays?'))
        if play_el:
            match = re.search(r'(\d+)\s+plays?', play_el)
            if match:
                song_info['play_count'] = int(match.group(1))

    def extract_song_id(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        path = parsed.path
        match = re.search(r'/song/([a-f0-9-]+)', path)
        return match.group(1) if match else None

    def parse_multiple(self, urls: List[str]) -> List[Dict]:
        results = []
        for url in urls:
            song_info = self.parse_song_url(url)
            if song_info:
                results.append(song_info)
        return results

    def get_audio_download_url(self, song_id: str) -> Optional[str]:
        return f"https://cdn1.suno.ai/{song_id}.mp3"

    def get_image_download_url(self, song_id: str) -> Optional[str]:
        return f"https://cdn2.suno.ai/{song_id}.jpeg"

def parse_suno_song(url: str) -> Optional[Dict]:
    parser = SunoSongParser()
    return parser.parse_song_url(url)

if __name__ == "__main__":
    test_url = "https://suno.com/song/0f4a755e-63ee-49ef-8f7c-af0500ed4577"
    result = parse_suno_song(test_url)
    if result:
        print("Successfully parsed song:")
        print(f"Title: {result['title']}")
        print(f"Artist: {result['artist']['display_name']} (@{result['artist']['handle']})")
        print(f"Audio: {result['audio_url']}")
        print(f"Duration: {result['duration']}")
        print(f"Plays: {result['play_count']}")
