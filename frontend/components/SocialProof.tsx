import AnimateOnScroll from "./AnimateOnScroll";

export default function SocialProof() {
  return (
    <AnimateOnScroll>
      <div className="py-8 border-b border-border-subtle">
        <div className="max-w-5xl mx-auto px-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-sm text-text-muted">
          <span className="inline-flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent-green">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            Built at TartanHacks 2026
          </span>
          <span className="text-border-subtle">|</span>
          <span className="inline-flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent-purple">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
            Powered by Claude &amp; Dedalus AI
          </span>
          <span className="text-border-subtle">|</span>
          <span className="bg-accent-green/10 text-accent-green px-3 py-1 rounded-full text-xs font-medium">
            Open Source
          </span>
        </div>
      </div>
    </AnimateOnScroll>
  );
}
