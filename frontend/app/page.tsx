import AnnouncementBanner from "@/components/AnnouncementBanner";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import SocialProof from "@/components/SocialProof";
import TerminalDemo from "@/components/TerminalDemo";
import LogoGrid from "@/components/LogoGrid";
import BeforeAfter from "@/components/BeforeAfter";
import FeatureCards from "@/components/FeatureCards";
import HowItWorks from "@/components/HowItWorks";
import ArchitectureFlow from "@/components/ArchitectureFlow";
import AgentCards from "@/components/AgentCards";
import CTA from "@/components/CTA";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="pt-[104px]">
      <AnnouncementBanner />
      <Navbar />
      <Hero />
      <SocialProof />
      <BeforeAfter />
      <TerminalDemo />
      <LogoGrid />
      <FeatureCards />
      <HowItWorks />
      <ArchitectureFlow />
      <AgentCards />
      <CTA />
      <Footer />
    </main>
  );
}
