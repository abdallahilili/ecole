import { PageCrud } from "../../composants/PageCrud";
import type { Groupe } from "../../types";

import { tr } from "../../i18n";
export function PageGroupes() {
  return (
    <PageCrud<Groupe>
      titre={tr("Groupes")}
      url="/referentiels/groupes/"
      cleLigne={(g) => g.id}
      champRecherche={false}
      colonnes={[
        { cle: "nom", titre: tr("Groupe") },
        { cle: "classe_nom", titre: tr("Classe") },
      ]}
      champs={[
        { nom: "nom", label: tr("Nom du groupe"), requis: true, colonnePleine: true },
        {
          nom: "classe", label: tr("Classe"), type: "select", requis: true,
          optionsUrl: "/referentiels/classes/?annee_active=1", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
      ]}
    />
  );
}
