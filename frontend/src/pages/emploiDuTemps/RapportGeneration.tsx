import type { RapportGeneration } from "../../types";

/** Compte rendu de la generation automatique : score, ressources insuffisantes, conflits restants. */
export function RapportGenerationPanneau({ rapport }: { rapport: Partial<RapportGeneration> }) {
  if (rapport.unites === undefined) return null;
  return (
    <div className="space-y-2 text-sm">
      <p>
        <b>{rapport.seances_creees}</b> seance(s) placee(s) en <b>{rapport.duree_s} s</b> ({rapport.generations} generations,
        {" "}{rapport.arret}). Penalites de preference : {rapport.penalites}.
      </p>
      {rapport.publiable ? (
        <p className="rounded border border-accent-vert bg-green-50 px-3 py-2 text-accent-vert">
          Aucun conflit : l&apos;emploi du temps peut etre publie apres verification dans l&apos;editeur.
        </p>
      ) : (
        <p className="rounded border border-accent-rouge bg-red-50 px-3 py-2 text-accent-rouge">
          {rapport.conflits?.length ?? 0} conflit(s) non resolu(s) : cet emploi du temps ne peut pas etre publie.
        </p>
      )}
      {(rapport.diagnostics?.length ?? 0) > 0 && (
        <div>
          <p className="font-medium text-texte">Ressources ou donnees insuffisantes :</p>
          <ul className="list-disc pl-5 text-texte-attenue">{rapport.diagnostics!.map((d) => <li key={d}>{d}</li>)}</ul>
        </div>
      )}
      {(rapport.conflits?.length ?? 0) > 0 && (
        <div>
          <p className="font-medium text-texte">Conflits restants :</p>
          <ul className="list-disc pl-5 text-accent-rouge">{rapport.conflits!.slice(0, 15).map((c) => <li key={c}>{c}</li>)}</ul>
        </div>
      )}
    </div>
  );
}
