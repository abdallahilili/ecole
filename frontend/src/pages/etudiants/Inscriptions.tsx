import { Link } from "react-router-dom";
import { Eye } from "lucide-react";
import { PageCrud } from "../../composants/PageCrud";
import type { Inscription } from "../../types";
import { Badge } from "../../composants/Badge";
import { SelecteurEtudiant } from "../../composants/SelecteurEtudiant";
import { api } from "../../services/api";
import { formaterMontant, UNITE_MONETAIRE } from "../../services/fichiers";

import { tr } from "../../i18n";

/** Choix d'une classe : le champ « Montant mensuel » est pre-rempli avec son tarif (modifiable ensuite). */
function proposerMontant(nom: string, classe: string) {
  if (nom !== "classe") return;
  if (!classe) return { montant_mensuel: "" };
  return api.get("/etudiants/inscriptions/montant-defaut/", { params: { classe } })
    .then(({ data }) => ({ montant_mensuel: data.montant_mensuel ?? "" }))
    .catch(() => undefined);
}

function adresseFiche(i: Inscription) {
  return `/etudiants/fiche/${i.etudiant}?inscription=${i.id}`;
}

export function PageInscriptions() {
  return (
    <PageCrud<Inscription>
      titre={tr("Inscriptions")}
      url="/etudiants/inscriptions/"
      cleLigne={(i) => i.id}
      champRecherche={false}
      largeurForm="max-w-2xl"
      valeursParDefaut={{ type_inscription: "INSCRIPTION", statut: "ACTIVE" }}
      estInactif={(i) => i.statut !== "ACTIVE"}
      surChangement={proposerMontant}
      actionsLigne={(i) => (
        <Link to={adresseFiche(i)} className="text-texte-attenue hover:text-entete" title={tr("Detail : fiche de l'etudiant et de paiement")}>
          <Eye size={15} />
        </Link>
      )}
      colonnes={[
        { cle: "numero_inscription", titre: tr("N° d'inscription"), rendu: (i) => <span className="font-medium">{i.numero_inscription}</span> },
        { cle: "etudiant_matricule", titre: tr("Matricule") },
        {
          cle: "etudiant_nom", titre: tr("Etudiant"),
          rendu: (i) => <Link to={adresseFiche(i)} className="text-entete hover:underline">{i.etudiant_nom}</Link>,
        },
        { cle: "annee_scolaire_libelle", titre: tr("Annee") },
        { cle: "classe_nom", titre: tr("Classe") },
        { cle: "groupe_nom", titre: tr("Groupe") },
        { cle: "montant_mensuel", titre: tr("Montant mensuel"), alignerDroite: true, rendu: (i) => formaterMontant(i.montant_mensuel) },
        { cle: "statut", titre: tr("Statut"), rendu: (i) => <Badge statut={i.statut} /> },
      ]}
      champs={[
        {
          nom: "etudiant", label: tr("Etudiant"), requis: true, etape: tr("Etudiant"), colonnePleine: true,
          rendu: (valeur, onChange) => <SelecteurEtudiant valeur={valeur} onChange={onChange} />,
        },
        {
          nom: "annee_scolaire", label: tr("Annee scolaire"), type: "select", requis: true, etape: tr("Classe et frais"),
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
        {
          nom: "classe", label: tr("Classe"), type: "select", requis: true,
          optionsUrl: "/referentiels/classes/?annee_active=1", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
        },
        {
          nom: "montant_mensuel", label: `${tr("Montant mensuel")} (${UNITE_MONETAIRE})`, type: "decimal",
          visible: (valeurs) => !!valeurs.classe,
          aide: tr("Tarif de la classe, modifiable. La fiche de paiement des mois est creee avec l'inscription."),
        },
        {
          nom: "groupe", label: tr("Groupe"), type: "select",
          optionsUrl: "/referentiels/groupes/", optionLabel: (g) => `${g.classe_nom} - ${g.nom}`,
        },
        {
          nom: "type_inscription", label: tr("Type"), type: "select", etape: tr("Details"), optionsStatiques: [
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
