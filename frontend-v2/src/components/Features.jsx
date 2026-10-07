import { Camera, FileText, Gauge, MapPinned } from "lucide-react";
import { motion } from "framer-motion";
import { Reveal } from "./Reveal";

const features = [
  {
    icon: Camera,
    title: "Photo Complaint",
    desc: "A user can capture or upload a clear road photo and start a complaint in seconds.",
  },
  {
    icon: MapPinned,
    title: "GPS Location",
    desc: "Latitude, longitude, and timestamp are captured automatically for accurate pothole placement.",
  },
  {
    icon: Gauge,
    title: "Road Score",
    desc: "Damage type, severity, and road condition score help prioritize repair urgency.",
  },
  {
    icon: FileText,
    title: "Complaint Reports",
    desc: "Users can save drafts, submit complaints, and download PDFs with all required evidence.",
  },
];

export default function Features() {
  return (
    <section id="features" className="relative bg-sectionLight px-6 md:px-12 py-24 lg:py-32">
      <div className="mx-auto max-w-7xl">
        <Reveal>
          <span className="text-xs font-bold uppercase tracking-widest text-signalDim">User Portal</span>
          <h2 className="mt-3 max-w-2xl font-display text-3xl sm:text-4xl font-bold text-inkDark leading-tight">
            Everything a citizen needs to report a dangerous road spot
          </h2>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-mutedDark">
            RoadGuard AI keeps the public website focused on users first: report, review, and track pothole data without exposing admin controls.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f, i) => (
            <Reveal key={f.title} delay={i * 90}>
              <motion.div
                whileHover={{ y: -6 }}
                transition={{ type: "spring", stiffness: 300, damping: 22 }}
                className="group h-full rounded-xl border border-[#E4E8F0] bg-white p-6 shadow-[0_4px_20px_rgba(11,18,32,0.06)] transition-all hover:shadow-[0_16px_40px_-12px_rgba(37,99,235,0.22)]"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-signal/10 text-signal transition-colors group-hover:bg-signal group-hover:text-white">
                  <f.icon className="h-5 w-5" />
                </div>
                <h3 className="mt-5 font-display text-lg font-semibold text-inkDark leading-snug">
                  {f.title}
                </h3>
                <p className="mt-2 text-sm text-mutedDark leading-relaxed">{f.desc}</p>
              </motion.div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
