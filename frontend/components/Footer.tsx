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
    <footer className="py-16 border-t border-border-subtle">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid md:grid-cols-4 gap-12">
          {/* Brand */}
          <div>
            <span className="text-text-primary font-serif text-2xl">
              Cloudify
            </span>
            <p className="text-text-muted text-sm mt-4 leading-relaxed">
              AI-powered cloud migration for Spring Boot + React apps. Built
              with Dedalus AI &amp; Claude.
            </p>
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

        <div className="mt-16 pt-8 border-t border-border-subtle flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-text-muted text-sm">
            Built with love for TartanHacks 2026
          </p>
          <p className="text-text-muted text-sm">
            &copy; 2026 Cloudify. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
