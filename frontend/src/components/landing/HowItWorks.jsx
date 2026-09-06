import Reveal from "../Reveal";

const STEPS = [
  { n: "01", t: "Photograph the defect", b: "Any phone camera. The GPS pin comes from your browser, or you type the coordinates.", img: "/img/tex-street.webp" },
  { n: "02", t: "The model reads the surface", b: "Detection, area measurement, severity banding and a weighted risk index — about a second on CPU.", img: "/img/tex-crack.webp" },
  { n: "03", t: "File the report", b: "Download the PDF or submit it. Every submission is stored, mapped and tracked to resolution.", img: "/img/tex-urban.webp" },
];

export default function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-6xl px-4 py-20">
      <Reveal>
        <h2 className="text-3xl font-semibold tracking-tight">Three steps</h2>
      </Reveal>
      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        {STEPS.map((s, i) => (
          <Reveal key={s.n} delay={i * 0.09}>
            <div className="glass glass-hover h-full overflow-hidden">
              <img src={s.img} alt="" className="h-40 w-full object-cover opacity-85" />
              <div className="p-5">
                <span className="text-xs font-bold tracking-widest text-[color:var(--color-brand)]">{s.n}</span>
                <h3 className="mt-2 font-semibold">{s.t}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-[color:var(--color-muted)]">{s.b}</p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
