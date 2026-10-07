import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Camera, FileCheck, MapPin } from "lucide-react";
import Navbar from "./Navbar";
import { IMAGES } from "../constants/images";

function StatFloat({ label, value, sub, valueClass, style, delay = 0 }) {
  return (
    <motion.div
      animate={{ y: [0, -8, 0] }}
      transition={{ duration: 5 + delay, repeat: Infinity, ease: "easeInOut", delay }}
      className="stat-card absolute z-20 w-44 rounded-xl p-4"
      style={style}
    >
      <p className="label">{label}</p>
      <p className={`mt-1 font-display text-lg font-bold ${valueClass}`}>{value}</p>
      <p className="sub mt-1">{sub}</p>
    </motion.div>
  );
}

export default function Hero() {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLoaded(true), 80);
    return () => clearTimeout(t);
  }, []);

  return (
    <section className="relative w-full overflow-hidden bg-base">
      <div className="absolute inset-0">
        <img
          src={IMAGES.potholeRoad}
          alt=""
          aria-hidden
          className="h-full w-full object-cover opacity-55"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-base via-base/85 to-base/35" />
        <div className="absolute inset-0 bg-gradient-to-t from-base via-base/20 to-base/60" />
      </div>

      <div className="absolute inset-0 bg-grid opacity-25 animate-gridDrift" />

      <Navbar />

      <div className="relative z-10 mx-auto max-w-7xl px-6 md:px-12 pt-36 pb-28 lg:pt-44 lg:pb-36">
        <div className="grid lg:grid-cols-2 gap-14 items-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: loaded ? 1 : 0, y: loaded ? 0 : 30 }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-signal/20 bg-panel/75 px-4 py-1.5 text-xs font-semibold text-ink/85 backdrop-blur-sm">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-signal animate-pulseDot" />
              </span>
              Citizen road damage reporting platform
            </div>

            <h1 className="font-display font-bold tracking-tight text-[2.7rem] leading-[1.06] sm:text-6xl lg:text-[4.35rem] lg:leading-[1.03]">
              <span className="text-gradient">RoadGuard AI.</span>
              <br />
              <span className="text-signal">Report hazards faster.</span>
            </h1>

            <p className="mt-6 max-w-xl text-lg text-ink/75 leading-relaxed">
              One clear road photo can alert a city, protect a rider, and turn a dangerous pothole into repair-ready evidence.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <a
                href="/signup"
                className="inline-flex items-center gap-2 rounded-lg bg-signal px-6 py-3.5 text-base font-semibold text-white shadow-glow transition-all hover:-translate-y-0.5 hover:bg-signalDim"
              >
                Start a Complaint
                <Camera className="h-4 w-4" />
              </a>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 rounded-lg border border-line bg-panel/70 px-6 py-3.5 text-base font-semibold text-ink transition-all hover:-translate-y-0.5 hover:border-signal hover:text-white"
              >
                View Workflow
              </a>
            </div>

            <div className="mt-12 flex flex-wrap gap-x-10 gap-y-4">
              {[
                { icon: Camera, title: "Safer Commutes", sub: "Spot hazards early" },
                { icon: MapPin, title: "India-Ready Maps", sub: "Local road context" },
                { icon: FileCheck, title: "Actionable Proof", sub: "Clear repair priority" },
              ].map(({ icon: Icon, title, sub }) => (
                <div key={title} className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full border border-line bg-panel/70">
                    <Icon className="h-4 w-4 text-signal" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">{title}</div>
                    <div className="text-xs text-ink/55">{sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: loaded ? 1 : 0, scale: loaded ? 1 : 0.95 }}
            transition={{ duration: 0.9, delay: 0.2 }}
            className="relative hidden lg:block"
          >
            <div className="relative aspect-[4/5] w-full">
              <div className="relative h-full overflow-hidden rounded-2xl border border-signal/25 shadow-cardHover">
                <img
                  src={IMAGES.potholeRoad}
                  alt="Pothole damaged road detected by RoadGuard AI"
                  className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-base/65 via-transparent to-signal/5" />

                <div className="absolute inset-x-0 top-0 h-1/4 animate-scan pointer-events-none z-10">
                  <div className="h-full w-full bg-gradient-to-b from-signal/0 via-signal/35 to-signal/0" />
                  <div className="h-px w-full bg-signal shadow-[0_0_20px_2px_rgba(37,99,235,0.8)]" />
                </div>

                <div className="absolute left-[42%] bottom-[16%] z-10 h-24 w-36 animate-lockOn">
                  <div className="absolute inset-0 border-2 border-hazard/90 [clip-path:polygon(0_0,20%_0,20%_8%,0_8%)]" />
                  <div className="absolute inset-0 border-2 border-hazard/90 [clip-path:polygon(80%_0,100%_0,100%_8%,80%_8%)]" />
                  <div className="absolute inset-0 border-2 border-hazard/90 [clip-path:polygon(0_92%,20%_92%,20%_100%,0_100%)]" />
                  <div className="absolute inset-0 border-2 border-hazard/90 [clip-path:polygon(80%_92%,100%_92%,100%_100%,80%_100%)]" />
                </div>
              </div>

              <StatFloat
                label="Severity"
                value="Critical"
                sub="Repair priority flagged"
                valueClass="text-hazard"
                style={{ top: "-0.5rem", right: "0" }}
              />
              <StatFloat
                label="Road Score"
                value="32/100"
                sub="Critical condition"
                valueClass="text-signal"
                style={{ top: "40%", left: "-1rem" }}
                delay={1}
              />
              <StatFloat
                label="Complaint"
                value="Ready"
                sub="Image and GPS attached"
                valueClass="text-amber-400"
                style={{ bottom: "0.5rem", right: "0" }}
                delay={2}
              />
            </div>
          </motion.div>
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-sectionLight to-transparent" />
    </section>
  );
}
