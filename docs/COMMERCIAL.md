# Cache now, product later

## Do this

Keep a local SQLite cache of `owner/repo → {trust, health, authenticity, flags, scanned_at}`.

That is useful immediately (rate limits) and is the seed of a product: what did this repo look like 90 days ago?

## Do not do this

Do not build a warehouse of stargazer profiles so we can sell it later.

Reasons, in order:

1. GitHub AUP / API terms disallow selling personal information collected from the service.
2. Farm accounts get deleted; the raw identity table rots.
3. The valuable object is the **repo verdict over time**, which you can produce again from the API.
4. Selling "these 1.3M logins are bots" is a moderation list with legal and accuracy risk. StarScout publishes suspected sets for research under their own constraints; that is not a SaaS SKU.

## A ToS-safer commercial shape (later)

- On-demand scan API: customer submits `owner/repo`, receives the JSON contract.
- Optional historical *repo* series from caches the customer or you computed.
- Badge for maintainers who scan *their own* repo.
- Enterprise due-diligence: batch scan of a dependency tree, billed per scan.

Revisit this file before any paid hosting. Token pooling, attribution of GitHub as the data source, privacy policy, and "suspected not proven" language are prerequisites — not polish.
