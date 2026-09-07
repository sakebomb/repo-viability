# repo-viability

Objective signals for **whether a GitHub repository is viable to trust**, not whether it matches your taste.

Stars and forks are treated as *evidence to audit*, not as a popularity score. This project does **not** require n8n, Node, or an LLM. It speaks JSON so a personal triage pipeline can consume a trust report without inventing momentum from raw star counts.

```
python3 -m repo_viability torvalds/linux
python3 -m repo_viability owner/repo --json
GITHUB_TOKEN=ghp_... python3 -m repo_viability some/repo --sample 40
```

From a checkout:

```
cd repo-viability
PYTHONPATH=src python3 -m repo_viability pallets/flask --json
```

No `npm install`. A token is optional (60 req/hr anonymous, 5,000 with a classic PAT that can read public repos).

**Stargazer identities (2026):** GitHub now limits `/repos/{owner}/{repo}/stargazers` to admins and collaborators. For everyone else the CLI still returns health/ratio scores, sets `authenticity` to `unknown`, and adds `stargazers_unreadable`. That is a suspected-signal gap, not a fraud conviction. Use `/repos/{owner}/{repo}/stargazers/history` (counts only) in a later burst/MAD mode — do not scrape HTML to dodge the API.

## What it measures (v0.1)

| Family | Signals | Status |
|---|---|---|
| Authenticity | empty-account share, new-at-star-time, star/fork/issue ratios | implemented |
| Health | last push age, license present, contributor count, description/homepage | implemented |
| Risk | archived/disabled flags, extreme ratio shapes | implemented |
| Lockstep farms | GHArchive / CopyCatch-style clustering | specified, not in v0.1 |
| Downstream demand | package downloads vs stars | specified, not in v0.1 |

Output is a **suspected-signal report**, not a fraud conviction.

## What we reuse vs rewrite

We reimplement published heuristics with attribution. We do not vendor other codebases.

- StarScout + ICSE 2026 paper: low-activity / empty-account idea; lockstep as a future deep mode
- Astronomer (MIT): account-age and contribution thinness as trust features
- StarGuard / fake-star-detector writeups: burst + empty-account pairing later
- GitHub AUP / API ToS: cache derived repo scores; do not resell personal profiles

See [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md) and [docs/SIGNALS.md](docs/SIGNALS.md).

## Cache (not a sellable user database)

Scans write **repo-level derived scores** to `~/.cache/repo-viability/cache.sqlite`.

That cache is for rate limits and later history of a *repository's* authenticity score. It is not a dataset of stargazer identities to sell. GitHub terms prohibit selling personal information collected from the service. If this becomes a commercial API, sell the **repo verdict**, not a dossier of users.

## JSON contract

```json
{
  "schema_version": "0.1",
  "repo": "pallets/flask",
  "trust_score": 78,
  "health_score": 84,
  "authenticity": "likely_genuine",
  "flags": [],
  "ratios": {"forks_per_star": 0.16, "open_issues_per_star": 0.01},
  "sample": {"stargazers_scored": 30, "empty_account_share": 0.07},
  "evidence": ["..."]
}
```

`authenticity`: `likely_genuine` | `mostly_genuine` | `mixed` | `high_risk` | `unknown`.

## Roadmap

1. v0.1 — API sample + ratios + local cache (this tree)
2. v0.2 — star timeline bursts (MAD) + fork-owner quality
3. v0.3 — optional GHArchive/BigQuery lockstep deep mode
4. Hosted badge / API only after rate-limit and ToS design is explicit

## License

MIT. Heuristic ideas from cited papers remain theirs; this implementation is original.
