import { useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const sampleArgs = `--source-path /path/to/app \\
--gcp-project your-project-id \\
--region us-central1 \\
--mode automated`;

export default function App() {
  const [args, setArgs] = useState(sampleArgs);
  const [status, setStatus] = useState("idle");
  const [migrationId, setMigrationId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const logEndRef = useRef(null);

  const canRun = useMemo(() => status !== "running", [status]);

  const appendLog = (line) => {
    setLogs((prev) => {
      const next = [...prev, line];
      return next.slice(-2000);
    });
  };

  const startMigration = async () => {
    setError(null);
    setLogs([]);
    setStatus("starting");

    try {
      const response = await fetch(`${API_BASE}/api/migrations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ args })
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

      eventSource.onmessage = (event) => {
        appendLog(event.data);
        requestAnimationFrame(() => {
          logEndRef.current?.scrollIntoView({ behavior: "smooth" });
        });

        if (event.data === "[SYSTEM] EOF") {
          eventSource.close();
          setStatus("completed");
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
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
          <p className="eyebrow">Cloudify Console</p>
          <h1>Run migrations. Watch logs live.</h1>
          <p className="subhead">
            Paste CLI arguments below, kick off the migration, and stream logs in
            real time.
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
          <button
            className="primary"
            onClick={startMigration}
            disabled={!canRun}
          >
            {status === "running" ? "Running..." : "Run Migration"}
          </button>
        </div>
        <textarea
          value={args}
          onChange={(e) => setArgs(e.target.value)}
          placeholder="Enter CLI args for migration_orchestrator.py migrate"
          rows={6}
        />
        <p className="hint">
          Tip: This content is passed to `python migration_orchestrator.py
          migrate` on the server.
        </p>
        {error && <div className="error">{error}</div>}
      </div>

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
        <span>Output endpoints are determined by your Cloudify config.</span>
        <span className="mono">Backend: {API_BASE}</span>
      </footer>
    </div>
  );
}
