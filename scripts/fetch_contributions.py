#!/usr/bin/env python3
"""
Fetch the real daily contribution counts for the profile README heatmap and
write data/contributions.json (raw days + derived stats: streaks, best day,
monthly totals, public/private split).

Two modes:

1. AUTHENTICATED (preferred) -- if GH_TOKEN / PROFILE_TOKEN / GITHUB_TOKEN is
   set, query the GitHub GraphQL API as the profile owner. With the `read:user`
   scope this is the only mode that can report the public/private SPLIT and the
   commit/PR/issue breakdown.

2. PUBLIC FALLBACK -- no token available. Scrapes the public contributions
   fragment (the same HTML the profile page uses). How complete this is depends
   entirely on the account's "Include private contributions on my profile"
   setting: with it ON the fragment reports private counts too (so the total is
   correct), but the public/private split is never available from this source.

Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import re
import sys

USERNAME = os.environ.get("GH_PROFILE_USER", "anassagd432")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")

GRAPHQL_URL = "https://api.github.com/graphql"
PUBLIC_URL = f"https://github.com/users/{USERNAME}/contributions"

GRAPHQL_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      restrictedContributionsCount
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
""".strip()


def _token():
    for key in ("GH_TOKEN", "PROFILE_TOKEN", "GITHUB_TOKEN"):
        val = os.environ.get(key)
        if val and val.strip():
            return val.strip()
    return None


def token_private_repo_count(token):
    """REST /user only returns `total_private_repos` when the token carries the
    `user` scope -- and that same scope is what makes contributionsCollection
    report private contributions. Returns None when the scope is missing, which
    is how we tell "genuinely zero private work" apart from "can't see it"."""
    import requests

    try:
        resp = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme-bot/1.0"},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("total_private_repos")
    except Exception:  # noqa: BLE001 -- best-effort probe only
        return None


def fetch_days_authenticated(token):
    """GraphQL as the owner -- includes private contributions when the token
    carries the `user` scope."""
    import requests

    today = datetime.date.today()
    since = today - datetime.timedelta(days=365)
    # GitHub's profile calendar always starts on a Sunday -- align so the grid
    # matches the profile page cell-for-cell.
    since -= datetime.timedelta(days=(since.weekday() + 1) % 7)
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {
            "login": USERNAME,
            "from": since.isoformat() + "T00:00:00Z",
            "to": today.isoformat() + "T23:59:59Z",
        },
    }
    resp = requests.post(
        GRAPHQL_URL,
        json=payload,
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme-bot/1.0"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(f"GraphQL errors: {body['errors']}")

    coll = body["data"]["user"]["contributionsCollection"]
    cal = coll["contributionCalendar"]
    days = []
    for week in cal["weeks"]:
        for d in week["contributionDays"]:
            days.append({"date": d["date"], "count": d["contributionCount"]})
    days.sort(key=lambda d: d["date"])
    if not days:
        raise RuntimeError("GraphQL returned an empty contribution calendar")

    private = coll.get("restrictedContributionsCount") or 0
    private_repos = token_private_repo_count(token)
    scope_ok = private_repos is not None
    # Either signal is enough to know private contributions are in the total.
    includes_private = scope_ok or private > 0

    if not includes_private:
        print(
            "WARNING: private contributions appear invisible to this token (no "
            "`user`/`read:user` scope, and 0 private contributions reported) -- "
            "the total below may be PUBLIC ONLY.",
            file=sys.stderr,
        )

    return days, {
        "source": "graphql-authenticated",
        "includes_private": includes_private,
        "total": cal["totalContributions"],
        "private": private,
        "private_repos_visible": private_repos,
        "commits": coll.get("totalCommitContributions"),
        "pull_requests": coll.get("totalPullRequestContributions"),
        "issues": coll.get("totalIssueContributions"),
        "reviews": coll.get("totalPullRequestReviewContributions"),
        "repos": coll.get("totalRepositoriesWithContributedCommits"),
    }


def fetch_days_public():
    """Public HTML fragment -- PUBLIC contributions only, no auth."""
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(PUBLIC_URL, headers={"User-Agent": "profile-readme-bot/1.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        sys.exit(1)

    days = []
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        td_id = td.get("id")
        tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else ""
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            m = re.match(r"(\d+)", text)
            count = int(m.group(1)) if m else 0
        days.append({"date": date, "count": count})

    days.sort(key=lambda d: d["date"])
    return days, {
        "source": "public-html",
        # Whether private contributions are included depends on the account's
        # "Include private contributions on my profile" setting, which this
        # source cannot report -- hence unknown rather than False.
        "includes_private": None,
        "total": sum(d["count"] for d in days),
        "private": None,
        "private_repos_visible": None,
        "commits": None,
        "pull_requests": None,
        "issues": None,
        "reviews": None,
        "repos": None,
    }


def compute_current_streak(days):
    if not days:
        return 0, None, None
    idx = len(days) - 1
    if days[idx]["count"] == 0:
        idx -= 1  # today isn't over yet -- don't break the streak on it
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start_idx = idx + 1
    if streak == 0:
        return 0, None, None
    return streak, days[start_idx]["date"], days[end_idx]["date"]


def compute_longest_streak(days):
    if not days:
        return 0, None, None
    longest = run = 0
    longest_start = longest_end = None
    run_start_idx = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0
    return longest, longest_start, longest_end


def build_data(days, meta):
    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"]) if days else {"date": "N/A", "count": 0}
    cur_len, cur_start, cur_end = compute_current_streak(days)
    long_len, long_start, long_end = compute_longest_streak(days)

    monthly = {}
    for d in days:
        key = d["date"][:7]
        monthly[key] = monthly.get(key, 0) + d["count"]
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": meta["source"],
        "includes_private": meta["includes_private"],
        "range": {"start": days[0]["date"], "end": days[-1]["date"]} if days else {"start": "", "end": ""},
        "total_contributions": total,
        "private_contributions": meta["private"],
        "public_contributions": (total - meta["private"]) if meta["private"] is not None else None,
        "private_repos_visible": meta.get("private_repos_visible"),
        "breakdown": {
            "commits": meta["commits"],
            "pull_requests": meta["pull_requests"],
            "issues": meta["issues"],
            "reviews": meta["reviews"],
            "repositories": meta["repos"],
        },
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly_list,
        "days": days,
    }


if __name__ == "__main__":
    token = _token()
    if token:
        try:
            days, meta = fetch_days_authenticated(token)
        except Exception as exc:  # noqa: BLE001 -- fall back rather than fail the job
            print(f"authenticated fetch failed ({exc}); falling back to public scrape", file=sys.stderr)
            days, meta = fetch_days_public()
    else:
        print(
            "note: no GH_TOKEN/PROFILE_TOKEN set -- using the public contributions "
            "fragment. The total is correct as long as 'Include private "
            "contributions on my profile' is enabled, but the public/private split "
            "and the commit/PR/issue breakdown require a token with `read:user`.",
            file=sys.stderr,
        )
        days, meta = fetch_days_public()

    data = build_data(days, meta)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    split = ""
    if data["private_contributions"] is not None:
        split = (f" ({data['public_contributions']} public + "
                 f"{data['private_contributions']} private)")
    print(
        f"wrote {OUT_PATH}: {data['total_contributions']} contributions{split} "
        f"via {data['source']}, current streak {data['current_streak']['length']}, "
        f"longest streak {data['longest_streak']['length']}"
    )
