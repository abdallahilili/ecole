import { Link } from "react-router-dom";
import { PageCrud } from "../../composants/PageCrud";
import type { GrilleFrais } from "../../types";

export function PageGrillesFrais() {
  return (
    <div>
      <div className="mb-3">
        <Link to="/scolarite" className="text-sm text-entete hover:underline">&larr; Retour aux paiements</Link>
      </div>
      <PageCrud<GrilleFrais>
      titre="Grilles de frais"
      url="/scolarite/grilles-frais/"
      cleLigne={(g) => g.id}
      champRecherche={false}
      valeursParDefaut={{ nombre_mois: 9, frais_inscription: 0 }}
      colonnes={[
        { cle: "annee_scolaire_libelle", titre: "Annee scolaire" },
        { cle: "niveau_nom", titre: "Niveau" },
        { cle: "montant_mensuel", titre: "Mensualite", alignerDroite: true },
        { cle: "frais_inscription", titre: "Frais d'inscription", alignerDroite: true },
        { cle: "nombre_mois", titre: "Nombre de mois", alignerDroite: true },
      ]}
      champs={[
        {
          nom: "annee_scolaire", label: "Annee scolaire", type: "select", requis: true,
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
        {
          nom: "niveau", label: "Niveau", type: "select", requis: true,
          optionsUrl: "/referentiels/niveaux/", optionLabel: (n) => n.nom,
        },
        { nom: "montant_mensuel", label: "Montant mensuel", type: "decimal", requis: true },
        { nom: "frais_inscription", label: "Frais d'inscription", type: "decimal" },
        { nom: "nombre_mois", label: "Nombre de mois", type: "nombre" },
      ]}
      />
    </div>
  );
}
