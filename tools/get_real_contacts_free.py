import re
import sys
from ddgs import DDGS
from utils import tmp_path

# Waterfall tiers: progressively broader if earlier tiers yield <3 results
_QUERY_TIERS = [
    'site:linkedin.com/in/ ("HSE" OR "Health and Safety" OR "Digital" OR "CTO") "{company}"',
    'site:linkedin.com/in/ ("EHS" OR "Safety Manager" OR "Innovation" OR "Operations") "{company}"',
    'site:linkedin.com/in/ "{company}" ("Director" OR "VP" OR "Head of")',
]

_CSUITE_KEYWORDS = [
    'ceo', 'cto', 'coo', 'ciso', 'chief ', 'president', 'founder',
    'managing director', 'group director', 'executive director', 'chairman',
]
_DIRECTOR_KEYWORDS = [
    'director', ' vp ', 'vice president', 'head of', 'svp', 'evp',
    'general manager', 'regional manager', 'country manager',
]


def _infer_tier(name_role: str) -> str:
    lower = name_role.lower()
    if any(k in lower for k in _CSUITE_KEYWORDS):
        return 'csuite'
    if any(k in lower for k in _DIRECTOR_KEYWORDS):
        return 'director'
    return 'manager'


def _parse_name(name_role: str) -> str:
    """Extract just the person's name from a 'Name - Title at Company' string."""
    # Strip common suffixes first
    cleaned = re.sub(r'\s*-\s*LinkedIn$', '', name_role, flags=re.IGNORECASE)
    # Split on dash or pipe, take first segment
    parts = re.split(r'\s*[-|]\s*', cleaned, maxsplit=1)
    return parts[0].strip()


def find_real_people(company_name: str) -> dict:
    print(f"Searching for real employees at {company_name}...")
    results = []
    tier_used = 1

    try:
        with DDGS() as ddgs:
            for i, query_template in enumerate(_QUERY_TIERS, start=1):
                query = query_template.replace("{company}", company_name)
                tier_results = list(ddgs.text(query, max_results=5))

                for r in tier_results:
                    raw_title = r['title'].replace(" - LinkedIn", "").split("|")[0].strip()
                    entry = {
                        "Name & Role": raw_title,
                        "Name": _parse_name(raw_title),
                        "Link": r['href'],
                        "tier": _infer_tier(raw_title),
                    }
                    # deduplicate by link
                    if not any(x['Link'] == entry['Link'] for x in results):
                        results.append(entry)

                tier_used = i
                if len(results) >= 3:
                    break

        return {"contacts": results, "enrichment_tier": tier_used}
    except Exception as e:
        return {"contacts": [], "enrichment_tier": 0, "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/get_real_contacts_free.py <company_name>")
        sys.exit(1)

    company = sys.argv[1]
    data = find_real_people(company)

    save_path = tmp_path(f"real_contacts_{company.replace(' ', '_')}.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        tier = data.get("enrichment_tier", 1)
        f.write(f"Enrichment Tier: {tier}\n")
        for person in data.get("contacts", []):
            f.write(f"- [{person['tier'].upper()}] {person['Name & Role']} ({person['Link']})\n")

    print(f"Real contacts saved to {save_path} (tier {data.get('enrichment_tier')})")
    for person in data.get("contacts", []):
        print(f"  [{person['tier']}] {person['Name & Role']}")
