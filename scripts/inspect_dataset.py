from pathlib import Path
import pandas as pd

# Change this to your actual Excel filename.
FILE_PATH = Path("data\saas-subscriptions-v1.0.0-analysis.xlsx")

if not FILE_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {FILE_PATH.resolve()}"
    )

df = pd.read_excel(FILE_PATH)

print("\n========== BASIC INFORMATION ==========")
print("Rows:", len(df))
print("Columns:", len(df.columns))
print("\nColumn names:")
print(df.columns.tolist())

print("\n========== DATA TYPES ==========")
print(df.dtypes)

print("\n========== MISSING VALUES ==========")
print(df.isna().sum())

print("\n========== UNIQUE COUNTS ==========")
for col in [
    "invoice_id",
    "account_id",
    "subscription_id",
    "plan_name",
    "region",
    "segment",
]:
    if col in df.columns:
        print(f"{col}: {df[col].nunique(dropna=True)}")

print("\n========== DUPLICATE CHECKS ==========")
print(
    "Duplicate invoice IDs:",
    df["invoice_id"].duplicated().sum()
)

print(
    "Duplicate complete rows:",
    df.duplicated().sum()
)

print("\n========== DATE RANGE ==========")
df["invoice_date"] = pd.to_datetime(
    df["invoice_date"], errors="coerce"
)

print("Earliest:", df["invoice_date"].min())
print("Latest:", df["invoice_date"].max())

print("\n========== INVOICE STATUS ==========")
print(df["invoice_status"].value_counts(dropna=False))

print("\n========== PLAN DISTRIBUTION ==========")
print(df["plan_name"].value_counts(dropna=False))

print("\n========== REGION DISTRIBUTION ==========")
print(df["region"].value_counts(dropna=False))

print("\n========== SEGMENT DISTRIBUTION ==========")
print(df["segment"].value_counts(dropna=False))

print("\n========== NUMERIC SUMMARY ==========")
numeric_cols = [
    "seats",
    "mrr",
    "amount_due",
    "amount_paid",
]

print(df[numeric_cols].describe())

print("\n========== MRR REPEAT CHECK ==========")
mrr_per_subscription = (
    df.groupby("subscription_id")["mrr"]
    .agg(["count", "nunique", "min", "max"])
)

print("\nSubscriptions with multiple invoice rows:")
print((mrr_per_subscription["count"] > 1).sum())

print("\nSubscriptions with multiple MRR values:")
print((mrr_per_subscription["nunique"] > 1).sum())

print("\n========== MONTHLY INVOICE COUNTS ==========")
df["invoice_month"] = (
    df["invoice_date"].dt.to_period("M").astype(str)
)

print(df.groupby("invoice_month").size())

print("\n========== AUDIT COMPLETE ==========")