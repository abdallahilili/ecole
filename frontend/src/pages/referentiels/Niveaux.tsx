import { PageCrud } from "../../composants/PageCrud";
import type { Niveau } from "../../types";

import { tr } from "../../i18n";
export function PageNiveaux() {
  return (
    <PageCrud<Niveau>
      titre={tr("Niveaux")}
      url="/referentiels/niveaux/"
      cleLigne={(n) => n.id}
      colonnes={[
        { cle: "ordre", titre: tr("Ordre") },
        { cle: "nom", titre: tr("Nom") },
        { cle: "nom_ar", titre: tr("Nom (arabe)") },
        { cle: "code", titre: tr("Code") },
      ]}
      champs={[
        { nom: "nom", label: tr("Nom"), requis: true, colonnePleine: true },
        { nom: "nom_ar", label: tr("Nom (arabe)"), colonnePleine: true, direction: "rtl" },
        { nom: "code", label: tr("Code"), requis: true },
        { nom: "ordre", label: tr("Ordre pedagogique"), type: "nombre" },
      ]}
    />
  );
}
