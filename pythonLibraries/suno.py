import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def classify_suno_url(url):
    return 'unknown'
    
def parseSongHTML(html_string):
  """Parses a Suno song HTML string to extract song metadata,

  author details, URLs, and IDs.
  """
  soup = BeautifulSoup(html_string, "html.parser")

  # Extract OpenGraph Title and Canonical Link/Song ID
  og_title = soup.find("meta", property="og:title")
  title = og_title["content"] if og_title else None

  canonical_link = soup.find("link", rel="canonical")
  song_url = canonical_link["href"] if canonical_link else None
  song_id = song_url.split("/")[-1] if song_url else None

  # Extract Cover Image Artwork
  og_image = soup.find("meta", property="og:image")
  cover_image = og_image["content"] if og_image else None

  # Extract Meta Description for Author Name and Handle parsing
  meta_desc = soup.find("meta", attrs={"name": "description"})
  desc_text = meta_desc["content"] if meta_desc else ""

  author_name = None
  author_handle = None

  if desc_text:
    # Parses strings matching formats like "SongName by AuthorName (@handle)..."
    match = re.search(r"by\s+(.*?)\s+\((@[\w\d_]+)\)", desc_text)
    if match:
      author_name = match.group(1).strip()
      author_handle = match.group(2).strip()

  # Fallback: Extract from the HTML <title> tag if needed
  page_title = soup.find("title")
  page_title_text = page_title.text.strip() if page_title else None

  return {
      "title": title,
      "author": author_name,
      "author_handle": author_handle,
      "song_id": song_id,
      "song_url": song_url,
      "cover_image": cover_image,
      "page_title": page_title_text,
  }

def parseSongRSC ( string ):
    return
    
def parsePlaylistHTML( string ):
    return

def parsePlaylistRSC ( string ):
    return
