name: Update Milwaukee Jobs (twice daily)

on:
  workflow_dispatch:
  schedule:
    - cron: "0 12,23 * * *"

permissions:
  contents: write

jobs:
  update-jobs:
    runs-on: ubuntu-latest

    env:
      ADZUNA_APP_ID: ${{ secrets.ADZUNA_APP_ID }}
      ADZUNA_APP_KEY: ${{ secrets.ADZUNA_APP_KEY }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Fetch latest jobs
        run: python fetch_jobs.py

      - name: Commit updated jobs
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add jobs.json
          git diff --cached --quiet || git commit -m "Update jobs data"
          git push
