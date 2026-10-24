import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { PageTableauDeBord } from "../pages/TableauDeBord";
import { PageAnneesScolaires } from "../pages/referentiels/AnneesScolaires";
import { PageNiveaux } from "../pages/referentiels/Niveaux";
import { PageSalles } from "../pages/referentiels/Salles";
import { PageClasses } from "../pages/referentiels/Classes";
import { PageTarifs } from "../pages/referentiels/Tarifs";
import { PageGroupes } from "../pages/referentiels/Groupes";
import { PageMatieres } from "../pages/referentiels/Matieres";
import { PageCoefficientsMatiere } from "../pages/referentiels/CoefficientsMatiere";
import { PageEtudiants } from "../pages/etudiants/Etudiants";
import { PageInscriptions } from "../pages/etudiants/Inscriptions";
import { PageGrillesFrais } from "../pages/scolarite/GrillesFrais";
import { PagePaiementsScolarite } from "../pages/scolarite/PaiementsScolarite";
import { PageProfesseurs } from "../pages/professeurs/Professeurs";
import { PageAffectationsProfesseur } from "../pages/professeurs/AffectationsProfesseur";
import { PageUtilisateurs } from "../pages/utilisateurs/Utilisateurs";
import { PagePresences } from "../pages/presences/Presences";
import { PageHistoriquePresences } from "../pages/presences/HistoriquePresences";
import { PagePresencesProfesseurs } from "../pages/presences/PresencesProfesseurs";
import { PageNotifications } from "../pages/presences/Notifications";
import { PageParametres } from "../pages/parametres/Parametres";
import { PageNotes } from "../pages/evaluations/Notes";
import { PageResultats } from "../pages/evaluations/Resultats";
import { PageEmploisDuTemps } from "../pages/emploiDuTemps/EmploisDuTemps";
import { PageEditeurEmploi } from "../pages/emploiDuTemps/EditeurEmploi";
import { PagePlanification } from "../pages/emploiDuTemps/Planification";
import { PageDisponibilites } from "../pages/emploiDuTemps/Disponibilites";
import { PageRemuneration } from "../pages/remuneration/Remuneration";
import { PageReleveDetail } from "../pages/remuneration/ReleveDetail";
import { PageMaRemuneration } from "../pages/remuneration/MaRemuneration";

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
