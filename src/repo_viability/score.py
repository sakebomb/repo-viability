"""Turn GitHub metadata + a stargazer sample into a viability report."""

from __future__ import annotations

from datetime import datetime, timezone


SCHEMA_VERSION = "0.1"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _days_ago(value: str | None) -> float | None:
    dt = _parse_dt(value)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def classify_account(user: dict, starred_at: str | None) -> dict:
    """Empty-account / low-activity heuristic inspired by StarScout + Astronomer."""
    created_days = _days_ago(user.get("created_at"))
    star_delay_days = None
    created = _parse_dt(user.get("created_at"))
    starred = _parse_dt(starred_at)
    if created and starred:
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if starred.tzinfo is None:
            starred = starred.replace(tzinfo=timezone.utc)
        star_delay_days = max(0.0, (starred - created).total_seconds() / 86400.0)

    followers = user.get("followers") or 0
    public_repos = user.get("public_repos") or 0
    following = user.get("following") or 0
    bio = (user.get("bio") or "").strip()
    blog = (user.get("blog") or "").strip()
    name = (user.get("name") or "").strip()

    flags: list[str] = []
    if created_days is not None and created_days < 60:
        flags.append("account_young")
    if star_delay_days is not None and star_delay_days < 2:
        flags.append("starred_near_creation")
    if followers == 0:
        flags.append("zero_followers")
    if public_repos == 0:
        flags.append("zero_repos")
    if following == 0:
        flags.append("zero_following")
    if not bio and not blog and not name:
        flags.append("empty_profile")

    emptyish = (
        "zero_followers" in flags
        and "zero_repos" in flags
        and ("account_young" in flags or "starred_near_creation" in flags or "empty_profile" in flags)
    )
    return {
        "login": user.get("login"),
        "flags": flags,
        "emptyish": emptyish,
        "created_days": created_days,
        "star_delay_days": star_delay_days,
    }


def authenticity_label(empty_share: float | None, sample_n: int, stars: int) -> str:
    if sample_n < 8 and stars > 50:
        return "unknown"
    if empty_share is None:
        return "unknown"
    if empty_share >= 0.45:
        return "high_risk"
    if empty_share >= 0.28:
        return "mixed"
    if empty_share >= 0.14:
        return "mostly_genuine"
    return "likely_genuine"


def score_report(repo: dict, sample_accounts: list[dict], contributor_count: int) -> dict:
    stars = repo.get("stargazers_count") or 0
    forks = repo.get("forks_count") or 0
    open_issues = repo.get("open_issues_count") or 0
    watchers = repo.get("subscribers_count") or repo.get("watchers_count") or 0

    forks_per_star = (forks / stars) if stars else None
    issues_per_star = (open_issues / stars) if stars else None

    empty = [a for a in sample_accounts if a.get("emptyish")]
    empty_share = (len(empty) / len(sample_accounts)) if sample_accounts else None
    young_share = (
        sum(1 for a in sample_accounts if "account_young" in a.get("flags", [])) / len(sample_accounts)
        if sample_accounts
        else None
    )

    flags: list[str] = []
    evidence: list[str] = []

    if repo.get("archived"):
        flags.append("archived")
        evidence.append("Repository is archived.")
    if repo.get("disabled"):
        flags.append("disabled")
    if not repo.get("license"):
        flags.append("no_license")
        evidence.append("No license detected on the GitHub repo object.")
    if not repo.get("description"):
        flags.append("no_description")

    pushed_days = _days_ago(repo.get("pushed_at"))
    if pushed_days is not None and pushed_days > 365:
        flags.append("stale_push")
        evidence.append(f"Last push was {pushed_days:.0f} days ago.")

    if stars >= 200 and forks_per_star is not None and forks_per_star < 0.02:
        flags.append("tiny_fork_ratio")
        evidence.append(
            f"Fork/star ratio is {forks_per_star:.3f}. Organic projects this size usually fork more."
        )
    if stars >= 200 and issues_per_star is not None and issues_per_star < 0.002 and open_issues <= 2:
        flags.append("ghost_issue_tracker")
        evidence.append("Almost no issues relative to star count.")

    if empty_share is not None:
        evidence.append(
            f"{len(empty)}/{len(sample_accounts)} sampled recent stargazers look empty/low-activity "
            f"({empty_share:.0%})."
        )
        if empty_share >= 0.28:
            flags.append("high_empty_stargazer_share")

    if contributor_count == 1 and stars >= 100:
        flags.append("single_contributor")
        evidence.append("Only one visible contributor on a relatively starred repo (bus factor 1).")

    auth = authenticity_label(empty_share, len(sample_accounts), stars)

    trust = 80
    if empty_share is not None:
        trust -= int(empty_share * 70)
    if "tiny_fork_ratio" in flags:
        trust -= 12
    if "ghost_issue_tracker" in flags:
        trust -= 8
    if "high_empty_stargazer_share" in flags:
        trust -= 10
    if stars < 15:
        trust = max(trust, 70)
        if not sample_accounts:
            auth = "unknown"
    trust = max(0, min(100, trust))

    health = 70
    if repo.get("license"):
        health += 8
    if repo.get("description"):
        health += 4
    if repo.get("homepage"):
        health += 3
    if pushed_days is not None:
        if pushed_days <= 30:
            health += 10
        elif pushed_days <= 180:
            health += 4
        elif pushed_days > 365:
            health -= 20
    if contributor_count >= 5:
        health += 8
    elif contributor_count <= 1:
        health -= 8
    if repo.get("archived") or repo.get("disabled"):
        health -= 30
    if not repo.get("has_issues"):
        health -= 5
    health = max(0, min(100, health))

    return {
        "schema_version": SCHEMA_VERSION,
        "repo": repo.get("full_name"),
        "html_url": repo.get("html_url"),
        "trust_score": trust,
        "health_score": health,
        "authenticity": auth,
        "flags": flags,
        "ratios": {
            "stars": stars,
            "forks": forks,
            "open_issues": open_issues,
            "watchers": watchers,
            "forks_per_star": round(forks_per_star, 4) if forks_per_star is not None else None,
            "open_issues_per_star": round(issues_per_star, 4) if issues_per_star is not None else None,
        },
        "health": {
            "license": (repo.get("license") or {}).get("spdx_id"),
            "pushed_days_ago": round(pushed_days, 1) if pushed_days is not None else None,
            "contributor_sample_count": contributor_count,
            "archived": bool(repo.get("archived")),
            "default_branch": repo.get("default_branch"),
        },
        "sample": {
            "stargazers_scored": len(sample_accounts),
            "empty_account_share": round(empty_share, 3) if empty_share is not None else None,
            "young_account_share": round(young_share, 3) if young_share is not None else None,
        },
        "evidence": evidence,
        "disclaimer": (
            "Suspected signals only. Empty-account share is estimated from a recent "
            "stargazer sample, not a census of every star."
        ),
    }
