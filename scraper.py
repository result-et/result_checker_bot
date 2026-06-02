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
      - announcement_type (str)
      - description (str)
      - is_matching (bool)
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching the careers page: {e}")
        raise e
        
    soup = BeautifulSoup(response.text, 'html.parser')
    announcements = []
    
    # Locate individual list items representing announcements
    # Based on the page structure, announcements are lists of cards in a <ul>
    list_items = soup.find_all('li')
    
    for item in list_items:
        card = item.find(class_='card')
        if not card:
            # Try finding by accordion container id prefix if card class is missing
            card = item.find(id=re.compile(r'^accordion_'))
            
        if not card:
            continue
            
        # 1. Parse Card Header for Announcement Type
        announcement_type = "ANNOUNCEMENT"
        header = card.find(class_='card-header')
        if header:
            strongs = header.find_all('strong')
            for strong in strongs:
                if 'announcement' in strong.get_text().lower():
                    next_sibling = strong.next_sibling
                    if next_sibling:
                        announcement_type = clean_text(str(next_sibling))
        
        # 2. Parse Panel Body for Details
        panel_body = card.find(class_='panel-body')
        if not panel_body:
            continue
            
        position = ""
        location = ""
        description = ""
        candidate_list_html = ""
        
        # Find all Mylead divs inside the panel body
        lead_divs = panel_body.find_all(class_=lambda x: x and 'Mylead' in x)
        
        for div in lead_divs:
            strong = div.find('strong')
            if not strong:
                continue
                
            label = strong.get_text().strip().lower()
            # Extract content after the strong tag
            found_strong = False
            content_html_list = []
            for content in div.contents:
                if content == strong:
                    found_strong = True
                    continue
                if found_strong:
                    content_html_list.append(str(content))
            
            raw_value = "".join(content_html_list)
            if "<" in raw_value and ">" in raw_value:
                value_text = clean_text(BeautifulSoup(raw_value, 'html.parser').get_text())
            else:
                value_text = clean_text(raw_value)
            
            if 'postion' in label or 'position' in label:
                position = value_text
            elif 'location' in label:
                location = value_text
            elif 'description' in label:
                # Description can be multiline, we clean it up but preserve structure
                if "<" in raw_value and ">" in raw_value:
                    raw_desc = BeautifulSoup(raw_value, 'html.parser').get_text(separator='\n')
                else:
                    raw_desc = raw_value
                description = "\n".join([line.strip() for line in raw_desc.split('\n') if line.strip()])
            elif 'candidate' in label:
                candidate_list_html = raw_value.strip()
        
        # Clean up defaults
        position = position or "Unknown Position"
        location = location or "Ethiopian Airlines"
        description = description or "No description details provided."
        
        # 3. Generate unique ID using SHA-256 hash of position, location, type, and description
        unique_string = f"{position}|{location}|{announcement_type}|{description}"
        announcement_id = hashlib.sha256(unique_string.encode('utf-8')).hexdigest()
        
        # 4. Check if position matches AMT or Pilot filter
        is_matching = is_target_position(position)
        
        announcements.append({
            "id": announcement_id,
            "position": position,
            "location": location,
            "announcement_type": announcement_type,
            "description": description,
            "candidate_list_html": candidate_list_html,
            "is_matching": is_matching
        })
        
    return announcements
