import { lazy } from "react";
import type { ComponentType, ReactElement } from "react";
import { Navigate } from "react-router-dom";

/** Chaque page n'est telechargee qu'au premier affichage (decoupage du code par route) :
 * le chargement initial de l'application reste rapide. */
function page(charger: () => Promise<Record<string, ComponentType<any>>>, nom: string) {
  return lazy(() => charger().then((module) => ({ default: module[nom] })));
}

const PageTableauDeBord = page(() => import("../pages/TableauDeBord"), "PageTableauDeBord");
const PageAnneesScolaires = page(() => import("../pages/referentiels/AnneesScolaires"), "PageAnneesScolaires");
const PageNiveaux = page(() => import("../pages/referentiels/Niveaux"), "PageNiveaux");
const PageSalles = page(() => import("../pages/referentiels/Salles"), "PageSalles");
const PageClasses = page(() => import("../pages/referentiels/Classes"), "PageClasses");
const PageTarifs = page(() => import("../pages/referentiels/Tarifs"), "PageTarifs");
const PageGroupes = page(() => import("../pages/referentiels/Groupes"), "PageGroupes");
const PageMatieres = page(() => import("../pages/referentiels/Matieres"), "PageMatieres");
const PageCoefficientsMatiere = page(() => import("../pages/referentiels/CoefficientsMatiere"), "PageCoefficientsMatiere");
const PageEtudiants = page(() => import("../pages/etudiants/Etudiants"), "PageEtudiants");
const PageInscriptions = page(() => import("../pages/etudiants/Inscriptions"), "PageInscriptions");
const PageGrillesFrais = page(() => import("../pages/scolarite/GrillesFrais"), "PageGrillesFrais");
const PagePaiementsScolarite = page(() => import("../pages/scolarite/PaiementsScolarite"), "PagePaiementsScolarite");
const PageProfesseurs = page(() => import("../pages/professeurs/Professeurs"), "PageProfesseurs");
const PageAffectationsProfesseur = page(() => import("../pages/professeurs/AffectationsProfesseur"), "PageAffectationsProfesseur");
const PageUtilisateurs = page(() => import("../pages/utilisateurs/Utilisateurs"), "PageUtilisateurs");
const PagePresences = page(() => import("../pages/presences/Presences"), "PagePresences");
const PageHistoriquePresences = page(() => import("../pages/presences/HistoriquePresences"), "PageHistoriquePresences");
const PagePresencesProfesseurs = page(() => import("../pages/presences/PresencesProfesseurs"), "PagePresencesProfesseurs");
const PageNotifications = page(() => import("../pages/presences/Notifications"), "PageNotifications");
const PageParametres = page(() => import("../pages/parametres/Parametres"), "PageParametres");
const PageNotes = page(() => import("../pages/evaluations/Notes"), "PageNotes");
const PageResultats = page(() => import("../pages/evaluations/Resultats"), "PageResultats");
const PageEmploisDuTemps = page(() => import("../pages/emploiDuTemps/EmploisDuTemps"), "PageEmploisDuTemps");
const PageEditeurEmploi = page(() => import("../pages/emploiDuTemps/EditeurEmploi"), "PageEditeurEmploi");
const PagePlanification = page(() => import("../pages/emploiDuTemps/Planification"), "PagePlanification");
const PageDisponibilites = page(() => import("../pages/emploiDuTemps/Disponibilites"), "PageDisponibilites");
const PageRemuneration = page(() => import("../pages/remuneration/Remuneration"), "PageRemuneration");
const PageReleveDetail = page(() => import("../pages/remuneration/ReleveDetail"), "PageReleveDetail");
const PageMaRemuneration = page(() => import("../pages/remuneration/MaRemuneration"), "PageMaRemuneration");

export interface RouteProtegee {
  chemin: string;
  module: string;
  element: ReactElement;
}

export const routesProtegees: RouteProtegee[] = [
  { chemin: "/", module: "tableau_de_bord", element: <PageTableauDeBord /> },
  { chemin: "/annees-scolaires", module: "annees_scolaires", element: <PageAnneesScolaires /> },
  { chemin: "/niveaux", module: "niveaux", element: <PageNiveaux /> },
  { chemin: "/classes", module: "classes", element: <PageClasses /> },
  { chemin: "/tarifs", module: "tarifs", element: <PageTarifs /> },
  { chemin: "/groupes", module: "groupes", element: <PageGroupes /> },
  { chemin: "/salles", module: "salles", element: <PageSalles /> },
  { chemin: "/matieres", module: "matieres", element: <PageMatieres /> },
  { chemin: "/matieres/coefficients", module: "matieres", element: <PageCoefficientsMatiere /> },
  { chemin: "/etudiants", module: "etudiants", element: <PageEtudiants /> },
  { chemin: "/inscriptions", module: "etudiants", element: <PageInscriptions /> },
  { chemin: "/scolarite", module: "scolarite", element: <PagePaiementsScolarite /> },
  { chemin: "/scolarite/grilles-frais", module: "scolarite", element: <PageGrillesFrais /> },
  { chemin: "/professeurs", module: "professeurs", element: <PageProfesseurs /> },
  { chemin: "/affectations", module: "professeurs", element: <PageAffectationsProfesseur /> },
  { chemin: "/presences", module: "presences", element: <PagePresences /> },
  { chemin: "/presences/historique", module: "presences", element: <PageHistoriquePresences /> },
  { chemin: "/presences-professeurs", module: "presences_professeurs", element: <PagePresencesProfesseurs /> },
  { chemin: "/notifications", module: "notifications", element: <PageNotifications /> },
  { chemin: "/notes", module: "evaluations", element: <PageNotes /> },
  { chemin: "/resultats", module: "resultats", element: <PageResultats /> },
  { chemin: "/emplois-du-temps", module: "emplois_du_temps", element: <PageEmploisDuTemps /> },
  { chemin: "/emplois-du-temps/:id", module: "emplois_du_temps", element: <PageEditeurEmploi /> },
  { chemin: "/planification", module: "planification", element: <PagePlanification /> },
  { chemin: "/disponibilites", module: "disponibilites", element: <PageDisponibilites /> },
  { chemin: "/remuneration", module: "remuneration", element: <PageRemuneration /> },
  { chemin: "/remuneration/:id", module: "remuneration", element: <PageReleveDetail /> },
  { chemin: "/ma-remuneration", module: "ma_remuneration", element: <PageMaRemuneration /> },
  { chemin: "/utilisateurs", module: "utilisateurs", element: <PageUtilisateurs /> },
  { chemin: "/parametres", module: "parametres", element: <PageParametres /> },
  { chemin: "*", module: "tableau_de_bord", element: <Navigate to="/" replace /> },
];
