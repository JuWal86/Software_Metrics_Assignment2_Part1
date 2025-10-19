# Fetch GitHub issues to build weekly base measures.
# Usage:
#   python src/fetch_github.py --repo owner/name --since 2024-01-01 --until 2025-12-31 --out data/base_measures.csv
# Notes:
#   - Requires a GitHub token (env GITHUB_TOKEN or --token).
#   - Aggregates weekly opened (inflow) and closed (outflow) issues.
#   - Severity inferred from labels: 'severity:critical|high|medium|low' or 'priority:p0..p3'.
import argparse, os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import pandas as pd
import requests
from pathlib import Path

def week_floor(d):
    return (d - timedelta(days=d.weekday())).date()

def severity_from(labels):
    txt = " ".join([l.get("name","").lower().strip() for l in labels])

    # Normalize common patterns to one of: critical/high/medium/low
    # Examples handled:
    # - "Severity-High", "severity-high", "bugzilla/severity-high"
    # - "severity: high", "severity:low"
    normalized = (
        txt.replace("bugzilla/", "")
           .replace("severity-", "severity:")
    )

    # direct matches like "severity: high"
    if "severity: critical" in normalized or "p0" in normalized:
        return "critical"
    if "severity: high" in normalized or "p1" in normalized:
        return "high"
    if "severity: low" in normalized or "p3" in normalized:
        return "low"
    if "severity: medium" in normalized or "p2" in normalized:
        return "medium"

    # helpful fallbacks
    if "critical" in normalized:
        return "critical"
    if "high" in normalized:
        return "high"
    if "low" in normalized:
        return "low"
    if "bug" in normalized or "defect" in normalized:
        return "medium"

    return "medium"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--out", default="data/base_measures.csv")
    args = ap.parse_args()
    headers = {"Accept": "application/vnd.github+json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    session = requests.Session()
    session.headers.update(headers)

    def paged(url, params):
        while True:
            r = session.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                data = []
            for item in data:
                yield item
            next_url = None
            if "link" in r.headers:
                for part in r.headers["link"].split(","):
                    if 'rel="next"' in part:
                        next_url = part[part.find("<")+1:part.find(">")]
                        break
            if not next_url:
                break
            url, params = next_url, {}

    created = defaultdict(lambda: dict(inflow=0, outflow=0, sev={"critical":0,"high":0,"medium":0,"low":0}))
    since_dt = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    until_dt = datetime.fromisoformat(args.until).replace(tzinfo=timezone.utc)

    for it in paged(f"https://api.github.com/repos/{args.repo}/issues", {"state":"all","since":args.since,"per_page":100}):
        if "pull_request" in it:
            continue
        created_at = datetime.fromisoformat(it["created_at"].replace("Z","+00:00"))
        if not (since_dt <= created_at <= until_dt):
            continue
        wk = week_floor(created_at)
        sev = severity_from(it.get("labels", []))
        created[wk]["inflow"] += 1
        created[wk]["sev"][sev] += 1
        if it.get("closed_at"):
            closed_at = datetime.fromisoformat(it["closed_at"].replace("Z","+00:00"))
            cwk = week_floor(closed_at)
            created[cwk]["outflow"] += 1

    if not created:
        print("No issues found in range.")
        return

    weeks = sorted(created.keys())
    start_w, end_w = weeks[0], weeks[-1]
    all_weeks = []
    d = start_w
    while d <= end_w:
        all_weeks.append(d)
        d = d + timedelta(days=7)

    rows = []
    running_open = 0
    for w in all_weeks:
        data = created.get(w, {"inflow":0,"outflow":0,"sev":{"critical":0,"high":0,"medium":0,"low":0}})
        running_open = max(0, running_open + data["inflow"] - data["outflow"])
        rows.append({
            "week_start": str(w),
            "defects_inflow_total": data["inflow"],
            "defects_outflow_total": data["outflow"],
            "severity_critical_in": data["sev"]["critical"],
            "severity_high_in": data["sev"]["high"],
            "severity_medium_in": data["sev"]["medium"],
            "severity_low_in": data["sev"]["low"],
            "avg_resolution_time_hours": 36,
            "backlog_total": running_open
        })

    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print("Wrote", args.out)

if __name__ == "__main__":
    main()