# SaaS Subscriptions & Customer Churn Dataset v1.0.0

A deterministic synthetic B2B SaaS billing system with upgrades, churn, monthly invoices, and failed-payment recovery.

This is synthetic educational data generated to model a fictional business. It does not represent a real company or establish industry benchmarks.

## Contents

- `plans`: 4 rows
- `accounts`: 5,000 rows
- `subscriptions`: 5,000 rows
- `invoices`: 85,448 rows
- `payments`: 87,287 rows

The source CSV ZIP preserves normalized source tables. SQLite contains the same
tables. XLSX and Parquet contain an analysis-ready denormalized view. Starter
examples demonstrate safe read-only exploration.

## Reproducibility

Built by `datasets/generate.py` with version `1.0.0` and seed
`2025090502`. See `manifest.json` for row profiles, reference outputs,
validation checks, file sizes, and SHA-256 checksums.

## License

See `LICENSE.txt`. Limitations from the catalog:
- This is synthetic educational data generated to model a fictional business. It does not represent a real company or establish industry benchmarks.
- Synthetic invoices use monthly billing only.
- MRR excludes usage pricing and tax.
- No PII is included.
