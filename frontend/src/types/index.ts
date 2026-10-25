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
  classe: string;
  annee_scolaire: string;
  montant_mensuel: string | null;
  frais_inscription: string | null;
  nombre_mois: number | null;
  frais_inscription_paye: boolean;
  mois_payes: string[];
  total_paye: string;
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

export interface EleveNote {
  numero: number;
  etudiant: number;
  matricule: string;
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
}

export interface DisponibiliteProfesseur {
  id: number;
  professeur: number;
  professeur_nom: string;
  jour: number;
  heure_debut: string;
  heure_fin: string;
  type: "INDISPONIBLE" | "PREFERE";
  commentaire: string;
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
  resultats: T[];
}
