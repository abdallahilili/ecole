import { PageCrud } from "../../composants/PageCrud";
import type { AffectationProfesseur } from "../../types";

import { tr } from "../../i18n";
export function PageAffectationsProfesseur() {
  return (
    <PageCrud<AffectationProfesseur>
      titre={tr("Affectations des professeurs")}
      url="/professeurs/affectations/"
      cleLigne={(a) => a.id}
      champRecherche={false}
      colonnes={[
        { cle: "professeur_nom", titre: tr("Professeur") },
        { cle: "matiere_nom", titre: tr("Matiere") },
        { cle: "classe_nom", titre: tr("Classe") },
        { cle: "groupe_nom", titre: tr("Groupe") },
        { cle: "annee_scolaire_libelle", titre: tr("Annee") },
      ]}
      champs={[
        {
          nom: "professeur", label: tr("Professeur"), type: "select", requis: true,
          optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => `${p.nom_complet} (${p.matricule})`,
        },
        {
          nom: "matiere", label: tr("Matiere"), type: "select", requis: true,
          optionsUrl: "/referentiels/matieres/", optionLabel: (m) => m.nom_affiche ?? m.nom,
        },
        {
          nom: "classe", label: tr("Classe"), type: "select", requis: true,
          optionsUrl: "/referentiels/classes/?annee_active=1", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        {
          nom: "groupe", label: tr("Groupe (optionnel)"), type: "select",
          optionsUrl: "/referentiels/groupes/", optionLabel: (g) => `${g.classe_nom} - ${g.nom}`,
        },
        {
          nom: "annee_scolaire", label: tr("Annee scolaire"), type: "select", requis: true,
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
      ]}
    />
  );
}
