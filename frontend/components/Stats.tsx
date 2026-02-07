import AnimateOnScroll from "./AnimateOnScroll";

const stats = [
  { value: "5", label: "AI Agents" },
  { value: "1", label: "Single Command" },
  { value: "< 2 min", label: "Avg. Migration" },
  { value: "100%", label: "Automated" },
];

export default function Stats() {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_50%,rgba(98,20,217,0.08),transparent_60%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_70%_50%,rgba(26,255,117,0.04),transparent_60%)]" />
      <div className="relative max-w-5xl mx-auto px-6">
        <AnimateOnScroll>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="font-serif text-4xl md:text-5xl text-text-primary mb-2">
                  {stat.value}
                </div>
                <div className="text-text-muted text-sm uppercase tracking-wide">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </AnimateOnScroll>
      </div>
    </section>
  );
}
