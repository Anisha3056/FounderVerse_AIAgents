
import { useState } from "react";
import { createCompany } from "../services/api";

export default function CompanySetup({ token, onCompanyCreated }) {
  const [form, setForm] = useState({
    company_name: "",
    industry: "SaaS",
    stage: "idea",
    region: "",
    team_size: 1,
    initial_capital: 0,
    initial_customers: 0,
    monthly_revenue: 0,
    monthly_revenue_status: "known",
    monthly_expenses: 0,
    target_market: "",
    acquisition_channel: "Organic",

    // Optional founder-specific assumptions.
    expected_new_customers: "",
    known_monthly_churn_percent: "",
    expected_monthly_expense_growth_percent: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function updateField(field, value) {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (
      form.known_monthly_churn_percent !== "" &&
      Number(form.known_monthly_churn_percent) > 100
    ) {
      setError("Monthly churn must be between 0% and 100%.");
      return;
    }

    if (
      form.expected_monthly_expense_growth_percent !== "" &&
      Number(form.expected_monthly_expense_growth_percent) > 100
    ) {
      setError("Monthly expense growth must not exceed 100%.");
      return;
    }

    setLoading(true);

    // Blank optional values become null, not zero.
    const payload = {
      ...form,
      expected_new_customers:
        form.expected_new_customers === ""
          ? null
          : Number(form.expected_new_customers),
      known_monthly_churn_percent:
        form.known_monthly_churn_percent === ""
          ? null
          : Number(form.known_monthly_churn_percent),
      expected_monthly_expense_growth_percent:
        form.expected_monthly_expense_growth_percent === ""
          ? null
          : Number(form.expected_monthly_expense_growth_percent),
       monthly_revenue:
    form.monthly_revenue_status === "known"
      ? Number(form.monthly_revenue)
      : null,
    };

    try {
      const result = await createCompany(payload, token);

      localStorage.setItem(
        "founderverse_company_id",
        result.company_id
      );

      onCompanyCreated(result.company_id);
    } catch (err) {
      setError(err.message || "Unable to create company.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="setup-card">
        <div className="auth-heading">
          <span>01 / COMPANY SETUP</span>
          <h2>Tell us about your startup.</h2>
          <p>
            Your business data forms the foundation of your
            FounderVerse simulation. Leave unknown assumptions
            blank and we will use documented baseline values.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <label>Company Name</label>
          <input
            type="text"
            placeholder="e.g. LearnFlow"
            value={form.company_name}
            onChange={(e) =>
              updateField("company_name", e.target.value)
            }
            required
          />

          <label>Industry</label>
          <select
            value={form.industry}
            onChange={(e) => updateField("industry", e.target.value)}
          >
            <option value="SaaS">SaaS</option>
          </select>

          <label>Startup Stage</label>
          <select
            value={form.stage}
            onChange={(e) => updateField("stage", e.target.value)}
          >
            <option value="idea">Idea</option>
            <option value="early">Early</option>
            <option value="growth">Growth</option>
            <option value="scale">Scale</option>
          </select>

          <label>Region</label>
          <input
            type="text"
            placeholder="e.g. India"
            value={form.region}
            onChange={(e) => updateField("region", e.target.value)}
          />

          <label>Team Size</label>
          <input
            type="number"
            min="1"
            step="1"
            required
            value={form.team_size}
            onChange={(e) =>
              updateField("team_size", Number(e.target.value))
            }
          />

          <label>Initial Capital (₹)</label>
          <input
            type="number"
            min="0"
            step="any"
            value={form.initial_capital}
            onChange={(e) =>
              updateField("initial_capital", Number(e.target.value))
            }
          />

          <label>Current Customers</label>
          <input
            type="number"
            min="0"
            step="1"
            value={form.initial_customers}
            onChange={(e) =>
              updateField("initial_customers", Number(e.target.value))
            }
          />

          
<label>Do you know your current monthly revenue?</label>

<select
  value={form.monthly_revenue_status}
  onChange={(e) =>
    updateField("monthly_revenue_status", e.target.value)
  }
>
  <option value="known">Yes, I know the amount</option>
  <option value="unknown">Not sure yet</option>
</select>

{form.monthly_revenue_status === "known" ? (
  <>
    <label>Monthly Revenue (₹)</label>
    <input
      type="number"
      min="0"
      step="any"
      placeholder="Enter 0 if you currently earn nothing"
      value={form.monthly_revenue}
      onChange={(e) =>
        updateField("monthly_revenue", Number(e.target.value))
      }
      required
    />
  </>
) : (
  <p className="setup-help">
    No problem! We'll record revenue as unknown and clearly
    label any financial projections that use a zero-revenue
    assumption.
  </p>
)}


          <label>Monthly Expenses (₹)</label>
          <input
            type="number"
            min="0"
            step="any"
            value={form.monthly_expenses}
            onChange={(e) =>
              updateField("monthly_expenses", Number(e.target.value))
            }
          />

          <label>Target Market</label>
          <input
            type="text"
            placeholder="e.g. Small businesses"
            value={form.target_market}
            onChange={(e) =>
              updateField("target_market", e.target.value)
            }
          />

          <label>Primary Acquisition Channel</label>
          <select
            value={form.acquisition_channel}
            onChange={(e) =>
              updateField("acquisition_channel", e.target.value)
            }
          >
            <option value="Organic">Organic</option>
            <option value="Social Media">Social Media</option>
            <option value="Paid Ads">Paid Ads</option>
            <option value="Sales">Sales</option>
            <option value="Referrals">Referrals</option>
            <option value="Partnerships">Partnerships</option>
          </select>

          <div className="setup-section">
            <h3>Business Forecast Assumptions</h3>
            <p>
              Optional: enter your own estimates to personalize the
              simulation. Leave a field blank if you do not know it.
            </p>
          </div>

          <label>Expected New Customers per Month</label>
          <input
            type="number"
            min="0"
            step="1"
            placeholder="Leave blank to use the baseline"
            value={form.expected_new_customers}
            onChange={(e) =>
              updateField("expected_new_customers", e.target.value)
            }
          />

          <label>Known Monthly Customer Churn (%)</label>
          <input
            type="number"
            min="0"
            max="100"
            step="0.01"
            placeholder="e.g. 1.2"
            value={form.known_monthly_churn_percent}
            onChange={(e) =>
              updateField("known_monthly_churn_percent", e.target.value)
            }
          />

          <label>Expected Monthly Expense Growth (%)</label>
          <input
            type="number"
            min="0"
            max="100"
            step="0.1"
            placeholder="Leave blank to use the baseline"
            value={form.expected_monthly_expense_growth_percent}
            onChange={(e) =>
              updateField(
                "expected_monthly_expense_growth_percent",
                e.target.value
              )
            }
          />

          {error && <div className="auth-error">{error}</div>}

          <button
            type="submit"
            className="primary-button"
            disabled={loading}
          >
            {loading ? "Creating..." : "Create My Startup →"}
          </button>
        </form>
      </div>
    </div>
  );
}
