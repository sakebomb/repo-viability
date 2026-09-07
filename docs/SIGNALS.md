# Signal specification (v0.1)

All scores are **suspected signals**. They are designed to be inspected, not to auto-ban a project.

## Implemented

### Empty / low-activity stargazers
Inspired by StarScout's low-activity signature and Astronomer's thin-profile features.

An account in the recent-stargazer sample is `emptyish` when it has zero followers **and** zero public repos **and** at least one of:

- account younger than 60 days
- starred within 2 days of account creation
- no name, bio, or blog

`empty_account_share` is that count over the sample size. Labels:

| share | label |
|---|---|
| < 14% | likely_genuine |
| 14-27% | mostly_genuine |
| 28-44% | mixed |
| >= 45% | high_risk |
| sample too small | unknown |

Small repos (<15 stars) default toward `unknown` / mid trust because the sample is not informative.

### Ratios
- `forks_per_star` — bought stars are cheap; bought forks with follow-on commits are not. Flag when stars >= 200 and ratio < 0.02.
- `open_issues_per_star` — ghost towns with huge star counts get `ghost_issue_tracker`.

These thresholds are starting priors from public writeups. They will move once we have a labeled set.

### Health
- license present on the GitHub repo object
- last `pushed_at` age
- contributor list length (API sample, not a full census)
- archived / disabled
- description / homepage present

Health is independent of authenticity. A dead honest repo can be 90 trust / 20 health.

## Specified, not shipped

| Signal | Why it matters | Blocker |
|---|---|---|
| MAD burst on star timeline | Catches one-day purchased dumps | Need starred_at paging across history; rate limit |
| Lockstep / CopyCatch | Catches farms that drip stars from aged accounts | Needs GHArchive / BigQuery, not the REST sample |
| Fork quality | Empty forks != interested developers | Extra API pages |
| Package downloads vs stars | Marketing vs actual use | npm/pypi/crates clients |
| External event alignment | Real spikes follow HN/release/CVE | Extra sources |

## What we will not store

- stargazer login lists in the default cache
- emails, bios, or follower graphs for resale
- anything that would make the cache a recruiting or spam list
