import { PageCrud } from "../../composants/PageCrud";
import type { Utilisateur } from "../../types";

import { tr } from "../../i18n";
export function PageUtilisateurs() {
  return (
    <PageCrud<Utilisateur>
      titre={tr("Utilisateurs")}
      url="/utilisateurs/"
      cleLigne={(u) => u.id}
      valeursParDefaut={{ role: "PROFESSEUR", actif: true }}
      colonnes={[
        { cle: "identifiant", titre: tr("Identifiant") },
        { cle: "nom", titre: tr("Nom") },
        { cle: "prenom", titre: tr("Prenom") },
        { cle: "role", titre: tr("Role") },
        {
          cle: "actif", titre: tr("Statut"),
          rendu: (u) => (
            <span className={u.actif ? "text-accent-vert" : "text-accent-rouge"}>
              {u.actif ? tr("Actif") : tr("Inactif")}
            </span>
          ),
        },
      ]}
      champs={[
        { nom: "identifiant", label: tr("Identifiant"), requis: true },
        {
          nom: "mot_de_passe", label: tr("Mot de passe"), type: "motdepasse", colonnePleine: true,
          placeholder: tr("Obligatoire a la creation (8 caracteres min.) - laisser vide pour ne pas le changer"),
        },
        { nom: "nom", label: tr("Nom"), requis: true },
        { nom: "prenom", label: tr("Prenom") },
        { nom: "telephone", label: tr("Telephone") },
        {
          nom: "role", label: tr("Role"), type: "select", requis: true, optionsStatiques: [
            { value: "ADMINISTRATEUR", label: tr("Administrateur") },
            { value: "DIRECTEUR", label: tr("Directeur") },
            { value: "RESPONSABLE_SCOLARITE", label: tr("Responsable de la scolarite") },
            { value: "RESPONSABLE_PEDAGOGIQUE", label: tr("Responsable pedagogique") },
            { value: "COMPTABLE", label: tr("Comptable") },
            { value: "PROFESSEUR", label: tr("Professeur") },
          ],
        },
        {
          nom: "professeur", label: tr("Fiche professeur liee (si role Professeur)"), type: "select",
          optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => `${p.nom_complet} (${p.matricule})`,
        },
        { nom: "actif", label: tr("Actif"), type: "checkbox" },
      ]}
    />
  );
}
