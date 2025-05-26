# scraper.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def scrape_flip_woningen(stad, dagen=7):
    base_url = "https://www.funda.nl/koop/"
    einddatum = datetime.today()
    startdatum = einddatum - timedelta(days=dagen)

    url = f"{base_url}{stad.lower()}/0-1000000/"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; woning-scraper/1.0)"
    }

    print(f"🌍 Scraping URL: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"⚠️ Fout bij ophalen pagina: status {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    woning_divs = soup.find_all('div', class_='search-result-content')

    woningen = []
    for woning in woning_divs:
        titel_elem = woning.find('h2', class_='search-result__header-title')
        prijs_elem = woning.find('span', class_='search-result-price')
        url_elem = woning.find_parent('a')

        if titel_elem and prijs_elem and url_elem:
            woningen.append({
                "titel": titel_elem.get_text(strip=True),
                "prijs": prijs_elem.get_text(strip=True),
                "url": "https://www.funda.nl" + url_elem['href']
            })

    print(f"✅ Gevonden {len(woningen)} woningen in {stad} (laatste {dagen} dagen)")
    return woningen
