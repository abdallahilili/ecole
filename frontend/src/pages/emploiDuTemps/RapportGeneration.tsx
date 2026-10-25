import type { RapportGeneration } from "../../types";

import { tr, tx } from "../../i18n";
/** Compte rendu de la generation automatique : score, ressources insuffisantes, conflits restants. */
export function RapportGenerationPanneau({ rapport }: { rapport: Partial<RapportGeneration> }) {
  if (rapport.unites === undefined) return null;
  return (
    <div className="space-y-2 text-sm">
      <p>
        {tx("{0} seance(s) placee(s) en {1} ({2} generations, {3}). Penalites de preference : {4}.", <b>{rapport.seances_creees}</b>, <b>{rapport.duree_s} s</b>, rapport.generations, rapport.arret, rapport.penalites)}
      </p>
      {rapport.publiable ? (
        <p className="rounded border border-accent-vert bg-green-50 px-3 py-2 text-accent-vert">
          {tr("Aucun conflit : l'emploi du temps peut etre publie apres verification dans l'editeur.")}
        </p>
      ) : (
        <p className="rounded border border-accent-rouge bg-red-50 px-3 py-2 text-accent-rouge"> {tr("{0} conflit(s) non resolu(s) : cet emploi du temps ne peut pas etre publie.", rapport.conflits?.length ?? 0)} </p>
      )}
      {(rapport.diagnostics?.length ?? 0) > 0 && (
        <div>
          <p className="font-medium text-texte">{tr("Ressources ou donnees insuffisantes :")}</p>
          <ul className="list-disc ps-5 text-texte-attenue">{rapport.diagnostics!.map((d) => <li key={d}>{d}</li>)}</ul>
        </div>
      )}
      {(rapport.conflits?.length ?? 0) > 0 && (
        <div>
          <p className="font-medium text-texte">{tr("Conflits restants :")}</p>
          <ul className="list-disc ps-5 text-accent-rouge">{rapport.conflits!.slice(0, 15).map((c) => <li key={c}>{c}</li>)}</ul>
        </div>
      )}
    </div>
  );
}
