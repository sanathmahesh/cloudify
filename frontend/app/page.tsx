import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import LogoGrid from "@/components/LogoGrid";
import FeatureCards from "@/components/FeatureCards";
import AgentCards from "@/components/AgentCards";
import Stats from "@/components/Stats";
import CTA from "@/components/CTA";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main>
      <Navbar />
      <Hero />
      <LogoGrid />
      <FeatureCards />
      <AgentCards />
      <Stats />
      <CTA />
      <Footer />
    </main>
  );
}
