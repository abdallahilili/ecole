import { PageCrud } from "../../composants/PageCrud";
import type { Groupe } from "../../types";

export function PageGroupes() {
  return (
    <PageCrud<Groupe>
      titre="Groupes"
      url="/referentiels/groupes/"
      cleLigne={(g) => g.id}
      champRecherche={false}
      colonnes={[
        { cle: "nom", titre: "Groupe" },
        { cle: "classe_nom", titre: "Classe" },
      ]}
      champs={[
        { nom: "nom", label: "Nom du groupe", requis: true, colonnePleine: true },
        {
          nom: "classe", label: "Classe", type: "select", requis: true,
          optionsUrl: "/referentiels/classes/", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
      ]}
    />
  );
}
