import { useCallback, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const sampleArgs = `--source-path /Users/aritraraychaudhuri/Downloads/BasicApp \
--gcp-project cloudify-486706 \
--mode automated`;

const AGENTS = [
  { key: "CodeAnalyzer", label: "Code Analysis" },
  { key: "Infrastructure", label: "Infrastructure" },
  { key: "DatabaseMigration", label: "Database Migration" },
  { key: "BackendDeployment", label: "Backend Deploy" },
  { key: "FrontendDeployment", label: "Frontend Deploy" },
];

function initAgentState() {
  const state = {};
  for (const a of AGENTS) {
    state[a.key] = { status: "pending", time: null };
  }
  return state;
}

// Parse STDERR log lines emitted by base_agent.py
const RE_STARTED = /Agent\.(\w+)\s+-\s+INFO\s+-\s+Starting\s+/;
const RE_COMPLETED = /Completed\s+(\w+)\s+-\s+Status:\s+(\w+)\s+\(([0-9.]+)s\)/;

function parseAgentEvent(line) {
  let m = line.match(RE_STARTED);
  if (m) return { agent: m[1], type: "started" };
  m = line.match(RE_COMPLETED);
  if (m) return { agent: m[1], type: "completed", agentStatus: m[2], time: parseFloat(m[3]) };
  return null;
}

export default function App() {
  const [args, setArgs] = useState(sampleArgs);
  const [status, setStatus] = useState("idle");
  const [migrationId, setMigrationId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [agents, setAgents] = useState(initAgentState);
  const logEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  const canRun = useMemo(() => status !== "running" && status !== "starting", [status]);
  const canCancel = useMemo(() => status === "running", [status]);

  const completedCount = useMemo(
    () => AGENTS.filter((a) => agents[a.key].status === "completed").length,
    [agents]
  );
  const progressPct = (completedCount / AGENTS.length) * 100;

  const appendLog = (line) => {
    setLogs((prev) => {
      const next = [...prev, line];
      return next.slice(-2000);
    });
  };

  const handleLogLine = useCallback((line) => {
    // Strip [STDERR] / [STDOUT] prefix for cleaner display
    const cleaned = line.replace(/^\[(STDERR|STDOUT)\]\s*/, "");
    appendLog(cleaned);

    const evt = parseAgentEvent(line);
    if (!evt) return;

    setAgents((prev) => {
      const cur = prev[evt.agent];
      if (!cur) return prev;

      if (evt.type === "started") {
        return { ...prev, [evt.agent]: { ...cur, status: "running" } };
      }
      if (evt.type === "completed") {
        return {
          ...prev,
          [evt.agent]: {
            status: evt.agentStatus === "success" ? "completed" : "failed",
            time: evt.time,
          },
        };
      }
      return prev;
    });
  }, []);

  const cancelMigration = async () => {
    if (!migrationId) return;
    try {
      await fetch(`${API_BASE}/api/migrations/${migrationId}/cancel`, {
        method: "POST",
      });
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setStatus("cancelled");
    } catch (err) {
      setError("Failed to cancel: " + err.message);
    }
  };

  const startMigration = async () => {
    setError(null);
    setLogs([]);
    setAgents(initAgentState());
    setStatus("starting");

    try {
      const response = await fetch(`${API_BASE}/api/migrations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ args }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "Failed to start migration");
      }

      const data = await response.json();
      setMigrationId(data.id);
      setStatus("running");

      const eventSource = new EventSource(
        `${API_BASE}/api/migrations/${data.id}/stream`
      );
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        handleLogLine(event.data);
        requestAnimationFrame(() => {
          logEndRef.current?.scrollIntoView({ behavior: "smooth" });
        });

        if (event.data === "[SYSTEM] EOF") {
          eventSource.close();
          eventSourceRef.current = null;
          setStatus("completed");
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        eventSourceRef.current = null;
        setStatus("error");
        setError("Log stream disconnected.");
      };
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  };

  return (
    <div className="app">
      <div className="hero">
        <div>
          <p className="eyebrow">Cloud Migration Console</p>
          <h1>Cloudify</h1>
          <p className="subhead">
            Powered by Dedalus SDK with multi-model handoffs and tool calling.
            Run migrations and stream logs in real time.
          </p>
        </div>
        <div className="status-card">
          <div className="status-label">Status</div>
          <div className={`status-pill status-${status}`}>{status}</div>
          <div className="status-id">
            {migrationId ? `ID: ${migrationId}` : "No active run"}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Migration Request</h2>
          <div className="button-group">
            {canCancel && (
              <button className="cancel" onClick={cancelMigration}>
                Cancel
              </button>
            )}
            <button
              className="primary"
              onClick={startMigration}
              disabled={!canRun}
            >
              {status === "running" ? "Running..." : "Run Migration"}
            </button>
          </div>
        </div>
        <textarea
          value={args}
          onChange={(e) => setArgs(e.target.value)}
          placeholder="Enter CLI args for migration_orchestrator.py migrate"
          rows={6}
        />
        <p className="hint">
          Tip: This content is passed to `python migration_orchestrator.py
          migrate` on the server. Uses Dedalus SDK for multi-model handoffs.
        </p>
        {error && <div className="error">{error}</div>}
      </div>

      {/* Agent Progress Panel */}
      {status !== "idle" && (
        <div className="panel">
          <div className="panel-header">
            <h2>Agent Progress</h2>
            <span className="mono">
              {completedCount}/{AGENTS.length} agents
            </span>
          </div>

          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          <div className="agent-list">
            {AGENTS.map((a) => {
              const info = agents[a.key];
              return (
                <div className={`agent-row agent-${info.status}`} key={a.key}>
                  <span className="agent-icon">
                    {info.status === "completed" && "\u2713"}
                    {info.status === "failed" && "\u2717"}
                    {info.status === "running" && "\u25CB"}
                    {info.status === "pending" && "\u2022"}
                  </span>
                  <span className="agent-name">{a.label}</span>
                  <span className="agent-time">
                    {info.time != null ? `${info.time.toFixed(1)}s` : info.status === "running" ? "running..." : ""}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="panel logs">
        <div className="panel-header">
          <h2>Live Logs</h2>
          <span className="mono">{logs.length} lines</span>
        </div>
        <div className="log-window">
          {logs.length === 0 && (
            <div className="log-empty">
              Logs will appear here once the migration starts.
            </div>
          )}
          {logs.map((line, idx) => (
            <div className="log-line" key={`${idx}-${line}`}>
              {line}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>

      <footer>
        <span>Cloudify v2.0.0 — Dedalus SDK + Multi-Model Handoffs</span>
        <span className="mono">Backend: {API_BASE}</span>
      </footer>
    </div>
  );
}
