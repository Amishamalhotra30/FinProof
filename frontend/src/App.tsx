import { useMemo, useState } from "react";
import "./index.css";

type Scenario = "NORMAL" | "MIXED" | "ADVERSARIAL" | "FAILURE_HEAVY";

type Batch = {
  batch_id: string;
  name: string;
  scenario: string;
  seed: number;
  status: string;
  case_count?: number;
  financial_impact?: string;
  stages?: Stage[];
};

type Stage = {
  name: string;
  status: string;
  duration_ms: number;
  records_processed: number;
  error?: string | null;
};

type Discrepancy = {
  discrepancy_id: string;
  control_id: string;
  expected_value?: string | number | null;
  observed_value?: string | number | null;
  difference: string | number;
  materiality: string;
  blocking: boolean;
  affected_event_ids: string[];
  evidence_references?: string[];
  investigation_status?: string;
};

type Verification = {
  case_id: string;
  status: string;
  controls: Array<{
    control_id: string;
    control_name: string;
    status: string;
    expected_value?: string | number | null;
    observed_value?: string | number | null;
    difference?: string | number | null;
    severity: string;
    blocking: boolean;
  }>;
  discrepancies: Discrepancy[];
};

type Reconstruction = {
  available: boolean;
  event_count: number;
  relationship_count: number;
  chain_count: number;
  chains: Array<{
    chain_id: string;
    event_ids: string[];
  }>;
};

type AuditEntry = {
  audit_id: string;
  case_id: string;
  verification_status: string;
  investigation_status?: string | null;
  evidence_ids: string[];
  policy_rule_id?: string | null;
  decision: string;
  reason_code: string;
  basis: string[];
  financial_impact: string | number;
  materiality: string;
  human_action?: string | null;
  human_comment?: string | null;
  timestamp: string;
};

type CaseAudit = {
  case_id: string;
  count: number;
  entries: AuditEntry[];
};

type View =
  | "overview"
  | "cases"
  | "investigations"
  | "review"
  | "audit"
  | "metrics";

const API = "/api";

function money(value: string | number | null | undefined) {
  const amount = Number(value ?? 0);

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Math.abs(amount));
}

function formatEventType(eventId: string) {
  const match = eventId.match(/CASE_\\d+_(.+?)_EVENT$/i);

  if (match) {
    return match[1].replaceAll("_", " ").toUpperCase();
  }

  return eventId
    .split(":")
    .filter(Boolean)
    .pop()
    ?.replaceAll("_", " ")
    .toUpperCase() ?? "EVENT";
}

function formatCaseLabel(eventIds: string[], fallback: number) {
  const match = eventIds[0]?.match(/CASE_\\d+/i);
  return match ? match[0].toUpperCase() : `CHAIN ${String(fallback).padStart(2, "0")}`;
}

function statusClass(status: string) {
  const value = status.toLowerCase();

  if (
    value.includes("pass") ||
    value.includes("verified") ||
    value.includes("complete") ||
    value.includes("resolved")
  ) {
    return "status-good";
  }

  if (
    value.includes("pending") ||
    value.includes("investigat") ||
    value.includes("review")
  ) {
    return "status-warn";
  }

  if (
    value.includes("fail") ||
    value.includes("block") ||
    value.includes("error")
  ) {
    return "status-bad";
  }

  return "status-neutral";
}

async function getJSON<T>(url: string): Promise<T> {
  const response = await fetch(`${API}${url}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

function App() {
  const [view, setView] = useState<View>("overview");
  const [scenario, setScenario] = useState<Scenario>("MIXED");
  const [batch, setBatch] = useState<Batch | null>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [reconstruction, setReconstruction] =
    useState<Reconstruction | null>(null);

  const [selectedCase, setSelectedCase] = useState<Discrepancy | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [reviewingCase, setReviewingCase] =
    useState<Discrepancy | null>(null);

  const [reviewAction, setReviewAction] = useState<
    "APPROVE" | "REJECT" | "REQUEST_MORE_EVIDENCE"
  >("APPROVE");

  const [reviewComment, setReviewComment] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);

  const [auditData, setAuditData] = useState<CaseAudit[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const discrepancies = verification?.discrepancies ?? [];

  const stats = useMemo(() => {
    const totalImpact = discrepancies.reduce(
      (sum, item) => sum + Math.abs(Number(item.difference ?? 0)),
      0,
    );

    const high = discrepancies.filter(
      (item) => item.materiality === "HIGH",
    ).length;

    const blocking = discrepancies.filter((item) => item.blocking).length;

    return {
      cases: discrepancies.length,
      impact: totalImpact,
      high,
      blocking,
    };
  }, [discrepancies]);

  async function createAndRunBatch() {
    setLoading(true);
    setError("");
    setNotice("");

    try {
      const seedMap: Record<Scenario, number> = {
        NORMAL: 101,
        MIXED: 202,
        ADVERSARIAL: 303,
        FAILURE_HEAVY: 404,
      };

      const createResponse = await fetch(`${API}/batches`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: "FinProof Demo Batch",
          scenario,
          seed: seedMap[scenario],
          num_cases: 100,
        }),
      });

      if (!createResponse.ok) {
        throw new Error(`Batch creation failed: ${createResponse.status}`);
      }

      const created = (await createResponse.json()) as Batch;
      setBatch(created);

      const runResponse = await fetch(
        `${API}/batches/${created.batch_id}/run`,
        {
          method: "POST",
        },
      );

      if (!runResponse.ok) {
        throw new Error(`Pipeline execution failed: ${runResponse.status}`);
      }

      const result = await runResponse.json();

      const returnedBatch = (result.batch ?? created) as Batch;

      setBatch(returnedBatch);
      setStages(
        returnedBatch.stages ??
        result.stages ??
        result.pipeline_stages ??
        [],
      );

      const batchId = created.batch_id;

      const [verificationData, reconstructionData] = await Promise.all([
        getJSON<Verification>(`/batches/${batchId}/verification`),
        getJSON<Reconstruction>(`/batches/${batchId}/reconstruction`),
      ]);

      setVerification(verificationData);
      setReconstruction(reconstructionData);

      setNotice("Complete control pipeline finished successfully.");
      setView("overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  function selectCase(item: Discrepancy) {
    setSelectedCase(item);
    setView("investigations");
  }

  async function loadAuditHistory() {
    if (discrepancies.length === 0) {
      setAuditData([]);
      return;
    }

    setAuditLoading(true);

    try {
      const results = await Promise.all(
        discrepancies.map(async (item) => {
          try {
            return await getJSON<CaseAudit>(
              `/cases/${encodeURIComponent(item.discrepancy_id)}/audit`,
            );
          } catch {
            return null;
          }
        }),
      );

      setAuditData(
        results.filter(
          (item): item is CaseAudit => item !== null,
        ),
      );
    } finally {
      setAuditLoading(false);
    }
  }

  async function submitReview() {
    if (!reviewingCase) {
      return;
    }

    if (!reviewComment.trim()) {
      setError("A review comment is required.");
      return;
    }

    setReviewSubmitting(true);
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        `${API}/cases/${encodeURIComponent(
          reviewingCase.discrepancy_id,
        )}/review`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            action: reviewAction,
            comment: reviewComment.trim(),
            reviewer_id: "DEMO_REVIEWER",
          }),
        },
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail ??
            `Review action failed: ${response.status}`,
        );
      }

      setReviewingCase(null);
      setReviewComment("");

      setNotice(
        `Review action ${reviewAction.replaceAll(
          "_",
          " ",
        )} recorded successfully.`,
      );

      await loadAuditHistory();
      setView("audit");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to record review action.",
      );
    } finally {
      setReviewSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">F</div>
          <div>
            <div className="brand-name">FinProof</div>
            <div className="brand-subtitle">Financial Control</div>
          </div>
        </div>

        <div className="nav-label">CONTROL CENTER</div>

        <nav>
          <NavButton
            active={view === "overview"}
            onClick={() => setView("overview")}
            icon="◈"
            label="Overview"
          />
          <NavButton
            active={view === "cases"}
            onClick={() => setView("cases")}
            icon="▦"
            label="Cases"
            count={discrepancies.length || undefined}
          />
          <NavButton
            active={view === "investigations"}
            onClick={() => setView("investigations")}
            icon="⌁"
            label="Investigations"
          />
          <NavButton
            active={view === "review"}
            onClick={() => setView("review")}
            icon="✓"
            label="Review Queue"
            count={stats.high || undefined}
          />
          <NavButton
            active={view === "audit"}
            onClick={() => setView("audit")}
            icon="◷"
            label="Audit"
          />
          <NavButton
            active={view === "metrics"}
            onClick={() => setView("metrics")}
            icon="⌁"
            label="Metrics"
          />
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="pulse" />
            <div>
              <strong>System operational</strong>
              <small>All deterministic controls online</small>
            </div>
          </div>

          <div className="version">FINPROOF · DEMO BUILD</div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">FINANCIAL CONTROL CENTER</div>
            <h1>
              {view === "overview" && "Control Overview"}
              {view === "cases" && "Case Explorer"}
              {view === "investigations" && "Case Investigation"}
              {view === "review" && "Human Review Queue"}
              {view === "audit" && "Audit Trail"}
              {view === "metrics" && "Operational & Benchmark Metrics"}
            </h1>
          </div>

          <div className="topbar-right">
            {batch && (
              <div className="batch-pill">
                <span className="online-dot" />
                {batch.batch_id}
              </div>
            )}

            <button
              className="primary-button compact"
              onClick={() => setView("overview")}
            >
              Control Center
            </button>
          </div>
        </header>

        {error && (
          <div className="alert alert-error">
            <strong>Pipeline error</strong>
            <span>{error}</span>
            <button onClick={() => setError("")}>×</button>
          </div>
        )}

        {notice && (
          <div className="alert alert-success">
            <strong>Pipeline complete</strong>
            <span>{notice}</span>
            <button onClick={() => setNotice("")}>×</button>
          </div>
        )}

        {!batch ? (
          <LaunchScreen
            scenario={scenario}
            setScenario={setScenario}
            loading={loading}
            onRun={createAndRunBatch}
          />
        ) : (
          <div className="content">
            {view === "overview" && (
              <Overview
                batch={batch}
                stages={stages}
                stats={stats}
                reconstruction={reconstruction}
                verification={verification}
                onRun={createAndRunBatch}
                loading={loading}
                onCase={selectCase}
              />
            )}

            {view === "cases" && (
              <Cases
                discrepancies={discrepancies}
                onSelect={selectCase}
              />
            )}

            {view === "investigations" && (
              <Investigation
                selectedCase={selectedCase ?? discrepancies[0] ?? null}
                reconstruction={reconstruction}
                verification={verification}
              />
            )}

            {view === "review" && (
              <ReviewQueue
                discrepancies={discrepancies}
                onSelect={selectCase}
                onReview={(item) => {
                  setReviewingCase(item);
                  setReviewAction("APPROVE");
                  setReviewComment("");
                  setError("");
                }}
              />
            )}

            {view === "audit" && (
              <Audit
                stages={stages}
                batch={batch}
                discrepancies={discrepancies}
                auditData={auditData}
                loading={auditLoading}
                onRefresh={loadAuditHistory}
              />
            )}

            {view === "metrics" && (
              <Metrics stats={stats} batch={batch} stages={stages} />
            )}
          </div>
        )}
      </main>

      {reviewingCase && (
        <div className="review-modal-backdrop">
          <div className="review-modal">
            <div className="review-modal-header">
              <div>
                <div className="section-kicker">
                  CONTROLLED HUMAN ACTION
                </div>
                <h2>Review case</h2>
                <p>{reviewingCase.discrepancy_id}</p>
              </div>

              <button
                className="text-button"
                onClick={() => {
                  if (!reviewSubmitting) {
                    setReviewingCase(null);
                  }
                }}
              >
                Close
              </button>
            </div>

            <div className="review-modal-summary">
              <div>
                <span>CONTROL</span>
                <strong>{reviewingCase.control_id}</strong>
              </div>

              <div>
                <span>GAP</span>
                <strong>{money(reviewingCase.difference)}</strong>
              </div>

              <div>
                <span>MATERIALITY</span>
                <strong>{reviewingCase.materiality}</strong>
              </div>
            </div>

            <div className="review-action-group">
              <button
                className={
                  reviewAction === "APPROVE"
                    ? "primary-button"
                    : "secondary-button"
                }
                onClick={() => setReviewAction("APPROVE")}
                disabled={reviewSubmitting}
              >
                Approve
              </button>

              <button
                className={
                  reviewAction === "REJECT"
                    ? "primary-button"
                    : "secondary-button"
                }
                onClick={() => setReviewAction("REJECT")}
                disabled={reviewSubmitting}
              >
                Reject
              </button>

              <button
                className={
                  reviewAction === "REQUEST_MORE_EVIDENCE"
                    ? "primary-button"
                    : "secondary-button"
                }
                onClick={() =>
                  setReviewAction("REQUEST_MORE_EVIDENCE")
                }
                disabled={reviewSubmitting}
              >
                Request More Evidence
              </button>
            </div>

            <label className="review-comment-label">
              Review comment
            </label>

            <textarea
              className="review-comment"
              value={reviewComment}
              onChange={(event) =>
                setReviewComment(event.target.value)
              }
              placeholder="Explain the human decision..."
              rows={4}
              disabled={reviewSubmitting}
            />

            <div className="review-modal-footer">
              <span>
                Action:{" "}
                <strong>
                  {reviewAction.replaceAll("_", " ")}
                </strong>
              </span>

              <button
                className="primary-button"
                onClick={submitReview}
                disabled={reviewSubmitting}
              >
                {reviewSubmitting
                  ? "Recording..."
                  : "Record Decision"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function NavButton({
  active,
  onClick,
  icon,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
  count?: number;
}) {
  return (
    <button
      className={`nav-button ${active ? "active" : ""}`}
      onClick={onClick}
    >
      <span className="nav-icon">{icon}</span>
      <span>{label}</span>
      {count !== undefined && count > 0 && (
        <span className="nav-count">{count}</span>
      )}
    </button>
  );
}

function LaunchScreen({
  scenario,
  setScenario,
  loading,
  onRun,
}: {
  scenario: Scenario;
  setScenario: (value: Scenario) => void;
  loading: boolean;
  onRun: () => void;
}) {
  return (
    <div className="launch">
      <div className="launch-grid">
        <section className="hero-card">
          <div className="hero-kicker">EVIDENCE-DRIVEN FINANCIAL CONTROL</div>
          <h2>
            Know what happened.
            <br />
            Know <em>why</em>.
            <br />
            Know when to stop.
          </h2>
          <p>
            FinProof reconciles financial records, reconstructs event chains,
            verifies financial controls, investigates unexplained gaps, and
            decides whether the evidence is strong enough to act.
          </p>

          <div className="pipeline-line">
            <span>Reconcile</span>
            <b>→</b>
            <span>Reconstruct</span>
            <b>→</b>
            <span>Verify</span>
            <b>→</b>
            <span>Investigate</span>
            <b>→</b>
            <span>Decide</span>
          </div>
        </section>

        <section className="run-card">
          <div className="section-kicker">DEMO ENVIRONMENT</div>
          <h3>Run a control batch</h3>
          <p>
            Generate a deterministic financial dataset and execute the full
            FinProof pipeline.
          </p>

          <label>Scenario</label>

          <div className="scenario-grid">
            {(
              [
                ["NORMAL", "Healthy controls"],
                ["MIXED", "Realistic mixed cases"],
                ["ADVERSARIAL", "Hard edge cases"],
                ["FAILURE_HEAVY", "Failure simulation"],
              ] as [Scenario, string][]
            ).map(([value, description]) => (
              <button
                key={value}
                className={`scenario ${
                  scenario === value ? "selected" : ""
                }`}
                onClick={() => setScenario(value)}
              >
                <strong>{value.replace("_", " ")}</strong>
                <small>{description}</small>
              </button>
            ))}
          </div>

          <button
            className="primary-button run-button"
            onClick={onRun}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" />
                Running control pipeline…
              </>
            ) : (
              <>Run Demo Control →</>
            )}
          </button>

          <div className="demo-note">
            <span>◆</span>
            Deterministic seed · 100 cases · repeatable results
          </div>
        </section>
      </div>
    </div>
  );
}

function Overview({
  batch,
  stages,
  stats,
  reconstruction,
  verification,
  onRun,
  loading,
  onCase,
}: {
  batch: Batch;
  stages: Stage[];
  stats: {
    cases: number;
    impact: number;
    high: number;
    blocking: number;
  };
  reconstruction: Reconstruction | null;
  verification: Verification | null;
  onRun: () => void;
  loading: boolean;
  onCase: (item: Discrepancy) => void;
}) {
  const failedControls =
    verification?.controls.filter((control) => control.status === "FAIL") ?? [];

  return (
    <>
      <div className="batch-header">
        <div>
          <div className="batch-label">ACTIVE BATCH</div>
          <h2>{batch.name}</h2>
          <p>
            Scenario <strong>{batch.scenario}</strong> · Seed{" "}
            <strong>{batch.seed}</strong> · 100 deterministic cases
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={onRun}
          disabled={loading}
        >
          ↻ Run Again
        </button>
      </div>

      <section className="control-banner">
        <div className="control-icon">!</div>
        <div className="control-copy">
          <div className="control-label">OVERALL CONTROL STATE</div>
          <h2>
            {stats.cases === 0 ? "Controls verified" : "Review required"}
          </h2>
          <p>
            {stats.cases === 0
              ? "No financial discrepancies were detected."
              : `${stats.cases} discrepancy cases require investigation or review.`}
          </p>
        </div>
        <div className="control-side">
          <span>FINANCIAL IMPACT</span>
          <strong>{money(stats.impact)}</strong>
        </div>
      </section>

      <div className="metric-grid">
        <MetricCard
          label="Cases requiring attention"
          value={stats.cases}
          detail={`${stats.high} high materiality`}
        />
        <MetricCard
          label="Financial impact"
          value={money(stats.impact)}
          detail="Aggregate discrepancy"
        />
        <MetricCard
          label="Blocking issues"
          value={stats.blocking}
          detail="Require controlled action"
        />
        <MetricCard
          label="Reconstructed events"
          value={reconstruction?.event_count ?? 0}
          detail={`${reconstruction?.chain_count ?? 0} event chains`}
        />
      </div>

      <div className="two-column">
        <Panel
          title="Pipeline execution"
          subtitle="End-to-end control processing"
        >
          <div className="stage-list">
            {stages.length === 0 ? (
              <Empty text="Pipeline timing unavailable." />
            ) : (
              stages.map((stage) => (
                <div className="stage-row" key={stage.name}>
                  <div className={`stage-dot ${statusClass(stage.status)}`} />
                  <div className="stage-name">
                    <strong>{stage.name.replaceAll("_", " ")}</strong>
                    <small>{stage.records_processed} records</small>
                  </div>
                  <div className="stage-status">
                    {stage.status}
                  </div>
                  <div className="stage-time">
                    {Number(stage.duration_ms).toFixed(2)} ms
                  </div>
                </div>
              ))
            )}
          </div>
        </Panel>

        <Panel
          title="Verification controls"
          subtitle={`${failedControls.length} failed controls`}
        >
          <div className="control-list">
            {(verification?.controls ?? []).slice(0, 7).map((control) => (
              <div className="control-row" key={control.control_id}>
                <div>
                  <strong>{control.control_name}</strong>
                  <small>{control.control_id}</small>
                </div>
                <span className={`status-chip ${statusClass(control.status)}`}>
                  {control.status}
                </span>
              </div>
            ))}

            {!verification?.controls.length && (
              <Empty text="No control results available." />
            )}
          </div>
        </Panel>
      </div>

      <Panel
        title="Cases requiring attention"
        subtitle="Prioritize by financial impact"
        action={
          <button
            className="text-button"
            onClick={() => {
              const first = verification?.discrepancies[0];
              if (first) onCase(first);
            }}
          >
            View all →
          </button>
        }
      >
        {stats.cases === 0 ? (
          <Empty text="No discrepancy cases detected." />
        ) : (
          <div className="case-table">
            <div className="table-header">
              <span>CASE</span>
              <span>CONTROL</span>
              <span>GAP</span>
              <span>MATERIALITY</span>
              <span>STATE</span>
            </div>

            {verification?.discrepancies.slice(0, 6).map((item) => (
              <button
                className="table-row"
                key={item.discrepancy_id}
                onClick={() => onCase(item)}
              >
                <span className="case-id">{item.discrepancy_id}</span>
                <span>{item.control_id}</span>
                <span className="amount">{money(item.difference)}</span>
                <span>
                  <span
                    className={`status-chip ${statusClass(
                      item.materiality,
                    )}`}
                  >
                    {item.materiality}
                  </span>
                </span>
                <span>
                  <span
                    className={`status-chip ${statusClass(
                      item.investigation_status ?? "UNINVESTIGATED",
                    )}`}
                  >
                    {item.investigation_status ?? "UNINVESTIGATED"}
                  </span>
                </span>
              </button>
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}

function Cases({
  discrepancies,
  onSelect,
}: {
  discrepancies: Discrepancy[];
  onSelect: (item: Discrepancy) => void;
}) {
  const [filter, setFilter] = useState("ALL");

  const filtered =
    filter === "ALL"
      ? discrepancies
      : discrepancies.filter((item) => item.materiality === filter);

  return (
    <>
      <div className="page-intro">
        <div>
          <div className="section-kicker">CASE EXPLORER</div>
          <h2>Every discrepancy has a trace.</h2>
          <p>
            Start with the financial gap, then drill into controls, events,
            evidence, and the final decision.
          </p>
        </div>

        <div className="filter-group">
          {["ALL", "HIGH", "MEDIUM", "LOW"].map((item) => (
            <button
              key={item}
              className={`filter-button ${filter === item ? "active" : ""}`}
              onClick={() => setFilter(item)}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <Panel title={`${filtered.length} cases`} subtitle="Sorted by current filter">
        {filtered.length === 0 ? (
          <Empty text="No cases match this filter." />
        ) : (
          <div className="case-table">
            <div className="table-header">
              <span>CASE</span>
              <span>CONTROL</span>
              <span>EXPECTED → OBSERVED</span>
              <span>GAP</span>
              <span>SEVERITY</span>
            </div>

            {filtered.map((item) => (
              <button
                className="table-row"
                key={item.discrepancy_id}
                onClick={() => onSelect(item)}
              >
                <span className="case-id">{item.discrepancy_id}</span>
                <span>{item.control_id}</span>
                <span>
                  {money(item.expected_value)} →{" "}
                  {money(item.observed_value)}
                </span>
                <span className="amount">{money(item.difference)}</span>
                <span
                  className={`status-chip ${statusClass(item.materiality)}`}
                >
                  {item.materiality}
                </span>
              </button>
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}

function Investigation({
  selectedCase,
  reconstruction,
  verification,
}: {
  selectedCase: Discrepancy | null;
  reconstruction: Reconstruction | null;
  verification: Verification | null;
}) {
  if (!selectedCase) {
    return (
      <Empty
        text="Select a discrepancy from Cases to inspect the investigation."
      />
    );
  }

  const control = verification?.controls.find(
    (item) => item.control_id === selectedCase.control_id,
  );

  return (
    <>
      <div className="case-investigation-header">
        <div>
          <div className="section-kicker">INVESTIGATION</div>
          <h2>{selectedCase.discrepancy_id}</h2>
          <p>
            Control failure · {selectedCase.control_id} ·{" "}
            {selectedCase.materiality} materiality
          </p>
        </div>

        <span className={`large-status ${statusClass(selectedCase.materiality)}`}>
          {selectedCase.blocking ? "BLOCKING" : "REVIEW"}
        </span>
      </div>

      <div className="investigation-grid">
        <Panel title="Financial gap" subtitle="Expected vs observed">
          <div className="gap-grid">
            <div>
              <span>EXPECTED</span>
              <strong>{money(selectedCase.expected_value)}</strong>
            </div>
            <div>
              <span>OBSERVED</span>
              <strong>{money(selectedCase.observed_value)}</strong>
            </div>
            <div className="gap-value">
              <span>VARIANCE</span>
              <strong>{money(selectedCase.difference)}</strong>
            </div>
          </div>
        </Panel>

        <Panel title="Control failure" subtitle={control?.control_name}>
          <div className="failure-box">
            <div>
              <span>CONTROL</span>
              <strong>{selectedCase.control_id}</strong>
            </div>
            <div>
              <span>STATUS</span>
              <strong className="bad-text">
                {control?.status ?? "FAIL"}
              </strong>
            </div>
            <div>
              <span>BLOCKING</span>
              <strong>{selectedCase.blocking ? "YES" : "NO"}</strong>
            </div>
          </div>
        </Panel>
      </div>

      <Panel
        title="Reconstructed event chain"
        subtitle="Application-derived financial lineage"
      >
        <div className="chain">
          {reconstruction?.chains.slice(0, 4).map((chain, index) => (
            <div className="chain-row" key={chain.chain_id}>
              <div
                className="chain-node primary"
                title={chain.chain_id}
                style={{ minWidth: 0, overflow: "hidden" }}
              >
                <small>EVENT CHAIN</small>
                <strong>
                  {formatCaseLabel(chain.event_ids, index + 1)}
                </strong>
                <div
                  style={{
                    marginTop: "8px",
                    fontSize: "12px",
                    lineHeight: 1.5,
                    color: "var(--muted, #7f8ca3)",
                    whiteSpace: "normal",
                    overflowWrap: "anywhere",
                  }}
                >
                  {chain.event_ids
                    .slice(0, 8)
                    .map(formatEventType)
                    .join(" → ")}
                  {chain.event_ids.length > 8
                    ? ` → +${chain.event_ids.length - 8} more`
                    : ""}
                </div>
              </div>

              <div className="chain-arrow">→</div>

              <div className="chain-node">
                <small>EVENTS</small>
                <strong>{chain.event_ids.length}</strong>
              </div>

              <div className="chain-arrow">→</div>

              <div className="chain-node">
                <small>POSITION</small>
                <strong>{index === 0 ? "Observed" : "Related"}</strong>
              </div>
            </div>
          ))}

          {!reconstruction?.chains.length && (
            <Empty text="No reconstructed chains available." />
          )}
        </div>
      </Panel>

      <Panel
        title="Evidence Provenance"
        subtitle="Source references supporting the observed discrepancy"
      >
        <div className="evidence-panel">
          <div className="evidence-summary">
            <div>
              <span>EVIDENCE REFERENCES</span>
              <strong>
                {selectedCase.evidence_references?.length ?? 0}
              </strong>
            </div>
            <div>
              <span>AFFECTED EVENTS</span>
              <strong>{selectedCase.affected_event_ids.length}</strong>
            </div>
            <div>
              <span>PROVENANCE</span>
              <strong>TRACEABLE</strong>
            </div>
          </div>

          <div className="evidence-list">
            {(selectedCase.evidence_references ?? []).length === 0 ? (
              <Empty text="No evidence references were returned for this discrepancy." />
            ) : (
              (selectedCase.evidence_references ?? []).map((evidenceId) => (
                <div className="evidence-row" key={evidenceId}>
                  <div className="evidence-icon">E</div>
                  <div className="evidence-copy">
                    <strong>{evidenceId}</strong>
                    <small>
                      Supporting evidence reference · linked to the verified
                      control failure
                    </small>
                  </div>
                  <span className="status-chip status-good">VERIFIED LINK</span>
                </div>
              ))
            )}
          </div>

          <div className="evidence-footer">
            <span>OBSERVED EVENT IDS</span>
            <div className="evidence-tags">
              {selectedCase.affected_event_ids.slice(0, 12).map((eventId) => (
                <span key={eventId} title={eventId}>
                  {formatEventType(eventId)}
                </span>
              ))}
              {selectedCase.affected_event_ids.length > 12 && (
                <span>
                  +{selectedCase.affected_event_ids.length - 12} more
                </span>
              )}
            </div>
          </div>
        </div>
      </Panel>

      <Panel
        title="AI Investigation Trace"
        subtitle="Auditable actions — private model reasoning is never exposed"
      >
        <div className="trace">
          <TraceItem
            number="01"
            title="Discrepancy detected"
            text={`Control ${selectedCase.control_id} produced a variance of ${money(
              selectedCase.difference,
            )}.`}
            state="complete"
          />
          <TraceItem
            number="02"
            title="Related evidence searched"
            text="Application-controlled evidence retrieval was requested for the affected event chain."
            state="complete"
          />
          <TraceItem
            number="03"
            title="Hypotheses evaluated"
            text="Candidate explanations are evaluated against available evidence and arithmetic constraints."
            state="complete"
          />
          <TraceItem
            number="04"
            title="Application validation"
            text="Any proposed explanation must satisfy deterministic evidence and discrepancy validation."
            state="active"
          />
          <TraceItem
            number="05"
            title="Decision policy"
            text="The final action depends on evidence sufficiency, materiality, blocking status, and policy."
            state="pending"
          />
        </div>
      </Panel>

      <div className="stop-card">
        <div className="stop-icon">!</div>
        <div>
          <strong>FinProof knows when to stop.</strong>
          <p>
            If evidence is insufficient or contradictory, the system does not
            fabricate a resolution. The case is routed to controlled human
            review.
          </p>
        </div>
      </div>
    </>
  );
}

function ReviewQueue({
  discrepancies,
  onSelect,
  onReview,
}: {
  discrepancies: Discrepancy[];
  onSelect: (item: Discrepancy) => void;
  onReview: (item: Discrepancy) => void;
}) {
  const reviewCases = discrepancies.filter(
    (item) => item.blocking || item.materiality === "HIGH",
  );

  return (
    <>
      <div className="page-intro">
        <div>
          <div className="section-kicker">HUMAN-IN-THE-LOOP</div>
          <h2>Review only what needs a human.</h2>
          <p>
            FinProof escalates cases when policy, materiality, contradiction,
            or insufficient evidence prevents safe automation.
          </p>
        </div>
      </div>

      <div className="review-summary">
        <div>
          <span>REVIEW QUEUE</span>
          <strong>{reviewCases.length}</strong>
        </div>
        <div>
          <span>HIGH MATERIALITY</span>
          <strong>
            {
              discrepancies.filter((item) => item.materiality === "HIGH")
                .length
            }
          </strong>
        </div>
        <div>
          <span>BLOCKING</span>
          <strong>
            {discrepancies.filter((item) => item.blocking).length}
          </strong>
        </div>
      </div>

      <Panel title="Cases awaiting controlled action">
        {reviewCases.length === 0 ? (
          <Empty text="No cases currently require human review." />
        ) : (
          <div className="review-list">
            {reviewCases.map((item) => (
              <div className="review-item" key={item.discrepancy_id}>
                <div>
                  <span className="case-id">{item.discrepancy_id}</span>
                  <h3>{item.control_id}</h3>
                  <p>
                    Financial discrepancy of{" "}
                    <strong>{money(item.difference)}</strong>.{" "}
                    {item.blocking
                      ? "Blocking failure."
                      : "High materiality case."}
                  </p>
                </div>

                <div className="review-actions">
                  <button
                    className="secondary-button"
                    onClick={() => onSelect(item)}
                  >
                    Inspect
                  </button>
                  <button
                    className="primary-button"
                    onClick={() => onReview(item)}
                  >
                    Review
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}

function Audit({
  stages,
  batch,
  discrepancies,
  auditData,
  loading,
  onRefresh,
}: {
  stages: Stage[];
  batch: Batch;
  discrepancies: Discrepancy[];
  auditData: CaseAudit[];
  loading: boolean;
  onRefresh: () => void;
}) {
  const pipelineEvents = [
    {
      stage: "INGESTION",
      text: "Source records accepted and normalized.",
    },
    {
      stage: "RECONCILIATION",
      text: "Financial records reconciled and relationships evaluated.",
    },
    {
      stage: "RECONSTRUCTION",
      text: "Event graph and financial chains reconstructed.",
    },
    {
      stage: "VERIFICATION",
      text: "Deterministic financial controls evaluated.",
    },
    {
      stage: "INVESTIGATION",
      text: "Evidence-driven investigation evaluated unexplained discrepancies.",
    },
    {
      stage: "DECISION",
      text: "Policy determines automation, review, or blocking.",
    },
  ];

  const auditEntries = auditData.flatMap((item) =>
    item.entries.map((entry) => ({
      ...entry,
      case_id: item.case_id,
    })),
  );

  return (
    <>
      <div className="page-intro">
        <div>
          <div className="section-kicker">AUDIT TRAIL</div>
          <h2>Every decision leaves a trace.</h2>
          <p>
            Batch <strong>{batch.batch_id}</strong> · append-only
            decision and processing history.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={onRefresh}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "↻ Refresh Audit"}
        </button>
      </div>

      <Panel
        title="Decision audit history"
        subtitle={`${auditEntries.length} recorded decision event${
          auditEntries.length === 1 ? "" : "s"
        }`}
      >
        {auditEntries.length === 0 ? (
          <Empty
            text={
              loading
                ? "Loading decision audit history…"
                : discrepancies.length === 0
                  ? "No discrepancy decisions exist for this batch."
                  : "No persisted case audit entries were returned yet. Run a review action, then refresh."
            }
          />
        ) : (
          <div className="decision-audit-list">
            {[...auditEntries]
              .sort(
                (a, b) =>
                  new Date(a.timestamp).getTime() -
                  new Date(b.timestamp).getTime(),
              )
              .map((entry) => (
                <div className="decision-audit-item" key={entry.audit_id}>
                  <div className="decision-audit-marker">
                    <span>✓</span>
                  </div>

                  <div className="decision-audit-content">
                    <div className="decision-audit-top">
                      <div>
                        <span className="case-id">
                          {entry.case_id}
                        </span>
                        <strong>
                          {entry.decision.replaceAll("_", " ")}
                        </strong>
                      </div>

                      <span
                        className={`status-chip ${statusClass(
                          entry.decision,
                        )}`}
                      >
                        {entry.decision}
                      </span>
                    </div>

                    <div className="decision-audit-grid">
                      <div>
                        <span>VERIFICATION</span>
                        <strong>{entry.verification_status}</strong>
                      </div>

                      <div>
                        <span>INVESTIGATION</span>
                        <strong>
                          {entry.investigation_status ?? "—"}
                        </strong>
                      </div>

                      <div>
                        <span>MATERIALITY</span>
                        <strong>{entry.materiality}</strong>
                      </div>

                      <div>
                        <span>FINANCIAL IMPACT</span>
                        <strong>
                          {money(entry.financial_impact)}
                        </strong>
                      </div>
                    </div>

                    <div className="decision-audit-reason">
                      <span>POLICY BASIS</span>
                      <p>
                        {entry.basis.length > 0
                          ? entry.basis.join(" · ")
                          : entry.reason_code}
                      </p>
                    </div>

                    {entry.human_action && (
                      <div className="human-audit-note">
                        <strong>
                          HUMAN ACTION ·{" "}
                          {entry.human_action.replaceAll("_", " ")}
                        </strong>

                        {entry.human_comment && (
                          <p>{entry.human_comment}</p>
                        )}
                      </div>
                    )}

                    <small>
                      audit_id={entry.audit_id} · policy=
                      {entry.policy_rule_id ?? "—"} ·{" "}
                      {new Date(entry.timestamp).toLocaleString()}
                    </small>
                  </div>
                </div>
              ))}
          </div>
        )}
      </Panel>

      <Panel
        title="Pipeline processing history"
        subtitle="Deterministic stage execution for this batch"
      >
        <div className="audit-timeline">
          {pipelineEvents.map((event, index) => {
            const stage = stages.find((item) =>
              item.name
                .toLowerCase()
                .includes(event.stage.toLowerCase()),
            );

            return (
              <div className="audit-event" key={event.stage}>
                <div className="audit-marker">
                  <span>{String(index + 1).padStart(2, "0")}</span>
                </div>

                <div className="audit-content">
                  <div className="audit-top">
                    <strong>{event.stage}</strong>
                    <span>
                      {stage
                        ? `${stage.duration_ms.toFixed(2)} ms`
                        : "—"}
                    </span>
                  </div>

                  <p>{event.text}</p>

                  <small>
                    batch_id={batch.batch_id} · status=
                    {stage?.status ?? "COMPLETED"}
                  </small>
                </div>
              </div>
            );
          })}
        </div>
      </Panel>
    </>
  );
}

function Metrics({
  stats,
  batch,
  stages,
}: {
  stats: {
    cases: number;
    impact: number;
    high: number;
    blocking: number;
  };
  batch: Batch;
  stages: Stage[];
}) {
  const totalTime = stages.reduce(
    (sum, stage) => sum + Number(stage.duration_ms || 0),
    0,
  );

  const hasTiming = stages.length > 0;

  return (
    <>
      <div className="page-intro">
        <div>
          <div className="section-kicker">OBSERVABILITY</div>
          <h2>Measure the system separately from the benchmark.</h2>
          <p>
            Operational telemetry describes this run. Benchmark metrics remain
            a separate evaluation surface.
          </p>
        </div>
      </div>

      <div className="metric-section-label">OPERATIONAL METRICS</div>

      <div className="metric-grid">
        <MetricCard
          label="Records / cases"
          value={100}
          detail={`${batch.scenario} scenario`}
        />
        <MetricCard
          label="Pipeline duration"
          value={hasTiming ? `${totalTime.toFixed(2)} ms` : "Unavailable"}
          detail={hasTiming ? "Sum of stage timings" : "No stage telemetry returned"}
        />
        <MetricCard
          label="Discrepancy cases"
          value={stats.cases}
          detail={`${stats.high} high materiality`}
        />
        <MetricCard
          label="Unresolved financial impact"
          value={money(stats.impact)}
          detail="Current batch"
        />
      </div>

      <div className="metric-section-label">BENCHMARK METRICS</div>

      <div className="benchmark-grid">
        <BenchmarkCard label="Reconstruction accuracy" value="100%" />
        <BenchmarkCard label="Verification false-pass" value="0.00%" />
        <BenchmarkCard label="False explanations" value="0" />
        <BenchmarkCard label="False resolutions" value="0" />
        <BenchmarkCard label="Automation rate" value="60%" />
        <BenchmarkCard label="Human investigation reduction" value="75%" />
      </div>

      <div className="benchmark-note">
        <strong>Benchmark integrity</strong>
        <p>
          Benchmark figures are not presented as measurements of this demo
          batch. They represent the deterministic evaluation results of the
          FinProof control pipeline.
        </p>
      </div>
    </>
  );
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function BenchmarkCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="benchmark-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  children,
  action,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h3>{title}</h3>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>

      {children}
    </section>
  );
}

function TraceItem({
  number,
  title,
  text,
  state,
}: {
  number: string;
  title: string;
  text: string;
  state: "complete" | "active" | "pending";
}) {
  return (
    <div className={`trace-item ${state}`}>
      <div className="trace-number">{number}</div>

      <div className="trace-line" />

      <div className="trace-content">
        <div className="trace-heading">
          <strong>{title}</strong>
          <span>
            {state === "complete" ? "AUDITED" : state.toUpperCase()}
          </span>
        </div>

        <p>{text}</p>
      </div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

export default App;