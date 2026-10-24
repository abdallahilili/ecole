import type { ReactNode } from "react";

interface Props {
  valeur: ReactNode;
  libelle: string;
  icone?: ReactNode;
  accent?: "vert" | "rouge" | "neutre";
}

const BANDEAU: Record<string, string> = {
  vert: "bg-accent-vert",
  rouge: "bg-accent-rouge",
  neutre: "bg-bordure",
};

/** Carte KPI a bandeau colore en haut, inspiree des cartes du tableau de
 * bord Acumatica (image de reference) : fond blanc, icone + grand chiffre
 * en gras, libelle en dessous. */
export function CarteKpi({ valeur, libelle, icone, accent = "neutre" }: Props) {
  return (
    <div className="overflow-hidden rounded-md border border-bordure bg-fond-carte shadow-carte">
      <div className={`h-1 ${BANDEAU[accent]}`} />
      <div className="flex items-center gap-3 px-4 py-4">
        {icone && <div className="text-texte-attenue">{icone}</div>}
        <div>
          <div className="text-2xl font-bold leading-none text-texte">{valeur}</div>
          <div className="mt-1 text-sm text-texte-attenue">{libelle}</div>
        </div>
      </div>
    </div>
  );
}
