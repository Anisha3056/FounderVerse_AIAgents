import { useEffect, useMemo, useRef, useState } from "react";
import "./Landing.css";

/* ---------------- DATA ---------------- */

const AGENTS = [
  { name: "Finance", role: "Financial Strategy", icon: "₹", color: "gold",
    text: "Tracks revenue, expenses, cash flow and runway before you spend a rupee." },
  { name: "Marketing", role: "Growth & Marketing", icon: "✦", color: "slate",
    text: "Weighs acquisition, positioning and campaigns against real customer growth." },
  { name: "Sales", role: "Sales Strategy", icon: "↗", color: "clay",
    text: "Reads your pipeline, conversions and expansion potential." },
  { name: "CTO", role: "Technology", icon: "⌘", color: "sage",
    text: "Judges product and technical decisions for feasibility and risk." },
  { name: "Legal", role: "Risk & Compliance", icon: "§", color: "rose",
    text: "Flags contracts, compliance gaps and legal exposure early." },
];

const AGENT_BY_NAME = Object.fromEntries(AGENTS.map((a) => [a.name, a]));

const SCRIPT = [
  {
    q: "Should we increase our marketing budget next month?",
    replies: [
      ["Finance", "Hold. Runway is under 9 months. Cap the increase at 10%."],
      ["Marketing", "Proceed. CAC is falling, so double down on the best channel."],
      ["Sales", "Proceed carefully. The pipeline can absorb 30% more leads."],
      ["CTO", "Hold. Onboarding can't handle a traffic spike yet."],
      ["Legal", "Proceed, but review ad claims before they go live."],
    ],
  },
  {
    q: "Is it the right time to hire two engineers?",
    replies: [
      ["Finance", "Proceed with one hire first. Burn rises by roughly 18%."],
      ["Marketing", "Neutral. Product velocity helps retention more than ads."],
      ["Sales", "Proceed. Three customers are waiting on missing features."],
      ["CTO", "Proceed. Tech debt is slowing every release."],
      ["Legal", "Proceed. Make sure IP assignment is in every contract."],
    ],
  },
  {
    q: "Should we launch a new pricing tier this quarter?",
    replies: [
      ["Finance", "Proceed. A higher tier lifts MRR without raising costs."],
      ["Marketing", "Proceed. Test messaging with existing customers first."],
      ["Sales", "Hold. Reps need a month to learn the new pitch."],
      ["CTO", "Proceed. Billing already supports plan upgrades."],
      ["Legal", "Proceed. Update terms and notify current subscribers."],
    ],
  },
];

const STEPS = [
  { n: "01", title: "Ask",
    text: "Type any business decision you're facing, like hiring, pricing, spending or launching.",
    shows: ["Your question", "Choose a consultation mode", "Individual · Collaborative · Both"] },
  { n: "02", title: "Opinions",
    text: "Five specialists answer independently, each from their own domain.",
    shows: ["Recommendation", "Reasoning", "Key factors", "Risk", "Suggested action"] },
  { n: "03", title: "Discussion",
    text: "The agents read each other's views, challenge them and revise their positions.",
    shows: ["Agreements", "Disagreements", "Additional insight", "Revised position"] },
  { n: "04", title: "Synthesis",
    text: "A final boardroom assessment turns the debate into one clear recommendation.",
    shows: ["Executive summary", "Unresolved disagreements", "Next steps", "Success metrics"] },
  { n: "05", title: "Decide",
    text: "You make the call, Proceed or Hold Off, and explain why. It's saved to your history.",
    shows: ["Proceed / Hold Off", "Your reasoning", "Saved to Decision History"] },
];

const STRIP = [
  "Finance Agent", "Marketing Agent", "Sales Agent", "CTO Agent", "Legal Agent",
  "AI Boardroom", "Executive Discussion", "Final Synthesis",
  "Startup Simulation", "Decision History",
];

/* ---------------- HOOKS ---------------- */

function useInView(threshold = 0.2) {
  const ref = useRef(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setSeen(true);
          io.disconnect();
        }
      },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return [ref, seen];
}

function Reveal({ children, delay = 0, className = "" }) {
  const [ref, seen] = useInView(0.15);
  return (
    <div
      ref={ref}
      className={`reveal ${seen ? "in" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

function Count({ to }) {
  const [ref, seen] = useInView(0.4);
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!seen) return;
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / 1300, 1);
      setValue(Math.round(to * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [seen, to]);
  return <span ref={ref}>{value}</span>;
}

/* ---------------- HERO: LIVE BOARDROOM ---------------- */

function BoardroomDemo() {
  const [typed, setTyped] = useState("");
  const [replies, setReplies] = useState([]);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let dead = false;
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    (async () => {
      let i = 0;
      while (!dead) {
        const scene = SCRIPT[i % SCRIPT.length];
        setReplies([]);
        setPending(false);
        setTyped("");
        for (let c = 1; c <= scene.q.length; c++) {
          if (dead) return;
          setTyped(scene.q.slice(0, c));
          await sleep(26);
        }
        await sleep(500);
        for (const reply of scene.replies) {
          if (dead) return;
          setPending(true);
          await sleep(750);
          if (dead) return;
          setReplies((prev) => [...prev, reply]);
          setPending(false);
          await sleep(220);
        }
        await sleep(3400);
        i += 1;
      }
    })();
    return () => {
      dead = true;
    };
  }, []);

  return (
    <div className="chat-card">
      <div className="chat-top">
        <div className="chat-dots"><i /><i /><i /></div>
        <span className="chat-title">AI Boardroom</span>
        <span className="chat-live"><i /> Live</span>
      </div>
      <div className="chat-body">
        <div className="bubble-founder">
          {typed}
          <span className="caret" />
        </div>
        {replies.map(([name, text]) => {
          const agent = AGENT_BY_NAME[name];
          return (
            <div className="reply" key={`${name}-${text}`}>
              <span className={`l-ico ${agent.color}`}>{agent.icon}</span>
              <div>
                <b>{name}</b>
                <p>{text}</p>
              </div>
            </div>
          );
        })}
        {pending && <div className="typing"><i /><i /><i /></div>}
      </div>
    </div>
  );
}

/* ---------------- FLOW (auto-cycling steps) ---------------- */

function Flow() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => setActive((a) => (a + 1) % STEPS.length), 3200);
    return () => clearInterval(id);
  }, [paused]);

  const step = STEPS[active];

  return (
    <div
      className="flow"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="flow-track">
        <div
          className="flow-progress"
          style={{ width: `${(active / (STEPS.length - 1)) * 100}%` }}
        />
        {STEPS.map((s, i) => (
          <button
            key={s.n}
            type="button"
            className={`flow-node ${i === active ? "active" : ""} ${i < active ? "done" : ""}`}
            onClick={() => setActive(i)}
          >
            <span className="flow-dot">{i < active ? "✓" : s.n}</span>
            <span className="flow-label">{s.title}</span>
          </button>
        ))}
      </div>
      <div className="flow-panel" key={active}>
        <div>
          <span className="eyebrow">STEP {step.n}</span>
          <h3>{step.title}</h3>
          <p>{step.text}</p>
        </div>
        <ul>
          {step.shows.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ---------------- SIMULATION (animated chart) ---------------- */

const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  notation: "compact",
  maximumFractionDigits: 1,
});

function SimulationDemo() {
  const [month, setMonth] = useState(1);

  useEffect(() => {
    const id = setInterval(() => setMonth((m) => (m >= 12 ? 1 : m + 1)), 1100);
    return () => clearInterval(id);
  }, []);

  const data = useMemo(() => {
    const customers = [120, 134, 151, 170, 189, 213, 238, 265, 296, 330, 368, 410];
    let cash = 2400000;
    return customers.map((c, i) => {
      const mrr = c * 1200;
      const expenses = 190000 + i * 9000;
      cash += mrr - expenses;
      return { customers: c, mrr, expenses, cash };
    });
  }, []);

  const W = 520, H = 230, padX = 28, top = 20, bottom = 30, maxV = 520000;
  const x = (i) => padX + (i * (W - padX * 2)) / 11;
  const y = (v) => H - bottom - (v / maxV) * (H - top - bottom);
  const visible = data.slice(0, month);
  const line = (key) => visible.map((d, i) => `${x(i)},${y(d[key])}`).join(" ");
  const area = `${x(0)},${H - bottom} ${line("mrr")} ${x(month - 1)},${H - bottom}`;
  const now = data[month - 1];
  const profit = now.mrr - now.expenses;

  return (
    <div className="sim-card">
      <div className="sim-head">
        <div>
          <span className="eyebrow">CURRENT SIMULATION</span>
          <h3>Month {month}</h3>
        </div>
        <span className={`sim-badge ${profit >= 0 ? "up" : "down"}`}>
          {profit >= 0 ? "Profitable" : "Burning cash"}
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="sim-chart" role="img"
           aria-label="MRR versus expenses over twelve months">
        {[0.25, 0.5, 0.75, 1].map((g) => (
          <line key={g} x1={padX} x2={W - padX} y1={y(maxV * g)} y2={y(maxV * g)} className="grid-line" />
        ))}
        <polygon points={area} className="sim-area" />
        <polyline points={line("expenses")} className="sim-line expenses" />
        <polyline points={line("mrr")} className="sim-line mrr" />
        <circle cx={x(month - 1)} cy={y(now.mrr)} r="5" className="sim-dot" />
        <circle cx={x(month - 1)} cy={y(now.mrr)} r="12" className="sim-pulse" />
        {data.map((_, i) => (
          <text key={i} x={x(i)} y={H - 8} className="sim-tick">{i + 1}</text>
        ))}
      </svg>

      <div className="sim-legend">
        <span><i className="mrr" /> MRR</span>
        <span><i className="expenses" /> Expenses</span>
      </div>

      <div className="sim-metrics">
        <div><span>Customers</span><strong>{now.customers}</strong></div>
        <div><span>MRR</span><strong>{money.format(now.mrr)}</strong></div>
        <div><span>Profit</span><strong className={profit >= 0 ? "pos" : "neg"}>{money.format(profit)}</strong></div>
        <div><span>Cash</span><strong>{money.format(now.cash)}</strong></div>
      </div>
    </div>
  );
}

/* ---------------- DECISION CARD ---------------- */

const DECISIONS = [
  { key: "proceed", label: "Proceed",
    why: "CAC is falling and the pipeline can absorb more leads. I'll raise spend by 10% and review in 30 days." },
  { key: "hold", label: "Hold Off",
    why: "Runway is shorter than I'd like. I'll wait until MRR covers expenses before increasing spend." },
];

function DecisionDemo() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((v) => (v + 1) % DECISIONS.length), 3600);
    return () => clearInterval(id);
  }, []);
  const d = DECISIONS[i];
  return (
    <div className="decision-demo">
      <span className="eyebrow">FOUNDER DECISION</span>
      <h3>What do you want to do?</h3>
      <div className="dd-options">
        {DECISIONS.map((opt, idx) => (
          <div key={opt.key} className={`dd-option ${opt.key} ${idx === i ? "selected" : ""}`}>
            <span>{opt.key === "proceed" ? "✓" : "⏸"}</span>
            {opt.label}
          </div>
        ))}
      </div>
      <p className="dd-why" key={d.key}>{d.why}</p>
      <div className="dd-saved"><i /> Saved to Decision History</div>
    </div>
  );
}

/* ---------------- PAGE ---------------- */

export default function Landing({ onEnter }) {
  const [light, setLight] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const heroRef = useRef(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function handleMouseMove(event) {
    const el = heroRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${event.clientX - rect.left}px`);
    el.style.setProperty("--my", `${event.clientY - rect.top}px`);
  }

  function scrollTo(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className={`landing ${light ? "light" : ""}`}>
      <header className={`l-nav ${scrolled ? "scrolled" : ""}`}>
        <div className="l-nav-inner">
          <div className="l-logo">
            <span className="l-logo-mark">F</span>
            <span>FounderVerse</span>
          </div>
          <nav className="l-links">
            <button type="button" onClick={() => scrollTo("agents")}>Agents</button>
            <button type="button" onClick={() => scrollTo("boardroom")}>Boardroom</button>
            <button type="button" onClick={() => scrollTo("simulation")}>Simulation</button>
            <button type="button" onClick={() => scrollTo("decisions")}>Decisions</button>
          </nav>
          <div className="l-nav-actions">
            <button type="button" className="l-theme" onClick={() => setLight((v) => !v)} title="Toggle theme">
              {light ? "☀" : "☾"}
            </button>
            <button type="button" className="l-btn ghost" onClick={onEnter}>Sign in</button>
            <button type="button" className="l-btn solid" onClick={onEnter}>Get started</button>
          </div>
        </div>
      </header>

      <section className="l-hero" ref={heroRef} onMouseMove={handleMouseMove}>
        <div className="l-hero-glow" />
        <div className="l-hero-grid">
          <div className="l-hero-copy">
            <span className="l-pill"><i /> AI STARTUP SIMULATOR</span>
            <h1>
              Run your startup.
              <br />
              <em>Before you risk it.</em>
            </h1>
            <p>
              FounderVerse gives you a boardroom of five AI executives who debate every
              decision, then a simulation that shows how your company evolves, month by
              month. You make the final call.
            </p>
            <div className="l-cta">
              <button type="button" className="l-btn solid big" onClick={onEnter}>
                Enter FounderVerse →
              </button>
              <button type="button" className="l-btn ghost big" onClick={() => scrollTo("boardroom")}>
                See how it works
              </button>
            </div>
            <div className="l-hero-mini">
              <div><strong>5</strong><span>AI executives</span></div>
              <div><strong>1</strong><span>live boardroom</span></div>
              <div><strong>∞</strong><span>decisions to test</span></div>
            </div>
          </div>

          <div className="l-hero-visual">
            <div className="float-chip c1"><span className="l-ico gold">₹</span> Finance</div>
            <div className="float-chip c2"><span className="l-ico slate">✦</span> Marketing</div>
            <div className="float-chip c3"><span className="l-ico clay">↗</span> Sales</div>
            <div className="float-chip c4"><span className="l-ico sage">⌘</span> CTO</div>
            <div className="float-chip c5"><span className="l-ico rose">§</span> Legal</div>
            <BoardroomDemo />
          </div>
        </div>
      </section>

      <div className="l-marquee" aria-hidden="true">
        <div className="l-marquee-track">
          {[...STRIP, ...STRIP].map((item, i) => (
            <span key={i}>{item}<b>✦</b></span>
          ))}
        </div>
      </div>

      <section className="l-stats">
        <Reveal className="l-stat"><strong><Count to={5} /></strong><span>Specialist AI agents</span></Reveal>
        <Reveal className="l-stat" delay={90}><strong><Count to={3} /></strong><span>Consultation modes</span></Reveal>
        <Reveal className="l-stat" delay={180}><strong><Count to={8} /></strong><span>Live business metrics</span></Reveal>
        <Reveal className="l-stat" delay={270}><strong><Count to={1} /></strong><span>Founder in control</span></Reveal>
      </section>

      <section className="l-section" id="agents">
        <Reveal className="l-head">
          <span className="eyebrow">01 / THE BOARD</span>
          <h2>Five executives. <em>Five perspectives.</em></h2>
          <p>Every question goes to specialists who think about your company from a different angle, so you never decide with a blind spot.</p>
        </Reveal>
        <div className="l-agents">
          {AGENTS.map((agent, i) => (
            <Reveal key={agent.name} delay={i * 90} className="l-agent">
              <span className={`l-ico big ${agent.color}`}>{agent.icon}</span>
              <h3>{agent.name}</h3>
              <b>{agent.role}</b>
              <p>{agent.text}</p>
              <span className="l-agent-line" />
            </Reveal>
          ))}
        </div>
      </section>

      <section className="l-section" id="boardroom">
        <Reveal className="l-head">
          <span className="eyebrow">02 / THE BOARDROOM</span>
          <h2>From a question to <em>a clear decision.</em></h2>
          <p>Choose individual opinions, a collaborative debate, or both. Hover to pause, or click any step.</p>
        </Reveal>
        <Reveal><Flow /></Reveal>
      </section>

      <section className="l-section" id="simulation">
        <div className="l-split">
          <Reveal className="l-split-copy">
            <span className="eyebrow">03 / THE SIMULATION</span>
            <h2>Watch your company <em>evolve.</em></h2>
            <p>
              Advance one virtual month at a time. Customer growth, churn, revenue,
              expenses, profit and cash are recalculated from your current company
              state, so you can see the consequences of a decision before it's real.
            </p>
            <ul className="l-ticks">
              <li>Month-over-month change on every key metric</li>
              <li>A timeline of your startup's whole journey</li>
              <li>Runway and burn tracked automatically</li>
            </ul>
          </Reveal>
          <Reveal delay={120}><SimulationDemo /></Reveal>
        </div>
      </section>

      <section className="l-section" id="decisions">
        <div className="l-split reverse">
          <Reveal delay={120}><DecisionDemo /></Reveal>
          <Reveal className="l-split-copy">
            <span className="eyebrow">04 / THE FOUNDER</span>
            <h2>The board advises. <em>You decide.</em></h2>
            <p>
              Record Proceed or Hold Off with your own reasoning. Every question, every
              agent response and every decision is stored, so you can look back on how
              you thought.
            </p>
            <ul className="l-ticks">
              <li>Full boardroom conversation saved with each decision</li>
              <li>Expand any past decision to re-read the debate</li>
              <li>Warnings when a decision affects other agents</li>
            </ul>
          </Reveal>
        </div>
      </section>

      <section className="l-final">
        <Reveal className="l-final-inner">
          <span className="eyebrow">READY WHEN YOU ARE</span>
          <h2>Your boardroom is <em>waiting.</em></h2>
          <p>Create your startup, ask your first question, and see how the board responds.</p>
          <button type="button" className="l-btn solid big" onClick={onEnter}>
            Enter FounderVerse →
          </button>
        </Reveal>
      </section>

      <footer className="l-footer">
        <span>FOUNDERVERSE</span>
        <span>Build · Decide · Evolve</span>
      </footer>
    </div>
  );
}