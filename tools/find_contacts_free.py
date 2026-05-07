"""
Free contact finder — no API keys required.
Generates targeted Google/LinkedIn search URLs for manual or automated lookup,
and returns a structured contact list for the research brief.

Upgrade path: replace simulate_contact_search() with a real scraper
(e.g. DuckDuckGo HTML search + BeautifulSoup) when ready.
"""

import sys
import json
from urllib.parse import quote_plus
from utils import tmp_path

# Titles viact.ai cares about — HSE buyers and Digital decision-makers
TARGET_TITLES = [
    "HSE Manager",
    "Head of Safety",
    "EHS Manager",
    "Chief Safety Officer",
    "VP Safety",
    "Chief Digital Officer",
    "Digital Transformation Lead",
    "Chief Technology Officer",
    "IoT Lead",
    "Head of Innovation",
]


def build_search_urls(company_name: str) -> list[dict]:
    """Return Google search URLs that surface LinkedIn profiles for target titles."""
    urls = []
    for title in TARGET_TITLES:
        query = f'site:linkedin.com/in "{company_name}" "{title}"'
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        urls.append({"title": title, "search_url": url})
    return urls


def simulate_contact_search(company_name: str) -> list[dict]:
    """
    PoC placeholder — returns structured dummy contacts.
    Replace this function body with real scraping once a free scraper is added.
    """
    return [
        {
            "name": f"[Search Google for {company_name} HSE Manager]",
            "title": "HSE Manager",
            "source": "LinkedIn (via Google)",
            "email": "unknown — enrich manually or via Apollo",
        },
        {
            "name": f"[Search Google for {company_name} Chief Digital Officer]",
            "title": "Chief Digital Officer",
            "source": "LinkedIn (via Google)",
            "email": "unknown — enrich manually or via Apollo",
        },
    ]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/find_contacts_free.py <company_name>")
        sys.exit(1)

    company = sys.argv[1]
    print(f"\nSearching for contacts at: {company}")
    print("=" * 50)

    # Simulated contacts
    contacts = simulate_contact_search(company)
    print("\n[Contacts Found]")
    for c in contacts:
        print(f"  - {c['name']} | {c['title']}")

    # Google search URLs — click these to find real LinkedIn profiles
    print("\n[Google Search URLs — Click to find real profiles]")
    urls = build_search_urls(company)
    for u in urls:
        print(f"  [{u['title']}]\n  {u['search_url']}\n")

    # Save everything to .tmp
    output = {
        "company": company,
        "simulated_contacts": contacts,
        "search_urls": urls,
    }
    save_path = tmp_path(f"contacts_{company.replace(' ', '_')}.json")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved to: {save_path}")
