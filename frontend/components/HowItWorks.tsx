"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

const steps = [
  {
    num: "01",
    title: "Analyze Your Codebase",
    description:
      "The Code Analysis Agent scans your Spring Boot properties, React configuration, database setup, and API endpoints to build a complete migration plan.",
    highlight: "Code Analyzer",
  },
  {
    num: "02",
    title: "Provision Infrastructure",
    description:
      "The Infrastructure Agent creates Cloud Run services, Artifact Registry repos, Cloud SQL instances, and Firebase projects — all configured with proper IAM policies.",
    highlight: "Infrastructure",
  },
  {
    num: "03",
    title: "Migrate Your Database",
    description:
      "The Database Agent handles schema migration from H2 to Cloud SQL PostgreSQL, transfers data, and updates connection strings across your app.",
    highlight: "Database",
  },
  {
    num: "04",
    title: "Deploy Backend & Frontend",
    description:
      "Dedicated agents generate optimized Dockerfiles, build container images, deploy to Cloud Run, update API endpoints, and ship your frontend to Firebase Hosting.",
    highlight: "Backend + Frontend",
  },
  {
    num: "05",
    title: "Verify & Go Live",
    description:
      "The Orchestrator confirms all services are healthy, runs smoke tests, and provides you with your live production URLs. Your app is in the cloud.",
    highlight: "Orchestrator",
  },
];

export default function HowItWorks() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  });

  const progressHeight = useTransform(scrollYProgress, [0.1, 0.9], ["0%", "100%"]);

  return (
    <section className="py-24 relative overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="bg-accent-purple/10 text-accent-purple px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider">
            How It Works
          </span>
          <h2 className="font-serif text-[clamp(2rem,4vw,3rem)] text-text-primary mt-4 mb-4">
            Five Steps to the <span className="gradient-text">Cloud</span>
          </h2>
          <p className="text-text-secondary max-w-xl mx-auto" style={{ textWrap: "balance" } as React.CSSProperties}>
            From local development to production deployment, fully automated.
          </p>
        </div>

        <div ref={containerRef} className="relative">
          {/* Vertical progress line */}
          <div className="absolute left-8 md:left-1/2 top-0 bottom-0 w-px bg-border-subtle md:-translate-x-px">
            <motion.div
              className="w-full bg-gradient-to-b from-accent-purple to-accent-green"
              style={{ height: progressHeight }}
            />
          </div>

          {/* Steps */}
          <div className="space-y-16 md:space-y-24">
            {steps.map((step, i) => (
              <StepItem key={step.num} step={step} index={i} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function StepItem({ step, index }: { step: (typeof steps)[number]; index: number }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "center center"],
  });
  const opacity = useTransform(scrollYProgress, [0, 1], [0.3, 1]);
  const y = useTransform(scrollYProgress, [0, 1], [40, 0]);

  const isLeft = index % 2 === 0;

  return (
    <motion.div
      ref={ref}
      style={{ opacity, y }}
      className={`relative grid md:grid-cols-2 gap-8 md:gap-16 items-center ${
        isLeft ? "" : "md:direction-rtl"
      }`}
    >
      {/* Timeline dot */}
      <div className="absolute left-8 md:left-1/2 w-4 h-4 rounded-full bg-accent-purple border-4 border-bg-primary -translate-x-1/2 z-10" />

      {/* Content */}
      <div className={`pl-20 md:pl-0 ${isLeft ? "md:pr-16 md:text-right" : "md:pl-16 md:text-left md:col-start-2"}`} style={{ direction: "ltr" }}>
        <span className="text-xs font-mono text-accent-purple mb-2 block">{step.num}</span>
        <h3 className="text-text-primary text-xl font-semibold mb-3">{step.title}</h3>
        <p className="text-text-secondary leading-relaxed text-sm">{step.description}</p>
      </div>

      {/* Visual indicator */}
      <div className={`hidden md:flex ${isLeft ? "md:col-start-2 justify-start pl-16" : "justify-end pr-16"}`} style={{ direction: "ltr" }}>
        <div className="bg-bg-card border border-border-subtle rounded-2xl px-6 py-4 inline-flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-accent-green animate-pulse" />
          <span className="text-text-primary text-sm font-mono">{step.highlight}</span>
        </div>
      </div>
    </motion.div>
  );
}
