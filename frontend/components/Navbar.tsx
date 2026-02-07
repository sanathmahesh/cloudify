"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence, useScroll, useSpring } from "framer-motion";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "Agents", href: "#agents" },
  { label: "GitHub", href: "https://github.com/sanathmahesh/cloudify" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 });

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      {/* Scroll progress bar */}
      <motion.div
        className="fixed top-0 left-0 right-0 h-[2px] scroll-progress z-[80] origin-left"
        style={{ scaleX }}
      />

      <nav
        className={`fixed top-[40px] left-0 right-0 z-[60] transition-all duration-300 ${
          scrolled
            ? "bg-bg-primary/80 backdrop-blur-lg border-b border-border-subtle"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
          <a href="#" className="text-text-primary font-serif text-2xl">
            Cloudify
          </a>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="nav-link-underline text-text-secondary hover:text-text-primary transition-colors text-sm font-medium"
              >
                {link.label}
              </a>
            ))}
          </div>

          <motion.a
            href="#cta"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="hidden md:inline-flex bg-accent-purple hover:bg-accent-purple-light text-white rounded-full px-6 py-2.5 text-sm font-medium transition-colors"
          >
            Get Started
          </motion.a>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden text-text-primary p-2"
            aria-label="Toggle menu"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {mobileOpen ? (
                <path d="M6 6l12 12M6 18L18 6" />
              ) : (
                <path d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden bg-bg-primary/95 backdrop-blur-lg border-b border-border-subtle overflow-hidden"
            >
              <div className="px-6 py-4 flex flex-col gap-4">
                {navLinks.map((link) => (
                  <a
                    key={link.label}
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className="text-text-secondary hover:text-text-primary transition-colors text-sm font-medium"
                  >
                    {link.label}
                  </a>
                ))}
                <a
                  href="#cta"
                  onClick={() => setMobileOpen(false)}
                  className="bg-accent-purple text-white rounded-full px-6 py-2.5 text-sm font-medium text-center"
                >
                  Get Started
                </a>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>
    </>
  );
}
