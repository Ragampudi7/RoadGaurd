import { AlertTriangle, Bell, FileSearch, MapPinned } from "lucide-react";
import { Reveal } from "./Reveal";

const outcomes = [
  {
    icon: MapPinned,
    title: "Mapped Evidence",
    desc: "Every complaint keeps the photo, coordinates, and timestamp together so the location is easy to verify.",
  },
  {
    icon: AlertTriangle,
    title: "Severity Clarity",
    desc: "Potholes and cracks are separated by severity so dangerous roads can be understood at a glance.",
  },
  {
    icon: FileSearch,
    title: "Authority-Ready PDF",
    desc: "The report includes the road image, damage type, score, GPS data, and repair priority in one document.",
  },
  {
    icon: Bell,
    title: "Nearby Awareness",
    desc: "Map markers help users notice risky areas around them before those hazards become accidents.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="relative overflow-hidden bg-base px-6 md:px-12 py-24 lg:py-28">
      <div className="absolute inset-0 bg-grid opacity-[0.08]" />

      <div className="relative mx-auto max-w-7xl">
        <Reveal>
          <div className="mx-auto max-w-3xl text-center">
            <span className="text-xs font-bold uppercase tracking-widest text-signal">After the complaint</span>
            <h2 className="mt-3 font-display text-3xl sm:text-4xl font-bold text-white">
              RoadGuard turns a user photo into useful road intelligence
            </h2>
            <p className="mt-4 text-base leading-relaxed text-ink/62">
              The lower section now explains what the system produces after reporting, so it does not repeat the feature cards above.
            </p>
          </div>
        </Reveal>

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {outcomes.map((item, i) => (
            <Reveal key={item.title} delay={i * 110}>
              <div className="h-full rounded-xl border border-line bg-panel/80 p-6 transition-all hover:-translate-y-1 hover:border-signal/40 hover:bg-panel2">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-signal/10 text-signal">
                  <item.icon className="h-5 w-5" />
                </div>
                <h3 className="mt-5 font-display text-lg font-semibold text-white">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/60">{item.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
