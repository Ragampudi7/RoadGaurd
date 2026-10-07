/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#05070D",
        panel: "#0E1525",
        panel2: "#111A2E",
        signal: "#2563eb",
        signalDim: "#1d4ed8",
        hazard: "#ef4444",
        ink: "#E8ECF4",
        inkDark: "#0B1220",
        muted: "#94a3b8",
        mutedDark: "#5B6478",
        line: "#1C2333",
        sectionLight: "#F5F7FB",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      boxShadow: {
        card: "0 4px 24px -4px rgba(0, 0, 0, 0.4)",
        cardHover: "0 12px 40px -8px rgba(37, 99, 235, 0.35)",
        glow: "0 0 40px rgba(37, 99, 235, 0.25)",
      },
      keyframes: {
        scan: {
          "0%": { transform: "translateY(-10%)", opacity: "0" },
          "10%": { opacity: "1" },
          "90%": { opacity: "1" },
          "100%": { transform: "translateY(420%)", opacity: "0" },
        },
        lockOn: {
          "0%, 100%": { opacity: "0.35", transform: "scale(0.98)" },
          "50%": { opacity: "1", transform: "scale(1)" },
        },
        floatSlow: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
        gridDrift: {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "60px 60px" },
        },
      },
      animation: {
        scan: "scan 3.2s cubic-bezier(0.4,0,0.2,1) infinite",
        lockOn: "lockOn 2.4s ease-in-out infinite",
        floatSlow: "floatSlow 6s ease-in-out infinite",
        pulseDot: "pulseDot 1.6s ease-in-out infinite",
        gridDrift: "gridDrift 4s linear infinite",
      },
    },
  },
  plugins: [],
};
