import { useState, useEffect } from "react";
import { askBoardroom, continueBoardroom, getBoardroomUsage, getSimulationState, advanceSimulation, submitDecision, getDecisionHistory } from "./services/api";
const AGENTS = [
  {
    name: "Finance",
    role: "Financial Strategy",
    icon: "₹",
    color: "purple",
    description:
      "Tracks revenue, expenses, cash flow, runway and financial decisions.",
  },
  {
    name: "Marketing",
    role: "Growth & Marketing",
    icon: "✦",
    color: "blue",
    description:
      "Analyzes acquisition, positioning, campaigns and customer growth.",
  },
  {
    name: "Sales",
    role: "Sales Strategy",
    icon: "↗",
    color: "orange",
    description:
      "Focuses on customers, conversions, sales pipeline and expansion.",
  },
  {
    name: "CTO",
    role: "Technology",
    icon: "⌘",
    color: "green",
    description:
      "Handles technology, product development and technical decisions.",
  },
  {
    name: "Legal",
    role: "Risk & Compliance",
    icon: "§",
    color: "pink",
    description:
      "Monitors contracts, compliance, legal risks and business protection.",
  },
];
function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
}
function formatNumber(value) {
  return new Intl.NumberFormat("en-IN").format(
    Number(value) || 0
  );
}
function formatPercentage(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}
function formatStage(stage) {
  if (!stage) {
    return "Idea";
  }
  return stage.charAt(0).toUpperCase() + stage.slice(1);
}
function formatDelta(value, type = "number") {
  const numericValue =
    Number(value) || 0;
  const sign =
    numericValue > 0
      ? "+"
      : numericValue < 0
        ? "-"
        : "";
  const absoluteValue =
    Math.abs(numericValue);
  if (type === "currency") {
    return `${sign}${formatCurrency(
      absoluteValue
    )}`;
  }
  if (type === "percentage") {
    return `${sign}${(
      absoluteValue * 100
    ).toFixed(1)}%`;
  }
  return `${sign}${formatNumber(
    absoluteValue
  )}`;
}
export default function FounderVerseDashboard({
  token,
  user,
  company,
}) {
  const [lightMode, setLightMode] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [activePage, setActivePage] = useState("dashboard");
  const [question, setQuestion] = useState("");
  const [consultationMode, setConsultationMode] = useState("individual");
  const [boardroomResponse, setBoardroomResponse] = useState(null);
  const [boardroomLoading, setBoardroomLoading] = useState(false);
  const [collaborationLoading, setCollaborationLoading] = useState(false);
  const [boardroomError, setBoardroomError] = useState("");
  const [simulationState, setSimulationState] = useState(company || null);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState("");
  const [decision, setDecision] = useState("");
  const [explanation, setExplanation] = useState("");
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [decisionError, setDecisionError] = useState("");
  const [decisionSaved, setDecisionSaved] = useState(false);
  const [decisionWarning, setDecisionWarning] = useState("");
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [monthlyUsage, setMonthlyUsage] = useState(null);
  const [usageLoading, setUsageLoading] = useState(false);
  const [upgradeNotice, setUpgradeNotice] = useState(false);
  const trialExhausted = monthlyUsage != null && monthlyUsage.remaining <= 0;
  async function refreshBoardroomUsage() {
    if (!token) return;
    setUsageLoading(true);
    try {
      const usage = await getBoardroomUsage(token);
      setMonthlyUsage(usage);
    } catch (error) {
      console.error("Could not load monthly consultation usage:", error);
    } finally {
      setUsageLoading(false);
    }
  }
  useEffect(() => {
    refreshBoardroomUsage();
  }, [token]);
  useEffect(() => {
    if (activePage === "simulation" && company?._id) {
      loadSimulationState();
    }
  }, [activePage, company?._id]);
  const companyName = company?.company_name || "Your Startup";
  const industry = company?.industry || "SaaS";
  const stage = company?.stage || "idea";
  function logout() {
    localStorage.removeItem("founderverse_token");
    localStorage.removeItem("founderverse_user_id");
    localStorage.removeItem("founderverse_company_id");
    window.location.reload();
  }
  async function handleAskBoardroom(event) {
    event.preventDefault();
    if (!question.trim()) {
      return;
    }
    if (trialExhausted) {
      setUpgradeNotice(true);
      return;
    }
    if (!company?._id) {
      setBoardroomError("Company information is not available.");
      return;
    }
    setBoardroomLoading(true);
    setBoardroomError("");
    setBoardroomResponse(null);
    setActivePage("boardroom");
    setDecision("");
    setExplanation("");
    setDecisionError("");
    setDecisionSaved(false);
    setDecisionWarning("");
    try {
      const response = await askBoardroom(
        company._id,
        question.trim(),
        token,
        consultationMode
      );
      setBoardroomResponse(response);
      if (response.usage) setMonthlyUsage(response.usage);
      else await refreshBoardroomUsage();
    } catch (error) {
      console.error(
        "Boardroom request failed:",
        error
      );
      if (error.code === "TRIAL_LIMIT_REACHED" || error.status === 429) {
        if (error.usage) setMonthlyUsage(error.usage);
        else await refreshBoardroomUsage();
        setUpgradeNotice(true);
        setBoardroomError("");
      } else {
        setBoardroomError(error.message || "Unable to contact the AI Boardroom.");
      }
    } finally {
      setBoardroomLoading(false);
    }
  }
  async function handleContinueBoardroom() {
    if (!company?._id || !boardroomResponse?.question || !boardroomResponse?.responses?.length) {
      setBoardroomError("The original opinions are missing. Please start the consultation again.");
      return;
    }
    setCollaborationLoading(true);
    setBoardroomError("");
    try {
      const result = await continueBoardroom(
        company._id,
        boardroomResponse.question,
        boardroomResponse.responses,
        token
      );
      setBoardroomResponse((previous) => {
        const initialPerformance = previous?.performance || {};
        const continuationPerformance = result.performance || {};
        const initialTotal = Number(initialPerformance.total_backend_ms) || 0;
        const continuationTotal = Number(continuationPerformance.total_backend_ms) || 0;
        return {
          ...previous,
          ...result,
          // Preserve the original opinions and report backend phases separately.
          responses: previous?.responses || result.responses || [],
          mode: "both",
          performance: {
            ...initialPerformance,
            ...continuationPerformance,
            initial_opinions_ms: initialPerformance.initial_opinions_ms,
            initial_backend_total_ms: initialPerformance.total_backend_ms,
            continuation_backend_total_ms: continuationPerformance.total_backend_ms,
            total_backend_ms: Math.round((initialTotal + continuationTotal) * 100) / 100,
            measurement_scope: "Sum of the two backend orchestration phases; excludes HTTP routing/authentication and frontend rendering.",
          },
        };
      });
    } catch (error) {
      console.error("Boardroom continuation failed:", error);
      setBoardroomError(error.message || "Unable to continue the boardroom discussion. Your original opinions are still available; please try again.");
    } finally {
      setCollaborationLoading(false);
    }
  }

  async function handleSubmitDecision() {
    if (!decision) {
      setDecisionError(
        "Please choose Proceed or Hold Off."
      );
      return;
    }
    if (!explanation.trim()) {
      setDecisionError(
        "Please explain why you are making this decision."
      );
      return;
    }
    if (!company?._id) {
      setDecisionError(
        "Company information is not available."
      );
      return;
    }
    setDecisionLoading(true);
    setDecisionError("");
    setDecisionSaved(false);
    setDecisionWarning("");
    try {
      const savedDecision = await submitDecision(
        company._id,
        {
          decision,
          explanation:
            explanation.trim(),
          question:
            boardroomResponse?.question || "",
          boardroom_responses:
            boardroomResponse?.responses || [],
        },
        token
      );
      setDecisionWarning(
        savedDecision.affected_agents_warning || ""
      );
      setDecisionSaved(true);
    } catch (error) {
     console.error(
        "Failed to save decision:",
        error
      );
      setDecisionError(
        error.message ||
        "Unable to save your decision."
      );
    } finally {
      setDecisionLoading(false);
    }
  }
  function renderDashboard() {
    const cash = company?.cash ?? 0;
    const revenue = company?.revenue ?? 0;
    const revenueStatus = company?.monthly_revenue_status ?? "unknown";
    const expenses = company?.expenses ?? 0;
    const profit = company?.profit ?? 0;
    const customers = company?.customers ?? 0;
    const churnRate = company?.churn_rate ?? 0;
    const runway = company?.runway_months ?? 0;
    const valuation = company?.valuation ?? 0;
    const currentMonth = company?.current_month ?? 1;
    return (
      <>
        {/* WELCOME */}
        <div className="welcome">
          <div>
            <span className="eyebrow">
              WELCOME TO FOUNDERVERSE
            </span>
            <h2>
              Build your vision.
              <br />
              Make your next move.
            </h2>
            <p className="welcome-text">
              Your {industry} startup is ready.
              Consult your AI boardroom and see how
              your decisions unfold through simulation.
            </p>
          </div>
        </div>
        {/* COMPANY */}
        <div className="section-heading">
          <div>
            <h3>Your startup</h3>
            <p>
              {companyName} · {industry}
            </p>
          </div>
          <div className="status-badge">
            <span className="status-dot" />
            MongoDB connected
          </div>
        </div>
        {/* BASIC COMPANY INFO */}
        <div className="metrics-grid">
          <div className="metric-card">
            <span>Stage</span>
            <strong>
              {formatStage(stage)}
            </strong>
          </div>
          <div className="metric-card">
            <span>Industry</span>
            <strong>
              {industry}
            </strong>
          </div>
          <div className="metric-card">
            <span>AI Agents</span>
            <strong>
              5
            </strong>
          </div>
          <div className="metric-card">
            <span>Simulation</span>
            <strong>
              Month {currentMonth}
            </strong>
          </div>
        </div>
        {/* CURRENT BUSINESS STATE */}
        <div className="section-heading">
          <div>
            <h3>Current business state</h3>
            <p>
              Live metrics from your FounderVerse company state.
            </p>
          </div>
        </div>
        <div className="metrics-grid">
          {/* CASH */}
          <div className="metric-card">
            <span>Cash</span>
            <strong>
              {formatCurrency(cash)}
            </strong>
          </div>
          {/* MRR */}
          <div className="metric-card">
            <span>MRR</span>
            <strong>
              {revenueStatus === "known"
  ? formatCurrency(revenue)
  : "Unknown"}
            </strong>
          </div>
          {/* EXPENSES */}
          <div className="metric-card">
            <span>Monthly Expenses</span>
            <strong>
              {formatCurrency(expenses)}
            </strong>
          </div>
          {/* PROFIT */}
          <div className="metric-card">
            <span>Monthly Profit</span>
            <strong
              className={
                profit < 0
                  ? "negative-value"
                  : "positive-value"
              }
            >
              {formatCurrency(profit)}
            </strong>
          </div>
          {/* CUSTOMERS */}
          <div className="metric-card">
            <span>Customers</span>
            <strong>
              {formatNumber(customers)}
            </strong>
          </div>
          {/* CHURN */}
          <div className="metric-card">
            <span>Churn Rate</span>
            <strong>
              {formatPercentage(churnRate)}
            </strong>
          </div>
          {/* RUNWAY */}
          <div className="metric-card">
            <span>Runway</span>
            <strong>
              {runway > 0
                ? `${Number(runway).toFixed(1)} months`
                : "Not burning"}
            </strong>
          </div>
          {/* VALUATION */}
          <div className="metric-card">
            <span>Valuation</span>
            <strong>
              {valuation > 0
                ? formatCurrency(valuation)
                : "Not calculated"}
            </strong>
          </div>
        </div>
        {/* BOARDROOM */}
        <div className="section-heading">
          <div>
            <h3>AI Boardroom</h3>
            <p>
              Ask a business question and get perspectives
              from your specialist AI agents.
            </p>
          </div>
          <button
            className="secondary-button"
            onClick={() =>
              setActivePage("boardroom")
            }
          >
            Meet the agents →
          </button>
        </div>
        <form
          className="boardroom-question"
          onSubmit={handleAskBoardroom}
        >
          <div>
            <span className="eyebrow">
              ASK YOUR BOARDROOM
            </span>
            <textarea
              value={question}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
              placeholder="e.g. Should we increase our marketing budget next month?"
              rows={3}
            />
          </div>
          <button
            type="submit"
            className="primary-button"
            disabled={boardroomLoading}
          >
            {boardroomLoading
              ? "Consulting..."
              : "Ask the Boardroom →"}
          </button>
        </form>
        {/* AGENTS */}
        <div className="agent-grid compact">
          {AGENTS.map((agent) => (
            <AgentCard
              key={agent.name}
              agent={agent}
            />
          ))}
        </div>
      </>
    );
  }
  function renderBoardroom() {
    return (
      <div className="page-section">
        {/* PAGE HEADER */}
        <div className="page-heading">
          <span className="eyebrow">
            02 / STRATEGY
          </span>
          <h2>
            AI Boardroom
          </h2>
          <p>
            Five specialist AI agents analyze your startup
            from different business perspectives.
          </p>
        </div>
        {/* MONTHLY FREE-TRIAL USAGE */}
        <div className="coming-card" style={{ marginBottom: "1rem", padding: "1rem 1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
            <div>
              <span className="eyebrow">FREE MONTHLY TRIAL</span>
              <h3 style={{ margin: "0.35rem 0" }}>
                {usageLoading && !monthlyUsage ? "Loading your allowance…" : `${monthlyUsage?.remaining ?? 15} of ${monthlyUsage?.limit ?? 15} questions remaining`}
              </h3>
              <p style={{ margin: 0 }}>All consultation modes share this monthly allowance. Continuing a Both Experiences session does not use another question.</p>
            </div>
            <button type="button" className="secondary-button" onClick={() => setUpgradeNotice(true)}>Upgrade to Premium</button>
          </div>
          <div style={{ height: "7px", background: "rgba(150,140,220,.18)", borderRadius: "999px", marginTop: "0.9rem", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, ((monthlyUsage?.used ?? 0) / (monthlyUsage?.limit || 15)) * 100))}%`, background: "linear-gradient(90deg, #8b5cf6, #6d4aff)", transition: "width .25s ease" }} />
          </div>
        </div>

        {trialExhausted ? (
          <div className="coming-card" style={{ padding: "2rem", textAlign: "center", marginBottom: "1.5rem" }}>
            <div className="large-icon">✦</div>
            <h3>You've used all 15 free questions this month.</h3>
            <p>Your monthly allowance will reset at the start of next month. You can still review your previous opinions and decisions.</p>
            <button type="button" className="primary-button" onClick={() => setUpgradeNotice(true)}>Upgrade to Premium →</button>
            {upgradeNotice && <p role="status" style={{ marginTop: "1rem" }}>Premium access is coming soon! No payment is required right now.</p>}
          </div>
        ) : (
        /* QUESTION FORM */
        <form
          className="boardroom-question"
          onSubmit={handleAskBoardroom}
        >
          <div>
            <span className="eyebrow">
              WHAT DECISION ARE YOU FACING?
            </span>
            <textarea
              value={question}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
              placeholder="Ask your boardroom a business question..."
              rows={4}
            />
            <div className="consultation-mode-picker" role="radiogroup" aria-label="Consultation mode">
              <button type="button" role="radio" aria-checked={consultationMode === "individual"}
                className={`consultation-mode-card ${consultationMode === "individual" ? "selected" : ""}`}
                onClick={() => setConsultationMode("individual")}>
                <span className="mode-card-icon">◉</span>
                <span className="mode-card-copy"><strong>Individual opinions</strong><small>5 independent perspectives · lower API usage</small></span>
                <span className="mode-card-check">{consultationMode === "individual" ? "✓" : ""}</span>
              </button>
              <button type="button" role="radio" aria-checked={consultationMode === "collaborative"}
                className={`consultation-mode-card ${consultationMode === "collaborative" ? "selected" : ""}`}
                onClick={() => setConsultationMode("collaborative")}>
                <span className="mode-card-icon">✦</span>
                <span className="mode-card-copy"><strong>Collaborative boardroom</strong><small>Opinions, debate, and final synthesis</small></span>
                <span className="mode-card-check">{consultationMode === "collaborative" ? "✓" : ""}</span>
              </button>
              <button type="button" role="radio" aria-checked={consultationMode === "both"}
                className={`consultation-mode-card ${consultationMode === "both" ? "selected" : ""}`}
                onClick={() => setConsultationMode("both")}>
                <span className="mode-card-icon">◈</span>
                <span className="mode-card-copy"><strong>Both experiences</strong><small>Independent opinions plus collaboration</small></span>
                <span className="mode-card-check">{consultationMode === "both" ? "✓" : ""}</span>
              </button>
            </div>
          </div>
          <button
            type="submit"
            className="primary-button"
            disabled={boardroomLoading}
          >
            {boardroomLoading
              ? "Consulting..."
              : consultationMode === "individual"
                ? "Get Individual Opinions →"
                : consultationMode === "collaborative"
                  ? "Start Collaborative Boardroom →"
                  : "Get Both Experiences →"}
          </button>
        </form>
        )}
        {upgradeNotice && !trialExhausted && (
          <div className="coming-card" role="status" style={{ marginBottom: "1rem", padding: "1rem" }}>
            <h3>Premium access is coming soon! 💜</h3>
            <p>No payment is needed right now. Your free monthly allowance remains available.</p>
            <button type="button" className="secondary-button" onClick={() => setUpgradeNotice(false)}>Got it</button>
          </div>
        )}
        {/* LOADING */}
        {boardroomLoading && (
          <div className="coming-card boardroom-placeholder">
            <div className="large-icon">
              ✦
            </div>
            <h3>
              Consulting the Boardroom...
            </h3>
            <p>
              Your specialist AI agents are analyzing
              the decision from their respective perspectives.
            </p>
          </div>
        )}
        {/* ERROR */}
        {boardroomError && (
          <div className="coming-card boardroom-placeholder">
            <div className="large-icon">
              !
            </div>
            <h3>
              Boardroom unavailable
            </h3>
            <p>
              {boardroomError}
            </p>
          </div>
        )}
        {/* BOARDROOM CONVERSATION */}
        {boardroomResponse && !boardroomLoading && (
          <div className="boardroom-conversation">
            {/* FOUNDER QUESTION */}
            <div className="founder-message">
              <div className="conversation-label">
                <span className="eyebrow">
                  FOUNDER
                </span>
              </div>
              <div className="founder-question-card">
                <p>
                  {boardroomResponse.question}
                </p>
              </div>
            </div>
            {/* AI AGENT RESPONSES */}
            <div className="agent-conversation">
              {boardroomResponse.responses?.map(
                (agentResponse, index) => {
                  const agentInfo = AGENTS.find(
                    (agent) =>
                      agent.name.toLowerCase() ===
                      agentResponse.agent_name
                        ?.replace(" Agent", "")
                        .toLowerCase()
                  );
                  const response =
                    agentResponse.response || {};
                  return (
                    <div
                      className="agent-message"
                      key={
                        agentResponse.agent_name ||
                        index
                      }
                    >
                      {/* AGENT HEADER */}
                      <div className="agent-message-header">
                        <div
                          className={`agent-icon ${agentInfo?.color || "purple"
                            }`}
                        >
                          {agentInfo?.icon || "✦"}
                        </div>
                        <div>
                          <span className="eyebrow">
                            AI SPECIALIST
                          </span>
                          <h3>
                            {agentResponse.agent_name}
                          </h3>
                          <p className="agent-role">
                            {agentInfo?.role ||
                              "Executive Advisor"}
                          </p>
                        </div>
                      </div>
                      {/* RECOMMENDATION */}
                      <div className="agent-response-section">
                        <span className="response-label">
                          RECOMMENDATION
                        </span>
                        <p>
                          {response.summary}
                        </p>
                      </div>
                      {/* REASONING */}
                      <div className="agent-response-section">
                        <span className="response-label">
                          REASONING
                        </span>
                        <p>
                          {response.reasoning}
                        </p>
                      </div>
                      {/* KEY FACTORS */}
                      {response.key_factors?.length > 0 && (
                        <div className="agent-response-section">
                          <span className="response-label">
                            KEY FACTORS
                          </span>

                          <ul className="key-factors">
                            {response.key_factors.map(
                              (factor, factorIndex) => (
                                <li key={factorIndex}>
                                  {factor}
                                </li>
                              )
                            )}
                          </ul>
                        </div>
                      )}
                      {/* RISK */}
                      <div className="agent-response-section">
                        <span className="response-label">
                          RISK
                        </span>
                        <p>
                          {response.risk}
                        </p>
                      </div>
                      {/* SUGGESTED ACTION */}
                      <div className="agent-response-section">
                        <span className="response-label">
                          SUGGESTED ACTION
                        </span>

                        <p>
                          {response.action}
                        </p>
                      </div>

                    </div>
                  );
                }
              )}
                          </div>

            {/* Both Experiences: continue only when the founder chooses to. */}
            {boardroomResponse.mode === "both" &&
              !boardroomResponse.discussions?.length &&
              !boardroomResponse.synthesis && (
                <div className="coming-card" style={{ marginTop: "1rem", padding: "1.25rem" }}>
                  <h3>Ready to bring these opinions into the boardroom?</h3>
                  <p>The five independent opinions are ready. Continue to let the agents discuss trade-offs and prepare a final synthesis. Your existing opinions will be reused.</p>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={handleContinueBoardroom}
                    disabled={collaborationLoading || boardroomLoading}
                  >
                    {collaborationLoading ? "Starting boardroom discussion…" : "Bring These Opinions to the Boardroom →"}
                  </button>
                </div>
              )}

            {collaborationLoading && (
              <div className="coming-card" style={{ marginTop: "1rem" }}>
                <h3>The boardroom is discussing…</h3>
                <p>Keeping your original opinions while the agents review trade-offs and prepare the synthesis.</p>
              </div>
            )}

            {/* Collaboration stages only exist for collaborative/both mode. */}
            {(boardroomResponse.mode || consultationMode) !== "individual" && (
              <>
            {/* COLLABORATIVE BOARDROOM DISCUSSION */}
            {boardroomResponse.discussions?.length > 0 && (
              <div className="boardroom-discussion">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">
                      EXECUTIVE DISCUSSION
                    </span>
                    <h3>
                      The Boardroom Exchange
                    </h3>
                    <p>
                      Each executive reviews the other perspectives,
                      identifies agreements and disagreements, and
                      reconsiders their original recommendation.
                    </p>
                  </div>
                </div>

                <div className="discussion-agents">
                  {boardroomResponse.discussions.map(
                    (item, index) => (
                      <div
                        className="agent-message discussion-card"
                        key={`${item.agent_name}-${index}`}
                      >
                        {/* DISCUSSION HEADER */}
                        <div className="agent-message-header">
                          <div className="agent-icon purple">
                            ✦
                          </div>

                          <div>
                            <span className="eyebrow">
                              EXECUTIVE DISCUSSION
                            </span>
                            <h3>{item.agent_name}</h3>
                          </div>
                        </div>

                        {item.error ? (
                          <div className="agent-response-section">
                            <p>{item.error}</p>
                          </div>
                        ) : (
                          <>
                            {/* AGREEMENTS */}
                            <div className="agent-response-section">
                              <span className="response-label">
                                AGREEMENTS
                              </span>

                              {item.discussion?.agreements?.length > 0 ? (
                                <ul className="key-factors">
                                  {item.discussion.agreements.map(
                                    (point, pointIndex) => (
                                      <li key={pointIndex}>
                                        {point}
                                      </li>
                                    )
                                  )}
                                </ul>
                              ) : (
                                <p>
                                  No specific agreements identified.
                                </p>
                              )}
                            </div>

                            {/* DISAGREEMENTS */}
                            <div className="agent-response-section">
                              <span className="response-label">
                                DISAGREEMENTS
                              </span>

                              {item.discussion?.disagreements?.length > 0 ? (
                                <ul className="key-factors">
                                  {item.discussion.disagreements.map(
                                    (point, pointIndex) => (
                                      <li key={pointIndex}>
                                        {point}
                                      </li>
                                    )
                                  )}
                                </ul>
                              ) : (
                                <p>
                                  No specific disagreements identified.
                                </p>
                              )}
                            </div>

                            {/* ADDITIONAL INSIGHT */}
                            <div className="agent-response-section">
                              <span className="response-label">
                                ADDITIONAL INSIGHT
                              </span>

                              <p>
                                {item.discussion?.additional_insight ||
                                  "No additional insight available."}
                              </p>
                            </div>

                            {/* REVISED POSITION */}
                            <div className="agent-response-section">
                              <span className="response-label">
                                REVISED POSITION
                              </span>

                              <p>
                                {item.discussion?.revised_position ||
                                  "No revised position available."}
                              </p>
                            </div>
                          </>
                        )}
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {/* FINAL BOARDROOM SYNTHESIS */}
            {boardroomResponse.synthesis && (
              <div className="boardroom-synthesis">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">
                      FINAL ASSESSMENT
                    </span>
                    <h3>
                      Boardroom Recommendation
                    </h3>
                    <p>
                      A consolidated view of the executives'
                      recommendations, discussions, and remaining
                      uncertainties.
                    </p>
                  </div>
                </div>

                {boardroomResponse.synthesis.status === "unavailable" ? (
                  <div className="coming-card boardroom-placeholder">
                    <h3>
                      Final synthesis unavailable
                    </h3>
                    <p>
                      {boardroomResponse.synthesis.error ||
                        "The final synthesis could not be generated."}
                    </p>
                    <p>
                      You can still review the individual agent
                      recommendations and available discussions above.
                    </p>
                  </div>
                ) : (
                  <>
                    {/* EXECUTIVE SUMMARY */}
                    <div className="agent-message synthesis-card">
                      <div className="agent-response-section">
                        <span className="response-label">
                          EXECUTIVE SUMMARY
                        </span>

                        <p>
                          {boardroomResponse.synthesis.executive_summary}
                        </p>
                      </div>

                      <div className="agent-response-section">
                        <span className="response-label">
                          RECOMMENDED ACTION
                        </span>

                        <p>
                          {boardroomResponse.synthesis.recommended_action}
                        </p>
                      </div>
                    </div>

                    {/* AREAS OF AGREEMENT */}
                    <div className="agent-message synthesis-card">
                      <div className="agent-response-section">
                        <span className="response-label">
                          AREAS OF AGREEMENT
                        </span>

                        {boardroomResponse.synthesis.agreements?.length > 0 ? (
                          <ul className="key-factors">
                            {boardroomResponse.synthesis.agreements.map(
                              (point, index) => (
                                <li key={index}>{point}</li>
                              )
                            )}
                          </ul>
                        ) : (
                          <p>
                            No clear areas of agreement were identified.
                          </p>
                        )}
                      </div>
                    </div>

                    {/* UNRESOLVED DISAGREEMENTS */}
                    <div className="agent-message synthesis-card">
                      <div className="agent-response-section">
                        <span className="response-label">
                          UNRESOLVED DISAGREEMENTS
                        </span>

                        {boardroomResponse.synthesis.disagreements?.length > 0 ? (
                          <ul className="key-factors">
                            {boardroomResponse.synthesis.disagreements.map(
                              (point, index) => (
                                <li key={index}>{point}</li>
                              )
                            )}
                          </ul>
                        ) : (
                          <p>
                            No material disagreements were identified
                            in the final synthesis.
                          </p>
                        )}
                      </div>
                    </div>

                    {/* KEY RISKS */}
                    <div className="agent-message synthesis-card">
                      <div className="agent-response-section">
                        <span className="response-label">
                          KEY RISKS
                        </span>

                        {boardroomResponse.synthesis.key_risks?.length > 0 ? (
                          <ul className="key-factors">
                            {boardroomResponse.synthesis.key_risks.map(
                              (risk, index) => (
                                <li key={index}>{risk}</li>
                              )
                            )}
                          </ul>
                        ) : (
                          <p>
                            No key risks were provided in the synthesis.
                          </p>
                        )}
                      </div>
                    </div>

                    {/* NEXT STEPS */}
                    <div className="agent-message synthesis-card">
                      <div className="agent-response-section">
                        <span className="response-label">
                          NEXT STEPS
                        </span>

                        {boardroomResponse.synthesis.next_steps?.length > 0 ? (
                          <ol className="key-factors">
                            {boardroomResponse.synthesis.next_steps.map(
                              (step, index) => (
                                <li key={index}>{step}</li>
                              )
                            )}
                          </ol>
                        ) : (
                          <p>
                            No next steps were provided.
                          </p>
                        )}
                      </div>
                    </div>

                    {/* SUCCESS METRICS */}
                    <div className="agent-message synthesis-card">
                      <div className="agent-response-section">
                        <span className="response-label">
                          SUCCESS METRICS
                        </span>

                        {boardroomResponse.synthesis.success_metrics?.length > 0 ? (
                          <ul className="key-factors">
                            {boardroomResponse.synthesis.success_metrics.map(
                              (metric, index) => (
                                <li key={index}>{metric}</li>
                              )
                            )}
                          </ul>
                        ) : (
                          <p>
                            No success metrics were provided.
                          </p>
                        )}
                      </div>
                    </div>

                    {/* UNRESOLVED ASSUMPTIONS */}
                    <div className="agent-message synthesis-card">
                      <div className="agent-response-section">
                        <span className="response-label">
                          UNRESOLVED ASSUMPTIONS
                        </span>

                        {boardroomResponse.synthesis.unresolved_assumptions?.length > 0 ? (
                          <ul className="key-factors">
                            {boardroomResponse.synthesis.unresolved_assumptions.map(
                              (assumption, index) => (
                                <li key={index}>{assumption}</li>
                              )
                            )}
                          </ul>
                        ) : (
                          <p>
                            No unresolved assumptions were provided.
                          </p>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
              </>
            )}

            {/* FOUNDER DECISION */}
            <div className="decision-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">
                    FOUNDER DECISION
                  </span>
                  <h3>
                    What do you want to do?
                  </h3>
                  <p>
                    The board has given you its perspectives.
                    The decision is yours.
                  </p>
                </div>
              </div>
              {/* PROCEED / HOLD OFF */}
              <div className="decision-options">
                <button
                  type="button"
                  className={`decision-button proceed ${decision === "proceed"
                      ? "selected"
                      : ""
                    }`}
                  onClick={() => {
                    setDecision("proceed");
                    setDecisionError("");
                    setDecisionSaved(false);
                    setDecisionWarning("");
                  }}
                >
                  <span className="decision-icon">
                    ✓
                  </span>
                  <span>
                    <strong>
                      Proceed
                    </strong>
                    <small>
                      Move forward with the decision.
                    </small>
                  </span>
                </button>
                <button
                  type="button"
                  className={`decision-button hold ${decision === "hold_off"
                      ? "selected"
                      : ""
                    }`}
                  onClick={() => {
                    setDecision("hold_off");
                    setDecisionError("");
                    setDecisionSaved(false);
                    setDecisionWarning("");
                  }}
                >
                  <span className="decision-icon">
                    ⏸
                  </span>
                  <span>
                    <strong>
                      Hold Off
                    </strong>
                    <small>
                      Wait before taking this action.
                    </small>
                  </span>
                </button>
              </div>
              {/* EXPLANATION */}
              <div className="decision-explanation">
                <label>
                  Why are you making this decision?
                </label>
                <textarea
                  value={explanation}
                  onChange={(event) =>
                    setExplanation(
                      event.target.value
                    )
                  }
                  placeholder="Explain your reasoning. What influenced your decision?"
                  rows={6}
                />
              </div>
              {/* ERROR */}
              {decisionError && (
                <div className="auth-error">
                  {decisionError}
                </div>
              )}
              {/* SUCCESS / SUBMIT */}
              {decisionSaved ? (
                <>
                  <div className="decision-success">
                    ✓ Decision recorded successfully.
                  </div>
                  {decisionWarning && (
                    <div className="decision-warning">
                      {decisionWarning}
                    </div>
                  )}
                </>
              ) : (
                <button
                  type="button"
                  className="primary-button"
                  onClick={handleSubmitDecision}
                  disabled={decisionLoading}
                >
                  {decisionLoading
                    ? "Recording Decision..."
                    : "Record My Decision →"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }
  function renderSimulation() {
    const state =
      simulationState || company || {};
    const previous =
      state.previous_state || null;
    const timeline =
      state.timeline || [];
    const cash =
      Number(state.cash) || 0;
    const revenue =
      Number(state.revenue) || 0;
    const revenueStatus =
      state.monthly_revenue_status ?? "unknown";
    const expenses =
      Number(state.expenses) || 0;
    const profit =
      Number(state.profit) || 0;
    const customers =
      Number(state.customers) || 0;
    const churnRate =
      Number(state.churn_rate) || 0;
    const runway =
      Number(state.runway_months) || 0;
    const growthRate =
      Number(state.monthly_growth_rate) || 0;
    const currentMonth =
      Number(state.current_month) || 1;
    const customerDelta =
      previous
        ? customers - Number(previous.customers || 0)
        : 0;
    const revenueDelta =
      previous
        ? revenue - Number(previous.revenue || 0)
        : 0;
    const expenseDelta =
      previous
        ? expenses - Number(previous.expenses || 0)
        : 0;
    const profitDelta =
      previous
        ? profit - Number(previous.profit || 0)
        : 0;
    const cashDelta =
      previous
        ? cash - Number(previous.cash || 0)
        : 0;
    return (
      <div className="page-section">
        {/* PAGE HEADER */}
        <div className="page-heading">
          <span className="eyebrow">
            03 / PROGRESS
          </span>
          <h2>
            Startup Simulation
          </h2>
          <p>
            Advance through time and observe how
            {companyName} evolves.
          </p>
        </div>
        {/* CURRENT MONTH */}
        <div className="simulation-header-card">
          <div>
            <span className="eyebrow">
              CURRENT SIMULATION
            </span>
            <h3>
              Month {currentMonth}
            </h3>
            <p>
              Your startup's current business state.
            </p>
          </div>
          <button
            className="primary-button"
            onClick={handleAdvanceMonth}
            disabled={simulationLoading}
          >
            {simulationLoading
              ? "Simulating..."
              : "Advance One Month →"}
          </button>
        </div>
        {/* CURRENT STATE */}
        <div className="section-heading">
          <div>
            <h3>
              Business state
            </h3>
            <p>
              Your company's current simulation metrics.
            </p>
          </div>
        </div>
        <div className="metrics-grid">
          <div className="metric-card">
            <span>
              CASH
            </span>
            <strong>
              {formatCurrency(cash)}
            </strong>
          </div>
          <div className="metric-card">
            <span>
              MRR
            </span>
            <strong>
              {revenueStatus === "known"
  ? formatCurrency(revenue)
  : "Unknown"}
            </strong>
          </div>
          <div className="metric-card">
            <span>
              EXPENSES
            </span>
            <strong>
              {formatCurrency(expenses)}
            </strong>
          </div>
          <div className="metric-card">
            <span>
              PROFIT
            </span>
            <strong
              className={
                profit < 0
                  ? "negative-value"
                  : "positive-value"
              }
            >
              {formatCurrency(profit)}
            </strong>
          </div>
          <div className="metric-card">
            <span>
              CUSTOMERS
            </span>
            <strong>
              {formatNumber(customers)}
            </strong>
          </div>
          <div className="metric-card">
            <span>
              CHURN RATE
            </span>
            <strong>
              {formatPercentage(churnRate)}
            </strong>
          </div>
          <div className="metric-card">
            <span>
              RUNWAY
            </span>
            <strong>
              {runway > 0
                ? `${runway.toFixed(1)} months`
                : "Not burning"}
            </strong>
          </div>
          <div className="metric-card">
            <span>
              GROWTH RATE
            </span>
            <strong>
              {formatPercentage(growthRate)}
            </strong>
          </div>
        </div>
        {/* MONTH OVER MONTH */}
        <div className="section-heading">
          <div>
            <h3>
              Month-over-month change
            </h3>
            <p>
              How your startup changed since the previous month.
            </p>
          </div>
        </div>
        {!previous ? (
          <div className="coming-card">
            <div className="large-icon">
              ◷
            </div>
            <h3>
              First simulation month
            </h3>
            <p>
              Advance the simulation to generate your
              first month-over-month comparison.
            </p>
          </div>
        ) : (
          <div className="metrics-grid">
            <div className="metric-card">
              <span>
                CUSTOMER CHANGE
              </span>
              <strong
                className={
                  customerDelta >= 0
                    ? "positive-value"
                    : "negative-value"
                }
              >
                {formatDelta(customerDelta)}
              </strong>
              <small>
                vs Month {currentMonth - 1}
              </small>
            </div>
            <div className="metric-card">
              <span>
                MRR CHANGE
              </span>
              <strong
                className={
                  revenueDelta >= 0
                    ? "positive-value"
                    : "negative-value"
                }
              >
                {revenueStatus === "known" && previous &&
 previous.monthly_revenue_status !== "unknown"
  ? formatDelta(revenueDelta, "currency")
  : "Unavailable"}
              </strong>
              <small>
                vs Month {currentMonth - 1}
              </small>
            </div>
            <div className="metric-card">
              <span>
                EXPENSE CHANGE
              </span>
              <strong
                className={
                  expenseDelta <= 0
                    ? "positive-value"
                    : "negative-value"
                }
              >
                {formatDelta(
                  expenseDelta,
                  "currenccy"
                )}
              </strong>
              <small>
                vs Month {currentMonth - 1}
              </small>
            </div>
            <div className="metric-card">
              <span>
                PROFIT CHANGE
              </span>
              <strong
                className={
                  profitDelta >= 0
                    ? "positive-value"
                    : "negative-value"
                }
              >
                {formatDelta(
                  profitDelta,
                  "currency"
                )}
              </strong>
              <small>
                vs Month {currentMonth - 1}
              </small>
            </div>
          </div>
        )}
        {/* TIMELINE */}
        <div className="section-heading">
          <div>
            <h3>
              Company timeline
            </h3>
            <p>
              Your startup's journey through the simulation.
            </p>
          </div>
        </div>
        <div className="simulation-timeline">
          {timeline.map(
            (snapshot, index) => {
              const isCurrent =
                snapshot.month === currentMonth;
              return (
                <div
                  className={`timeline-item ${isCurrent
                      ? "current"
                      : ""
                    }`}
                  key={snapshot._id || snapshot.month}
                >
                  <div className="timeline-marker">
                    <span />
                  </div>
                  <div className="timeline-content">
                    <div className="timeline-header">
                      <div>
                        <span className="eyebrow">
                          {isCurrent
                            ? "CURRENT"
                            : "SIMULATION"}
                        </span>
                        <h3>
                          Month {snapshot.month}
                        </h3>
                      </div>
                    </div>
                    <div className="timeline-metrics">
                      <div>
                        <span>
                          Customers
                        </span>
                        <strong>
                          {formatNumber(
                            snapshot.customers
                          )}
                        </strong>
                      </div>
                      <div>
                        <span>
                          MRR
                        </span>
                        <strong>
                          {(snapshot.monthly_revenue_status ?? "unknown") === "known"
  ? formatCurrency(snapshot.revenue)
  : "Unknown"}
                        </strong>
                      </div>
                      <div>
                        <span>
                          Profit
                        </span>
                        <strong>
                          {formatCurrency(
                            snapshot.profit
                          )}
                        </strong>
                      </div>
                      <div>
                        <span>
                          Cash
                        </span>
                        <strong>
                          {formatCurrency(
                            snapshot.cash
                          )}
                        </strong>
                      </div>
                    </div>
                  </div>
                </div>
              );
            }
          )}
        </div>
        {/* SIMULATION EXPLANATION */}
        <div className="section-heading">
          <div>
            <h3>
              How the simulation works
            </h3>
            <p>
              FounderVerse advances the startup one
              virtual month at a time.
            </p>
          </div>
        </div>
        <div className="coming-card">
          <div className="large-icon">
            ◷
          </div>
          <h3>
            Observe → Simulate → Evolve
          </h3>
          <p>
            Each month, customer growth, churn,
            revenue, expenses, profit and cash are
            recalculated from the current company state.
          </p>
          <p>
            Later, founder decisions from the AI
            Boardroom will influence these transitions.
          </p>
        </div>
        {/* ADVANCE */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginTop: "24px",
          }}
        >
          <button
            className="primary-button"
            onClick={handleAdvanceMonth}
            disabled={simulationLoading}
          >
            {simulationLoading
              ? "Running Simulation..."
              : `Advance from Month ${currentMonth} →`}
          </button>
        </div>
      </div>
    );
  }
  async function handleAdvanceMonth() {
    if (!company?._id) {
      setSimulationError(
        "Company information is not available."
      );
      return;
    }
    setSimulationLoading(true);
    setSimulationError("");
    try {
      await advanceSimulation(
        company._id,
        token
      );
      await loadSimulationState();
    } catch (error) {
      console.error(
        "Failed to advance simulation:",
        error
      );
      setSimulationError(
        error.message ||
        "Unable to advance simulation."
      );
    } finally {
      setSimulationLoading(false);
    }
  }
  async function loadSimulationState() {
    if (!company?._id) {
      return;
    }
    setSimulationLoading(true);
    setSimulationError("");
    try {
      const state = await getSimulationState(
        company._id,
        token
      );
      setSimulationState(state);
    } catch (error) {
      console.error(
        "Failed to load simulation state:",
        error
      );
      setSimulationError(
        error.message ||
        "Unable to load simulation state."
      );
    } finally {
      setSimulationLoading(false);
    }
  }
  async function loadDecisionHistory() {
    if (!company?._id) {
      return;
    }
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const data = await getDecisionHistory(
        company._id,
        token
      );
      setHistory(data.decisions || []);
    } catch (error) {
      console.error(
        "Failed to load decision history:",
        error
      );
      setHistoryError(
        error.message ||
        "Unable to load decision history."
      );
    } finally {
      setHistoryLoading(false);
    }
  }
  function formatHistoryDate(value) {
    if (!value) {
      return "Unknown time";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "Unknown time";
    }
    return date.toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }
  function renderHistory() {
    return (
      <div className="page-section">
        <div className="page-heading">
          <span className="eyebrow">04 / MEMORY</span>
          <h2>Decision History</h2>
          <p>
            Review your previous boardroom conversations, agent
            perspectives and founder decisions.
          </p>
        </div>
        {historyLoading && (
          <div className="coming-card boardroom-placeholder">
            <div className="large-icon">◷</div>
            <h3>Loading decision history...</h3>
            <p>Retrieving your previous FounderVerse decisions.</p>
          </div>
        )}
        {!historyLoading && historyError && (
          <div className="coming-card boardroom-placeholder">
            <div className="large-icon">!</div>
            <h3>History unavailable</h3>
            <p>{historyError}</p>
          </div>
        )}
        {!historyLoading && !historyError && history.length === 0 && (
          <div className="coming-card">
            <div className="large-icon">◫</div>
            <h3>No decisions yet</h3>
            <p>
              Your boardroom conversations and founder decisions
              will appear here after you record your first decision.
            </p>
          </div>
        )}
        {!historyLoading && !historyError && history.length > 0 && (
          <div className="history-list">
            {history.map((item, index) => (
              <DecisionHistoryCard
                key={item._id || index}
                item={item}
                index={index}
                formatHistoryDate={formatHistoryDate}
              />
            ))}
          </div>
        )}
      </div>
    );
  }
  function DecisionHistoryCard({ item, index, formatHistoryDate }) {
    const [expanded, setExpanded] = useState(false);
    const responses = Array.isArray(item.boardroom_responses)
      ? item.boardroom_responses
      : [];
    const isProceed = item.decision === "proceed";
    function displayValue(value) {
      if (Array.isArray(value)) {
        return value.length ? value.join(", ") : "None provided.";
      }
      if (value === null || value === undefined || value === "") {
        return "Not provided.";
      }
      return String(value);
    }
    return (
      <article className="history-card" key={item._id || index}>
        {/* Always-visible decision summary */}
        <div className="history-card-header">
          <div className="history-card-title">
            <span className="eyebrow">
              DECISION {String(index + 1).padStart(2, "0")}
            </span>
            <h3>{item.question || "Boardroom discussion"}</h3>
            <small>
              {formatHistoryDate(item.created_at)}
              {" · "}
              {responses.length} agent response
              {responses.length === 1 ? "" : "s"}
            </small>
          </div>
          <span
            className={`history-decision ${isProceed ? "proceed" : "hold"
              }`}
          >
            {isProceed ? "✓ Proceed" : "Ⅱ Hold Off"}
          </span>
        </div>
        <div className="history-founder-decision">
          <span className="history-field-label">
            FOUNDER'S EXPLANATION
          </span>
          <p>
            {item.explanation || "No explanation was recorded."}
          </p>
        </div>
        {/* Expand/collapse the full boardroom conversation */}
        <button
          type="button"
          className="history-expand-button"
          onClick={() => setExpanded((previous) => !previous)}
          aria-expanded={expanded}
        >
          <span>
            {expanded ? "Hide conversation" : "View full conversation"}
          </span>
          <span
            className={`history-expand-icon ${expanded ? "expanded" : ""
              }`}
            aria-hidden="true"
          >
            ⌄
          </span>
        </button>
        {expanded && (
          <div className="history-conversation">
            <div className="history-conversation-heading">
              <span className="eyebrow">AI BOARDROOM</span>
              <h4>Executive perspectives</h4>
              <p>
                The responses recorded when this decision was made.
              </p>
            </div>
            {responses.length === 0 ? (
              <div className="history-empty-conversation">
                No agent responses were saved with this decision.
                This can happen with older decisions that were recorded
                before conversation history was added.
              </div>
            ) : (
              responses.map((agentItem, agentIndex) => {
                const response = agentItem.response || agentItem;
                const agentName =
                  agentItem.agent_name ||
                  agentItem.agentName ||
                  `Agent ${agentIndex + 1}`;
                return (
                  <section
                    className="history-agent"
                    key={`${item._id || index}-${agentName}-${agentIndex}`}
                  >
                    <div className="history-agent-heading">
                      <div className="history-agent-avatar">
                        {agentName.charAt(0)}
                      </div>
                      <div>
                        <h4>{agentName}</h4>
                        <small>Executive response</small>
                      </div>
                    </div>
                    <div className="history-agent-field">
                      <span className="history-field-label">
                        RECOMMENDATION
                      </span>
                      <p>{displayValue(response.summary)}</p>
                    </div>
                    <div className="history-agent-field">
                      <span className="history-field-label">
                        REASONING
                      </span>
                      <p>{displayValue(response.reasoning)}</p>
                    </div>
                    <div className="history-agent-field">
                      <span className="history-field-label">
                        KEY FACTORS
                      </span>
                      {Array.isArray(response.key_factors) &&
                        response.key_factors.length > 0 ? (
                        <ul>
                          {response.key_factors.map((factor, factorIndex) => (
                            <li key={factorIndex}>{factor}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>{displayValue(response.key_factors)}</p>
                      )}
                    </div>
                    <div className="history-agent-field">
                      <span className="history-field-label">
                        RISKS
                      </span>
                      <p>{displayValue(response.risk)}</p>
                    </div>
                    <div className="history-agent-field">
                      <span className="history-field-label">
                        SUGGESTED NEXT ACTION
                      </span>
                      <p>{displayValue(response.action)}</p>
                    </div>
                  </section>
                );
              })
            )}
          </div>
        )}
      </article>
    );
  }
  function renderPage() {
    if (activePage === "boardroom") {
      return renderBoardroom();
    }
    if (activePage === "simulation") {
      return renderSimulation();
    }
    if (activePage === "history") {
      return renderHistory();
    }
    return renderDashboard();
  }
  return (
    <div
      className={`app ${lightMode ? "light" : ""}`}
    >
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            F
          </div>
          <div>
            <h1>
              FounderVerse
            </h1>
            <p>
              AI Startup Simulator
            </p>
          </div>
        </div>
        <span className="nav-label">
          WORKSPACE
        </span>
        <nav>
          <button
            className={`nav-item ${activePage === "dashboard"
                ? "active"
                : ""
              }`}
            onClick={() =>
              setActivePage("dashboard")
            }
          >
            ◈ Dashboard
          </button>
          <button
            className={`nav-item ${activePage === "boardroom"
                ? "active"
                : ""
              }`}
            onClick={() =>
              setActivePage("boardroom")
            }
          >
            ♟ AI Boardroom
          </button>
          <button
            className={`nav-item ${activePage === "simulation"
                ? "active"
                : ""
              }`}
            onClick={() =>
              setActivePage("simulation")
            }
          >
            ◷ Simulation
          </button>
          <button
            className={`nav-item ${activePage === "history"
                ? "active"
                : ""
              }`}
            onClick={() => {
              setActivePage("history");
              loadDecisionHistory();
            }}
          >
            ◫ History
          </button>
        </nav>
        <div className="sidebar-bottom">
          <span className="status-dot" />
          FounderVerse workspace
        </div>
      </aside>
      {/* MAIN */}
      <main className="main-content">
        <div className="topbar">
          <div>
            <span className="eyebrow">
              YOUR STARTUP JOURNEY
            </span>
            <h2>
              {activePage === "dashboard"
                ? "Founder Dashboard"
                : activePage === "boardroom"
                  ? "AI Boardroom"
                  : activePage === "history"
                    ? "Decision History"
                    : "Startup Simulation"}
            </h2>
          </div>
          <div className="topbar-actions">
            <button
              className="theme-button"
              onClick={() =>
                setLightMode(
                  (previous) => !previous
                )
              }
              title="Toggle theme"
            >
              {lightMode ? "☀" : "☾"}
            </button>
            <div className="profile-wrapper">
              <button
                className="profile"
                onClick={() =>
                  setProfileOpen(
                    (previous) => !previous
                  )
                }
              >
                <span className="avatar">
                  F
                </span>
                <span>
                  Founder
                </span>
                <span>
                  {profileOpen ? "⌃" : "⌄"}
                </span>
              </button>
              {profileOpen && (
                <div className="profile-menu">
                  <strong>
                    Founder Account
                  </strong>
                  <span>
                    {user?.email ||
                      "Authenticated user"}
                  </span>
                  <span>
                    {companyName}
                  </span>
                  <hr />
                  <button onClick={logout}>
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        {renderPage()}
        <footer>
          <span>
            FOUNDERVERSE
          </span>
          <span>
            Build · Decide · Evolve
          </span>
        </footer>
      </main>
    </div>
  );
}
/* =========================================================

   AGENT CARD

   ========================================================= */

function AgentCard({ agent }) {
  return (
    <div className="agent-card">
      <div
        className={`agent-icon ${agent.color}`}
      >
        {agent.icon}
      </div>
      <div className="agent-status">
        <span className="status-dot" />
        Ready
      </div>
      <span className="eyebrow">
        AI SPECIALIST
      </span>
      <h3>
        {agent.name}
      </h3>
      <p className="agent-role">
        {agent.role}
      </p>
      <p className="agent-description">
        {agent.description}
      </p>
    </div>
  );
}