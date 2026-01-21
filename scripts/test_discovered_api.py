#!/usr/bin/env python3
"""
Test Discovered CanPL.ca API Endpoints

After running discover_canpl_api.js, use this script to test calling
the discovered endpoints directly (without a browser).

Usage: python scripts/test_discovered_api.py
"""

import requests
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


def load_discovered_endpoints() -> Optional[Dict[str, Any]]:
    """Load discovered endpoints from JSON file."""
    data_dir = Path(__file__).parent.parent / 'data'
    endpoints_file = data_dir / 'discovered_canpl_endpoints.json'

    if not endpoints_file.exists():
        print("❌ No discovered endpoints file found.")
        print("   Run 'node scripts/discover_canpl_api.js' first.")
        return None

    with open(endpoints_file, 'r') as f:
        return json.load(f)


def test_endpoint(url: str, method: str = 'GET') -> Dict[str, Any]:
    """Test calling an endpoint directly."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://canpl.ca/',
        'Origin': 'https://canpl.ca'
    }

    result = {
        'url': url,
        'method': method,
        'success': False,
        'status_code': None,
        'content_type': None,
        'data': None,
        'error': None
    }

    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, timeout=15)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, timeout=15)
        else:
            response = requests.request(method, url, headers=headers, timeout=15)

        result['status_code'] = response.status_code
        result['content_type'] = response.headers.get('Content-Type', '')

        if response.status_code == 200:
            result['success'] = True

            # Try to parse as JSON
            try:
                result['data'] = response.json()
            except json.JSONDecodeError:
                result['data'] = response.text[:500]

    except requests.RequestException as e:
        result['error'] = str(e)

    return result


def analyze_endpoint_data(data: Any) -> Dict[str, Any]:
    """Analyze the structure of endpoint data."""
    analysis = {
        'type': type(data).__name__,
        'is_empty': False,
        'contains_matches': False,
        'contains_standings': False,
        'contains_teams': False,
        'sample_keys': [],
        'item_count': 0
    }

    if data is None:
        analysis['is_empty'] = True
        return analysis

    if isinstance(data, dict):
        analysis['sample_keys'] = list(data.keys())[:10]
        analysis['item_count'] = len(data)

        # Check for common patterns
        data_str = json.dumps(data).lower()
        analysis['contains_matches'] = any(
            k in data_str for k in ['match', 'fixture', 'game', 'score']
        )
        analysis['contains_standings'] = any(
            k in data_str for k in ['standing', 'table', 'points', 'position']
        )
        analysis['contains_teams'] = any(
            k in data_str for k in ['team', 'club', 'forge', 'cavalry', 'pacific']
        )

    elif isinstance(data, list):
        analysis['item_count'] = len(data)
        if data:
            if isinstance(data[0], dict):
                analysis['sample_keys'] = list(data[0].keys())[:10]

    return analysis


def test_discovered_endpoints():
    """Test all discovered endpoints."""
    discovery = load_discovered_endpoints()

    if not discovery:
        return

    endpoints = discovery.get('endpoints', [])

    print(f"📊 Testing {len(endpoints)} discovered endpoints...\n")
    print("=" * 70)

    useful_endpoints = []

    for i, endpoint in enumerate(endpoints, 1):
        url = endpoint.get('url', '')
        method = endpoint.get('method', 'GET')

        print(f"\n[{i}/{len(endpoints)}] Testing: {method} {url[:80]}...")

        result = test_endpoint(url, method)

        if result['success']:
            print(f"  ✅ SUCCESS! Status: {result['status_code']}")
            print(f"  Content-Type: {result['content_type']}")

            if result['data']:
                analysis = analyze_endpoint_data(result['data'])
                print(f"  Data type: {analysis['type']}, Items: {analysis['item_count']}")

                if analysis['sample_keys']:
                    print(f"  Keys: {', '.join(analysis['sample_keys'][:5])}")

                # Check if this is useful for our purposes
                if analysis['contains_matches'] or analysis['contains_standings'] or analysis['contains_teams']:
                    print(f"  🎯 USEFUL! Contains: ", end='')
                    useful = []
                    if analysis['contains_matches']:
                        useful.append('matches')
                    if analysis['contains_standings']:
                        useful.append('standings')
                    if analysis['contains_teams']:
                        useful.append('teams')
                    print(', '.join(useful))

                    useful_endpoints.append({
                        'url': url,
                        'method': method,
                        'analysis': analysis,
                        'data_sample': json.dumps(result['data'])[:500]
                    })

                # Show sample data
                sample = json.dumps(result['data'], indent=2)[:300]
                print(f"  Sample: {sample}...")

        else:
            print(f"  ❌ FAILED! Status: {result['status_code']}")
            if result['error']:
                print(f"  Error: {result['error']}")

    print("\n" + "=" * 70)
    print("📋 SUMMARY")
    print("=" * 70)

    if useful_endpoints:
        print(f"\n🎯 Found {len(useful_endpoints)} potentially useful endpoints:")

        for ep in useful_endpoints:
            print(f"\n  📡 {ep['method']} {ep['url']}")
            print(f"     Use for: ", end='')
            uses = []
            if ep['analysis']['contains_matches']:
                uses.append('match data')
            if ep['analysis']['contains_standings']:
                uses.append('standings')
            if ep['analysis']['contains_teams']:
                uses.append('team info')
            print(', '.join(uses))

        # Save useful endpoints
        data_dir = Path(__file__).parent.parent / 'data'
        useful_file = data_dir / 'useful_canpl_endpoints.json'
        with open(useful_file, 'w') as f:
            json.dump(useful_endpoints, f, indent=2)
        print(f"\n💾 Saved useful endpoints to {useful_file}")

        print("\n✅ NEXT STEPS:")
        print("   1. Review useful endpoints above")
        print("   2. Create API client wrapper (scripts/canpl_api_client.py)")
        print("   3. Use for live data updates")

    else:
        print("\n⚠️ No useful API endpoints found.")
        print("\n📋 RECOMMENDATIONS:")
        print("   1. CanPL.ca likely uses server-side rendering")
        print("   2. Fall back to FBref scraping (TASK 1.2)")
        print("   3. Or use HTML scraping with BeautifulSoup")


def try_common_api_patterns():
    """Try common API URL patterns that might work."""
    print("\n" + "=" * 70)
    print("🔍 Trying common API patterns...")
    print("=" * 70)

    common_patterns = [
        'https://canpl.ca/api/matches',
        'https://canpl.ca/api/v1/matches',
        'https://canpl.ca/api/fixtures',
        'https://canpl.ca/api/standings',
        'https://canpl.ca/api/teams',
        'https://canpl.ca/api/schedule',
        'https://api.canpl.ca/matches',
        'https://api.canpl.ca/v1/matches',
        'https://canpl.ca/data/matches.json',
        'https://canpl.ca/data/standings.json',
        'https://canpl.ca/_next/data/matches.json',
    ]

    found = []

    for url in common_patterns:
        print(f"\n  Testing: {url}")
        result = test_endpoint(url)

        if result['success'] and result['data']:
            print(f"  ✅ FOUND! Status: {result['status_code']}")
            found.append(url)
        else:
            print(f"  ❌ Not found ({result['status_code'] or 'error'})")

    if found:
        print(f"\n🎉 Found {len(found)} working endpoints!")
        for url in found:
            print(f"   - {url}")
    else:
        print("\n⚠️ No common patterns worked.")

    return found


if __name__ == '__main__':
    # First test discovered endpoints
    test_discovered_endpoints()

    # Also try common patterns
    try_common_api_patterns()
