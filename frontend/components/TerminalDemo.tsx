"use client";

import { motion, useInView } from "framer-motion";
import { useRef, useState, useEffect } from "react";
import type { CSSProperties } from "react";

type TerminalLine =
  | { type: "command"; text: string }
  | { type: "blank"; text?: string; delay: number }
  | { type: "header"; text: string; delay: number }
  | { type: "step"; text: string; delay: number }
  | { type: "success"; text: string; delay: number }
  | { type: "divider"; text: string; delay: number }
  | { type: "final"; text: string; delay: number }
  | { type: "url"; text: string; delay: number }
  | { type: "progress"; delay: number; duration?: number };

const terminalLines: TerminalLine[] = [
  { text: "$ cloudify migrate --project my-app", type: "command" },
  { text: "", type: "blank", delay: 200 },
  { text: "  Cloudify v1.0.0 — AI-Powered Cloud Migration", type: "header", delay: 400 },
  { text: "", type: "blank", delay: 700 },
  { text: "  [1/5] Analyzing codebase...", type: "step", delay: 900 },
  { type: "progress", delay: 1100, duration: 1.2 },
  { text: "        ✓ Detected Spring Boot 3.2 backend", type: "success", delay: 2300 },
  { text: "        ✓ Detected React 18 frontend (Vite)", type: "success", delay: 2600 },
  { text: "        ✓ Detected H2 database → Cloud SQL", type: "success", delay: 2900 },
  { text: "", type: "blank", delay: 3100 },
  { text: "  [2/5] Provisioning GCP infrastructure...", type: "step", delay: 3300 },
  { type: "progress", delay: 3500, duration: 1.2 },
  { text: "        ✓ Cloud Run service created", type: "success", delay: 4800 },
  { text: "        ✓ Artifact Registry configured", type: "success", delay: 5100 },
  { text: "        ✓ Firebase Hosting initialized", type: "success", delay: 5400 },
  { text: "", type: "blank", delay: 5600 },
  { text: "  [3/5] Migrating database...", type: "step", delay: 5800 },
  { type: "progress", delay: 6000, duration: 1.1 },
  { text: "        ✓ Cloud SQL instance provisioned", type: "success", delay: 7200 },
  { text: "        ✓ Schema migrated (12 tables)", type: "success", delay: 7500 },
  { text: "", type: "blank", delay: 7700 },
  { text: "  [4/5] Building & deploying backend...", type: "step", delay: 7900 },
  { type: "progress", delay: 8100, duration: 1.2 },
  { text: "        ✓ Dockerfile generated (multi-stage)", type: "success", delay: 9400 },
  { text: "        ✓ Image built & pushed", type: "success", delay: 9700 },
  { text: "        ✓ Deployed to Cloud Run", type: "success", delay: 10000 },
  { text: "", type: "blank", delay: 10200 },
  { text: "  [5/5] Deploying frontend...", type: "step", delay: 10400 },
  { type: "progress", delay: 10600, duration: 1.2 },
  { text: "        ✓ API endpoints updated", type: "success", delay: 11900 },
  { text: "        ✓ Production build complete", type: "success", delay: 12200 },
  { text: "        ✓ Deployed to Firebase Hosting", type: "success", delay: 12500 },
  { text: "", type: "blank", delay: 12700 },
  { text: "  ══════════════════════════════════════════", type: "divider", delay: 12900 },
  { text: "  ✅ Migration complete in 1m 47s", type: "final", delay: 13100 },
  { text: "  🌐 https://my-app-abc123.web.app", type: "url", delay: 13400 },
  { text: "  ══════════════════════════════════════════", type: "divider", delay: 13600 },
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
  const command = terminalLines[0].type === "command" ? terminalLines[0].text : "";

  useEffect(() => {
    if (isInView) {
      let cancelled = false;
      const timeouts: Array<ReturnType<typeof setTimeout>> = [];
      setTypedCommand("");
      setVisibleLines(0);
      setIsTyping(true);

      let i = 0;
      const interval = setInterval(() => {
        i++;
        setTypedCommand(command.slice(0, i));
        if (i >= command.length) {
          clearInterval(interval);
          setIsTyping(false);
          terminalLines.slice(1).forEach((line, idx) => {
            if ("delay" in line) {
              const timeout = setTimeout(() => {
                if (cancelled) return;
                setVisibleLines((prev) => Math.max(prev, idx + 1));
              }, line.delay);
              timeouts.push(timeout);
            }
          });
        }
      }, 45);

      return () => {
        cancelled = true;
        clearInterval(interval);
        timeouts.forEach(clearTimeout);
      };
    }
  }, [isInView, command]);

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
          <p className="text-text-secondary max-w-xl mx-auto" style={{ textWrap: "balance" } as CSSProperties}>
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
            {terminalLines.slice(1, visibleLines + 1).map((line, i) => {
              if (line.type === "progress") {
                return (
                  <motion.div
                    key={`progress-${i}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2 }}
                    className="my-2"
                  >
                    <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-accent-purple to-accent-green"
                        initial={{ width: "0%" }}
                        animate={{ width: "100%" }}
                        transition={{ duration: line.duration ?? 1.2, ease: "easeOut" }}
                      />
                    </div>
                  </motion.div>
                );
              }

              return (
                <motion.div
                  key={`line-${i}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.15 }}
                  className={`${getLineColor(line.type)} ${line.type === "blank" ? "h-4" : ""}`}
                >
                  {"text" in line ? line.text : ""}
                </motion.div>
              );
            })}

            {/* Cursor at end */}
            {!isTyping && visibleLines < terminalLines.length - 1 && (
              <span className="inline-block w-2 h-4 bg-text-secondary/60 animate-blink" />
            )}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
