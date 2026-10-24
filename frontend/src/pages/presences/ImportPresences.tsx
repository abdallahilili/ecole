import { ImportExcel } from "../../composants/ImportExcel";
import type { LigneApercu } from "../../composants/ImportExcel";
import { Badge } from "../../composants/Badge";
import type { StatutPresence } from "../../types";

interface LignePresence extends LigneApercu {
  statut: StatutPresence | null;
  ancien_statut: StatutPresence | null;
}

interface Props {
  cours: Record<string, string>;
  ouverte: boolean;
  onFermer: () => void;
  onImporte: (idSeance: number) => void;
}

/** Import Excel des presences d'un cours (modele pre-rempli avec les eleves de la classe). */
export function ImportPresences({ cours, ouverte, onFermer, onImporte }: Props) {
  return (
    <ImportExcel<LignePresence>
      titre="Importer les presences depuis Excel"
      ouverte={ouverte}
      onFermer={onFermer}
      consignes={
        <ol className="list-decimal space-y-1 pl-5">
          <li>Telechargez le modele du cours (il contient les eleves de la classe).</li>
          <li>Renseignez le statut : <b>P</b> (present), <b>A</b> (absent) ou <b>R</b> (retard).</li>
          <li>Importez le fichier, controlez l&apos;apercu, puis confirmez. Rien n&apos;est enregistre avant la confirmation.</li>
        </ol>
      }
      urlModele="/presences/seances/modele-import/"
      nomModele="modele_presences.xlsx"
      urlImport="/presences/seances/importer/"
      champs={cours}
      titreValeur="Statut"
      rendreValeur={(l) => (
        <>
          {l.ancien_statut && <span className="mr-1 text-texte-attenue line-through">{l.ancien_statut}</span>}
          {l.statut && <Badge statut={l.statut} />}
        </>
      )}
      onImporte={(donnees) => onImporte(donnees.seance)}
    />
  );
}
