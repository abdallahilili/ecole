import {
  LayoutDashboard, CalendarRange, Layers, School, Users2, DoorOpen, BookOpen,
  GraduationCap, ClipboardList, Wallet, UserCog, Shuffle, Tag, ClipboardCheck, UserCheck,
  MessageCircle, Settings, PenLine, Trophy, CalendarClock, SlidersHorizontal, CalendarX2, Banknote, HandCoins,
  BookUser, Building2, Award, Clock, ShieldCheck,
} from "lucide-react";

import { tr } from "../i18n";
export interface ElementMenu {
  module: string;
  libelle: string;
  chemin: string;
  icone: typeof LayoutDashboard;
}

/** Entree depliable regroupant plusieurs elements (sous-menu) ; visible si l'un de ses elements l'est. */
export interface GroupeMenu {
  cle: string;
  libelle: string;
  icone: typeof LayoutDashboard;
  elements: ElementMenu[];
}

export type EntreeMenu = ElementMenu | GroupeMenu;

export function estGroupe(entree: EntreeMenu): entree is GroupeMenu {
  return "elements" in entree;
}

export const MENU: EntreeMenu[] = [
  { module: "tableau_de_bord", libelle: tr("Tableau de bord"), chemin: "/", icone: LayoutDashboard },
  {
    cle: "registre", libelle: tr("Registre"), icone: BookUser, elements: [
      { module: "etudiants", libelle: tr("Etudiants"), chemin: "/etudiants", icone: GraduationCap },
      { module: "etudiants", libelle: tr("Inscriptions"), chemin: "/inscriptions", icone: ClipboardList },
    ],
  },
  {
    cle: "organisation", libelle: tr("Organisation scolaire"), icone: Building2, elements: [
      { module: "annees_scolaires", libelle: tr("Annees scolaires"), chemin: "/annees-scolaires", icone: CalendarRange },
      { module: "niveaux", libelle: tr("Niveaux"), chemin: "/niveaux", icone: Layers },
      { module: "classes", libelle: tr("Classes"), chemin: "/classes", icone: School },
      { module: "groupes", libelle: tr("Groupes"), chemin: "/groupes", icone: Users2 },
      { module: "salles", libelle: tr("Salles"), chemin: "/salles", icone: DoorOpen },
      { module: "matieres", libelle: tr("Matieres"), chemin: "/matieres", icone: BookOpen },
      { module: "tarifs", libelle: tr("Tarifs"), chemin: "/tarifs", icone: Tag },
    ],
  },
  {
    cle: "vie_scolaire", libelle: tr("Vie scolaire"), icone: ClipboardCheck, elements: [
      { module: "presences", libelle: tr("Presences"), chemin: "/presences", icone: ClipboardCheck },
      { module: "notifications", libelle: tr("Notifications"), chemin: "/notifications", icone: MessageCircle },
    ],
  },
  {
    cle: "evaluations", libelle: tr("Evaluations"), icone: Award, elements: [
      { module: "evaluations", libelle: tr("Notes"), chemin: "/notes", icone: PenLine },
      { module: "resultats", libelle: tr("Resultats"), chemin: "/resultats", icone: Trophy },
    ],
  },
  {
    cle: "horaires", libelle: tr("Horaires"), icone: Clock, elements: [
      { module: "emplois_du_temps", libelle: tr("Emplois du temps"), chemin: "/emplois-du-temps", icone: CalendarClock },
      { module: "planification", libelle: tr("Planification"), chemin: "/planification", icone: SlidersHorizontal },
      { module: "disponibilites", libelle: tr("Disponibilites"), chemin: "/disponibilites", icone: CalendarX2 },
    ],
  },
  {
    cle: "finances", libelle: tr("Finances"), icone: Wallet, elements: [
      { module: "scolarite", libelle: tr("Scolarite (frais)"), chemin: "/scolarite", icone: Wallet },
      { module: "remuneration", libelle: tr("Remuneration"), chemin: "/remuneration", icone: Banknote },
      { module: "ma_remuneration", libelle: tr("Ma remuneration"), chemin: "/ma-remuneration", icone: HandCoins },
    ],
  },
  {
    cle: "enseignants", libelle: tr("Enseignants"), icone: UserCog, elements: [
      { module: "professeurs", libelle: tr("Professeurs"), chemin: "/professeurs", icone: UserCog },
      { module: "professeurs", libelle: tr("Affectations"), chemin: "/affectations", icone: Shuffle },
      { module: "presences_professeurs", libelle: tr("Presences profs"), chemin: "/presences-professeurs", icone: UserCheck },
    ],
  },
  {
    cle: "administration", libelle: tr("Administration"), icone: ShieldCheck, elements: [
      { module: "utilisateurs", libelle: tr("Utilisateurs"), chemin: "/utilisateurs", icone: Users2 },
      { module: "parametres", libelle: tr("Parametres"), chemin: "/parametres", icone: Settings },
    ],
  },
];
