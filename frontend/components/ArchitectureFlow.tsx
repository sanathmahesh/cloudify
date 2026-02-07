"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import type { CSSProperties } from "react";

const nodes = [
  {
    label: "Code Analyzer",
    icon: "🔍",
    borderClass: "border-accent-purple/30",
    glow: "rgba(98, 20, 217, 0.35)",
  },
  {
    label: "Infrastructure",
    icon: "☁️",
    borderClass: "border-accent-purple-light/30",
    glow: "rgba(124, 58, 237, 0.35)",
  },
  {
    label: "Database",
    icon: "🗄️",
    borderClass: "border-accent-green/30",
    glow: "rgba(26, 255, 117, 0.35)",
  },
  {
    label: "Backend",
    icon: "⚙️",
    borderClass: "border-accent-purple/30",
    glow: "rgba(98, 20, 217, 0.35)",
  },
  {
    label: "Frontend",
    icon: "🎨",
    borderClass: "border-accent-green/30",
    glow: "rgba(26, 255, 117, 0.35)",
  },
];

export default function ArchitectureFlow() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-24 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[30%] left-[-5%] w-[300px] h-[300px] rounded-full bg-accent-purple/6 blur-[100px]" />
        <div className="absolute bottom-[20%] right-[-5%] w-[300px] h-[300px] rounded-full bg-accent-green/4 blur-[100px]" />
      </div>

      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="bg-accent-purple/10 text-accent-purple px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider">
            Architecture
          </span>
          <h2 className="font-serif text-[clamp(2rem,4vw,3rem)] text-text-primary mt-4 mb-4">
            The Agent <span className="gradient-text">Pipeline</span>
          </h2>
          <p className="text-text-secondary max-w-xl mx-auto" style={{ textWrap: "balance" } as CSSProperties}>
            Data flows through five specialized agents, each handling a critical phase of migration.
          </p>
        </div>

        {/* Flow visualization */}
        <div className="relative">
          {/* Connection line */}
          <div className="absolute top-1/2 left-0 right-0 h-px bg-border-subtle hidden md:block" />
          <motion.div
            className="absolute top-1/2 left-0 h-px bg-gradient-to-r from-accent-purple to-accent-green hidden md:block"
            initial={{ width: "0%" }}
            animate={isInView ? { width: "100%" } : { width: "0%" }}
            transition={{ duration: 2, ease: "easeOut", delay: 0.5 }}
          />
          <motion.div
            className="absolute top-1/2 -translate-y-1/2 left-0 w-2.5 h-2.5 rounded-full bg-accent-green/90 blur-[1px] hidden md:block"
            initial={{ x: 0, opacity: 0 }}
            animate={isInView ? { x: "calc(100% - 10px)", opacity: [0, 1, 1, 0] } : { opacity: 0 }}
            transition={{ duration: 4, ease: "linear", repeat: Infinity, repeatDelay: 1 }}
          />

          <div className="grid grid-cols-2 md:grid-cols-5 gap-6 md:gap-4 relative z-10">
            {nodes.map((node, i) => (
              <motion.div
                key={node.label}
                initial={{ opacity: 0, y: 30 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: 0.3 + i * 0.2 }}
                className="flex flex-col items-center"
              >
                {/* Node circle */}
                <motion.div
                  className={`w-16 h-16 rounded-full bg-bg-card border-2 ${node.borderClass} flex items-center justify-center text-2xl mb-3 relative`}
                  animate={
                    isInView
                      ? {
                          boxShadow: [
                            `0 0 0px rgba(0, 0, 0, 0)`,
                            `0 0 24px ${node.glow}`,
                            `0 0 0px rgba(0, 0, 0, 0)`,
                          ],
                        }
                      : {}
                  }
                  transition={{
                    duration: 2,
                    delay: 0.5 + i * 0.4,
                    repeat: Infinity,
                    repeatDelay: 3,
                  }}
                >
                  <span>{node.icon}</span>
                </motion.div>

                {/* Step number */}
                <span className="text-xs font-mono text-accent-purple mb-1">
                  0{i + 1}
                </span>

                {/* Label */}
                <span className="text-text-primary text-sm font-medium text-center">
                  {node.label}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
