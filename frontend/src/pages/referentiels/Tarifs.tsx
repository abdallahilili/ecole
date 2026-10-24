import { PageCrud } from "../../composants/PageCrud";
import type { TarifClasse } from "../../types";

/** Tarif (mensualite) propre a chaque classe, en ouguiya (UM) : ex. 6AF = 900 UM. */
export function PageTarifs() {
  return (
    <PageCrud<TarifClasse>
      titre="Tarifs par classe"
      url="/referentiels/tarifs-classes/"
      cleLigne={(t) => t.id}
      colonnes={[
        { cle: "classe_nom", titre: "Classe" },
        { cle: "niveau_nom", titre: "Niveau" },
        { cle: "annee_scolaire_libelle", titre: "Annee scolaire" },
        {
          cle: "montant", titre: "Tarif", alignerDroite: true,
          rendu: (t) => `${Number(t.montant).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} UM`,
        },
      ]}
      champs={[
        {
          nom: "classe", label: "Classe", type: "select", requis: true, colonnePleine: true,
          optionsUrl: "/referentiels/classes/", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        { nom: "montant", label: "Montant (UM)", type: "decimal", requis: true, colonnePleine: true },
      ]}
    />
  );
}
