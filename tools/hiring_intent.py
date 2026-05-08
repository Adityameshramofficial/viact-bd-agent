import sys
from ddgs import DDGS
from utils import tmp_path


def check_hiring_intent(company_name: str) -> dict:
    """
    Scrapes job postings to detect hiring intent for safety and digital roles.
    Returns safety_roles, tech_roles lists and an intent_score 0-3.
    """
    safety_query = f'"{company_name}" ("HSE" OR "safety" OR "EHS" OR "environment") ("job" OR "hiring" OR "vacancy" OR "careers")'
    tech_query = f'"{company_name}" ("digital" OR "IoT" OR "AI" OR "technology" OR "innovation") ("job" OR "hiring" OR "vacancy" OR "careers")'

    safety_roles = []
    tech_roles = []

    try:
        with DDGS() as ddgs:
            for r in ddgs.text(safety_query, max_results=5):
                title = r['title'].split("|")[0].strip()
                safety_roles.append({"title": title, "url": r['href']})

            for r in ddgs.text(tech_query, max_results=5):
                title = r['title'].split("|")[0].strip()
                tech_roles.append({"title": title, "url": r['href']})
    except Exception as e:
        return {"safety_roles": [], "tech_roles": [], "intent_score": 0, "error": str(e)}

    has_safety = len(safety_roles) > 0
    has_tech = len(tech_roles) > 0
    intent_score = (1 if has_safety else 0) + (2 if has_tech else 0)

    return {
        "safety_roles": safety_roles,
        "tech_roles": tech_roles,
        "intent_score": intent_score,  # 0=none, 1=safety only, 2=tech only, 3=both
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/hiring_intent.py <company_name>")
        sys.exit(1)

    company = sys.argv[1]
    result = check_hiring_intent(company)

    save_path = tmp_path(f"hiring_intent_{company.replace(' ', '_')}.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(f"Intent Score: {result['intent_score']}/3\n\n")
        f.write("Safety Roles:\n")
        for r in result['safety_roles']:
            f.write(f"  - {r['title']}\n")
        f.write("\nTech/Digital Roles:\n")
        for r in result['tech_roles']:
            f.write(f"  - {r['title']}\n")

    print(f"Hiring intent saved to {save_path}")
    print(f"Intent score: {result['intent_score']}/3")
