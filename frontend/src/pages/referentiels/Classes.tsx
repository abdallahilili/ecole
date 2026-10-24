import { PageCrud } from "../../composants/PageCrud";
import type { Classe } from "../../types";

export function PageClasses() {
  return (
    <PageCrud<Classe>
      titre="Classes"
      url="/referentiels/classes/"
      cleLigne={(c) => c.id}
      valeursParDefaut={{ capacite: 40 }}
      colonnes={[
        { cle: "nom", titre: "Classe" },
        { cle: "niveau_nom", titre: "Niveau" },
        { cle: "annee_scolaire_libelle", titre: "Annee scolaire" },
        { cle: "effectif", titre: "Effectif", alignerDroite: true },
        { cle: "capacite", titre: "Capacite", alignerDroite: true },
      ]}
      champs={[
        { nom: "nom", label: "Nom de la classe", requis: true, colonnePleine: true },
        {
          nom: "niveau", label: "Niveau", type: "select", requis: true,
          optionsUrl: "/referentiels/niveaux/", optionLabel: (n) => n.nom,
        },
        {
          nom: "annee_scolaire", label: "Annee scolaire", type: "select", requis: true,
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
        { nom: "capacite", label: "Capacite maximale", type: "nombre", requis: true },
        {
          nom: "salle_principale", label: "Salle principale", type: "select",
          optionsUrl: "/referentiels/salles/", optionLabel: (s) => `${s.nom} (${s.capacite} places)`,
        },
      ]}
    />
  );
}
