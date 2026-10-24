import { PageCrud } from "../../composants/PageCrud";
import type { Professeur } from "../../types";
import { Badge } from "../../composants/Badge";

export function PageProfesseurs() {
  return (
    <PageCrud<Professeur>
      titre="Professeurs"
      url="/professeurs/professeurs/"
      cleLigne={(p) => p.id}
      valeursParDefaut={{ statut: "ACTIF", mode_remuneration: "HORAIRE" }}
      colonnes={[
        { cle: "matricule", titre: "Matricule" },
        { cle: "nom_complet", titre: "Nom complet" },
        { cle: "specialite", titre: "Specialite" },
        { cle: "telephone", titre: "Telephone" },
        {
          cle: "mode_remuneration", titre: "Remuneration",
          rendu: (p) => p.mode_remuneration === "HORAIRE" ? `${p.tarif_horaire} / heure` : `${p.salaire_fixe} fixe`,
        },
        { cle: "statut", titre: "Statut", rendu: (p) => <Badge statut={p.statut} /> },
      ]}
      champs={[
        { nom: "matricule", label: "Matricule", requis: true },
        { nom: "nom", label: "Nom", requis: true },
        { nom: "prenom", label: "Prenom", requis: true },
        { nom: "telephone", label: "Telephone" },
        { nom: "email", label: "Email", type: "email" },
        { nom: "adresse", label: "Adresse", colonnePleine: true },
        { nom: "specialite", label: "Specialite", colonnePleine: true },
        { nom: "date_recrutement", label: "Date de recrutement", type: "date" },
        {
          nom: "statut", label: "Statut", type: "select",
          optionsStatiques: [{ value: "ACTIF", label: "Actif" }, { value: "INACTIF", label: "Inactif" }],
        },
        {
          nom: "mode_remuneration", label: "Mode de remuneration", type: "select",
          optionsStatiques: [{ value: "HORAIRE", label: "Au nombre d'heures" }, { value: "FIXE", label: "Salaire fixe" }],
        },
        { nom: "tarif_horaire", label: "Tarif horaire", type: "decimal" },
        { nom: "salaire_fixe", label: "Salaire fixe", type: "decimal" },
      ]}
    />
  );
}
