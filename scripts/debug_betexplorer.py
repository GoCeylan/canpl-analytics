"""Debug script to inspect BetExplorer page structure."""
import requests
import time
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

def fetch_with_selenium(url, wait_for_selector=None):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(3)  # Initial wait

        if wait_for_selector:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                )
            except:
                pass

        time.sleep(2)  # Extra wait
        return driver.page_source
    finally:
        driver.quit()

def analyze_betexplorer(html):
    soup = BeautifulSoup(html, 'html.parser')

    print(f"\nHTML size: {len(html)} bytes")

    # Save for inspection
    with open('debug_betexplorer.html', 'w') as f:
        f.write(html)
    print("Saved to debug_betexplorer.html")

    # Look for tables
    print("\n--- Tables ---")
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")

    for i, table in enumerate(tables[:5]):
        rows = table.find_all('tr')
        print(f"  Table {i}: {len(rows)} rows, class={table.get('class')}")
        if rows:
            first_row_text = rows[0].get_text()[:100].replace('\n', ' ')
            print(f"    First row: {first_row_text}")

    # Look for match links
    print("\n--- Match links ---")
    match_links = soup.find_all('a', href=lambda h: h and '/match/' in h)
    print(f"Found {len(match_links)} match links")
    for link in match_links[:10]:
        print(f"  {link.get('href')}: {link.get_text()[:50]}")

    # Look for team names
    print("\n--- Team names (searching for CPL teams) ---")
    teams = ['Forge', 'Cavalry', 'Pacific', 'Valour', 'York', 'Halifax', 'Ottawa', 'Edmonton', 'Vancouver']
    for team in teams:
        elements = soup.find_all(string=lambda s: s and team.lower() in s.lower())
        if elements:
            print(f"  {team}: {len(elements)} mentions")
            for elem in elements[:2]:
                print(f"    -> {elem[:80]}")

    # Look for odds
    print("\n--- Odds elements ---")
    odds_patterns = ['td.table-main__odds', 'span.odds', '[class*="odds"]', 'td[data-odd]']
    for pattern in odds_patterns:
        elements = soup.select(pattern)
        if elements:
            print(f"  {pattern}: {len(elements)} elements")

if __name__ == '__main__':
    # Try BetExplorer
    url = "https://www.betexplorer.com/football/canada/canadian-premier-league-2024/results/"
    print(f"Fetching: {url}")

    html = fetch_with_selenium(url, wait_for_selector='table')
    analyze_betexplorer(html)

    # Also try without the year
    url2 = "https://www.betexplorer.com/football/canada/canadian-premier-league/results/"
    print(f"\n\nTrying: {url2}")
    html2 = fetch_with_selenium(url2, wait_for_selector='table')
    analyze_betexplorer(html2)
