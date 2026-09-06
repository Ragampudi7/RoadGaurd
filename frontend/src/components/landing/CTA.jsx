import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import Reveal from "../Reveal";

export default function CTA() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-24">
      <Reveal>
        <div className="glass relative overflow-hidden p-10 text-center">
          <img src="/img/tex-crack.webp" alt=""
               className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-15" />
          <div className="relative">
            <h2 className="text-3xl font-semibold tracking-tight">Found a bad stretch of road?</h2>
            <p className="mx-auto mt-3 max-w-lg text-[color:var(--color-muted)]">
              One photo is enough to produce a scored, evidence-backed report.
            </p>
            <Link to="/signup" className="btn btn-primary mt-7">
              Start a report <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
