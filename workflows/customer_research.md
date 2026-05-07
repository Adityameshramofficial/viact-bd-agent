# Workflow: Customer Background Research (100% Free + Real Data)

## Objective
Generate a BD research brief with REAL news and REAL employee contacts using 0 paid credits. Prepare for outreach from aditya.meshram@viact.ai.

## Execution Steps
1. **Real News**: Run `python tools/research_company.py <company_name>` to get live news from NewsAPI.
2. **Real Contacts**: Run `python tools/get_real_contacts_free.py <company_name>` to extract real LinkedIn profiles from the web.
3. **AI Synthesis**: Read the outputs from `.tmp/`. Identify 3 pain points based on the news, and list the real contacts found.
4. **Draft Outreach**: Draft a short, professional cold email signed by Aditya Meshram (aditya.meshram@viact.ai), targeting one of the real HSE/Digital contacts found.

## Expected Output
- Final report saved in `.tmp/final_poc_report_<company_name>.md`

## Edge Cases
- If NewsAPI returns 0 results: try a shorter company name (e.g. "L&T" not "Larsen and Toubro")
- If DuckDuckGo returns 0 LinkedIn results: the query may be too specific — try removing the OR conditions and just search `site:linkedin.com/in/ "HSE" "<company>"`
- If DuckDuckGo rate-limits: wait 30 seconds and retry — it's a free service with soft limits
