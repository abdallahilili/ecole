import { Link } from "react-router-dom";
import { PageCrud } from "../../composants/PageCrud";
import type { AffectationMatiereClasse } from "../../types";

import { tr } from "../../i18n";
/** Coefficient et volume horaire d'une matiere, qui peuvent varier
 * librement d'une classe a l'autre (exigence explicite du cahier des
 * charges : jamais de coefficient unique impose a toutes les classes). */
export function PageCoefficientsMatiere() {
  return (
    <div>
      <div className="mb-3">
        <Link to="/matieres" className="text-sm text-entete hover:underline">{tr("← Retour aux matieres")}</Link>
      </div>
      <PageCrud<AffectationMatiereClasse>
      titre={tr("Coefficients et volumes horaires par classe")}
      url="/referentiels/affectations-matiere-classe/"
      cleLigne={(a) => a.id}
      champRecherche={false}
      valeursParDefaut={{ coefficient: 1, volume_horaire_hebdo: 1, nombre_seances_semaine: 1 }}
      colonnes={[
        { cle: "matiere_nom", titre: tr("Matiere") },
        { cle: "classe_nom", titre: tr("Classe") },
        { cle: "coefficient", titre: tr("Coefficient"), alignerDroite: true },
        { cle: "volume_horaire_hebdo", titre: tr("Vol. horaire/sem."), alignerDroite: true },
        { cle: "nombre_seances_semaine", titre: tr("Seances/sem."), alignerDroite: true },
      ]}
      champs={[
        {
          nom: "matiere", label: tr("Matiere"), type: "select", requis: true,
          optionsUrl: "/referentiels/matieres/", optionLabel: (m) => m.nom,
        },
        {
          nom: "classe", label: tr("Classe"), type: "select", requis: true,
          optionsUrl: "/referentiels/classes/?annee_active=1", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        { nom: "coefficient", label: tr("Coefficient"), type: "decimal", requis: true },
        { nom: "volume_horaire_hebdo", label: tr("Volume horaire hebdomadaire"), type: "decimal", requis: true },
        { nom: "nombre_seances_semaine", label: tr("Nombre de seances/semaine"), type: "nombre" },
      ]}
      />
    </div>
  );
}
