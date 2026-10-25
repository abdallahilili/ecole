import { ImportExcel } from "../../composants/ImportExcel";
import type { LigneApercu } from "../../composants/ImportExcel";
import { Badge } from "../../composants/Badge";
import type { StatutPresence } from "../../types";

import { tr, tx } from "../../i18n";
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
      titre={tr("Importer les presences depuis Excel")}
      ouverte={ouverte}
      onFermer={onFermer}
      consignes={
        <ol className="list-decimal space-y-1 ps-5">
          <li>{tr("Telechargez le modele du cours (il contient les eleves de la classe).")}</li>
          <li>{tx("Renseignez le statut : {0} (present), {1} (absent) ou {2} (retard).", <b>P</b>, <b>A</b>, <b>R</b>)}</li>
          <li>{tr("Importez le fichier, controlez l'apercu, puis confirmez. Rien n'est enregistre avant la confirmation.")}</li>
        </ol>
      }
      urlModele="/presences/seances/modele-import/"
      nomModele="modele_presences.xlsx"
      urlImport="/presences/seances/importer/"
      champs={cours}
      titreValeur={tr("Statut")}
      rendreValeur={(l) => (
        <>
          {l.ancien_statut && <span className="me-1 text-texte-attenue line-through">{l.ancien_statut}</span>}
          {l.statut && <Badge statut={l.statut} />}
        </>
      )}
      onImporte={(donnees) => onImporte(donnees.seance)}
    />
  );
}
