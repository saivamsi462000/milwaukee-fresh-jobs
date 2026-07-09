"""
Milwaukee Fresh Jobs — data collector

Pulls current job postings for support/help-desk/technician roles in the
Milwaukee, WI area using the Adzuna Jobs API (https://developer.adzuna.com/),
a free, legitimate aggregator API — not a scraper of any job board's website.

Requires two free environment variables / GitHub Secrets:
  ADZUNA_APP_ID
  ADZUNA_APP_KEY
Get them free at https://developer.adzuna.com/ (sign up, create an app).

Run manually:
    ADZUNA_APP_ID=xxx ADZUNA_APP_KEY=yyy python fetch_jobs.py

Designed to be run twice a day by the included GitHub Actions workflow,
which commits the refreshed jobs.json back to the repo (and, if GitHub
Pages is enabled on this repo, that automatically republishes the live site).
"""

import os
import json
import sys
import time
from datetime import datetime, timezone
import urllib.request
import urllib.parse

APP_ID = os.environ.get("ADZUNA_APP_ID")
APP_KEY = os.environ.get("ADZUNA_APP_KEY")

# Search terms covering the "unsaturated" support/technician roles requested
SEARCH_TERMS = [
    "help desk technician",
    "technical support specialist",
    "desktop support technician",
    "IT support specialist",
    "QA technician",
    "debugging technician",
]

LOCATION = "Milwaukee"
COUNTRY = "us"
RESULTS_PER_TERM = 15
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "jobs.json")


def fetch_for_term(term):
    if not APP_ID or not APP_KEY:
        print("Missing ADZUNA_APP_ID / ADZUNA_APP_KEY environment variables.", file=sys.stderr)
        sys.exit(1)

    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": RESULTS_PER_TERM,
        "what": term,
        "where": LOCATION,
        "distance": 25,
        "content-type": "application/json",
    }
    url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/1?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        return data.get("results", [])
    except Exception as e:
        print(f"Warning: fetch failed for term '{term}': {e}", file=sys.stderr)
        return []


def normalize(raw):
    jobs = []
    seen_urls = set()
    for item in raw:
        url = item.get("redirect_url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        jobs.append({
            "title": item.get("title", "").strip(),
            "company": (item.get("company") or {}).get("display_name", "Unknown"),
            "location": (item.get("location") or {}).get("display_name", "Milwaukee, WI"),
            "posted": item.get("created"),
            "url": url,
            "source": "Adzuna aggregator",
        })
    return jobs


def main():
    all_raw = []
    for term in SEARCH_TERMS:
        results = fetch_for_term(term)
        all_raw.extend(results)
        time.sleep(1)  # be polite to the API

    jobs = normalize(all_raw)
    jobs.sort(key=lambda j: j["posted"] or "", reverse=True)

    output = {
        "last_updated": datetime.now(timezone.utc).astimezone().isoformat(),
        "jobs": jobs,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(jobs)} jobs to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
