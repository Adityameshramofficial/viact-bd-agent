# Workflow: PoC Customer Research (Zero-Cost Version)

## Objective
Demonstrate the full research-to-outreach pipeline using only free tools and public data — no paid API credits consumed.

## Owner
aditya.meshram@viact.ai

## Required Inputs
- `company_name`: Official name of the target company (e.g. "Larsen and Toubro")
- `domain`: Company website (e.g. lntecc.com)
- `sender_email`: Always use `aditya.meshram@viact.ai`

## Execution Steps

### Step 1 — News Intel (Free, NewsAPI)
```
python tools/research_company.py "<company_name>"
```
- Output: `.tmp/raw_news_<company_name>.txt`
- Read this file and identify 2–3 safety or business triggers relevant to viact.ai

### Step 2 — Public Contact Search (Free, No API)
```
python tools/find_contacts_free.py "<company_name>"
```
- Output: `.tmp/contacts_<company_name>.json`
- Open the `search_urls` in the JSON — these are clickable Google queries that surface LinkedIn profiles for HSE and Digital roles
- Manually note any real names found, or pass them back to Claude to enrich later

### Step 3 — AI Safety Trigger Analysis
Claude reads the news file and answers:
1. Is there a recent project expansion, accident, or compliance event?
2. Which of viact.ai's features (PPE detection, zone monitoring, productivity tracking, ISO reporting) maps to this trigger?
3. What is the strongest single opening line for an outreach email?

### Step 4 — Draft Outreach Email
Claude drafts a cold outreach email:
- From: aditya.meshram@viact.ai
- To: [Contact Name], [Title] at [Company]
- Subject line tied directly to a news trigger
- Body: 3 sentences max — trigger → viact.ai capability → CTA
- Output: `.tmp/outreach_<company_name>.md`

## Expected Outputs
| File | Contents |
|---|---|
| `.tmp/raw_news_<company>.txt` | Live news headlines |
| `.tmp/contacts_<company>.json` | Simulated contacts + real Google search URLs |
| `.tmp/outreach_<company>.md` | Ready-to-send cold email draft |

## Upgrade Path (When Budget Allows)
| Free Now | Paid Upgrade |
|---|---|
| NewsAPI (100 req/day) | Firecrawl (full website scraping) |
| Google search URLs (manual) | Apollo API (automated enrichment, 1 credit/contact) |
| Simulated contacts | Apollo bulk search + email reveal |

## Edge Cases
- If NewsAPI returns 0 results: try a shorter company name or acronym (e.g. "L&T" not "Larsen and Toubro")
- If no LinkedIn profiles found via Google: search `"<company>" "safety manager" site:linkedin.com` directly in browser
- If domain is unknown: search `"<company name>" annual report site:bseindia.com` for Indian companies
