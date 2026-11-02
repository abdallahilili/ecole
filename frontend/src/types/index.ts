export type Role =
  | "ADMINISTRATEUR" | "DIRECTEUR" | "RESPONSABLE_SCOLARITE"
  | "RESPONSABLE_PEDAGOGIQUE" | "COMPTABLE" | "PROFESSEUR";

export interface Utilisateur {
  id: number;
  identifiant: string;
  nom: string;
  prenom: string;
  telephone: string;
  role: Role;
  professeur: number | null;
  actif: boolean;
  date_creation: string;
  modules: string[];
}

export interface AnneeScolaire {
  id: number;
  libelle: string;
  date_debut: string;
  date_fin: string;
  debut_trimestre2: string | null;
  debut_trimestre3: string | null;
  debut_vacances: string | null;
  fin_vacances: string | null;
  debut_vacances2: string | null;
  fin_vacances2: string | null;
  debut_examen1: string | null;
  fin_examen1: string | null;
  debut_examen2: string | null;
  fin_examen2: string | null;
  debut_examen3: string | null;
  fin_examen3: string | null;
  active: boolean;
  cloturee: boolean;
}

export interface Niveau {
  id: number;
  nom: string;
  nom_ar: string;
  nom_affiche: string;
  code: string;
  ordre: number;
}

export interface Salle {
  id: number;
  nom: string;
  capacite: number;
  type_salle: string;
  equipements: string;
  disponible: boolean;
}

export interface Classe {
  id: number;
  nom: string;
  niveau: number;
  niveau_nom: string;
  annee_scolaire: number;
  annee_scolaire_libelle: string;
  capacite: number;
  salle_principale: number | null;
  effectif: number;
  actif?: boolean;
}

export interface TarifClasse {
  id: number;
  classe: number;
  classe_nom: string;
  niveau_nom: string;
  annee_scolaire_libelle: string;
  montant: string;
}

export interface Groupe {
  id: number;
  nom: string;
  classe: number;
  classe_nom: string;
}

export interface Matiere {
  id: number;
  nom: string;
  nom_ar: string;
  nom_affiche: string;
  code: string;
  description: string;
}

export interface AffectationMatiereClasse {
  id: number;
  matiere: number;
  matiere_nom: string;
  classe: number;
  classe_nom: string;
  coefficient: string;
  volume_horaire_hebdo: string;
  nombre_seances_semaine: number;
}

export interface Etudiant {
  id: number;
  matricule: string;
  /** Numero d'inscription de la classe demandee, sinon de l'annee active (null si non inscrit). */
  numero_inscription: string | null;
  nom: string;
  prenom: string;
  nom_complet: string;
  sexe: "M" | "F";
  date_naissance: string | null;
  lieu_naissance: string;
  numero_national: string;
  adresse: string;
  nom_pere: string;
  telephone_pere: string;
  nom_mere: string;
  telephone_mere: string;
  nom_tuteur: string;
  telephone_tuteur: string;
  telephone_principal: string;
  actif: boolean;
  cree_le: string;
}

export interface Inscription {
  id: number;
  numero_inscription: string;
  etudiant: number;
  etudiant_nom: string;
  etudiant_matricule: string;
  annee_scolaire: number;
  annee_scolaire_libelle: string;
  classe: number;
  classe_nom: string;
  groupe: number | null;
  groupe_nom: string | null;
  type_inscription: "INSCRIPTION" | "REINSCRIPTION" | "TRANSFERT";
  statut: "ACTIVE" | "TRANSFEREE" | "ABANDON" | "DIPLOME";
  date_inscription: string;
  date_fin: string | null;
  montant_mensuel: string | null;
  etablissement_origine: string;
  observations: string;
}

export interface Professeur {
  id: number;
  matricule: string;
  nom: string;
  prenom: string;
  nom_complet: string;
  telephone: string;
  email: string;
  adresse: string;
  specialite: string;
  date_recrutement: string | null;
  statut: "ACTIF" | "INACTIF";
  mode_remuneration: "HORAIRE" | "FIXE";
  tarif_horaire: string;
  salaire_fixe: string;
}

export interface AffectationProfesseur {
  id: number;
  professeur: number;
  professeur_nom: string;
  matiere: number;
  matiere_nom: string;
  classe: number;
  classe_nom: string;
  groupe: number | null;
  groupe_nom: string | null;
  annee_scolaire: number;
  annee_scolaire_libelle: string;
}

export interface GrilleFrais {
  id: number;
  annee_scolaire: number;
  annee_scolaire_libelle: string;
  niveau: number;
  niveau_nom: string;
  montant_mensuel: string;
  frais_inscription: string;
  nombre_mois: number;
}

export interface PaiementScolarite {
  id: number;
  reference: string;
  inscription: number;
  etudiant_nom: string;
  etudiant_matricule: string;
  numero_inscription: string;
  classe_nom: string;
  type_frais: "INSCRIPTION" | "MENSUALITE" | "AUTRE";
  mois_concerne: string | null;
  montant: string;
  mode_paiement: "ESPECES" | "VIREMENT" | "CHEQUE" | "MOBILE";
  date_paiement: string;
  enregistre_par: number;
  observations: string;
  cree_le: string;
}

export interface SituationScolarite {
  etudiant: string;
  matricule: string;
  numero_inscription: string;
  classe: string;
  annee_scolaire: string;
  montant_mensuel: string | null;
  frais_inscription: string | null;
  nombre_mois: number | null;
  frais_inscription_paye: boolean;
  mois_payes: string[];
  total_paye: string;
}

export type EtatMois = "NON_PAYE" | "PARTIEL" | "PAYE";

/** Un mois de la fiche de paiement d'un eleve. */
export interface LigneFiche {
  id: number;
  mois: string;
  montant: string;
  paye: string;
  reste: string;
  statut: EtatMois;
  reference: string | null;
  date_paiement: string | null;
  mode_paiement: PaiementScolarite["mode_paiement"] | null;
  encaisse_par: string | null;
}

export interface FicheScolarite {
  inscription: number;
  etudiant: number;
  etudiant_nom: string;
  matricule: string;
  numero_inscription: string;
  classe_nom: string;
  annee_scolaire_libelle: string;
  montant_mensuel: string | null;
  lignes: LigneFiche[];
  totaux: { du: string; paye: string; reste: string; mois_payes: number; nombre_mois: number };
}

export type StatutPresence = "PRESENT" | "ABSENT" | "RETARD";
export type StatutSeanceProfesseur = "PLANIFIE" | "EFFECTUE" | "ABSENT" | "RETARD" | "ANNULE" | "REMPLACE";

export interface Seance {
  id: number;
  annee_scolaire: number;
  annee_scolaire_libelle: string;
  classe: number;
  classe_nom: string;
  matiere: number;
  matiere_nom: string;
  professeur: number | null;
  professeur_nom: string | null;
  date: string;
  heure_debut: string;
  heure_fin: string;
  presences_validees: boolean;
  validee_le: string | null;
  statut_professeur: StatutSeanceProfesseur;
  professeur_remplacant: number | null;
  remplacant_nom: string | null;
  heure_reelle_debut: string | null;
  heure_reelle_fin: string | null;
  heures_effectuees: string;
  observations_professeur: string;
  nb_presents: number;
  nb_absents: number;
  nb_retards: number;
  nb_eleves: number;
}

export interface EleveListe {
  numero: number;
  etudiant: number;
  inscription: number;
  matricule: string;
  numero_inscription: string;
  nom_complet: string;
  statut: StatutPresence | null;
  observation: string;
}

export interface PresenceHistorique {
  id: number;
  seance: number;
  etudiant: number;
  etudiant_nom: string;
  etudiant_matricule: string;
  numero_inscription: string | null;
  date: string;
  heure_debut: string;
  heure_fin: string;
  classe_nom: string;
  matiere_nom: string;
  professeur_nom: string | null;
  statut: StatutPresence;
  observation: string;
  seance_validee: boolean;
  notification_statut: StatutNotification | null;
}

export type StatutNotification = "EN_ATTENTE" | "ENVOYE" | "LIVRE" | "ECHEC";

export interface NotificationWhatsApp {
  id: number;
  seance: number;
  etudiant_nom: string;
  etudiant_matricule: string;
  numero_inscription: string | null;
  classe_nom: string;
  matiere_nom: string;
  date: string;
  heure_debut: string;
  heure_fin: string;
  destinataire_nom: string;
  telephone: string;
  message: string;
  statut: StatutNotification;
  canal: "" | "API" | "MANUEL";
  erreur: string;
  tentatives: number;
  envoye_le: string | null;
  declenchee_manuellement: boolean;
  lien_wa_me: string;
}

export interface ConfigurationNotifications {
  api_configuree: boolean;
  whatsapp_actif: boolean;
  retard_est_absence: boolean;
  modele_message: string;
  nom_modele_api: string;
  max_tentatives: number;
}

export type StatutNote = "SAISIE" | "ABSENT_JUSTIFIE" | "ABSENT" | "NON_APPLICABLE" | "MANQUANTE";
export type TypeEvaluation = "DEVOIR" | "INTERROGATION" | "EXAMEN" | "AUTRE";

export interface Evaluation {
  id: number;
  annee_scolaire: number;
  trimestre: 1 | 2 | 3;
  classe: number;
  classe_nom: string;
  matiere: number;
  matiere_nom: string;
  libelle: string;
  type: TypeEvaluation;
  date: string | null;
  bareme: string;
  poids: string;
  nb_notes: number;
  nb_eleves: number;
  resultats_valides: boolean;
}

/** Evaluation d'une colonne de la grille des notes (devoir, moyenne des interrogations, composition...). */
export interface EvaluationGrille {
  id: number;
  libelle: string;
  type: TypeEvaluation;
  poids: string;
  bareme: string;
  nb_notes: number;
}

export interface CelluleNote { statut: StatutNote; valeur: string | null }

export interface EleveGrille {
  etudiant: number;
  numero: number;
  numero_inscription: string;
  nom_complet: string;
  /** Notes de l'eleve, par identifiant d'evaluation. */
  notes: Record<string, CelluleNote>;
}

/** Grille de saisie d'une matiere pour un trimestre : N devoirs, moyenne des interrogations (x3) et composition. */
export interface GrilleNotes {
  annee_scolaire: number;
  classe: number;
  matiere: number;
  trimestre: 1 | 2 | 3;
  coefficient: string;
  peut_modifier_coefficient: boolean;
  resultats_valides: boolean;
  regles: { abs_justifiee: string; abs_non_justifiee: string; exige_toutes_evaluations: boolean };
  bareme_defaut: string;
  max_devoirs: number;
  composition_attendue: { libelle: string; poids: string };
  /** `devoirs` : moyenne calculee ; `direct` : anciennes donnees, moyenne saisie directement. */
  interrogations: (EvaluationGrille & { mode: "devoirs" | "direct" }) | null;
  devoirs: (EvaluationGrille & { ordre: number })[];
  composition: EvaluationGrille | null;
  /** Anciennes evaluations hors modele, toujours saisissables. */
  autres: EvaluationGrille[];
  eleves: EleveGrille[];
}

export interface LigneResultatMatiere {
  etudiant: number;
  numero: number;
  numero_inscription: string;
  nom_complet: string;
  interrogations: CelluleNote | null;
  composition: CelluleNote | null;
  /** Moyenne de la matiere pour le trimestre choisi (/20) et son rang dans la classe. */
  moyenne: string | null;
  rang: number | null;
  moyennes: Record<string, string | null>;
  moyenne_annuelle: string | null;
}

/** Resultat d'une matiere : trimestre choisi, moyennes des trois trimestres et moyenne annuelle. */
export interface ResultatMatiere {
  trimestre: 1 | 2 | 3;
  interrogations: EvaluationGrille | null;
  composition: EvaluationGrille | null;
  poids_trimestres: string[];
  eleves: LigneResultatMatiere[];
}

export interface EleveNote {
  numero: number;
  etudiant: number;
  matricule: string;
  numero_inscription: string;
  nom_complet: string;
  statut: StatutNote;
  valeur: string | null;
}

export interface MatiereResultat {
  id: number;
  nom: string;
  code: string;
  coefficient: string;
  evaluee?: boolean;
}

export interface DetailMatiere {
  moyenne: string | null;
  incomplete?: boolean;
  total?: string | null;
  moyennes_trimestres?: Record<string, string | null>;
}

export interface LigneResultat {
  etudiant: number;
  matricule: string;
  numero_inscription: string;
  nom_complet: string;
  matieres: Record<string, DetailMatiere>;
  total_points: string;
  moyenne_generale: string | null;
  rang: number | null;
  incomplet: boolean;
  decision: "" | "ADMIS" | "REDOUBLE" | "EXCLU";
  observation_professeurs: string;
  observation_directeur: string;
  matieres_manquantes?: string[];
  moyennes_trimestres?: Record<string, string | null>;
  rangs_trimestres?: Record<string, number | null>;
}

export interface ResultatsClasse {
  periode: number;
  classe: number;
  classe_nom: string;
  annee_libelle: string;
  validee: boolean;
  matieres: MatiereResultat[];
  etudiants: LigneResultat[];
  effectif: number;
  statistiques: {
    effectif_note: number;
    moyenne_classe: string | null;
    plus_haute: string | null;
    plus_basse: string | null;
    taux_reussite: string | null;
  };
}

export interface ConfigurationHoraires {
  id: number;
  annee_scolaire: number;
  jours: string;
  heure_debut: string;
  heure_fin: string;
  duree_creneau: number;
  duree_min_seance: number;
  duree_max_seance: number;
  pauses: { debut: string; fin: string }[];
  max_creneaux_jour_professeur: number;
  max_creneaux_consecutifs_professeur: number;
  /** False : la salle n'est pas une contrainte (plusieurs cours possibles en meme temps), mais reste attribuee. */
  considerer_salles: boolean;
  /** True : un professeur n'a jamais deux seances qui s'enchainent avec la meme classe. */
  seances_successives_interdites: boolean;
}

export interface DisponibiliteProfesseur {
  id: number;
  professeur: number;
  professeur_nom: string;
  jour: number;
  heure_debut: string;
  heure_fin: string;
  /** DISPONIBLE : le professeur n'enseigne que dans ses creneaux disponibles. */
  type: "DISPONIBLE" | "INDISPONIBLE" | "PREFERE";
  commentaire: string;
}

/** Creneau de disponibilite saisi dans l'assistant de creation d'un emploi du temps (jour : 0 = lundi). */
export interface CreneauDisponible {
  jour: number;
  debut: string;
  fin: string;
}

export interface ProfesseurAssistant {
  id: number;
  nom: string;
  specialite: string;
  disponibilites: CreneauDisponible[];
}

export interface MatiereAssistant {
  id: number;
  nom: string;
}

/** Donnees de l'assistant de creation pour une classe : matieres de la classe, professeurs et affectations existantes. */
export interface DonneesAssistant {
  classe: { id: number; nom: string; annee_scolaire: number; annee_libelle: string };
  nom_propose: string;
  matieres: MatiereAssistant[];
  professeurs: ProfesseurAssistant[];
  initial: { professeur: number; matieres: { matiere: number; heures: number }[] }[];
  cadre: { jours: number[]; debut: string; fin: string; duree_creneau: number; pauses: { debut: string; fin: string }[] };
}

export interface IndisponibiliteSalle {
  id: number;
  salle: number;
  salle_nom: string;
  jour: number;
  heure_debut: string;
  heure_fin: string;
  motif: string;
}

export type StatutEmploi = "BROUILLON" | "PUBLIE" | "ARCHIVE";

export interface RapportGeneration {
  unites: number;
  seances_creees: number;
  violations: number;
  penalites: number;
  generations: number;
  duree_s: number;
  arret: string;
  graine: number | null;
  diagnostics: string[];
  conflits: string[];
  publiable: boolean;
}

export interface EmploiDuTemps {
  id: number;
  annee_scolaire: number;
  annee_scolaire_libelle: string;
  /** Classe de l'emploi du temps (vide pour un emploi qui couvre plusieurs classes). */
  classe: number | null;
  classe_nom: string | null;
  nom: string;
  statut: StatutEmploi;
  origine: "MANUEL" | "GENETIQUE";
  rapport: Partial<RapportGeneration>;
  nb_seances: number;
  cree_le: string;
  publie_le: string | null;
}

export interface ConflitEmploi {
  type: string;
  message: string;
  seances: (number | string)[];
}

export interface SeanceGrille {
  id: number;
  classe: number;
  classe_nom: string;
  groupe: number | null;
  groupe_nom: string | null;
  matiere: number;
  matiere_nom: string;
  professeur: number;
  professeur_nom: string;
  salle: number | null;
  salle_nom: string | null;
  jour: number;
  heure_debut: string;
  heure_fin: string;
  conflits: string[];
}

export interface VueEmploi {
  emploi: { id: number; nom: string; statut: StatutEmploi; origine: string; annee_scolaire: number; rapport: Partial<RapportGeneration>; modifiable: boolean };
  cadre: {
    jours: { id: number; nom: string }[];
    creneaux: { index: number; debut: string; fin: string; pause: boolean }[];
    duree_creneau: number;
    debut: string;
    fin: string;
    salles_contraintes?: boolean;
  };
  seances: SeanceGrille[];
  nb_conflits: number;
}

export interface VersionEmploi {
  numero: number;
  emploi: number;
  emploi_nom: string;
  commentaire: string;
  publie_le: string;
  publie_par: string | null;
  nb_seances: number;
}

export interface TotauxReleve {
  heures: string;
  brut: string;
  primes: string;
  retenues: string;
  net: string;
  paye: string;
  solde: string;
  statut_paiement: "NON_PAYE" | "PARTIEL" | "PAYE";
}

export interface ReleveRemuneration {
  id: number;
  professeur: number;
  professeur_nom: string;
  professeur_matricule: string;
  annee_scolaire: number;
  annee_scolaire_libelle: string;
  mois: string;
  statut: "BROUILLON" | "VALIDE";
  mode_remuneration: string;
  observations: string;
  valide_le: string | null;
  cree_le: string;
  totaux: TotauxReleve;
  nb_lignes: number;
}

export interface LigneReleve {
  id: number;
  seance: number;
  classe_nom: string;
  matiere_nom: string;
  date: string;
  heures: string;
  tarif: string;
  montant: string;
}

export interface AjustementReleve {
  id: number;
  type: "PRIME" | "RETENUE";
  libelle: string;
  montant: string;
  cree_le: string;
}

export interface PaiementProfesseur {
  id: number;
  reference: string;
  releve: number;
  professeur_nom: string;
  mois: string;
  type: "ACOMPTE" | "SOLDE" | "ANNULATION";
  montant: string;
  mode_paiement: "ESPECES" | "VIREMENT" | "CHEQUE" | "MOBILE";
  date_paiement: string;
  annulable: boolean;
  annule_par: string | null;
  observations: string;
  enregistre_par_nom: string;
}

export interface CorrectionHeures {
  id: number;
  seance: number;
  date_seance: string;
  anciennes_heures: string;
  nouvelles_heures: string;
  ancien_montant: string;
  nouveau_montant: string;
  motif: string;
  corrige_par_nom: string | null;
  corrige_le: string;
}

export interface ReleveDetail extends ReleveRemuneration {
  lignes: LigneReleve[];
  ajustements: AjustementReleve[];
  paiements: PaiementProfesseur[];
  corrections: CorrectionHeures[];
}

export interface EtatMensuel {
  mois: string;
  releves: ReleveRemuneration[];
  total: Omit<TotauxReleve, "statut_paiement">;
  total_valide: Omit<TotauxReleve, "statut_paiement">;
  sans_releve: { professeur: number; nom: string }[];
}

export interface HeuresMatiereClasse {
  matiere: number;
  matiere_nom: string;
  classe: number;
  classe_nom: string;
  heures: string;
  seances: number;
  heures_comptabilisees: string;
  heures_a_comptabiliser: string;
}

export interface TarifProfesseurMatiere {
  id: number;
  professeur: number;
  professeur_nom: string;
  matiere: number;
  matiere_nom: string;
  tarif_horaire: string;
}

export interface ListePaginee<T> {
  total: number;
  page: number;
  taille_page: number;
  nombre_pages: number;
  /** Colonnes triables/filtrables cote serveur. */
  champs?: string[];
  /** La liste masque ses elements inactifs par defaut (?inactifs=1 pour les afficher). */
  inactifs_disponibles?: boolean;
  resultats: T[];
}
