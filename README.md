# Milwaukee Fresh Jobs

A free, auto-updating job board for international students in Milwaukee,
focused on Help Desk, Technical Support, Desktop Support, and QA/Debugging
Technician roles. Updates twice a day automatically, at no cost, with no
server to maintain.

## How it works

- `index.html` — the public website. Reads `jobs.json` and displays it.
- `jobs.json` — the current list of live jobs. Rewritten automatically.
- `fetch_jobs.py` — pulls fresh listings from the **Adzuna Jobs API**, a free
  legitimate job-aggregator API (this avoids the Terms-of-Service problems
  of scraping Indeed/LinkedIn/Glassdoor directly).
- `.github/workflows/update-jobs.yml` — a GitHub Actions workflow that runs
  `fetch_jobs.py` automatically at 8 AM and 6 PM Central Time every day, and
  commits the refreshed `jobs.json`. GitHub Pages then republishes the site
  automatically whenever the repo changes.

## One-time setup (about 10 minutes)

### 1. Get a free Adzuna API key
1. Go to https://developer.adzuna.com/ and click **Register**.
2. Once logged in, go to your dashboard — you'll see an **App ID** and
   **App Key**. Copy both.

### 2. Create the GitHub repository
1. On GitHub, click **New repository**. Name it e.g. `milwaukee-fresh-jobs`.
   Make it **Public**.
2. Upload all the files in this folder (`index.html`, `jobs.json`,
   `fetch_jobs.py`, `README.md`, and the `.github/workflows/` folder with
   `update-jobs.yml` inside it) into the repo, preserving the folder
   structure. Easiest way: on your computer, run:
   ```
   git init
   git add .
   git commit -m "Initial site"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/milwaukee-fresh-jobs.git
   git push -u origin main
   ```

### 3. Add your Adzuna keys as GitHub Secrets (keeps them private)
1. In your repo on GitHub: **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**. Add:
   - Name: `ADZUNA_APP_ID`, Value: *(paste your App ID)*
   - Name: `ADZUNA_APP_KEY`, Value: *(paste your App Key)*

### 4. Turn on GitHub Pages
1. In your repo: **Settings → Pages**.
2. Under "Build and deployment", set **Source** to `Deploy from a branch`,
   branch `main`, folder `/ (root)`. Save.
3. GitHub will give you a live URL, something like:
   `https://YOUR-USERNAME.github.io/milwaukee-fresh-jobs/`
   That's your public site — share this link with other students.

### 5. Trigger the first update
1. In your repo: **Actions** tab → click **Update Milwaukee Jobs (twice daily)**
   → **Run workflow** (this runs it immediately instead of waiting for the
   next scheduled time).
2. After it finishes (~30 seconds), refresh your live site — real jobs
   should now appear.

From here on, it runs itself, every day, for free, forever — no laptop
access, no server, nothing to babysit.

## Customizing the search

Edit the `SEARCH_TERMS` list near the top of `fetch_jobs.py` to add or
remove job titles/keywords, or change `LOCATION` / `distance` to widen or
narrow the search radius around Milwaukee.

## Important notes

- **Verify before applying.** Aggregator data can occasionally be stale or
  duplicated — always click through and confirm the listing is still live
  on the employer's own site before applying.
- **This tool only uses Adzuna's official API**, not scraped HTML from
  LinkedIn/Indeed/Glassdoor, to stay within each site's Terms of Service.
  If you want to add more sources later (e.g., specific companies'
  Greenhouse/Lever career pages, which offer public JSON APIs), that's a
  safe path to expand coverage — ask and I can add it.
- GitHub Actions free tier covers this easily (two runs a day, each taking
  well under a minute).
