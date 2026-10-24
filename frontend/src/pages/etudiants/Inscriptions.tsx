import { PageCrud } from "../../composants/PageCrud";
import type { Inscription } from "../../types";
import { Badge } from "../../composants/Badge";

export function PageInscriptions() {
  return (
    <PageCrud<Inscription>
      titre="Inscriptions"
      url="/etudiants/inscriptions/"
      cleLigne={(i) => i.id}
      champRecherche={false}
      valeursParDefaut={{ type_inscription: "INSCRIPTION", statut: "ACTIVE" }}
      colonnes={[
        { cle: "etudiant_matricule", titre: "Matricule" },
        { cle: "etudiant_nom", titre: "Etudiant" },
        { cle: "annee_scolaire_libelle", titre: "Annee" },
        { cle: "classe_nom", titre: "Classe" },
        { cle: "groupe_nom", titre: "Groupe" },
        { cle: "statut", titre: "Statut", rendu: (i) => <Badge statut={i.statut} /> },
      ]}
      champs={[
        {
          nom: "etudiant", label: "Etudiant", type: "select", requis: true,
          optionsUrl: "/etudiants/etudiants/", optionLabel: (e) => `${e.nom_complet} (${e.matricule})`,
        },
        {
          nom: "annee_scolaire", label: "Annee scolaire", type: "select", requis: true,
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
        {
          nom: "classe", label: "Classe", type: "select", requis: true,
          optionsUrl: "/referentiels/classes/", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        {
          nom: "groupe", label: "Groupe", type: "select",
          optionsUrl: "/referentiels/groupes/", optionLabel: (g) => `${g.classe_nom} - ${g.nom}`,
        },
        {
          nom: "type_inscription", label: "Type", type: "select", optionsStatiques: [
            { value: "INSCRIPTION", label: "Nouvelle inscription" },
            { value: "REINSCRIPTION", label: "Reinscription" },
            { value: "TRANSFERT", label: "Transfert" },
          ],
        },
        {
          nom: "statut", label: "Statut", type: "select", optionsStatiques: [
            { value: "ACTIVE", label: "Active" },
            { value: "TRANSFEREE", label: "Transferee" },
            { value: "ABANDON", label: "Abandon" },
            { value: "DIPLOME", label: "Diplome / fin de cycle" },
          ],
        },
        { nom: "date_inscription", label: "Date d'inscription", type: "date", requis: true },
        { nom: "date_fin", label: "Date de fin", type: "date" },
        { nom: "etablissement_origine", label: "Etablissement d'origine", colonnePleine: true },
        { nom: "observations", label: "Observations", type: "textarea", colonnePleine: true },
      ]}
    />
  );
}
