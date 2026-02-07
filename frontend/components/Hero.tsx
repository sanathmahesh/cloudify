"use client";

import { motion, type Variants } from "framer-motion";

const container: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15 },
  },
};

const item: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" as const } },
};

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Gradient mesh blobs */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-accent-purple/15 blur-[120px] animate-float-blob" />
        <div className="absolute top-[10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-accent-green/10 blur-[120px] animate-float-blob-delayed" />
        <div className="absolute bottom-[-10%] left-[30%] w-[400px] h-[400px] rounded-full bg-accent-purple-light/10 blur-[120px] animate-float-blob-slow" />
      </div>

      {/* Existing radial gradients */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(98,20,217,0.15),transparent_70%)] animate-gradient" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_50%,rgba(26,255,117,0.05),transparent_60%)]" />
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="visible"
        className="relative z-10 text-center max-w-4xl px-6"
      >
        {/* Cloudify logo with neon cloud */}
        <motion.div variants={item} className="relative inline-block mb-8">
          {/* Neon cloud glow */}
          <svg
            viewBox="0 0 440 220"
            fill="none"
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[320px] md:w-[440px] h-auto drop-shadow-[0_0_30px_rgba(255,255,255,0.4)] animate-cloud-pulse"
          >
            <path
              d="M350 160H90a70 70 0 0 1-10-139.2A80 80 0 0 1 230 40a60 60 0 0 1 100 20 50 50 0 0 1 20 100z"
              stroke="white"
              strokeWidth="2"
              fill="none"
              className="drop-shadow-[0_0_15px_rgba(255,255,255,0.6)]"
            />
          </svg>
          <h1
            className="relative z-10 font-[family-name:var(--font-montserrat)] font-black text-[clamp(4rem,10vw,8rem)] text-white tracking-tight leading-none"
            style={{
              textShadow:
                "0 0 20px rgba(255,255,255,0.5), 0 0 60px rgba(255,255,255,0.3), 0 0 100px rgba(255,255,255,0.15)",
            }}
          >
            CLOUDIFY
          </h1>
        </motion.div>

        <motion.p
          variants={item}
          className="text-sm uppercase tracking-[0.2em] text-accent-purple font-medium mb-6"
        >
          AI-Powered Cloud Migration
        </motion.p>

        <motion.h1
          variants={item}
          className="font-serif text-[clamp(2.5rem,6vw,5rem)] text-text-primary leading-[1.1] mb-6"
          style={{ textWrap: "balance" } as React.CSSProperties}
        >
          Migrate to the <span className="gradient-text">Cloud</span>
          <br />
          in One Command
        </motion.h1>

        <motion.p
          variants={item}
          className="text-lg md:text-2xl text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed"
          style={{ textWrap: "balance" } as React.CSSProperties}
        >
          Cloudify uses AI agents to automatically analyze, containerize, and
          deploy your Spring Boot + React apps to Google Cloud Platform. No
          DevOps expertise needed.
        </motion.p>

        <motion.div
          variants={item}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <motion.a
            href="#cta"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="bg-accent-purple hover:bg-accent-purple-light text-white rounded-full px-8 py-3.5 font-medium transition-colors animate-glow"
          >
            Get Started
          </motion.a>
          <motion.a
            href="https://github.com/sanathmahesh/cloudify"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="border border-border-subtle text-text-primary rounded-full px-8 py-3.5 font-medium hover:bg-white/5 transition-colors"
          >
            View on GitHub
          </motion.a>
        </motion.div>
      </motion.div>
    </section>
  );
}
