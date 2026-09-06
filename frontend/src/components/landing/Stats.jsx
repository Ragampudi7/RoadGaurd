import Reveal from "../Reveal";

/* Model figures are real: measured on the 314-image held-out test split. */
const STATS = [
  { v: "0.796", l: "mAP50", s: "held-out test split" },
  { v: "0.847", l: "Precision", s: "of reported defects" },
  { v: "3,224", l: "Training images", s: "two merged datasets" },
  { v: "~1 s", l: "Analysis", s: "CPU, end to end" },
];

export default function Stats() {
  return (
    <section id="stats" className="mx-auto max-w-6xl px-4 py-20">
      <Reveal>
        <div className="glass grid gap-6 p-8 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.l}>
              <div className="text-3xl font-semibold tracking-tight text-[color:var(--color-brand)]">{s.v}</div>
              <div className="mt-1 text-sm font-medium">{s.l}</div>
              <div className="text-xs text-[color:var(--color-muted)]">{s.s}</div>
            </div>
          ))}
        </div>
      </Reveal>
      <Reveal delay={0.1}>
        <p className="mt-4 text-center text-xs text-[color:var(--color-muted)]">
          Measured on 314 held-out images never used for training or model selection.
          Recall is 0.719 — roughly a quarter of defects present are still missed.
        </p>
      </Reveal>
    </section>
  );
}
