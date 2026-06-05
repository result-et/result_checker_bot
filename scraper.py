import requests
from bs4 import BeautifulSoup
import hashlib
import re

URL = "https://corporate.ethiopianairlines.com/AboutEthiopian/careers/results"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def clean_text(text):
    """Cleans up whitespace and HTML entities from scraped text."""
    if not text:
        return ""
    # Replace non-breaking spaces and clean whitespace
    text = text.replace("&nbsp;", " ").replace("\xa0", " ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_target_position(position_name):
    """
    Determines if the position is related to AMT (Aircraft Maintenance Technician) or Pilot roles.
    Matches keywords like 'amt', 'aircraft maintenance', 'pilot', 'pts'.
    """
    if not position_name:
        return False
    
    pos_lower = position_name.lower()
    target_keywords = [
        "amt",
        "aircraft maintenance",
        "pilot",
        "pts"
    ]
    return any(keyword in pos_lower for keyword in target_keywords)

def scrape_announcements():
    """
    Scrapes the results page and returns a list of dictionaries representing announcements.

    Each announcement contains:
      - id (SHA-256 hash)
      - position (str)
      - location (str)
      - announcement (str)
      - is_matching (bool)
    """
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching the careers page: {e}")
        raise

    soup = BeautifulSoup(response.text, 'html.parser')
    announcements = []

    # Find all announcement cards
    cards = soup.find_all(class_='card')

    for card in cards:
        header = card.find(class_='card-header')

        if not header:
            continue

        position = ""
        location = ""
        announcement = ""

        for strong in header.find_all('strong'):
            label = clean_text(strong.get_text()).lower()

            value = clean_text(
                strong.next_sibling
                if isinstance(strong.next_sibling, str)
                else ""
            )

            if 'postion' in label or 'position' in label:
                position = value

            elif 'location' in label:
                location = value

            elif 'announcement' in label:
                announcement = value

        position = position
        location = location
        announcement = announcement

        # Create unique announcement ID
        unique_string = f"{position}|{location}|{announcement}"
        announcement_id = hashlib.sha256(
            unique_string.encode("utf-8")
        ).hexdigest()

        announcements.append({
            "id": announcement_id,
            "position": position,
            "location": location,
            "announcement_type": announcement,
            "is_matching": is_target_position(position)
        })

    return announcements