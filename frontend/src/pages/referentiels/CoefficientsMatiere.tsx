import { Link } from "react-router-dom";
import { PageCrud } from "../../composants/PageCrud";
import type { AffectationMatiereClasse } from "../../types";

/** Coefficient et volume horaire d'une matiere, qui peuvent varier
 * librement d'une classe a l'autre (exigence explicite du cahier des
 * charges : jamais de coefficient unique impose a toutes les classes). */
export function PageCoefficientsMatiere() {
  return (
    <div>
      <div className="mb-3">
        <Link to="/matieres" className="text-sm text-entete hover:underline">&larr; Retour aux matieres</Link>
      </div>
      <PageCrud<AffectationMatiereClasse>
      titre="Coefficients et volumes horaires par classe"
      url="/referentiels/affectations-matiere-classe/"
      cleLigne={(a) => a.id}
      champRecherche={false}
      valeursParDefaut={{ coefficient: 1, volume_horaire_hebdo: 1, nombre_seances_semaine: 1 }}
      colonnes={[
        { cle: "matiere_nom", titre: "Matiere" },
        { cle: "classe_nom", titre: "Classe" },
        { cle: "coefficient", titre: "Coefficient", alignerDroite: true },
        { cle: "volume_horaire_hebdo", titre: "Vol. horaire/sem.", alignerDroite: true },
        { cle: "nombre_seances_semaine", titre: "Seances/sem.", alignerDroite: true },
      ]}
      champs={[
        {
          nom: "matiere", label: "Matiere", type: "select", requis: true,
          optionsUrl: "/referentiels/matieres/", optionLabel: (m) => m.nom,
        },
        {
          nom: "classe", label: "Classe", type: "select", requis: true,
          optionsUrl: "/referentiels/classes/", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        { nom: "coefficient", label: "Coefficient", type: "decimal", requis: true },
        { nom: "volume_horaire_hebdo", label: "Volume horaire hebdomadaire", type: "decimal", requis: true },
        { nom: "nombre_seances_semaine", label: "Nombre de seances/semaine", type: "nombre" },
      ]}
      />
    </div>
  );
}
