import { PageCrud } from "../../composants/PageCrud";
import type { Inscription } from "../../types";
import { Badge } from "../../composants/Badge";

import { tr } from "../../i18n";
export function PageInscriptions() {
  return (
    <PageCrud<Inscription>
      titre={tr("Inscriptions")}
      url="/etudiants/inscriptions/"
      cleLigne={(i) => i.id}
      champRecherche={false}
      valeursParDefaut={{ type_inscription: "INSCRIPTION", statut: "ACTIVE" }}
      colonnes={[
        { cle: "etudiant_matricule", titre: tr("Matricule") },
        { cle: "etudiant_nom", titre: tr("Etudiant") },
        { cle: "annee_scolaire_libelle", titre: tr("Annee") },
        { cle: "classe_nom", titre: tr("Classe") },
        { cle: "groupe_nom", titre: tr("Groupe") },
        { cle: "statut", titre: tr("Statut"), rendu: (i) => <Badge statut={i.statut} /> },
      ]}
      champs={[
        {
          nom: "etudiant", label: tr("Etudiant"), type: "select", requis: true,
          optionsUrl: "/etudiants/etudiants/", optionLabel: (e) => `${e.nom_complet} (${e.matricule})`,
        },
        {
          nom: "annee_scolaire", label: tr("Annee scolaire"), type: "select", requis: true,
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
        {
          nom: "classe", label: tr("Classe"), type: "select", requis: true,
          optionsUrl: "/referentiels/classes/?annee_active=1", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        {
          nom: "groupe", label: tr("Groupe"), type: "select",
          optionsUrl: "/referentiels/groupes/", optionLabel: (g) => `${g.classe_nom} - ${g.nom}`,
        },
        {
          nom: "type_inscription", label: tr("Type"), type: "select", optionsStatiques: [
            { value: "INSCRIPTION", label: tr("Nouvelle inscription") },
            { value: "REINSCRIPTION", label: tr("Reinscription") },
            { value: "TRANSFERT", label: tr("Transfert") },
          ],
        },
        {
          nom: "statut", label: tr("Statut"), type: "select", optionsStatiques: [
            { value: "ACTIVE", label: tr("Active") },
            { value: "TRANSFEREE", label: tr("Transferee") },
            { value: "ABANDON", label: tr("Abandon") },
            { value: "DIPLOME", label: tr("Diplome / fin de cycle") },
          ],
        },
        { nom: "date_inscription", label: tr("Date d'inscription"), type: "date", requis: true },
        { nom: "date_fin", label: tr("Date de fin"), type: "date" },
        { nom: "etablissement_origine", label: tr("Etablissement d'origine"), colonnePleine: true },
        { nom: "observations", label: tr("Observations"), type: "textarea", colonnePleine: true },
      ]}
    />
  );
}
