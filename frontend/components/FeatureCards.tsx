"use client";

import AnimateOnScroll from "./AnimateOnScroll";
import CardSpotlight from "./CardSpotlight";

const features = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a4 4 0 0 1 4 4c0 1.5-.8 2.8-2 3.5V11h3a3 3 0 0 1 3 3v1" />
        <path d="M8 9.5C6.8 8.8 6 7.5 6 6a4 4 0 0 1 4-4" />
        <path d="M12 11v4" />
        <path d="M7 18a3 3 0 0 1-3-3v-1" />
        <circle cx="12" cy="19" r="3" />
      </svg>
    ),
    title: "AI-Powered Analysis",
    description:
      "Claude AI scans your codebase, detects configurations, and generates a tailored migration plan automatically.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 17 10 11 4 5" />
        <line x1="12" y1="19" x2="20" y2="19" />
      </svg>
    ),
    title: "One Command Deploy",
    description:
      "Migrate your entire stack — backend, frontend, and database — with a single CLI command. Zero manual config.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <polyline points="9 12 11 14 15 10" />
      </svg>
    ),
    title: "Safe & Reversible",
    description:
      "Dry-run mode, automatic backups, and interactive approvals ensure nothing breaks. Roll back anytime.",
  },
];

export default function FeatureCards() {
  return (
    <section id="features" className="py-24">
      <div className="max-w-7xl mx-auto px-6">
        <AnimateOnScroll>
          <div className="text-center mb-16">
            <span className="bg-accent-purple/10 text-accent-purple px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider">
              Features
            </span>
            <h2 className="font-serif text-[clamp(2rem,4vw,3rem)] text-text-primary mt-4 mb-4">
              Why <span className="gradient-text">Cloudify</span>?
            </h2>
            <p className="text-text-secondary max-w-2xl mx-auto">
              Three pillars that make cloud migration effortless.
            </p>
          </div>
        </AnimateOnScroll>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <AnimateOnScroll key={feature.title} delay={i * 0.1}>
              <CardSpotlight className="bg-bg-card border border-border-subtle rounded-3xl p-8 md:p-10 hover:border-accent-purple/30 transition-colors duration-300 h-full">
                <div className="relative z-10">
                  <div className="w-12 h-12 rounded-2xl bg-accent-purple/10 flex items-center justify-center mb-6 text-accent-purple">
                    {feature.icon}
                  </div>
                  <h3 className="text-text-primary text-xl font-semibold mb-3">
                    {feature.title}
                  </h3>
                  <p className="text-text-secondary leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </CardSpotlight>
            </AnimateOnScroll>
          ))}
        </div>
      </div>
    </section>
  );
}
