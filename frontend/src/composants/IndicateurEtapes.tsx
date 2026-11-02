import { Check } from "lucide-react";

interface Props {
  titres: string[];
  courante: number;
  onAller: (index: number) => void;
  /** Toutes les etapes sont atteignables d'un clic (modification) ; sinon seulement celles deja vues. */
  libre?: boolean;
}

/** Fil d'etapes d'un formulaire : cercles numerotes relies par un trait, l'etape en cours en couleur. */
export function IndicateurEtapes({ titres, courante, onAller, libre = false }: Props) {
  return (
    <ol className="mb-4 flex items-center">
      {titres.map((titre, index) => {
        const faite = index < courante;
        const active = index === courante;
        const dernier = index === titres.length - 1;
        return (
          <li key={`${index}-${titre}`} className={`flex items-center ${dernier ? "" : "flex-1"}`}>
            <button
              type="button"
              disabled={!libre && index > courante}
              onClick={() => onAller(index)}
              aria-current={active ? "step" : undefined}
              className="flex items-center gap-2 disabled:cursor-default"
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  active ? "bg-entete text-white" : faite ? "bg-accent-vert text-white" : "border border-bordure bg-white text-texte-attenue"
                }`}
              >
                {faite ? <Check size={14} /> : index + 1}
              </span>
              <span className={`text-sm ${active ? "font-semibold text-texte" : "hidden text-texte-attenue sm:inline"}`}>{titre}</span>
            </button>
            {!dernier && <span className={`mx-3 h-px flex-1 ${faite ? "bg-accent-vert" : "bg-bordure"}`} />}
          </li>
        );
      })}
    </ol>
  );
}
