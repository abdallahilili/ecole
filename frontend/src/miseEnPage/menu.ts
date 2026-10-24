import {
  LayoutDashboard, CalendarRange, Layers, School, Users2, DoorOpen, BookOpen,
  GraduationCap, ClipboardList, Wallet, UserCog, Shuffle, Tag, ClipboardCheck, UserCheck,
  MessageCircle, Settings, PenLine, Trophy, CalendarClock, SlidersHorizontal, CalendarX2, Banknote, HandCoins,
} from "lucide-react";

export interface ElementMenu {
  module: string;
  libelle: string;
  chemin: string;
  icone: typeof LayoutDashboard;
}

export const MENU: ElementMenu[] = [
  { module: "tableau_de_bord", libelle: "Tableau de bord", chemin: "/", icone: LayoutDashboard },
  { module: "annees_scolaires", libelle: "Annees scolaires", chemin: "/annees-scolaires", icone: CalendarRange },
  { module: "niveaux", libelle: "Niveaux", chemin: "/niveaux", icone: Layers },
  { module: "classes", libelle: "Classes", chemin: "/classes", icone: School },
  { module: "tarifs", libelle: "Tarifs", chemin: "/tarifs", icone: Tag },
  { module: "groupes", libelle: "Groupes", chemin: "/groupes", icone: Users2 },
  { module: "salles", libelle: "Salles", chemin: "/salles", icone: DoorOpen },
  { module: "matieres", libelle: "Matieres", chemin: "/matieres", icone: BookOpen },
  { module: "etudiants", libelle: "Etudiants", chemin: "/etudiants", icone: GraduationCap },
  { module: "etudiants", libelle: "Inscriptions", chemin: "/inscriptions", icone: ClipboardList },
  { module: "presences", libelle: "Presences", chemin: "/presences", icone: ClipboardCheck },
  { module: "notifications", libelle: "Notifications", chemin: "/notifications", icone: MessageCircle },
  { module: "evaluations", libelle: "Notes", chemin: "/notes", icone: PenLine },
  { module: "resultats", libelle: "Resultats", chemin: "/resultats", icone: Trophy },
  { module: "emplois_du_temps", libelle: "Emplois du temps", chemin: "/emplois-du-temps", icone: CalendarClock },
  { module: "planification", libelle: "Planification", chemin: "/planification", icone: SlidersHorizontal },
  { module: "disponibilites", libelle: "Disponibilites", chemin: "/disponibilites", icone: CalendarX2 },
  { module: "scolarite", libelle: "Scolarite (frais)", chemin: "/scolarite", icone: Wallet },
  { module: "remuneration", libelle: "Remuneration", chemin: "/remuneration", icone: Banknote },
  { module: "ma_remuneration", libelle: "Ma remuneration", chemin: "/ma-remuneration", icone: HandCoins },
  { module: "professeurs", libelle: "Professeurs", chemin: "/professeurs", icone: UserCog },
  { module: "professeurs", libelle: "Affectations", chemin: "/affectations", icone: Shuffle },
  { module: "presences_professeurs", libelle: "Presences profs", chemin: "/presences-professeurs", icone: UserCheck },
  { module: "utilisateurs", libelle: "Utilisateurs", chemin: "/utilisateurs", icone: Users2 },
  { module: "parametres", libelle: "Parametres", chemin: "/parametres", icone: Settings },
];
