"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import type { CSSProperties } from "react";

const beforeCommands = [
  "# Manual cloud migration steps...",
  "$ gcloud projects create my-app-prod",
  "$ gcloud services enable run.googleapis.com",
  "$ gcloud services enable artifactregistry.googleapis.com",
  "$ gcloud services enable sqladmin.googleapis.com",
  "$ gcloud artifacts repositories create my-repo \\",
  "    --repository-format=docker --location=us-central1",
  "$ gcloud sql instances create my-db \\",
  "    --database-version=POSTGRES_15 --tier=db-f1-micro",
  "$ gcloud sql databases create app_db -i my-db",
  "# Write Dockerfile manually...",
  "$ docker build -t us-central1-docker.pkg.dev/...",
  "$ docker push us-central1-docker.pkg.dev/...",
  "$ gcloud run deploy backend --image=... \\",
  "    --set-env-vars=DB_HOST=... --allow-unauthenticated",
  "# Update frontend API URLs manually...",
  "$ npm run build",
  "$ firebase init hosting",
  "$ firebase deploy --only hosting",
  "# Debug CORS errors...",
  "# Fix environment variables...",
  "# 3 hours later... maybe it works?",
];

const afterCommands = [
  "$ cloudify migrate --project my-app",
  "",
  "  ✅ Migration complete in 1m 47s",
  "  🌐 https://my-app-abc123.web.app",
];

export default function BeforeAfter() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-24 relative overflow-hidden" ref={ref}>
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-12">
          <span className="bg-accent-green/10 text-accent-green px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider">
            Comparison
          </span>
          <h2 className="font-serif text-[clamp(2rem,4vw,3rem)] text-text-primary mt-4 mb-4">
            Before &amp; After <span className="gradient-text">Cloudify</span>
          </h2>
          <p className="text-text-secondary max-w-xl mx-auto" style={{ textWrap: "balance" } as CSSProperties}>
            Twenty manual commands become one. Hours become minutes.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Before */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6 }}
            className="bg-[#0c0c0c] border border-red-500/20 rounded-2xl overflow-hidden"
          >
            <div className="flex items-center gap-2 px-4 py-3 border-b border-red-500/10 bg-[#0f0f0f]">
              <div className="w-3 h-3 rounded-full bg-red-500/60" />
              <span className="ml-2 text-red-400/80 text-xs font-mono">Without Cloudify</span>
            </div>
            <div className="p-5 font-mono text-xs leading-relaxed max-h-[400px] overflow-y-auto">
              {beforeCommands.map((line, i) => (
                <div key={i} className={line.startsWith("#") ? "text-text-muted/50" : "text-red-400/70"}>
                  {line || "\u00A0"}
                </div>
              ))}
            </div>
            <div className="px-5 py-3 border-t border-red-500/10 bg-red-500/5">
              <span className="text-red-400/80 text-xs font-mono">~3 hours • 20+ commands • error-prone</span>
            </div>
          </motion.div>

          {/* After */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="bg-[#0c0c0c] border border-accent-green/20 rounded-2xl overflow-hidden flex flex-col"
          >
            <div className="flex items-center gap-2 px-4 py-3 border-b border-accent-green/10 bg-[#0f0f0f]">
              <div className="w-3 h-3 rounded-full bg-accent-green/60" />
              <span className="ml-2 text-accent-green/80 text-xs font-mono">With Cloudify</span>
            </div>
            <div className="p-5 font-mono text-sm leading-relaxed flex-1 flex items-center">
              <div>
                {afterCommands.map((line, i) => (
                  <div
                    key={i}
                    className={
                      i === 0
                        ? "text-accent-green"
                        : line.includes("✅")
                        ? "text-accent-green font-bold"
                        : line.includes("🌐")
                        ? "text-accent-purple-light"
                        : "text-text-secondary"
                    }
                  >
                    {line || "\u00A0"}
                  </div>
                ))}
              </div>
            </div>
            <div className="px-5 py-3 border-t border-accent-green/10 bg-accent-green/5">
              <span className="text-accent-green/80 text-xs font-mono">~2 minutes • 1 command • fully automated</span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
