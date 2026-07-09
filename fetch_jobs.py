"""
Milwaukee Fresh Jobs — data collector

Pulls current job postings for support/help-desk/technician roles in the
Milwaukee, WI area from THREE legitimate, free sources — not scraping:

  1. Greenhouse (boards-api.greenhouse.io) — public API, returns the real
     direct apply link with no redirect.
  2. Lever (api.lever.co) — public API, also returns the real direct link.
  3. Adzuna (api.adzuna.com) — broad aggregator API, covers far more
     employers, but links route through an Adzuna redirect before landing
     on the real posting. Every job's "source" field tells you which of
     the three it came from, so the site can be transparent about this.

All results older than FRESHNESS_DAYS are dropped automatically, so
expired-feeling stale posts don't linger.

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
from datetime import datetime, timezone, timedelta
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
FRESHNESS_DAYS = 5  # drop anything older than this, every run
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "jobs.json")

# Add company board tokens here for any Milwaukee-area (or remote-friendly)
# employer you confirm uses Greenhouse. Find a company's token by checking
# if https://boards.greenhouse.io/<token> loads their career page.
GREENHOUSE_COMPANIES = [
    # "example-company-token",
]

# Same idea for Lever — check if https://jobs.lever.co/<token> loads.
LEVER_COMPANIES = [
    # "example-company-token",
]


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


def normalize_adzuna(raw):
    jobs = []
    for item in raw:
        url = item.get("redirect_url")
        if not url:
            continue
        jobs.append({
            "title": item.get("title", "").strip(),
            "company": (item.get("company") or {}).get("display_name", "Unknown"),
            "location": (item.get("location") or {}).get("display_name", "Milwaukee, WI"),
            "posted": item.get("created"),
            "url": url,
            "source": "Adzuna (redirect link)",
        })
    return jobs


def fetch_greenhouse(company_token):
    """Greenhouse public job board API — returns direct apply links."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs?content=true"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Warning: Greenhouse fetch failed for '{company_token}': {e}", file=sys.stderr)
        return []

    jobs = []
    for item in data.get("jobs", []):
        location = (item.get("location") or {}).get("name", "")
        if "milwaukee" not in location.lower() and "wisconsin" not in location.lower() and "wi" not in location.lower():
            continue
        jobs.append({
            "title": item.get("title", "").strip(),
            "company": company_token.replace("-", " ").title(),
            "location": location or "Milwaukee, WI",
            "posted": item.get("updated_at"),
            "url": item.get("absolute_url"),
            "source": "Greenhouse (direct link)",
        })
    return jobs


def fetch_lever(company_token):
    """Lever public postings API — returns direct apply links."""
    url = f"https://api.lever.co/v0/postings/{company_token}?mode=json"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Warning: Lever fetch failed for '{company_token}': {e}", file=sys.stderr)
        return []

    jobs = []
    for item in data:
        location = ((item.get("categories") or {}).get("location")) or ""
        if "milwaukee" not in location.lower() and "wisconsin" not in location.lower():
            continue
        posted_ms = item.get("createdAt")
        posted_iso = (
            datetime.fromtimestamp(posted_ms / 1000, tz=timezone.utc).isoformat()
            if posted_ms else None
        )
        jobs.append({
            "title": item.get("text", "").strip(),
            "company": company_token.replace("-", " ").title(),
            "location": location or "Milwaukee, WI",
            "posted": posted_iso,
            "url": item.get("hostedUrl"),
            "source": "Lever (direct link)",
        })
    return jobs


def filter_fresh(jobs):
    cutoff = datetime.now(timezone.utc) - timedelta(days=FRESHNESS_DAYS)
    fresh = []
    for j in jobs:
        posted = j.get("posted")
        if not posted:
            continue
        try:
            posted_dt = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            if posted_dt.tzinfo is None:
                posted_dt = posted_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if posted_dt >= cutoff:
            fresh.append(j)
    return fresh


def dedupe(jobs):
    seen = set()
    out = []
    for j in jobs:
        key = j["url"]
        if key and key not in seen:
            seen.add(key)
            out.append(j)
    return out


def main():
    all_jobs = []

    for token in GREENHOUSE_COMPANIES:
        all_jobs.extend(fetch_greenhouse(token))
        time.sleep(0.5)
    for token in LEVER_COMPANIES:
        all_jobs.extend(fetch_lever(token))
        time.sleep(0.5)

    all_raw = []
    for term in SEARCH_TERMS:
        all_raw.extend(fetch_for_term(term))
        time.sleep(1)
    all_jobs.extend(normalize_adzuna(all_raw))

    all_jobs = dedupe(all_jobs)
    all_jobs = filter_fresh(all_jobs)
    all_jobs.sort(key=lambda j: j["posted"] or "", reverse=True)

    output = {
        "last_updated": datetime.now(timezone.utc).astimezone().isoformat(),
        "freshness_window_days": FRESHNESS_DAYS,
        "jobs": all_jobs,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(all_jobs)} fresh jobs to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
