import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { IMAGES } from "../constants/images";

export default function AuthLayout({ children, title, subtitle }) {
  return (
    <div className="flex min-h-screen bg-base">
      <motion.div
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="relative hidden w-1/2 lg:block"
      >
        <img
          src={IMAGES.indiaPotholeAction}
          alt=""
          aria-hidden
          className="absolute inset-0 h-full w-full scale-110 object-cover object-center blur-md"
        />
        <div className="absolute inset-0 bg-base/62" />
        <img
          src={IMAGES.indiaPotholeAction}
          alt="Indian road with pothole awareness posters"
          className="absolute inset-0 h-full w-full object-contain object-center"
        />
        <div className="absolute inset-0 bg-gradient-to-br from-base/72 via-base/20 to-base/24" />
        <div className="absolute inset-x-0 top-0 h-44 bg-gradient-to-b from-base/90 via-base/45 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-base/65 to-transparent" />

        <div className="absolute inset-0 p-12">
          <Link
            to="/"
            className="inline-block max-w-xs font-display text-3xl font-bold leading-tight drop-shadow-[0_2px_14px_rgba(0,0,0,0.65)]"
          >
            <span className="text-white">Safer Indian Roads.</span>
            <br />
            <span className="text-signal">Faster Action.</span>
          </Link>
        </div>
      </motion.div>

      <div className="flex w-full flex-col justify-center bg-panel px-6 py-12 lg:w-1/2 lg:px-16">
        <Link to="/" className="mb-8 font-display text-lg font-bold lg:hidden">
          <span className="text-white">RoadGuard </span>
          <span className="text-signal">AI</span>
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mx-auto w-full max-w-md"
        >
          <h1 className="font-display text-3xl font-bold text-white">{title}</h1>
          <p className="mt-2 text-base text-ink/70">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </motion.div>
      </div>
    </div>
  );
}
