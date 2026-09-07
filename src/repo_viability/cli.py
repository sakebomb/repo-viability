from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .cache import connect, get as cache_get, put as cache_put
from .github_client import GitHub, GitHubError
from .score import classify_account, score_report


def parse_repo(raw: str) -> tuple[str, str]:
    raw = raw.strip().rstrip("/")
    if raw.startswith("https://github.com/"):
        raw = raw[len("https://github.com/") :]
    elif raw.startswith("http://github.com/"):
        raw = raw[len("http://github.com/") :]
    parts = [p for p in raw.split("/") if p]
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("Expected owner/repo or a GitHub URL")
    return parts[0], parts[1]


def analyze(owner: str, name: str, sample: int, token: str | None) -> dict:
    gh = GitHub(token=token)
    repo = gh.repo(owner, name)
    contributors = gh.contributors(owner, name, per_page=30)
    stars = []
    try:
        stars = gh.stargazers(owner, name, per_page=min(sample, 100))
    except GitHubError:
        stars = []

    accounts: list[dict] = []
    rows = stars[:sample]
    for row in rows:
        user = row.get("user") if isinstance(row, dict) and "user" in row else row
        starred_at = row.get("starred_at") if isinstance(row, dict) else None
        login = (user or {}).get("login")
        if not login:
            continue
        try:
            profile = gh.user(login)
        except GitHubError:
            continue
        accounts.append(classify_account(profile, starred_at))

    return score_report(repo, accounts, contributor_count=len(contributors))


def render_text(report: dict) -> str:
    lines = [
        f"{report.get('repo')}  trust={report.get('trust_score')}  "
        f"health={report.get('health_score')}  authenticity={report.get('authenticity')}",
        f"stars={report['ratios']['stars']}  forks={report['ratios']['forks']}  "
        f"fork/star={report['ratios']['forks_per_star']}  "
        f"issues/star={report['ratios']['open_issues_per_star']}",
        f"sample={report['sample']['stargazers_scored']}  "
        f"empty={report['sample']['empty_account_share']}  "
        f"young={report['sample']['young_account_share']}",
    ]
    if report.get("flags"):
        lines.append("flags: " + ", ".join(report["flags"]))
    for item in report.get("evidence") or []:
        lines.append(f"- {item}")
    lines.append(report.get("disclaimer", ""))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo-viability",
        description="Audit GitHub star/fork signals and repo health. No n8n required.",
    )
    parser.add_argument("repo", help="owner/repo or https://github.com/owner/repo")
    parser.add_argument("--json", action="store_true", help="Print the machine contract only")
    parser.add_argument("--sample", type=int, default=25, help="Recent stargazers to profile (default 25)")
    parser.add_argument("--token", help="GitHub token (else GITHUB_TOKEN / GH_TOKEN)")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--cache-hours", type=int, default=24)
    parser.add_argument("--version", action="version", version=f"repo-viability {__version__}")
    args = parser.parse_args(argv)

    owner, name = parse_repo(args.repo)
    key = f"{owner}/{name}".lower()

    conn = None
    if not args.no_cache:
        conn = connect()
        cached = cache_get(conn, key, args.cache_hours)
        if cached:
            cached["cached"] = True
            if args.json:
                print(json.dumps(cached, indent=2))
            else:
                print(render_text(cached))
                print("(cached)")
            return 0

    try:
        report = analyze(owner, name, sample=max(5, args.sample), token=args.token)
    except GitHubError as exc:
        print(str(exc), file=sys.stderr)
        if exc.status == 403:
            print("Hint: set GITHUB_TOKEN to raise the rate limit.", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"unexpected error: {exc}", file=sys.stderr)
        return 1

    if conn is not None:
        cache_put(conn, key, report)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    return 0
