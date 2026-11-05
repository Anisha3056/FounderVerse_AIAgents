#!/usr/bin/env python3
r"""
FounderVerse SaaS dataset audit
Uses only Python's standard library.

Usage:
  python audit_saas_dataset.py "C:\path\to\saas-subscriptions-v1.0.0-source-csv.zip"
  python audit_saas_dataset.py "C:\path\to\extracted\dataset-folder"

Outputs:
  saas_audit_output/audit_report.txt
  saas_audit_output/monthly_metrics.csv
  saas_audit_output/audit_summary.json
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


TABLES = {
    "accounts": {
        "file": "accounts.csv",
        "pk": "account_id",
        "columns": ["account_id", "created_at", "region", "segment", "acquisition_channel"],
    },
    "subscriptions": {
        "file": "subscriptions.csv",
        "pk": "subscription_id",
        "columns": ["subscription_id", "account_id", "plan_id", "started_at", "ended_at", "status", "seats", "mrr"],
    },
    "plans": {
        "file": "plans.csv",
        "pk": "plan_id",
        "columns": ["plan_id", "plan_name", "monthly_price", "included_seats"],
    },
    "invoices": {
        "file": "invoices.csv",
        "pk": "invoice_id",
        "columns": ["invoice_id", "subscription_id", "invoice_date", "due_date", "amount_due", "invoice_status"],
    },
    "payments": {
        "file": "payments.csv",
        "pk": "payment_id",
        "columns": ["payment_id", "invoice_id", "attempted_at", "payment_status", "amount"],
    },
}

RELATIONSHIPS = [
    ("subscriptions", "account_id", "accounts", "account_id"),
    ("subscriptions", "plan_id", "plans", "plan_id"),
    ("invoices", "subscription_id", "subscriptions", "subscription_id"),
    ("payments", "invoice_id", "invoices", "invoice_id"),
]


def parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    return date.fromisoformat(value[:10])


def read_csv_bytes(raw: bytes):
    text = raw.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text, newline="")))


def load_tables(source: Path):
    tables = {}
    if source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as zf:
            names = set(zf.namelist())
            for table, info in TABLES.items():
                # Locate the named CSV even if it is nested inside a folder.
                matches = [n for n in names if n.replace("\\", "/").split("/")[-1] == info["file"]]
                if len(matches) != 1:
                    raise ValueError(
                        f"Expected exactly one {info['file']} in ZIP; found {len(matches)}."
                    )
                tables[table] = read_csv_bytes(zf.read(matches[0]))
            extras = {}
            for wanted in ("README.md", "DATA_DICTIONARY.md", "LICENSE.txt"):
                matches = [n for n in names if n.replace("\\", "/").split("/")[-1] == wanted]
                if matches:
                    extras[wanted] = zf.read(matches[0]).decode("utf-8-sig", errors="replace")
    elif source.is_dir():
        for table, info in TABLES.items():
            path = source / info["file"]
            if not path.exists():
                raise FileNotFoundError(f"Missing required file: {path}")
            tables[table] = read_csv_bytes(path.read_bytes())
        extras = {}
        for wanted in ("README.md", "DATA_DICTIONARY.md", "LICENSE.txt"):
            path = source / wanted
            if path.exists():
                extras[wanted] = path.read_text(encoding="utf-8-sig", errors="replace")
    else:
        raise ValueError("Input must be a ZIP file or a folder containing the CSV files.")
    return tables, extras


def main():
    parser = argparse.ArgumentParser(description="Audit the FounderVerse SaaS source dataset.")
    parser.add_argument("source", help="Path to source ZIP or extracted dataset folder")
    args = parser.parse_args()
    source = Path(args.source).expanduser().resolve()
    tables, extras = load_tables(source)

    output_dir = (source.parent if source.is_file() else source) / "saas_audit_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    report = []
    summary = {
        "source": str(source),
        "table_counts": {},
        "schema_checks": {},
        "missing_values": {},
        "primary_key_duplicates": {},
        "foreign_key_checks": {},
        "categorical_distributions": {},
        "date_checks": {},
        "billing_reconciliation": {},
        "warnings": [],
    }

    def line(text=""):
        report.append(str(text))

    line("FOUNDERVERSE — SAAS DATASET AUDIT")
    line("=" * 42)
    line(f"Source: {source}")
    line("")

    for name, rows in tables.items():
        expected = TABLES[name]["columns"]
        actual = list(rows[0].keys()) if rows else []
        missing_columns = [c for c in expected if c not in actual]
        extra_columns = [c for c in actual if c not in expected]
        missing_values = {
            c: sum(not (r.get(c) or "").strip() for r in rows)
            for c in actual
            if any(not (r.get(c) or "").strip() for r in rows)
        }
        pk = TABLES[name]["pk"]
        pk_values = [r.get(pk, "") for r in rows]
        duplicate_count = len(pk_values) - len(set(pk_values))
        summary["table_counts"][name] = len(rows)
        summary["schema_checks"][name] = {
            "expected_columns": expected,
            "actual_columns": actual,
            "missing_columns": missing_columns,
            "extra_columns": extra_columns,
        }
        summary["missing_values"][name] = missing_values
        summary["primary_key_duplicates"][name] = duplicate_count

        line(f"[{name.upper()}]")
        line(f"Rows: {len(rows):,}")
        line(f"Columns: {', '.join(actual)}")
        line(f"Missing expected columns: {missing_columns or 'None'}")
        line(f"Unexpected columns: {extra_columns or 'None'}")
        line(f"Missing values: {missing_values or 'None'}")
        line(f"Duplicate {pk}: {duplicate_count}")
        line("")

        if missing_columns:
            summary["warnings"].append(f"{name}: missing expected columns {missing_columns}")
        if duplicate_count:
            summary["warnings"].append(f"{name}: duplicate primary keys = {duplicate_count}")

    # Foreign-key integrity
    line("[FOREIGN-KEY INTEGRITY]")
    for child, child_field, parent, parent_field in RELATIONSHIPS:
        parent_keys = {r[parent_field] for r in tables[parent]}
        bad_rows = [r for r in tables[child] if r.get(child_field) not in parent_keys]
        result = {
            "child_table": child,
            "child_field": child_field,
            "parent_table": parent,
            "parent_field": parent_field,
            "invalid_rows": len(bad_rows),
            "distinct_invalid_values": sorted({r.get(child_field, "") for r in bad_rows}),
        }
        summary["foreign_key_checks"][f"{child}.{child_field}->{parent}.{parent_field}"] = result
        line(f"{child}.{child_field} -> {parent}.{parent_field}: {len(bad_rows)} invalid row(s)")
        if bad_rows:
            summary["warnings"].append(
                f"Broken relationship {child}.{child_field} -> {parent}.{parent_field}: {len(bad_rows)} rows"
            )
    line("")

    # Categorical distributions
    categorical_fields = {
        "accounts": ["region", "segment", "acquisition_channel"],
        "subscriptions": ["status"],
        "plans": ["plan_name"],
        "invoices": ["invoice_status"],
        "payments": ["payment_status"],
    }
    line("[CATEGORICAL DISTRIBUTIONS]")
    for table, fields in categorical_fields.items():
        for field in fields:
            counts = dict(sorted(Counter(r.get(field, "") for r in tables[table]).items()))
            summary["categorical_distributions"][f"{table}.{field}"] = counts
            line(f"{table}.{field}: {counts}")
    line("")

    accounts = tables["accounts"]
    subs = tables["subscriptions"]
    plans = tables["plans"]
    invoices = tables["invoices"]
    payments = tables["payments"]

    # Subscription checks
    status_counts = Counter(r["status"] for r in subs)
    ended_before_start = 0
    active_with_end = 0
    cancelled_without_end = 0
    invalid_subscription_dates = 0
    for r in subs:
        try:
            started = parse_date(r.get("started_at"))
            ended = parse_date(r.get("ended_at"))
            if started and ended and ended < started:
                ended_before_start += 1
            if r["status"] == "active" and ended:
                active_with_end += 1
            if r["status"] == "cancelled" and not ended:
                cancelled_without_end += 1
        except ValueError:
            invalid_subscription_dates += 1

    subs_per_account = Counter(r["account_id"] for r in subs)
    multiple_sub_accounts = sum(n > 1 for n in subs_per_account.values())
    max_subs_per_account = max(subs_per_account.values(), default=0)

    # Invoice and payment reconciliation
    invoices_by_id = {r["invoice_id"]: r for r in invoices}
    payments_by_invoice = defaultdict(list)
    for p in payments:
        payments_by_invoice[p["invoice_id"]].append(p)

    no_payment_rows = [r for r in invoices if not payments_by_invoice[r["invoice_id"]]]
    no_payment_by_status = dict(Counter(r["invoice_status"] for r in no_payment_rows))
    paid_without_success = [
        r for r in invoices
        if r["invoice_status"] == "paid"
        and not any(p["payment_status"] == "succeeded" for p in payments_by_invoice[r["invoice_id"]])
    ]
    open_with_success = [
        r for r in invoices
        if r["invoice_status"] == "open"
        and any(p["payment_status"] == "succeeded" for p in payments_by_invoice[r["invoice_id"]])
    ]
    void_with_payments = [
        r for r in invoices
        if r["invoice_status"] == "void" and payments_by_invoice[r["invoice_id"]]
    ]
    payment_attempt_counts = Counter(len(payments_by_invoice[r["invoice_id"]]) for r in invoices)
    payment_status_counts = Counter(r["payment_status"] for r in payments)
    payment_date_before_invoice = 0
    payment_date_parse_errors = 0
    for p in payments:
        try:
            invoice_date = parse_date(invoices_by_id[p["invoice_id"]]["invoice_date"])
            attempted = parse_date(p["attempted_at"])
            if invoice_date and attempted and attempted < invoice_date:
                payment_date_before_invoice += 1
        except (ValueError, KeyError):
            payment_date_parse_errors += 1

    summary["date_checks"] = {
        "subscription_end_before_start": ended_before_start,
        "active_subscriptions_with_end_date": active_with_end,
        "cancelled_subscriptions_without_end_date": cancelled_without_end,
        "invalid_subscription_dates": invalid_subscription_dates,
        "accounts_with_multiple_subscription_rows": multiple_sub_accounts,
        "max_subscription_rows_per_account": max_subs_per_account,
        "payments_before_invoice_date": payment_date_before_invoice,
        "payment_date_parse_errors": payment_date_parse_errors,
    }
    summary["billing_reconciliation"] = {
        "invoice_count": len(invoices),
        "payment_attempt_count": len(payments),
        "invoices_with_at_least_one_payment": sum(bool(payments_by_invoice[r["invoice_id"]]) for r in invoices),
        "invoices_without_payment_rows": len(no_payment_rows),
        "invoices_without_payment_by_status": no_payment_by_status,
        "invoice_status_counts": dict(Counter(r["invoice_status"] for r in invoices)),
        "payment_status_counts": dict(payment_status_counts),
        "paid_invoices_without_successful_payment": len(paid_without_success),
        "open_invoices_with_successful_payment": len(open_with_success),
        "void_invoices_with_payment_rows": len(void_with_payments),
        "invoice_payment_attempt_count_distribution": dict(sorted(payment_attempt_counts.items())),
    }

    line("[SUBSCRIPTION / DATE CHECKS]")
    for k, v in summary["date_checks"].items():
        line(f"{k}: {v}")
    line("")
    line("[BILLING RECONCILIATION]")
    for k, v in summary["billing_reconciliation"].items():
        line(f"{k}: {v}")
    line("")

    # Monthly metrics. Month boundaries are calendar months.
    # Active at month end means started_on/before month-end and not ended_on/before month-end.
    months = set()
    for r in subs:
        if r.get("started_at"):
            months.add(r["started_at"][:7])
        if r.get("ended_at"):
            months.add(r["ended_at"][:7])
    for r in invoices:
        if r.get("invoice_date"):
            months.add(r["invoice_date"][:7])
    for r in payments:
        if r.get("attempted_at"):
            months.add(r["attempted_at"][:7])

    month_rows = []
    for month in sorted(months):
        year, mon = map(int, month.split("-"))
        month_start = date(year, mon, 1)
        if mon == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, mon + 1, 1)
        month_end = date.fromordinal(next_month.toordinal() - 1)
        previous_day = date.fromordinal(month_start.toordinal() - 1)

        active_start = 0
        active_end = 0
        mrr_end = 0.0
        started_count = 0
        churned_count = 0
        for r in subs:
            start = parse_date(r["started_at"])
            end = parse_date(r["ended_at"])
            mrr = float(r["mrr"])
            if start and start <= previous_day and (end is None or end > previous_day):
                active_start += 1
            if start and start <= month_end and (end is None or end > month_end):
                active_end += 1
                mrr_end += mrr
            if start and month_start <= start <= month_end:
                started_count += 1
            if end and month_start <= end <= month_end:
                churned_count += 1

        month_invoices = [r for r in invoices if r["invoice_date"][:7] == month]
        month_payments = [r for r in payments if r["attempted_at"][:7] == month]
        invoice_status = Counter(r["invoice_status"] for r in month_invoices)
        payment_status = Counter(r["payment_status"] for r in month_payments)

        month_rows.append({
            "month": month,
            "subscriptions_active_start": active_start,
            "subscriptions_started": started_count,
            "subscriptions_churned": churned_count,
            "subscription_churn_rate": (
                round(churned_count / active_start, 6) if active_start else ""
            ),
            "subscriptions_active_end": active_end,
            "mrr_active_end": round(mrr_end, 2),
            "invoice_count": len(month_invoices),
            "invoice_amount_due": round(sum(float(r["amount_due"]) for r in month_invoices), 2),
            "invoices_paid": invoice_status.get("paid", 0),
            "invoices_open": invoice_status.get("open", 0),
            "invoices_void": invoice_status.get("void", 0),
            "payment_attempt_count": len(month_payments),
            "payment_attempts_succeeded": payment_status.get("succeeded", 0),
            "payment_attempts_failed": payment_status.get("failed", 0),
            "payment_attempt_amount": round(sum(float(r["amount"]) for r in month_payments), 2),
        })

    monthly_path = output_dir / "monthly_metrics.csv"
    with monthly_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(month_rows[0].keys()) if month_rows else [])
        writer.writeheader()
        writer.writerows(month_rows)

    # Include license/docs in report for convenient provenance review.
    line("[DATASET DOCUMENTATION]")
    for name in ("README.md", "DATA_DICTIONARY.md", "LICENSE.txt"):
        if name in extras:
            line(f"--- {name} ---")
            line(extras[name].strip())
            line("")

    if not summary["warnings"]:
        summary["warnings"].append("No duplicate primary keys or broken foreign keys detected.")
    summary["output_files"] = {
        "report": str(output_dir / "audit_report.txt"),
        "monthly_metrics": str(monthly_path),
        "summary_json": str(output_dir / "audit_summary.json"),
    }

    (output_dir / "audit_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("AUDIT COMPLETE")
    print(f"Input: {source}")
    print(f"Output folder: {output_dir}")
    print("\nTable counts:")
    for table, count in summary["table_counts"].items():
        print(f"  {table}: {count:,}")
    print("\nPrimary-key duplicates:")
    for table, count in summary["primary_key_duplicates"].items():
        print(f"  {table}: {count}")
    print("\nForeign-key invalid rows:")
    for relationship, result in summary["foreign_key_checks"].items():
        print(f"  {relationship}: {result['invalid_rows']}")
    print("\nKey findings:")
    print(f"  Subscriptions active/cancelled: {status_counts.get('active', 0):,}/{status_counts.get('cancelled', 0):,}")
    print(f"  Invoices without payment rows: {len(no_payment_rows):,} ({no_payment_by_status})")
    print(f"  Paid invoices without successful payment: {len(paid_without_success):,}")
    print(f"  Open invoices with successful payment: {len(open_with_success):,}")
    print(f"  Accounts with multiple subscription rows: {multiple_sub_accounts:,}")
    print(f"\nReport: {output_dir / 'audit_report.txt'}")
    print(f"Monthly metrics: {monthly_path}")
    print(f"JSON summary: {output_dir / 'audit_summary.json'}")


if __name__ == "__main__":
    main()
