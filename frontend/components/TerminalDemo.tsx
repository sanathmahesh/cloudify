"use client";

import { motion, useInView } from "framer-motion";
import { useRef, useState, useEffect, useCallback } from "react";

const terminalLines = [
  { text: "$ cloudify migrate --project my-app", type: "command" as const, delay: 0 },
  { text: "", type: "blank" as const, delay: 1200 },
  { text: "  Cloudify v1.0.0 — AI-Powered Cloud Migration", type: "header" as const, delay: 1400 },
  { text: "", type: "blank" as const, delay: 1600 },
  { text: "  [1/5] Analyzing codebase...", type: "step" as const, delay: 1800 },
  { text: "        ✓ Detected Spring Boot 3.2 backend", type: "success" as const, delay: 2400 },
  { text: "        ✓ Detected React 18 frontend (Vite)", type: "success" as const, delay: 2800 },
  { text: "        ✓ Detected H2 database → Cloud SQL", type: "success" as const, delay: 3200 },
  { text: "", type: "blank" as const, delay: 3400 },
  { text: "  [2/5] Provisioning GCP infrastructure...", type: "step" as const, delay: 3600 },
  { text: "        ✓ Cloud Run service created", type: "success" as const, delay: 4200 },
  { text: "        ✓ Artifact Registry configured", type: "success" as const, delay: 4600 },
  { text: "        ✓ Firebase Hosting initialized", type: "success" as const, delay: 5000 },
  { text: "", type: "blank" as const, delay: 5200 },
  { text: "  [3/5] Migrating database...", type: "step" as const, delay: 5400 },
  { text: "        ✓ Cloud SQL instance provisioned", type: "success" as const, delay: 6000 },
  { text: "        ✓ Schema migrated (12 tables)", type: "success" as const, delay: 6400 },
  { text: "", type: "blank" as const, delay: 6600 },
  { text: "  [4/5] Building & deploying backend...", type: "step" as const, delay: 6800 },
  { text: "        ✓ Dockerfile generated (multi-stage)", type: "success" as const, delay: 7400 },
  { text: "        ✓ Image built & pushed", type: "success" as const, delay: 7800 },
  { text: "        ✓ Deployed to Cloud Run", type: "success" as const, delay: 8200 },
  { text: "", type: "blank" as const, delay: 8400 },
  { text: "  [5/5] Deploying frontend...", type: "step" as const, delay: 8600 },
  { text: "        ✓ API endpoints updated", type: "success" as const, delay: 9000 },
  { text: "        ✓ Production build complete", type: "success" as const, delay: 9400 },
  { text: "        ✓ Deployed to Firebase Hosting", type: "success" as const, delay: 9800 },
  { text: "", type: "blank" as const, delay: 10000 },
  { text: "  ══════════════════════════════════════════", type: "divider" as const, delay: 10200 },
  { text: "  ✅ Migration complete in 1m 47s", type: "final" as const, delay: 10400 },
  { text: "  🌐 https://my-app-abc123.web.app", type: "url" as const, delay: 10800 },
  { text: "  ══════════════════════════════════════════", type: "divider" as const, delay: 11000 },
];

function getLineColor(type: string) {
  switch (type) {
    case "command": return "text-accent-green";
    case "header": return "text-accent-purple-light";
    case "step": return "text-text-primary font-semibold";
    case "success": return "text-accent-green/80";
    case "final": return "text-accent-green font-bold";
    case "url": return "text-accent-purple-light";
    case "divider": return "text-text-muted/40";
    default: return "text-text-secondary";
  }
}

export default function TerminalDemo() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const [visibleLines, setVisibleLines] = useState(0);
  const [typedCommand, setTypedCommand] = useState("");
  const [isTyping, setIsTyping] = useState(true);
  const command = terminalLines[0].text;

  const typeCommand = useCallback(() => {
    let i = 0;
    setIsTyping(true);
    const interval = setInterval(() => {
      i++;
      setTypedCommand(command.slice(0, i));
      if (i >= command.length) {
        clearInterval(interval);
        setIsTyping(false);
        // Start revealing lines after command is typed
        let lineIndex = 1;
        const lineInterval = setInterval(() => {
          lineIndex++;
          setVisibleLines(lineIndex);
          if (lineIndex >= terminalLines.length) {
            clearInterval(lineInterval);
          }
        }, 200);
      }
    }, 50);
    return () => clearInterval(interval);
  }, [command]);

  useEffect(() => {
    if (isInView) {
      typeCommand();
    }
  }, [isInView, typeCommand]);

  return (
    <section className="py-24 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[20%] right-[-5%] w-[400px] h-[400px] rounded-full bg-accent-purple/8 blur-[100px] animate-float-blob-delayed" />
      </div>
      <div className="max-w-4xl mx-auto px-6" ref={ref}>
        <div className="text-center mb-12">
          <span className="bg-accent-purple/10 text-accent-purple px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider">
            Live Demo
          </span>
          <h2 className="font-serif text-[clamp(2rem,4vw,3rem)] text-text-primary mt-4 mb-4">
            See It in <span className="gradient-text">Action</span>
          </h2>
          <p className="text-text-secondary max-w-xl mx-auto" style={{ textWrap: "balance" } as React.CSSProperties}>
            One command. Five AI agents. Your app in the cloud.
          </p>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="bg-[#0c0c0c] border border-border-subtle rounded-2xl overflow-hidden shadow-2xl shadow-accent-purple/5"
        >
          {/* Terminal header */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border-subtle bg-[#0f0f0f]">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
            <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
            <div className="w-3 h-3 rounded-full bg-[#28c840]" />
            <span className="ml-3 text-text-muted text-xs font-mono">cloudify — bash</span>
          </div>

          {/* Terminal body */}
          <div className="p-6 font-mono text-sm leading-relaxed min-h-[420px] overflow-hidden">
            {/* Typing command line */}
            <div className={getLineColor("command")}>
              {typedCommand}
              {isTyping && (
                <span className="inline-block w-2 h-4 bg-accent-green ml-0.5 align-middle animate-blink" />
              )}
            </div>

            {/* Revealed lines */}
            {terminalLines.slice(1, visibleLines).map((line, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.15 }}
                className={`${getLineColor(line.type)} ${line.type === "blank" ? "h-4" : ""}`}
              >
                {line.text}
              </motion.div>
            ))}

            {/* Cursor at end */}
            {!isTyping && visibleLines < terminalLines.length && (
              <span className="inline-block w-2 h-4 bg-text-secondary/60 animate-blink" />
            )}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
