import sys
from ddgs import DDGS
from utils import tmp_path


def find_real_people(company_name):
    query = f'site:linkedin.com/in/ ("HSE" OR "Health and Safety" OR "Digital" OR "CTO") "{company_name}"'

    print(f"Searching the internet for real employees at {company_name}...")
    results = []

    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=5))

            for r in search_results:
                title_clean = r['title'].replace(" - LinkedIn", "").split("|")[0].strip()
                results.append({
                    "Name & Role": title_clean,
                    "Link": r['href']
                })
        return results
    except Exception as e:
        return f"Search failed: {e}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/get_real_contacts_free.py <company_name>")
        sys.exit(1)

    company = sys.argv[1]
    data = find_real_people(company)

    save_path = tmp_path(f"real_contacts_{company.replace(' ', '_')}.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            for person in data:
                f.write(f"- {person['Name & Role']} ({person['Link']})\n")

    print(f"Real contacts saved to {save_path}")
    if isinstance(data, list):
        for person in data:
            print(f"- {person['Name & Role']}")
