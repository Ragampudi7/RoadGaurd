import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Camera, FileCheck2 } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative mx-auto max-w-6xl px-4 pt-16 pb-20 sm:pt-24">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <motion.span
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5 }}
            className="chip border border-[color:var(--color-brand)]/30 bg-[color:var(--color-brand)]/12 text-[color:var(--color-brand)]">
            YOLO11 · 0.796 mAP50
          </motion.span>

          <motion.h1
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: .6, delay: .05 }}
            className="mt-5 text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl">
            Photograph a pothole.<br />
            <span className="bg-gradient-to-r from-[color:var(--color-brand)] to-[#7cc4ff] bg-clip-text text-transparent">
              File a report that gets acted on.
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: .6, delay: .12 }}
            className="mt-5 max-w-xl text-[15.5px] leading-relaxed text-[color:var(--color-muted)]">
            A computer-vision model finds the defects, scores the road surface,
            estimates how urgently it needs repair, and produces a
            complaint-ready PDF addressed to your municipal body — from one photo
            and a GPS pin.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: .6, delay: .19 }}
            className="mt-8 flex flex-wrap gap-3">
            <Link to="/signup" className="btn btn-primary">
              Report a road <ArrowRight size={16} />
            </Link>
            <a href="#how" className="btn btn-ghost">See how it works</a>
          </motion.div>

          <div className="mt-8 flex flex-wrap gap-x-7 gap-y-2 text-[13px] text-[color:var(--color-muted)]">
            <span className="inline-flex items-center gap-1.5"><Camera size={14} /> One photo, no special equipment</span>
            <span className="inline-flex items-center gap-1.5"><FileCheck2 size={14} /> Evidence-hashed PDF</span>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: .96 }} animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: .7, delay: .15 }}
          className="relative">
          <div className="glass overflow-hidden p-2">
            <img src="/img/hero.webp" alt="Water-filled pothole on a road surface"
                 className="w-full rounded-xl object-cover" />
          </div>

          {/* floating result card — the shape of a real analysis */}
          <motion.div
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: .6, delay: .45 }}
            className="glass absolute -bottom-7 -left-3 w-52 p-4 sm:-left-10"
            style={{ background: "rgb(14 18 24 / 0.86)" }}>
            <div className="text-[11px] uppercase tracking-wider text-[color:var(--color-muted)]">Road health</div>
            <div className="mt-1 flex items-end gap-2">
              <span className="text-3xl font-semibold text-[color:var(--color-fair)]">80.8</span>
              <span className="mb-1 text-xs text-[color:var(--color-muted)]">/ 100</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-[color:var(--color-fair)]" style={{ width: "80.8%" }} />
            </div>
            <div className="mt-2.5 text-xs text-[color:var(--color-muted)]">5 defects · Priority-2</div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
