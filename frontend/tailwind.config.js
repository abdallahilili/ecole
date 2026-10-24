/** Palette simple et professionnelle (sidebar + topbar), sans reference
 * visuelle imposee : priorite a la clarte et a la sobriete (cf. cahier
 * des charges section 10 - pas de surcharge visuelle). */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        entete: {
          DEFAULT: "#1d4e5f",
          fonce: "#163d4b",
        },
        fond: {
          DEFAULT: "#f5f6f8",
          carte: "#ffffff",
          barre: "#eef1f3",
        },
        accent: {
          vert: "#2f9e5b",
          rouge: "#d64545",
          bleu: "#3b7dd8",
          orange: "#e08e35",
        },
        texte: {
          DEFAULT: "#262b31",
          attenue: "#6b7280",
        },
        bordure: "#e2e5ea",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        carte: "0 1px 2px rgba(16, 24, 40, 0.06)",
      },
    },
  },
  plugins: [],
};
