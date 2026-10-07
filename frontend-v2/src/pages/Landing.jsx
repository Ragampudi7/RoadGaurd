import Hero from "../components/Hero";
import Features from "../components/Features";
import HowItWorks from "../components/HowItWorks";
import Stats from "../components/Stats";
import CTA from "../components/CTA";
import Footer from "../components/Footer";

export default function Landing() {
  return (
    <div className="bg-base font-body text-ink antialiased">
      <Hero />
      <Features />
      <HowItWorks />
      <Stats />
      <CTA />
      <Footer />
    </div>
  );
}
