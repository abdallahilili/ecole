import { PageCrud } from "../../composants/PageCrud";
import type { Professeur } from "../../types";
import { Badge } from "../../composants/Badge";

import { tr } from "../../i18n";
export function PageProfesseurs() {
  return (
    <PageCrud<Professeur>
      titre={tr("Professeurs")}
      url="/professeurs/professeurs/"
      cleLigne={(p) => p.id}
      valeursParDefaut={{ statut: "ACTIF", mode_remuneration: "HORAIRE" }}
      colonnes={[
        { cle: "matricule", titre: tr("Matricule") },
        { cle: "nom_complet", titre: tr("Nom complet") },
        { cle: "specialite", titre: tr("Specialite") },
        { cle: "telephone", titre: tr("Telephone") },
        {
          cle: "mode_remuneration", titre: tr("Remuneration"),
          rendu: (p) => p.mode_remuneration === "HORAIRE" ? tr("{0} / heure", p.tarif_horaire) : tr("{0} fixe", p.salaire_fixe),
        },
        { cle: "statut", titre: tr("Statut"), rendu: (p) => <Badge statut={p.statut} /> },
      ]}
      champs={[
        { nom: "matricule", label: tr("Matricule"), requis: true },
        { nom: "nom", label: tr("Nom"), requis: true },
        { nom: "prenom", label: tr("Prenom"), requis: true },
        { nom: "telephone", label: tr("Telephone") },
        { nom: "email", label: tr("Email"), type: "email" },
        { nom: "adresse", label: tr("Adresse"), colonnePleine: true },
        { nom: "specialite", label: tr("Specialite"), colonnePleine: true },
        { nom: "date_recrutement", label: tr("Date de recrutement"), type: "date" },
        {
          nom: "statut", label: tr("Statut"), type: "select",
          optionsStatiques: [{ value: "ACTIF", label: tr("Actif") }, { value: "INACTIF", label: tr("Inactif") }],
        },
        {
          nom: "mode_remuneration", label: tr("Mode de remuneration"), type: "select",
          optionsStatiques: [{ value: "HORAIRE", label: tr("Au nombre d'heures") }, { value: "FIXE", label: tr("Salaire fixe") }],
        },
        { nom: "tarif_horaire", label: tr("Tarif horaire"), type: "decimal" },
        { nom: "salaire_fixe", label: tr("Salaire fixe"), type: "decimal" },
      ]}
    />
  );
}
