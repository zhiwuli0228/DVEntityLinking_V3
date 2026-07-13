import type { Config } from "tailwindcss";

// Tremor-inspired dark workbench tokens. The shell uses a dark slate canvas
// to clearly depart from the old white-card form stack.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        shell: {
          bg: "#0b1220",
          panel: "#111a2b",
          panelSoft: "#16223a",
          border: "#233047",
          borderStrong: "#324460",
          ink: "#e6edf6",
          muted: "#93a4bd",
        },
        accent: {
          teal: "#2bb3a3",
          blue: "#3b82f6",
          green: "#22c55e",
          amber: "#f59e0b",
          red: "#ef4444",
          violet: "#8b5cf6",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        xl: "10px",
      },
    },
  },
  plugins: [],
} satisfies Config;
