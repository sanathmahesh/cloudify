"use client";

import { motion } from "framer-motion";
import AnimateOnScroll from "./AnimateOnScroll";
import CardSpotlight from "./CardSpotlight";

const agents = [
  {
    num: "01",
    title: "Event-Driven Orchestration",
    description:
      "Agents coordinate via pub-sub event bus for parallel execution and clear dependency management. The brain of the operation.",
    showDiagram: true,
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
      </svg>
    ),
  },
  {
    num: "02",
    title: "Code Analysis",
    description:
      "Scans Spring Boot properties, detects databases, identifies API endpoints and CORS settings.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
  },
  {
    num: "03",
    title: "Infrastructure Provisioning",
    description:
      "Creates Cloud Run services, Artifact Registry, Firebase projects, and configures IAM — all automated.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
      </svg>
    ),
  },
  {
    num: "04",
    title: "Database Migration",
    description:
      "Keeps H2 for dev or migrates to Cloud SQL (PostgreSQL). Handles schema and data transfer.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      </svg>
    ),
  },
  {
    num: "05",
    title: "Backend Deployment",
    description:
      "Generates optimized multi-stage Dockerfiles, builds images, and deploys to Cloud Run.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
      </svg>
    ),
  },
  {
    num: "06",
    title: "Frontend Deployment",
    description:
      "Detects Vite or CRA, updates API endpoints, builds production bundles, deploys to Firebase Hosting.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    ),
  },
];

export default function AgentCards() {
  const cardSpan = "col-span-1";
  const cardHeight = "h-[320px] lg:h-[340px]";

  return (
    <section id="agents" className="py-24">
      <div className="max-w-7xl mx-auto px-6">
        <AnimateOnScroll>
          <div className="text-center mb-16">
            <span className="bg-accent-purple/10 text-accent-purple px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider">
              Agents
            </span>
            <h2 className="font-serif text-[clamp(2rem,4vw,3rem)] text-text-primary mt-4 mb-4">
              Meet the <span className="gradient-text">Agents</span>
            </h2>
            <p className="text-text-secondary max-w-2xl mx-auto">
              Six specialized AI agents work together to migrate your entire
              stack.
            </p>
          </div>
        </AnimateOnScroll>

        {/* Bento grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:auto-rows-[minmax(0,1fr)] lg:grid-flow-row-dense">
          {agents.map((agent, i) => (
            <AnimateOnScroll key={agent.title} delay={i * 0.08}>
              <motion.div
                whileHover={{ y: -4 }}
                transition={{ duration: 0.2 }}
                className={cardSpan}
              >
                <CardSpotlight
                  className={`bg-bg-card border border-border-subtle rounded-3xl p-8 cursor-default group hover:border-accent-purple/30 transition-colors duration-300 h-full ${cardHeight} ${
                    agent.showDiagram ? "bg-gradient-to-br from-bg-card to-accent-purple/5" : ""
                  }`}
                >
                  <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                        agent.showDiagram ? "bg-accent-purple/20 text-accent-purple-light" : "bg-accent-purple/10 text-accent-purple"
                      }`}>
                        {agent.icon}
                      </div>
                      <span className="text-xl font-mono text-accent-purple">
                        {agent.num}
                      </span>
                    </div>
                    <h3 className={`text-text-primary font-semibold mb-3 ${
                      agent.showDiagram ? "text-xl" : "text-lg"
                    }`}>
                      {agent.title}
                    </h3>
                    <p className="text-text-secondary text-sm leading-relaxed">
                      {agent.description}
                    </p>

                    {agent.showDiagram && <OrchestratorDiagram />}
                  </div>
                </CardSpotlight>
              </motion.div>
            </AnimateOnScroll>
          ))}
        </div>
      </div>
    </section>
  );
}

function OrchestratorDiagram() {
  const pipeline = [
    { label: "Analyze", abbr: "AN", color: "text-accent-purple", border: "border-accent-purple/40" },
    { label: "Infra", abbr: "IN", color: "text-accent-purple-light", border: "border-accent-purple-light/40" },
    { label: "DB", abbr: "DB", color: "text-accent-green", border: "border-accent-green/40" },
    { label: "Backend", abbr: "BE", color: "text-accent-purple", border: "border-accent-purple/40" },
    { label: "Frontend", abbr: "FE", color: "text-accent-green", border: "border-accent-green/40" },
  ];

  return (
    <div className="mt-6 relative rounded-2xl border border-border-subtle bg-bg-primary/40 p-4 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(98,20,217,0.12),transparent_60%)]" />
      <div className="absolute top-1/2 left-6 right-6 h-px bg-border-subtle" />
      <motion.div
        className="absolute top-1/2 left-6 h-px bg-gradient-to-r from-accent-purple to-accent-green"
        initial={{ width: 0 }}
        animate={{ width: "calc(100% - 48px)" }}
        transition={{ duration: 2, repeat: Infinity, repeatDelay: 2, ease: "easeOut" }}
      />
      <motion.div
        className="absolute top-1/2 left-6 w-2.5 h-2.5 rounded-full bg-accent-green/80 -translate-y-1/2"
        animate={{ x: "calc(100% - 64px)", opacity: [0, 1, 1, 0] }}
        transition={{ duration: 3.5, repeat: Infinity, repeatDelay: 1, ease: "linear" }}
      />
      <div className="relative flex items-center justify-between gap-2">
        {pipeline.map((node) => (
          <div key={node.label} className="flex flex-col items-center gap-2">
            <div className={`w-8 h-8 rounded-full border ${node.border} bg-bg-card flex items-center justify-center`}>
              <span className={`text-[10px] font-mono ${node.color}`}>{node.abbr}</span>
            </div>
            <span className="text-[10px] uppercase tracking-wide text-text-muted">{node.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
