export default function Footer() {
  return (
    <footer className="border-t border-white/8">
      <div className="mx-auto max-w-6xl px-4 py-10 text-[12.5px] leading-relaxed text-[color:var(--color-muted)]">
        <p className="max-w-3xl">
          <strong className="text-[color:var(--color-ink)]">Automated visual estimate from a single photograph.</strong>{" "}
          Score, severity and risk thresholds are defined by this project and are not
          taken from IRC, MoRTH, GHMC or any other official standard. A photograph
          carries no depth or scale, so severity reflects the share of the frame a
          defect occupies, not how deep it is. Not a substitute for inspection by a
          qualified engineer.
        </p>
        <p className="mt-5">
          Road photographs from the{" "}
          <a href="https://universe.roboflow.com/siva-ragampudi/pothole-vhmow-jwwzq" target="_blank" rel="noreferrer">Pothole</a>{" "}and{" "}
          <a href="https://universe.roboflow.com/siva-ragampudi/road-c013o-tlkm7" target="_blank" rel="noreferrer">Road</a>{" "}
          datasets on Roboflow Universe, used under CC BY 4.0.
        </p>
        <p className="mt-5 opacity-70">RoadGuard AI · academic project</p>
      </div>
    </footer>
  );
}
