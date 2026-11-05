# SaaS Subscriptions & Customer Churn Dataset data dictionary

Version: 1.0.0  
Coverage: 2023-01-01 through 2025-12-31  
Source type: synthetic

## `plans`

Grain: One row per plan.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `plan_id` | text | no | Stable plan key. |
| `plan_name` | text | no | Plan display name. |
| `monthly_price` | decimal | no | Monthly recurring price. |
| `included_seats` | integer | no | Included user seats. |

## `accounts`

Grain: One row per account.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `account_id` | text | no | Stable account key. |
| `created_at` | date | no | Account creation date. |
| `region` | text | no | Commercial region. |
| `segment` | text | no | SMB, mid_market, or enterprise. |
| `acquisition_channel` | text | no | First-touch channel. |

## `subscriptions`

Grain: One row per account subscription period.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `subscription_id` | text | no | Stable subscription key. |
| `account_id` | text | no | Owning account. |
| `plan_id` | text | no | Subscribed plan. |
| `started_at` | date | no | Service start date. |
| `ended_at` | date | yes | Churn date when ended. |
| `status` | text | no | active or cancelled. |
| `seats` | integer | no | Purchased seats. |
| `mrr` | decimal | no | Contracted monthly recurring revenue. |

## `invoices`

Grain: One row per subscription billing month.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `invoice_id` | text | no | Stable invoice key. |
| `subscription_id` | text | no | Billed subscription. |
| `invoice_date` | date | no | Billing date. |
| `due_date` | date | no | Payment due date. |
| `amount_due` | decimal | no | Amount billed. |
| `invoice_status` | text | no | paid, open, or void. |

## `payments`

Grain: One row per payment attempt.
| Column | Type | Nullable | Description |
|---|---|---:|---|
| `payment_id` | text | no | Stable payment key. |
| `invoice_id` | text | no | Invoice attempted. |
| `attempted_at` | date | no | Attempt date. |
| `payment_status` | text | no | succeeded or failed. |
| `amount` | decimal | no | Attempted amount. |

## Relationships

- `subscriptions.account_id` → `accounts.account_id` (many-to-one)
- `subscriptions.plan_id` → `plans.plan_id` (many-to-one)
- `invoices.subscription_id` → `subscriptions.subscription_id` (many-to-one)
- `payments.invoice_id` → `invoices.invoice_id` (many-to-one)
