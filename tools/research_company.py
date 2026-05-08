import os
import requests
import sys
from ddgs import DDGS
from utils import get_env, tmp_path


def fetch_company_news(company_name: str) -> str:
    """Fetch recent news. Returns rich text (title + description). Falls back to DDG if NewsAPI is thin."""
    api_key = os.getenv("NEWS_API_KEY", "")
    articles = []

    if api_key:
        try:
            url = (
                f"https://newsapi.org/v2/everything"
                f"?q={company_name}&sortBy=publishedAt&pageSize=8&language=en&apiKey={api_key}"
            )
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                for a in resp.json().get("articles", []):
                    title = a.get("title", "").strip()
                    desc = (a.get("description") or "").strip()
                    source = a.get("source", {}).get("name", "")
                    if title and "[Removed]" not in title:
                        snippet = f"- [{source}] {title}"
                        if desc:
                            snippet += f": {desc[:180]}"
                        articles.append(snippet)
        except Exception:
            pass

    # DDG fallback or supplement if fewer than 4 real articles
    if len(articles) < 4:
        try:
            with DDGS() as ddgs:
                query = f"{company_name} safety incident expansion project 2024 OR 2025"
                for r in ddgs.text(query, max_results=6):
                    snippet = f"- [Web] {r['title'].strip()}"
                    body = (r.get("body") or "").strip()
                    if body:
                        snippet += f": {body[:180]}"
                    articles.append(snippet)
        except Exception:
            pass

    if not articles:
        return f"No recent news found for {company_name}."
    return "\n".join(articles[:10])


def fetch_active_projects(company_name: str) -> str:
    """Search for real active construction/industrial projects via DDG."""
    results = []
    queries = [
        f'"{company_name}" ("new project" OR "construction" OR "plant" OR "terminal" OR "facility") 2024 OR 2025',
        f'"{company_name}" ("contract awarded" OR "wins order" OR "joint venture" OR "expansion") 2024 OR 2025',
    ]
    try:
        with DDGS() as ddgs:
            for q in queries:
                for r in ddgs.text(q, max_results=4):
                    title = r['title'].strip()
                    body = (r.get("body") or "").strip()
                    entry = f"- {title}"
                    if body:
                        entry += f": {body[:160]}"
                    if not any(entry[:40] in existing for existing in results):
                        results.append(entry)
                if len(results) >= 6:
                    break
    except Exception:
        pass

    if not results:
        return f"No active project data found for {company_name}."
    return "\n".join(results[:6])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/research_company.py <company_name>")
        sys.exit(1)

    name = sys.argv[1]
    print(f"\n=== NEWS ===")
    news = fetch_company_news(name)
    print(news)

    print(f"\n=== ACTIVE PROJECTS ===")
    projects = fetch_active_projects(name)
    print(projects)

    save_path = tmp_path(f"raw_news_{name.replace(' ', '_')}.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write("=== NEWS ===\n")
        f.write(news)
        f.write("\n\n=== ACTIVE PROJECTS ===\n")
        f.write(projects)
    print(f"\nSaved to {save_path}")
