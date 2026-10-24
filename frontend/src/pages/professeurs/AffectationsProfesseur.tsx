import { PageCrud } from "../../composants/PageCrud";
import type { AffectationProfesseur } from "../../types";

export function PageAffectationsProfesseur() {
  return (
    <PageCrud<AffectationProfesseur>
      titre="Affectations des professeurs"
      url="/professeurs/affectations/"
      cleLigne={(a) => a.id}
      champRecherche={false}
      colonnes={[
        { cle: "professeur_nom", titre: "Professeur" },
        { cle: "matiere_nom", titre: "Matiere" },
        { cle: "classe_nom", titre: "Classe" },
        { cle: "groupe_nom", titre: "Groupe" },
        { cle: "annee_scolaire_libelle", titre: "Annee" },
      ]}
      champs={[
        {
          nom: "professeur", label: "Professeur", type: "select", requis: true,
          optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => `${p.nom_complet} (${p.matricule})`,
        },
        {
          nom: "matiere", label: "Matiere", type: "select", requis: true,
          optionsUrl: "/referentiels/matieres/", optionLabel: (m) => m.nom,
        },
        {
          nom: "classe", label: "Classe", type: "select", requis: true,
          optionsUrl: "/referentiels/classes/", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        {
          nom: "groupe", label: "Groupe (optionnel)", type: "select",
          optionsUrl: "/referentiels/groupes/", optionLabel: (g) => `${g.classe_nom} - ${g.nom}`,
        },
        {
          nom: "annee_scolaire", label: "Annee scolaire", type: "select", requis: true,
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
      ]}
    />
  );
}
