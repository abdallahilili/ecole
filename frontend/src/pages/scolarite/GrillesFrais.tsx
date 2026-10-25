import { Link } from "react-router-dom";
import { PageCrud } from "../../composants/PageCrud";
import type { GrilleFrais } from "../../types";

import { tr } from "../../i18n";
export function PageGrillesFrais() {
  return (
    <div>
      <div className="mb-3">
        <Link to="/scolarite" className="text-sm text-entete hover:underline">{tr("← Retour aux paiements")}</Link>
      </div>
      <PageCrud<GrilleFrais>
      titre={tr("Grilles de frais")}
      url="/scolarite/grilles-frais/"
      cleLigne={(g) => g.id}
      champRecherche={false}
      valeursParDefaut={{ nombre_mois: 9, frais_inscription: 0, actif: true }}
      colonnes={[
        { cle: "annee_scolaire_libelle", titre: tr("Annee scolaire") },
        { cle: "niveau_nom", titre: tr("Niveau") },
        { cle: "montant_mensuel", titre: tr("Mensualite"), alignerDroite: true },
        { cle: "frais_inscription", titre: tr("Frais d'inscription"), alignerDroite: true },
        { cle: "nombre_mois", titre: tr("Nombre de mois"), alignerDroite: true },
      ]}
      champs={[
        {
          nom: "annee_scolaire", label: tr("Annee scolaire"), type: "select", requis: true,
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
        {
          nom: "niveau", label: tr("Niveau"), type: "select", requis: true,
          optionsUrl: "/referentiels/niveaux/", optionLabel: (n) => n.nom,
        },
        { nom: "montant_mensuel", label: tr("Montant mensuel"), type: "decimal", requis: true },
        { nom: "frais_inscription", label: tr("Frais d'inscription"), type: "decimal" },
        { nom: "nombre_mois", label: tr("Nombre de mois"), type: "nombre" },
        { nom: "actif", label: tr("Actif (decocher s'il n'est plus utilise)"), type: "checkbox" },
      ]}
      />
    </div>
  );
}
