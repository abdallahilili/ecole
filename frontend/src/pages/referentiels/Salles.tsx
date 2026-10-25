import { PageCrud } from "../../composants/PageCrud";
import type { Salle } from "../../types";

import { tr } from "../../i18n";
export function PageSalles() {
  return (
    <PageCrud<Salle>
      titre={tr("Salles")}
      url="/referentiels/salles/"
      cleLigne={(s) => s.id}
      valeursParDefaut={{ disponible: true, capacite: 30 }}
      colonnes={[
        { cle: "nom", titre: tr("Nom") },
        { cle: "capacite", titre: tr("Capacite") },
        { cle: "type_salle", titre: tr("Type") },
        {
          cle: "disponible", titre: tr("Disponible"),
          rendu: (s) => (
            <span className={s.disponible ? "text-accent-vert" : "text-accent-rouge"}>
              {s.disponible ? tr("Oui") : tr("Non")}
            </span>
          ),
        },
      ]}
      champs={[
        { nom: "nom", label: tr("Nom"), requis: true, colonnePleine: true },
        { nom: "capacite", label: tr("Capacite"), type: "nombre", requis: true },
        { nom: "type_salle", label: tr("Type de salle") },
        { nom: "equipements", label: tr("Equipements"), colonnePleine: true },
        { nom: "disponible", label: tr("Disponible"), type: "checkbox" },
      ]}
    />
  );
}
