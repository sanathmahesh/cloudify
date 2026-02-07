"use client";

import { motion } from "framer-motion";

export default function AnnouncementBanner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="relative z-50 bg-gradient-to-r from-accent-purple/80 via-accent-purple to-accent-purple-light/80 text-white text-center py-2.5 px-4 text-sm font-medium"
    >
      <a
        href="https://github.com/sanathmahesh/cloudify"
        className="hover:underline inline-flex items-center gap-2"
      >
        We just launched at TartanHacks 2026 — Star us on GitHub
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </a>
    </motion.div>
  );
}
