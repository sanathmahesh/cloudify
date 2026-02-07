"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView, useScroll, useMotionValue, useMotionValueEvent, useSpring } from "framer-motion";
import type { CSSProperties } from "react";

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
  const [activeIndex, setActiveIndex] = useState(0);
  const sectionRef = useRef(null);
  const stepsRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const lineRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const activeIndexRef = useRef(0);
  const layoutRef = useRef({
    stepCenters: [] as number[],
    indicatorOffsets: [] as number[],
    lineHeight: 0,
  });
  const [panelHeight, setPanelHeight] = useState(0);
  const [indicatorOffsets, setIndicatorOffsets] = useState<number[]>([]);
  const progress = useMotionValue(0);
  const dotY = useMotionValue(0);
  const smoothProgress = useSpring(progress, { stiffness: 160, damping: 26, mass: 0.8 });
  const smoothDotY = useSpring(dotY, { stiffness: 200, damping: 28, mass: 0.8 });

  const { scrollY } = useScroll();

  const updateFromScroll = (latest: number) => {
    const { stepCenters, indicatorOffsets: indicatorOffsetsRef, lineHeight } = layoutRef.current;
    if (!stepCenters.length) return;
    const marker = latest + window.innerHeight * 0.5;
    let idx = 0;
    for (let i = 0; i < stepCenters.length; i += 1) {
      if (marker >= stepCenters[i]) idx = i;
    }
    if (idx !== activeIndexRef.current) {
      activeIndexRef.current = idx;
      setActiveIndex(idx);
    }
    const fallbackSpacing = lineHeight > 0 ? lineHeight / Math.max(steps.length - 1, 1) : 0;
    const targetY = indicatorOffsetsRef[idx] ?? idx * fallbackSpacing;
    const radius = 4;
    const clampedDotY = Math.max(0, Math.min(targetY - radius, Math.max(lineHeight - radius * 2, 0)));
    dotY.set(clampedDotY);
    progress.set(lineHeight === 0 ? 0 : targetY / lineHeight);
  };

  const measureLayout = () => {
    const stepsEl = stepsRef.current;
    if (!stepsEl) return;
    const rect = stepsEl.getBoundingClientRect();
    const stepNodes = Array.from(stepsEl.children) as HTMLElement[];
    layoutRef.current.stepCenters = stepNodes.map((node) => {
      const rect = node.getBoundingClientRect();
      return rect.top + rect.height / 2 + window.scrollY;
    });
    if (rect.height) {
      setPanelHeight(rect.height);
    }
    if (lineRef.current) {
      const lineRect = lineRef.current.getBoundingClientRect();
      layoutRef.current.lineHeight = lineRect.height;
      const offsets = stepNodes.map((node) => {
        const rect = node.getBoundingClientRect();
        const centerY = rect.top + rect.height / 2;
        const offset = centerY - lineRect.top;
        return Math.max(0, Math.min(offset, lineRect.height));
      });
      layoutRef.current.indicatorOffsets = offsets;
      setIndicatorOffsets(offsets);
    }
    updateFromScroll(scrollY.get());
  };

  useEffect(() => {
    measureLayout();
    const ro = new ResizeObserver(measureLayout);
    if (stepsRef.current) ro.observe(stepsRef.current);
    if (panelRef.current) ro.observe(panelRef.current);
    if (listRef.current) ro.observe(listRef.current);
    window.addEventListener("resize", measureLayout);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measureLayout);
    };
  }, []);

  useMotionValueEvent(scrollY, "change", (latest) => {
    updateFromScroll(latest);
  });

  return (
    <section className="py-24 relative overflow-hidden" ref={sectionRef}>
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="bg-accent-purple/10 text-accent-purple px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider">
            How It Works
          </span>
          <h2 className="font-serif text-[clamp(2rem,4vw,3rem)] text-text-primary mt-4 mb-4">
            Five Steps to the <span className="gradient-text">Cloud</span>
          </h2>
          <p className="text-text-secondary max-w-xl mx-auto" style={{ textWrap: "balance" } as CSSProperties}>
            From local development to production deployment, fully automated.
          </p>
        </div>

        <div className="grid lg:grid-cols-[1.05fr_1fr] gap-12 lg:gap-16 items-start">
          {/* Sticky diagram */}
          <motion.div
            ref={panelRef}
            className="relative self-start"
            style={
              panelHeight
                ? ({ "--panel-height": `${panelHeight}px` } as CSSProperties)
                : undefined
            }
          >
            <div className="relative bg-bg-card/60 border border-border-subtle rounded-3xl p-8 overflow-hidden flex flex-col lg:min-h-[var(--panel-height)]">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(98,20,217,0.12),transparent_60%)]" />
              <div className="relative flex flex-col flex-1">
                <div className="flex items-center justify-between mb-6">
                  <span className="text-xs font-mono text-accent-purple">LIVE FLOW</span>
                  <span className="text-xs text-text-muted">Step {activeIndex + 1} of {steps.length}</span>
                </div>

                <div className="relative pl-6 flex-1">
                  <div ref={lineRef} className="absolute left-2 top-1 bottom-1 w-px overflow-visible">
                    <div className="absolute inset-0 bg-border-subtle" />
                    <motion.div
                      className="absolute inset-0 bg-gradient-to-b from-accent-purple to-accent-green"
                      style={{ scaleY: smoothProgress, transformOrigin: "top" }}
                    />
                    <motion.div
                      className="absolute left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-accent-green"
                      style={{ y: smoothDotY }}
                    />
                  </div>

                  <div
                    ref={listRef}
                    className="space-y-6 lg:space-y-0 lg:relative lg:h-full"
                  >
                    {steps.map((step, idx) => {
                      const isActive = idx === activeIndex;
                      const top = indicatorOffsets[idx];
                      const style = top === undefined ? undefined : { top, transform: "translateY(-50%)" };
                      return (
                        <div
                          key={step.num}
                          className="flex items-center gap-4 lg:absolute lg:left-0"
                          style={style}
                        >
                          <motion.div
                            className={`w-3 h-3 rounded-full ${isActive ? "bg-accent-green" : "bg-border-subtle"}`}
                            animate={isActive ? { scale: [1, 1.4, 1] } : { scale: 1 }}
                            transition={{ duration: 1.2, repeat: isActive ? Infinity : 0 }}
                          />
                          <div className="space-y-1">
                            <div
                              className={`text-sm font-mono leading-relaxed ${
                                isActive ? "text-text-primary" : "text-text-muted"
                              }`}
                            >
                              {step.highlight}
                            </div>
                            <div className="text-[10px] uppercase tracking-wider text-text-muted">Step {step.num}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="mt-8 rounded-2xl bg-bg-primary/40 border border-border-subtle p-4">
                  <div className="text-xs font-mono text-text-muted">$ cloudify migrate --project my-app</div>
                  <div className="text-xs font-mono text-text-primary mt-3">
                    <span className="text-accent-purple">[{activeIndex + 1}/5]</span> {steps[activeIndex].title}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Scrollable steps */}
          <div ref={stepsRef} className="space-y-12">
            {steps.map((step, i) => (
              <StepItem
                key={step.num}
                step={step}
                index={i}
                activeIndex={activeIndex}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function StepItem({
  step,
  index,
  activeIndex,
}: {
  step: (typeof steps)[number];
  index: number;
  activeIndex: number;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { margin: "-40% 0px -40% 0px" });
  const isActive = index === activeIndex;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`rounded-2xl border p-6 md:p-8 transition-colors duration-300 ${
        isActive
          ? "border-accent-purple/40 bg-accent-purple/10"
          : "border-border-subtle bg-bg-card/30"
      }`}
    >
      <span className="text-xs font-mono text-accent-purple mb-2 block">{step.num}</span>
      <h3 className="text-text-primary text-xl font-semibold mb-3">{step.title}</h3>
      <p className="text-text-secondary leading-relaxed text-sm">{step.description}</p>
    </motion.div>
  );
}
