#!/usr/bin/env python3
"""
Collect live numbers for the "shipped" card: star and fork counts from the
public GitHub API, download counts from the public npm registry API.

Both are documented, versioned APIs. That is the point: an earlier version of
this card scraped GitHub's private contribution HTML, which can change without
notice. These endpoints cannot rot silently the same way.

Writes data/shipped.json. Run daily by .github/workflows/update-profile-art.yml.

    GH_PROFILE_USER=Fanfulla python scripts/fetch_shipped.py
"""
import datetime
import json
import os
import sys

import requests

USER = os.environ.get("GH_PROFILE_USER", "Fanfulla")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shipped.json")

# npm packages to pull download counts for, keyed by the repo that ships them.
NPM_PACKAGES = {"Lupin": "lupin-code"}

UA = {"User-Agent": "profile-readme-bot/1.0"}


def gh(path):
    """GitHub API. Uses GITHUB_TOKEN when present (higher rate limit in CI),
    works unauthenticated otherwise (60 req/h, plenty for one card a day)."""
    headers = dict(UA, Accept="application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"https://api.github.com/{path}", headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def npm_downloads(package):
    """Downloads in the last 30 days. Returns None rather than failing the whole
    card if npm is unreachable -- one missing number is not worth a red build."""
    try:
        r = requests.get(
            f"https://api.npmjs.org/downloads/point/last-month/{package}",
            headers=UA, timeout=30,
        )
        r.raise_for_status()
        return r.json().get("downloads")
    except requests.RequestException as exc:
        print(f"npm lookup failed for {package}: {exc}", file=sys.stderr)
        return None


def main():
    repos = [r for r in gh(f"users/{USER}/repos?per_page=100&sort=pushed")
             if not r["fork"]]
    if not repos:
        print(f"no public repos found for {USER}", file=sys.stderr)
        sys.exit(1)

    by_name = {}
    for r in repos:
        by_name[r["name"]] = {
            "name": r["name"],
            "url": r["html_url"],
            "stars": r["stargazers_count"],
            "forks": r["forks_count"],
            "language": r["language"],
            "pushed_at": r["pushed_at"][:10],
            "npm": None,
        }

    for repo_name, package in NPM_PACKAGES.items():
        if repo_name in by_name:
            by_name[repo_name]["npm"] = {
                "package": package,
                "downloads_30d": npm_downloads(package),
            }

    data = {
        "user": USER,
        "generated_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totals": {
            "repos": len(repos),
            "stars": sum(r["stargazers_count"] for r in repos),
            "forks": sum(r["forks_count"] for r in repos),
        },
        "repos": by_name,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    t = data["totals"]
    print(f"wrote {OUT_PATH}: {t['repos']} repos, {t['stars']} stars, {t['forks']} forks")


if __name__ == "__main__":
    main()
