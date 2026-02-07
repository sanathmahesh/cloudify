import AnimateOnScroll from "./AnimateOnScroll";

export default function CTA() {
  return (
    <section id="cta" className="py-24 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-accent-purple/15 blur-[140px] animate-float-blob" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[450px] h-[450px] rounded-full bg-accent-green/12 blur-[140px] animate-float-blob-delayed" />
      </div>
      <div className="relative max-w-4xl mx-auto px-6">
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
                className="bg-accent-purple hover:bg-accent-purple-light text-white rounded-full px-8 py-3.5 font-medium transition-all hover:scale-[1.02] animate-glow"
              >
                Start Migration
              </a>
              <a
                href="https://github.com/sanathmahesh/cloudify#readme"
                className="border border-border-subtle text-text-primary rounded-full px-8 py-3.5 font-medium hover:bg-white/5 transition-all hover:scale-[1.02]"
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
