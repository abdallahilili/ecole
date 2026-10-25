import { PageCrud } from "../../composants/PageCrud";
import type { TarifClasse } from "../../types";

import { tr } from "../../i18n";
import { UNITE_MONETAIRE } from "../../services/fichiers";
/** Tarif (mensualite) propre a chaque classe, en ouguiya (UM) : ex. 6AF = 900 UM. */
export function PageTarifs() {
  return (
    <PageCrud<TarifClasse>
      titre={tr("Tarifs par classe")}
      url="/referentiels/tarifs-classes/"
      cleLigne={(t) => t.id}
      colonnes={[
        { cle: "classe_nom", titre: tr("Classe") },
        { cle: "niveau_nom", titre: tr("Niveau") },
        { cle: "annee_scolaire_libelle", titre: tr("Annee scolaire") },
        {
          cle: "montant", titre: tr("Tarif"), alignerDroite: true,
          rendu: (t) => `${Number(t.montant).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ${UNITE_MONETAIRE}`,
        },
      ]}
      champs={[
        {
          nom: "classe", label: tr("Classe"), type: "select", requis: true, colonnePleine: true,
          optionsUrl: "/referentiels/classes/?annee_active=1", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        { nom: "montant", label: tr("Montant (UM)"), type: "decimal", requis: true, colonnePleine: true },
      ]}
    />
  );
}
