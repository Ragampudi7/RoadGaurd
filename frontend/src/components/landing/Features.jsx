import { ScanLine, Gauge, Map, FileText, ShieldCheck, Layers } from "lucide-react";
import Reveal from "../Reveal";

const ITEMS = [
  { icon: ScanLine, title: "Defect detection", body: "A YOLO11 model trained on 3,224 road images finds potholes and cracks, returning a box and a confidence for each." },
  { icon: Gauge, title: "Health score", body: "Damaged area as a share of the frame gives a 0-100 score and a Good / Fair / Poor / Dangerous band." },
  { icon: Layers, title: "Risk index", body: "Extent, worst single defect and density are weighted into an urgency score with a priority tier and response window." },
  { icon: FileText, title: "Complaint-ready PDF", body: "A four-page report with the annotated photograph, defect inventory, recommended remediation and a grievance statement." },
  { icon: Map, title: "Mapped submissions", body: "Every report is pinned by GPS and coloured by risk, so a street's history is visible at a glance." },
  { icon: ShieldCheck, title: "Evidence integrity", body: "Each report carries a SHA-256 hash of the exact photograph analysed, so the evidence can be verified later." },
];

export default function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl px-4 py-20">
      <Reveal>
        <h2 className="text-3xl font-semibold tracking-tight">What it actually does</h2>
        <p className="mt-2 max-w-2xl text-[color:var(--color-muted)]">
          Not a photo album with a complaint form attached — every number in the
          report is computed and every threshold is documented.
        </p>
      </Reveal>

      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ITEMS.map((f, i) => (
          <Reveal key={f.title} delay={i * 0.06}>
            <div className="glass glass-hover h-full p-5">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-[color:var(--color-brand)]/15
                               text-[color:var(--color-brand)]">
                <f.icon size={19} />
              </span>
              <h3 className="mt-4 font-semibold">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-[color:var(--color-muted)]">{f.body}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
