import { PageCrud } from "../../composants/PageCrud";
import type { Utilisateur } from "../../types";

export function PageUtilisateurs() {
  return (
    <PageCrud<Utilisateur>
      titre="Utilisateurs"
      url="/utilisateurs/"
      cleLigne={(u) => u.id}
      valeursParDefaut={{ role: "PROFESSEUR", actif: true }}
      colonnes={[
        { cle: "identifiant", titre: "Identifiant" },
        { cle: "nom", titre: "Nom" },
        { cle: "prenom", titre: "Prenom" },
        { cle: "role", titre: "Role" },
        {
          cle: "actif", titre: "Statut",
          rendu: (u) => (
            <span className={u.actif ? "text-accent-vert" : "text-accent-rouge"}>
              {u.actif ? "Actif" : "Inactif"}
            </span>
          ),
        },
      ]}
      champs={[
        { nom: "identifiant", label: "Identifiant", requis: true },
        { nom: "mot_de_passe", label: "Mot de passe", type: "texte", placeholder: "Laisser vide pour ne pas changer" },
        { nom: "nom", label: "Nom", requis: true },
        { nom: "prenom", label: "Prenom" },
        { nom: "telephone", label: "Telephone" },
        {
          nom: "role", label: "Role", type: "select", requis: true, optionsStatiques: [
            { value: "ADMINISTRATEUR", label: "Administrateur" },
            { value: "DIRECTEUR", label: "Directeur" },
            { value: "RESPONSABLE_SCOLARITE", label: "Responsable de la scolarite" },
            { value: "RESPONSABLE_PEDAGOGIQUE", label: "Responsable pedagogique" },
            { value: "COMPTABLE", label: "Comptable" },
            { value: "PROFESSEUR", label: "Professeur" },
          ],
        },
        {
          nom: "professeur", label: "Fiche professeur liee (si role Professeur)", type: "select",
          optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => `${p.nom_complet} (${p.matricule})`,
        },
        { nom: "actif", label: "Actif", type: "checkbox" },
      ]}
    />
  );
}
