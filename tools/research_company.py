import os
import requests
import sys
from utils import get_env, tmp_path


def fetch_company_news(company_name):
    api_key = get_env("NEWS_API_KEY")
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={company_name}&sortBy=publishedAt&pageSize=5&apiKey={api_key}"
    )

    response = requests.get(url)
    if response.status_code != 200:
        return f"Error fetching news: {response.status_code}"

    articles = response.json().get("articles", [])
    news_summary = ""
    for a in articles:
        news_summary += f"- {a['title']} (Source: {a['source']['name']})\n"
    return news_summary


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/research_company.py <company_name>")
        sys.exit(1)

    name = sys.argv[1]
    print(f"Fetching news for {name}...")
    data = fetch_company_news(name)

    # Save to .tmp as an intermediate file
    save_path = tmp_path(f"raw_news_{name.replace(' ', '_')}.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(data)

    print(f"Data saved to {save_path}")
    print(data)
