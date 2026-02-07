import AnimateOnScroll from "./AnimateOnScroll";

export default function CTA() {
  return (
    <section id="cta" className="py-24">
      <div className="max-w-4xl mx-auto px-6">
        <AnimateOnScroll>
          <div className="text-center bg-bg-card/50 backdrop-blur-xl border border-border-subtle rounded-3xl p-12 md:p-16">
            <h2 className="font-serif text-[clamp(2rem,4vw,3rem)] text-text-primary mb-4">
              Ready to Move to the Cloud?
            </h2>
            <p className="text-text-secondary text-lg max-w-xl mx-auto mb-8">
              Stop wrestling with Dockerfiles and GCP consoles. Let AI handle
              the migration.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="https://github.com/sanathmahesh/cloudify"
                className="bg-accent-purple hover:bg-accent-purple-light text-white rounded-full px-8 py-3.5 font-medium transition-colors animate-glow"
              >
                Start Migration
              </a>
              <a
                href="https://github.com/sanathmahesh/cloudify#readme"
                className="border border-border-subtle text-text-primary rounded-full px-8 py-3.5 font-medium hover:bg-white/5 transition-colors"
              >
                Read the Docs
              </a>
            </div>
          </div>
        </AnimateOnScroll>
      </div>
    </section>
  );
}
