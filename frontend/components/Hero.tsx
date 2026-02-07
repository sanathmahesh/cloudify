"use client";

import { motion, type Variants } from "framer-motion";
import type { CSSProperties } from "react";

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

      {/* Data streams + laptops (fills 8 & 4 o'clock) */}
      <div className="absolute inset-0 pointer-events-none">
        <svg
          viewBox="0 0 1000 600"
          preserveAspectRatio="none"
          className="absolute inset-0 w-full h-full"
        >
          <defs>
            <linearGradient id="dataStream" x1="0" y1="1" x2="1" y2="0">
              <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#1aff75" stopOpacity="0.9" />
            </linearGradient>
            <linearGradient id="lapGradL" x1="0" y1="1" x2="1" y2="0">
              <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#1aff75" stopOpacity="0.7" />
            </linearGradient>
            <linearGradient id="lapGradR" x1="1" y1="1" x2="0" y2="0">
              <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#1aff75" stopOpacity="0.7" />
            </linearGradient>
          </defs>
          <path
            d="M180 420 C 320 260, 400 220, 500 190"
            stroke="url(#dataStream)"
            strokeWidth="2"
            strokeDasharray="6 10"
            className="data-stream"
            strokeLinecap="round"
            fill="none"
          />
          <path
            d="M820 420 C 680 260, 600 220, 500 190"
            stroke="url(#dataStream)"
            strokeWidth="2"
            strokeDasharray="6 10"
            className="data-stream data-stream-delay"
            strokeLinecap="round"
            fill="none"
          />

          {/* Left laptop */}
          <g
            className="logo-flicker"
            opacity="0.85"
            transform="translate(70 360) scale(0.9)"
          >
            <rect x="30" y="20" width="160" height="90" rx="8" stroke="url(#lapGradL)" strokeWidth="2" />
            <rect x="42" y="32" width="136" height="66" rx="4" fill="url(#lapGradL)" opacity="0.12" />
            <rect x="18" y="112" width="184" height="10" rx="5" fill="#0f0f0f" stroke="url(#lapGradL)" strokeWidth="1.5" />
          </g>

          {/* Right laptop */}
          <g
            className="logo-flicker"
            opacity="0.85"
            transform="translate(710 360) scale(0.9)"
          >
            <rect x="30" y="20" width="160" height="90" rx="8" stroke="url(#lapGradR)" strokeWidth="2" />
            <rect x="42" y="32" width="136" height="66" rx="4" fill="url(#lapGradR)" opacity="0.12" />
            <rect x="18" y="112" width="184" height="10" rx="5" fill="#0f0f0f" stroke="url(#lapGradR)" strokeWidth="1.5" />
          </g>
        </svg>
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="visible"
        className="relative z-10 text-center max-w-4xl px-6"
      >
        {/* Cloudify logo with precision graphics */}
        <motion.div variants={item} className="relative inline-block mb-8">
          {/* Crazy background graphics behind logo */}
          <div className="absolute inset-0 -z-10 flex items-center justify-center pointer-events-none">
            <svg
              viewBox="0 0 700 700"
              fill="none"
              className="w-[520px] md:w-[720px] h-auto opacity-90 logo-orbit-rotate"
            >
              <defs>
                <linearGradient id="orbitA" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.9" />
                  <stop offset="50%" stopColor="#1aff75" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#ffffff" stopOpacity="0.25" />
                </linearGradient>
                <linearGradient id="orbitB" x1="1" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#1aff75" stopOpacity="0.7" />
                  <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.6" />
                </linearGradient>
              </defs>

              <g stroke="url(#orbitA)" strokeWidth="1.2" strokeLinecap="round">
                <circle cx="350" cy="350" r="250" strokeDasharray="18 14" className="logo-dash" />
                <circle cx="350" cy="350" r="200" strokeDasharray="6 10" className="logo-dash" />
                <circle cx="350" cy="350" r="150" opacity="0.8" />
                <path d="M110 350H590" opacity="0.5" />
                <path d="M350 110V590" opacity="0.5" />
                <path d="M150 150L550 550" opacity="0.35" />
                <path d="M550 150L150 550" opacity="0.35" />
              </g>

              <g stroke="url(#orbitB)" strokeWidth="1" strokeLinecap="round" className="logo-orbit-reverse">
                <circle cx="350" cy="350" r="115" strokeDasharray="10 12" />
                <path d="M90 350C180 250 520 450 610 350" opacity="0.7" />
                <path d="M140 420C240 520 460 180 560 280" opacity="0.6" />
              </g>

              <g className="logo-flicker">
                <circle cx="520" cy="210" r="3" fill="#1aff75" />
                <circle cx="180" cy="480" r="2.5" fill="#7c3aed" />
                <circle cx="470" cy="520" r="2" fill="#ffffff" />
                <circle cx="230" cy="200" r="2" fill="#ffffff" />
              </g>
            </svg>
          </div>

          {/* Clean cloud outline */}
          <svg
            viewBox="0 0 440 220"
            fill="none"
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[320px] md:w-[440px] h-auto animate-cloud-pulse"
          >
            <defs>
              <linearGradient id="cloudStroke" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#1aff75" stopOpacity="0.9" />
              </linearGradient>
            </defs>
            <path
              d="M350 160H90a70 70 0 0 1-10-139.2A80 80 0 0 1 230 40a60 60 0 0 1 100 20 50 50 0 0 1 20 100z"
              stroke="url(#cloudStroke)"
              strokeWidth="5"
              fill="none"
            />
          </svg>

          <h1
            className="relative z-10 font-[family-name:var(--font-montserrat)] font-semibold text-[clamp(4rem,10vw,8rem)] text-white/95 tracking-[0.08em] leading-none"
            style={{ textShadow: "0 4px 12px rgba(0,0,0,0.45)" }}
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
          style={{ textWrap: "balance" } as CSSProperties}
        >
          Migrate to the <span className="gradient-text">Cloud</span>
          <br />
          in One Command
        </motion.h1>

        <motion.p
          variants={item}
          className="text-lg md:text-2xl text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed"
          style={{ textWrap: "balance" } as CSSProperties}
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
