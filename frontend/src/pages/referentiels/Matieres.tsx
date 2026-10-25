import { Link } from "react-router-dom";
import { PageCrud } from "../../composants/PageCrud";
import type { Matiere } from "../../types";

import { tr } from "../../i18n";
export function PageMatieres() {
  return (
    <div>
      <div className="mb-3">
        <Link to="/matieres/coefficients" className="text-sm text-entete hover:underline">
          {tr("Gerer les coefficients et volumes horaires par classe →")}
        </Link>
      </div>
      <PageCrud<Matiere>
      titre={tr("Matieres")}
      url="/referentiels/matieres/"
      cleLigne={(m) => m.id}
      colonnes={[
        { cle: "nom", titre: tr("Nom") },
        { cle: "nom_ar", titre: tr("Nom (arabe)") },
        { cle: "code", titre: tr("Code") },
        { cle: "description", titre: tr("Description") },
      ]}
      valeursParDefaut={{ actif: true }}
      champs={[
        { nom: "nom", label: tr("Nom"), requis: true, colonnePleine: true },
        { nom: "nom_ar", label: tr("Nom (arabe)"), colonnePleine: true, direction: "rtl" },
        { nom: "code", label: tr("Code"), requis: true },
        { nom: "description", label: tr("Description"), type: "textarea", colonnePleine: true },
        { nom: "actif", label: tr("Actif (decocher s'il n'est plus utilise)"), type: "checkbox" },
      ]}
      />
    </div>
  );
}
