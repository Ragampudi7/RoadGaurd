import { motion, useReducedMotion } from "framer-motion";

/** Scroll-in reveal. Respects prefers-reduced-motion rather than overriding it. */
export default function Reveal({ children, delay = 0, y = 18, className = "" }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.55, delay, ease: [0.22, 0.61, 0.36, 1] }}>
      {children}
    </motion.div>
  );
}
