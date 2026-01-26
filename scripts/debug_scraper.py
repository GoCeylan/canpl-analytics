"""Debug script to inspect page structure."""
import requests
import time
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

def fetch_with_selenium(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(5)  # Wait for JS
        return driver.page_source
    finally:
        driver.quit()

def analyze_page(html, url):
    soup = BeautifulSoup(html, 'html.parser')

    print(f"\n{'='*60}")
    print(f"Analyzing: {url}")
    print(f"{'='*60}")

    # Save HTML for inspection
    with open('debug_page.html', 'w') as f:
        f.write(html)
    print(f"Saved HTML to debug_page.html ({len(html)} bytes)")

    # Look for match-related elements
    print("\n--- Looking for match elements ---")

    selectors = [
        'div.eventRow',
        'tr.deactivate',
        'div[class*="event"]',
        'a[href*="/match/"]',
        'div[class*="flex"]',
        'table tbody tr',
        'div.group',
        '[class*="participant"]',
        '[class*="match"]',
        '[class*="game"]',
    ]

    for sel in selectors:
        elements = soup.select(sel)
        if elements:
            print(f"  {sel}: {len(elements)} elements")
            if len(elements) <= 3:
                for e in elements[:3]:
                    text = e.get_text()[:100].strip().replace('\n', ' ')
                    print(f"    -> {text}")

    # Look for any links to matches
    print("\n--- Links containing 'cavalry' or 'forge' ---")
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        text = a.get_text().lower()
        if 'cavalry' in href or 'forge' in href or 'cavalry' in text or 'forge' in text:
            print(f"  {a['href']}: {a.get_text()[:50]}")

    # Check for React/Vue data attributes
    print("\n--- Data attributes ---")
    for elem in soup.find_all(attrs={'data-testid': True}):
        print(f"  data-testid: {elem.get('data-testid')}")

    # Check for JSON data in scripts
    print("\n--- Script tags with data ---")
    for script in soup.find_all('script'):
        text = script.string or ''
        if 'Forge' in text or 'Cavalry' in text or 'matchData' in text:
            print(f"  Found script with match data ({len(text)} chars)")
            # Print a snippet
            if 'Forge' in text:
                idx = text.find('Forge')
                print(f"    ...{text[max(0,idx-50):idx+100]}...")
                break

if __name__ == '__main__':
    url = "https://www.oddsportal.com/football/canada/canadian-premier-league-2024/results/"

    print("Fetching with Selenium...")
    html = fetch_with_selenium(url)
    analyze_page(html, url)
