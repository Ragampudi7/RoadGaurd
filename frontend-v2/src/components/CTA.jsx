import { motion } from "framer-motion";
import { Reveal } from "./Reveal";

export default function CTA() {
  return (
    <section id="about" className="bg-sectionLight px-6 md:px-12 py-24 lg:py-28">
      <Reveal>
        <motion.div
          whileInView={{ y: [18, 0], scale: [0.98, 1] }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="mx-auto max-w-5xl overflow-hidden rounded-2xl border border-line bg-gradient-to-br from-panel via-panel2 to-base shadow-cardHover"
        >
          <div className="relative px-8 sm:px-16 py-16 sm:py-20 text-center">
            <div className="absolute inset-0 bg-grid opacity-[0.06]" />

            <div className="relative">
              <h2 className="font-display text-3xl sm:text-5xl font-bold text-white leading-tight">
                Every reported pothole is a step toward a safer road.
              </h2>
              <p className="mt-5 mx-auto max-w-lg text-base sm:text-lg text-ink/70 leading-relaxed">
                RoadGuard AI connects photos, GPS, severity, and repair priority so road hazards become clear, trackable action.
              </p>
            </div>
          </div>
        </motion.div>
      </Reveal>
    </section>
  );
}
