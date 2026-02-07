const footerLinks = {
  Product: [
    { label: "Features", href: "#features" },
    { label: "Agents", href: "#agents" },
    { label: "GitHub", href: "https://github.com/sanathmahesh/cloudify" },
  ],
  Resources: [
    { label: "Cloud Run Docs", href: "https://cloud.google.com/run/docs" },
    { label: "Firebase Docs", href: "https://firebase.google.com/docs/hosting" },
    { label: "Dedalus AI", href: "https://dedaluslabs.ai" },
    { label: "Claude API", href: "https://docs.anthropic.com" },
  ],
  Connect: [
    { label: "GitHub", href: "https://github.com/sanathmahesh/cloudify" },
    { label: "Twitter", href: "https://twitter.com" },
  ],
};

export default function Footer() {
  return (
    <footer className="pt-16 pb-10 relative overflow-hidden">
      <div className="h-px w-full bg-gradient-to-r from-accent-purple/0 via-accent-purple/50 to-accent-green/0" />
      <div className="max-w-7xl mx-auto px-6 pt-12">
        <div className="grid md:grid-cols-4 gap-12">
          {/* Brand */}
          <div>
            <span className="text-text-primary font-serif text-3xl">
              Cloudify
            </span>
            <p className="text-text-muted text-sm mt-4 leading-relaxed">
              Migrate Spring Boot + React apps to GCP in one command. Built with
              Dedalus AI &amp; Claude.
            </p>
            <div className="mt-6">
              <p className="text-xs uppercase tracking-wider text-text-muted">
                Newsletter
              </p>
              <div className="mt-3 flex flex-col sm:flex-row gap-2">
                <input
                  type="email"
                  placeholder="you@company.com"
                  className="flex-1 bg-bg-primary/60 border border-border-subtle rounded-full px-4 py-2 text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent-purple/60"
                />
                <a
                  href="https://github.com/sanathmahesh/cloudify"
                  className="bg-accent-purple hover:bg-accent-purple-light text-white rounded-full px-5 py-2 text-sm font-medium transition-colors text-center"
                >
                  Notify me
                </a>
              </div>
              <p className="text-xs text-text-muted mt-2">
                Updates delivered via GitHub releases.
              </p>
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([heading, links]) => (
            <div key={heading}>
              <h4 className="text-text-primary font-semibold text-sm uppercase tracking-wide mb-4">
                {heading}
              </h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-text-muted hover:text-text-secondary transition-colors text-sm"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16">
          <div className="h-px w-full bg-gradient-to-r from-accent-purple/0 via-accent-purple/50 to-accent-green/0" />
          <div className="pt-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-text-muted text-sm">
            Built with love for TartanHacks 2026
          </p>
          <p className="text-text-muted text-sm">
            &copy; 2026 Cloudify. All rights reserved.
          </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
