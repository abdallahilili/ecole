import { Languages } from "lucide-react";
import { definirLangue, langue } from "../i18n";
import type { Langue } from "../i18n";

const LANGUES: { code: Langue; libelle: string }[] = [
  { code: "fr", libelle: "Français" },
  { code: "ar", libelle: "العربية" },
];

/** Bascule francais / arabe. Les libelles restent dans leur propre langue pour etre reconnus de tous. */
export function SelecteurLangue({ ton = "clair" }: { ton?: "clair" | "fonce" }) {
  const actif = ton === "clair" ? "bg-white text-entete" : "bg-entete text-white";
  const inactif = ton === "clair" ? "text-white hover:bg-white/15" : "text-texte hover:bg-fond-barre";
  return (
    <div className={`flex items-center gap-1 rounded border p-0.5 text-xs ${ton === "clair" ? "border-white/40" : "border-bordure"}`} dir="ltr">
      <Languages size={14} className={ton === "clair" ? "mx-1 text-white/80" : "mx-1 text-texte-attenue"} />
      {LANGUES.map((l) => (
        <button
          key={l.code}
          type="button"
          lang={l.code}
          aria-pressed={langue === l.code}
          onClick={() => langue !== l.code && definirLangue(l.code)}
          className={`rounded px-2 py-0.5 font-medium ${langue === l.code ? actif : inactif}`}
        >
          {l.libelle}
        </button>
      ))}
    </div>
  );
}
