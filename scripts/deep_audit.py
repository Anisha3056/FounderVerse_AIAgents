from pathlib import Path
import pandas as pd

FILE_PATH = Path("data\saas-subscriptions-v1.0.0-analysis.xlsx")  # Change if needed

df = pd.read_excel(FILE_PATH)
df["invoice_date"] = pd.to_datetime(df["invoice_date"])


# 1. Account-to-subscription relationship
subs_per_account = df.groupby("account_id")["subscription_id"].nunique()
accounts_per_sub = df.groupby("subscription_id")["account_id"].nunique()

print("\n=== ACCOUNT / SUBSCRIPTION MAPPING ===")
print("Accounts with multiple subscriptions:",
      (subs_per_account > 1).sum())
print("Subscriptions linked to multiple accounts:",
      (accounts_per_sub > 1).sum())

# 2. Monthly distinct customers and subscriptions
df["month"] = df["invoice_date"].dt.to_period("M").astype(str)

monthly = df.groupby("month").agg(
    invoice_count=("invoice_id", "nunique"),
    distinct_accounts=("account_id", "nunique"),
    distinct_subscriptions=("subscription_id", "nunique"),
    invoice_amount_due=("amount_due", "sum"),
    invoice_amount_paid=("amount_paid", "sum"),
).reset_index()

print("\n=== MONTHLY COUNTS AND BILLING ===")
print(monthly.to_string(index=False))

# 3. Check whether amount_due equals MRR
print("\n=== AMOUNT DUE VS MRR ===")
print("Rows where amount_due != mrr:",
      (~df["amount_due"].round(2).eq(df["mrr"].round(2))).sum())

# 4. Can missing regions be recovered per account?
regions_per_account = (
    df.dropna(subset=["region"])
      .groupby("account_id")["region"]
      .nunique()
)

known_region_accounts = set(regions_per_account.index)
all_accounts = set(df["account_id"].unique())

print("\n=== REGION COMPLETENESS ===")
print("Accounts with at least one known region:",
      len(known_region_accounts))
print("Accounts with no known region:",
      len(all_accounts - known_region_accounts))
print("Accounts with conflicting known regions:",
      (regions_per_account > 1).sum())

# 5. Deduplicate subscription-level MRR
subscription_data = df.drop_duplicates("subscription_id")

print("\n=== SUBSCRIPTION-LEVEL MRR ===")
print("Unique subscriptions:", len(subscription_data))
print("Sum of one MRR value per subscription:",
      round(subscription_data["mrr"].sum(), 2))

# Optional: monthly paid/open/void invoice counts
print("\n=== STATUS BY MONTH ===")
status_monthly = pd.crosstab(df["month"], df["invoice_status"])
print(status_monthly.to_string())

print("\nDEEP AUDIT COMPLETE")