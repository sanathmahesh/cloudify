import Image from "next/image";
import AnimateOnScroll from "./AnimateOnScroll";

const logos = [
  { name: "Google Cloud", file: "/logos/googlecloud.svg" },
  { name: "Anthropic", file: "/logos/anthropic.svg" },
  { name: "Docker", file: "/logos/docker.svg" },
  { name: "Firebase", file: "/logos/firebase.svg" },
  { name: "Spring Boot", file: "/logos/springboot.svg" },
  { name: "React", file: "/logos/react.svg" },
  { name: "Python", file: "/logos/python.svg" },
];

export default function LogoGrid() {
  return (
    <section className="py-20 border-y border-border-subtle">
      <AnimateOnScroll>
        <div className="max-w-5xl mx-auto px-6">
          <p className="text-center text-sm uppercase tracking-[0.2em] text-text-muted mb-12">
            Powered By
          </p>
          <div className="grid grid-cols-3 md:grid-cols-7 gap-8 md:gap-10 items-center justify-items-center">
            {logos.map((logo) => (
              <div
                key={logo.name}
                className="flex items-center justify-center h-10 opacity-40 hover:opacity-100 transition-opacity duration-300"
              >
                <Image
                  src={logo.file}
                  alt={logo.name}
                  width={40}
                  height={40}
                  className="h-8 w-auto object-contain invert"
                />
              </div>
            ))}
          </div>
        </div>
      </AnimateOnScroll>
    </section>
  );
}
