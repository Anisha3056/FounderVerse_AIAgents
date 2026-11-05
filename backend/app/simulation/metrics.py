
import csv
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path


# Project root / data
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _read_csv(filename: str) -> list[dict]:
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. "
            "Ensure the CSV files are in the project's data folder."
        )

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _parse_date(value: str | None):
    if not value:
        return None

    value = value.strip()

    if not value:
        return None

    # Handle common ISO and date-only CSV formats.
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        for date_format in (
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y",
        ):
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                continue

    return None


def _month_key(value: datetime) -> str:
    return f"{value.year:04d}-{value.month:02d}"


@lru_cache(maxsize=1)
def get_historical_profile() -> dict:
    """
    Calculate a reusable baseline from the supplied SaaS CSVs.

    The result contains observed dataset statistics, not guaranteed
    forecasts for a new startup.
    """
    accounts = _read_csv("accounts.csv")
    subscriptions = _read_csv("subscriptions.csv")
    plans = _read_csv("plans.csv")
    invoices = _read_csv("invoices.csv")
    payments = _read_csv("payments.csv")

    account_by_id = {
        row.get("account_id"): row
        for row in accounts
        if row.get("account_id")
    }

    plan_by_id = {
        row.get("plan_id"): row
        for row in plans
        if row.get("plan_id")
    }

    parsed_subscriptions = []

    for row in subscriptions:
        started = _parse_date(row.get("started_at"))
        ended = _parse_date(row.get("ended_at"))

        account = account_by_id.get(row.get("account_id"), {})
        plan = plan_by_id.get(row.get("plan_id"), {})

        try:
            mrr = float(row.get("mrr") or 0)
        except (ValueError, TypeError):
            mrr = 0.0

        parsed_subscriptions.append({
            **row,
            "_started": started,
            "_ended": ended,
            "_mrr": max(0.0, mrr),
            "_account": account,
            "_plan": plan,
        })

    # Use the last month present in the data as the observation end.
    all_dates = [
        date
        for row in parsed_subscriptions
        for date in (row["_started"], row["_ended"])
        if date is not None
    ]

    observation_end = max(all_dates) if all_dates else datetime.now()

    # Monthly subscription cohorts and subscription-month exposure.
    starts_by_month = Counter()
    active_by_month = defaultdict(int)
    cancelled_by_month = Counter()
    subscription_months = 0.0
    cancelled_lifetimes = []

    for row in parsed_subscriptions:
        started = row["_started"]
        ended = row["_ended"]

        if started is None:
            continue

        starts_by_month[_month_key(started)] += 1

        effective_end = min(ended, observation_end) if ended else observation_end

        if effective_end < started:
            continue

        start_month = started.year * 12 + started.month
        end_month = effective_end.year * 12 + effective_end.month

        exposure = max(1, end_month - start_month + 1)
        subscription_months += exposure

        # Count subscription exposure in each observed calendar month.
        month_number = start_month

        while month_number <= end_month:
            year = (month_number - 1) // 12
            month = (month_number - 1) % 12 + 1
            active_by_month[f"{year:04d}-{month:02d}"] += 1
            month_number += 1

        if ended is not None:
            cancelled_by_month[_month_key(ended)] += 1
            cancelled_lifetimes.append(
                max(0.0, (ended - started).days / 30.4375)
            )

    observed_months = sorted(active_by_month)

    monthly_new_counts = [
        starts_by_month[month]
        for month in sorted(starts_by_month)
    ]

    # Calculate acquisition as new subscriptions / prior active base.
    # This is a historical ratio, not a claim about causal marketing impact.
    acquisition_ratios = []

    for month in sorted(starts_by_month):
        previous_active = active_by_month.get(month, 0)
        new_count = starts_by_month[month]

        if previous_active > 0:
            acquisition_ratios.append(new_count / previous_active)

    acquisition_ratio = (
        statistics.median(acquisition_ratios)
        if acquisition_ratios
        else 0.0
    )

    # Exposure-based monthly cancellation estimate.
    cancelled_count = sum(
        1 for row in parsed_subscriptions
        if row["_ended"] is not None
    )

    monthly_churn = (
        cancelled_count / subscription_months
        if subscription_months > 0
        else 0.0
    )

    # A month-level cross-check is useful for diagnostics.
    monthly_churn_rates = []

    for month, active_count in active_by_month.items():
        cancellations = cancelled_by_month.get(month, 0)

        if active_count > 0:
            monthly_churn_rates.append(
                min(1.0, cancellations / active_count)
            )

    # Calculate observed plan MRR/customer ratios.
    positive_mrr = [
        row["_mrr"]
        for row in parsed_subscriptions
        if row["_mrr"] > 0
    ]

    observed_mrr_per_subscription = (
        statistics.median(positive_mrr)
        if positive_mrr
        else 0.0
    )

    invoice_status_counts = Counter(
        (row.get("status") or "unknown").strip().lower()
        for row in invoices
    )

    payment_status_counts = Counter(
        (row.get("status") or "unknown").strip().lower()
        for row in payments
    )

    return {
        "source": "project CSV datasets",
        "accounts_count": len(accounts),
        "subscriptions_count": len(subscriptions),
        "plans_count": len(plans),
        "invoices_count": len(invoices),
        "payments_count": len(payments),
        "observed_months": len(observed_months),
        "monthly_new_subscriptions_median": (
            statistics.median(monthly_new_counts)
            if monthly_new_counts else 0
        ),
        "historical_acquisition_ratio": max(
            0.0, acquisition_ratio
        ),
        "estimated_monthly_churn": min(
            0.5, max(0.0, monthly_churn)
        ),
        "median_monthly_churn_crosscheck": (
            statistics.median(monthly_churn_rates)
            if monthly_churn_rates else 0.0
        ),
        "median_cancelled_subscription_lifetime_months": (
            statistics.median(cancelled_lifetimes)
            if cancelled_lifetimes else None
        ),
        "median_mrr_per_subscription": (
            observed_mrr_per_subscription
        ),
        "invoice_status_counts": dict(invoice_status_counts),
        "payment_status_counts": dict(payment_status_counts),
    }
