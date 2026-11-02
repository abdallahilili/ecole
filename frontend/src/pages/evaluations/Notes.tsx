import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileSpreadsheet, Save, Upload } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { ImportExcel } from "../../composants/ImportExcel";
import type { LigneApercu } from "../../composants/ImportExcel";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import { messageErreurFichier, telechargerFichier } from "../../services/fichiers";
import type {
  AffectationMatiereClasse, AnneeScolaire, CelluleNote, Classe, EvaluationGrille, GrilleNotes, ResultatMatiere, StatutNote,
} from "../../types";

import { tr, tx } from "../../i18n";
interface LigneNote extends LigneApercu { statut: StatutNote | null; valeur: string | null; ancienne: string | null }
interface Colonne { evaluation: EvaluationGrille; titre: string }
interface Reglages { nombre: string; baremeDevoirs: string; baremeComposition: string; coefficient: string }
type Onglet = "devoirs" | "composition" | "resultat";

const NOMBRE_DEVOIRS_DEFAUT = "3";
const URL_EVALUATIONS = "/evaluations/evaluations/";

// --- lecture d'une cellule : nombre, A (absent), AJ (absent justifie), NA (non applicable) ou vide (pas de note)
type Lecture = { statut: StatutNote; valeur: number | null } | "MANQUANTE" | "INVALIDE";
const CODES: Record<string, StatutNote> = { A: "ABSENT", AJ: "ABSENT_JUSTIFIE", NA: "NON_APPLICABLE" };
const CODE_DE_STATUT: Record<string, string> = { ABSENT: "A", ABSENT_JUSTIFIE: "AJ", NON_APPLICABLE: "NA" };

function lire(texte: string, bareme: number): Lecture {
  const t = texte.trim().toUpperCase();
  if (t === "") return "MANQUANTE";
  if (CODES[t]) return { statut: CODES[t], valeur: null };
  if (!/^\d+([.,]\d{1,2})?$/.test(t)) return "INVALIDE";
  const n = Number(t.replace(",", "."));
  return n <= bareme ? { statut: "SAISIE", valeur: n } : "INVALIDE";
}

function texteDe(cellule?: CelluleNote | null): string {
  if (!cellule) return "";
  if (cellule.statut === "SAISIE") return cellule.valeur === null ? "" : String(Number(cellule.valeur));
  return CODE_DE_STATUT[cellule.statut] ?? "";
}

/** Valeur d'une note enregistree, pour un tableau de resultats (2 decimales, ou code A / AJ / NA). */
function afficherCellule(cellule?: CelluleNote | null): string {
  if (!cellule) return "-";
  return cellule.statut === "SAISIE" && cellule.valeur !== null ? Number(cellule.valeur).toFixed(2) : CODE_DE_STATUT[cellule.statut] ?? "-";
}

const cle = (evaluation: number, etudiant: number) => `${evaluation}:${etudiant}`;
const arrondir = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;
const sansZeros = (valeur: string) => String(Number(valeur));

// --- meme formule que le serveur (apps/evaluations/calculs.py) pour la moyenne des devoirs avant enregistrement
interface Notation { statut: StatutNote; valeur: number }
interface Element { notation: Notation | null; bareme: number; poids: number }
type Regles = GrilleNotes["regles"];

function moyennePonderee(elements: Element[], regles: Regles): number | null {
  let somme = 0, poidsTotal = 0, incomplete = false;
  for (const { notation, bareme, poids } of elements) {
    if (!notation) { incomplete = true; continue; }
    let contribution: number;
    if (notation.statut === "SAISIE") contribution = notation.valeur * 20 / bareme;
    else if (notation.statut === "NON_APPLICABLE") continue;
    else {
      const regle = notation.statut === "ABSENT_JUSTIFIE" ? regles.abs_justifiee : regles.abs_non_justifiee;
      if (regle !== "zero") continue;
      contribution = 0;
    }
    somme += contribution * poids;
    poidsTotal += poids;
  }
  if (poidsTotal === 0 || (incomplete && regles.exige_toutes_evaluations)) return null;
  return somme / poidsTotal;
}

function enReglages(grille: GrilleNotes): Reglages {
  return {
    nombre: String(grille.devoirs.length || NOMBRE_DEVOIRS_DEFAUT),
    baremeDevoirs: sansZeros(grille.interrogations?.bareme ?? grille.bareme_defaut),
    baremeComposition: sansZeros(grille.composition?.bareme ?? grille.bareme_defaut),
    coefficient: sansZeros(grille.coefficient),
  };
}

function titreDevoir(ordre: number) {
  return ordre === 1 ? tr("1er Dev") : tr("{0}e Dev", ordre);
}

export function PageNotes() {
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const peutCorriger = utilisateur?.role === "ADMINISTRATEUR" || utilisateur?.role === "DIRECTEUR";

  // --- selection
  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [annee, setAnnee] = useState("");
  const [trimestre, setTrimestre] = useState("1");
  const classes = useOptions<Classe>(`/referentiels/classes/?annee_scolaire=${annee}`, !!annee);
  const [classe, setClasse] = useState("");
  const affectations = useOptions<AffectationMatiereClasse>(`/referentiels/affectations-matiere-classe/?classe=${classe}`, !!classe);
  const [matiere, setMatiere] = useState("");
  const selectionComplete = !!(annee && classe && matiere);
  const cours = useMemo(() => ({ annee_scolaire: annee, classe, matiere, trimestre }), [annee, classe, matiere, trimestre]);

  // --- grille
  const [onglet, setOnglet] = useState<Onglet>("devoirs");
  const [grille, setGrille] = useState<GrilleNotes | null>(null);
  const [resultat, setResultat] = useState<ResultatMatiere | null>(null);
  const [texte, setTexte] = useState<Record<string, string>>({});
  const [modifiees, setModifiees] = useState<Set<string>>(new Set());
  const [reglages, setReglages] = useState<Reglages>({ nombre: NOMBRE_DEVOIRS_DEFAUT, baremeDevoirs: "20", baremeComposition: "20", coefficient: "" });
  const [motif, setMotif] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [colonneFichier, setColonneFichier] = useState("");
  const [importOuvert, setImportOuvert] = useState(false);
  const champs = useRef<Record<string, HTMLInputElement | null>>({});

  useEffect(() => {
    if (!annee && annees.length > 0) setAnnee(String((annees.find((a) => a.active) ?? annees[0]).id));
  }, [annees, annee]);

  /** Affiche la grille du serveur ; `conserver` garde les cellules modifiees et pas encore enregistrees. */
  const afficher = useCallback((donnees: GrilleNotes, conserver = false) => {
    const base: Record<string, string> = {};
    for (const eleve of donnees.eleves) {
      for (const [evaluation, cellule] of Object.entries(eleve.notes)) base[cle(Number(evaluation), eleve.etudiant)] = texteDe(cellule);
    }
    setGrille(donnees);
    setReglages(enReglages(donnees));
    if (conserver) {
      setTexte((courant) => {
        const fusion = { ...base };
        modifiees.forEach((k) => { if (k in courant) fusion[k] = courant[k]; });
        return fusion;
      });
    } else {
      setTexte(base);
      setModifiees(new Set());
      setMotif("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modifiees]);

  const charger = useCallback(async () => {
    if (!selectionComplete) {
      setGrille(null);
      return;
    }
    try {
      const { data } = await api.get<GrilleNotes>(`${URL_EVALUATIONS}grille/`, { params: cours });
      afficher(data);
    } catch (err) {
      setGrille(null);
      notifierErreur(messageErreur(err));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectionComplete, cours]);

  useEffect(() => { charger(); }, [charger]);

  // Le resultat est relu a chaque ouverture de l'onglet et apres chaque enregistrement (il ne compte que les notes enregistrees).
  useEffect(() => {
    if (onglet !== "resultat" || !selectionComplete || !grille) return;
    api.get<ResultatMatiere>(`${URL_EVALUATIONS}resultat-matiere/`, { params: cours })
      .then(({ data }) => setResultat(data))
      .catch((err) => notifierErreur(messageErreur(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onglet, selectionComplete, cours, grille]);

  // --- colonnes saisies une a une, par onglet
  const colonnesDevoirs: Colonne[] = useMemo(() => {
    if (!grille) return [];
    const liste: Colonne[] = [];
    if (grille.interrogations?.mode === "direct") liste.push({ evaluation: grille.interrogations, titre: tr("Moy. Interros") });
    grille.devoirs.forEach((d) => liste.push({ evaluation: d, titre: titreDevoir(d.ordre) }));
    return liste;
  }, [grille]);

  const colonnesComposition: Colonne[] = useMemo(() => {
    if (!grille) return [];
    const liste: Colonne[] = [];
    if (grille.composition) liste.push({ evaluation: grille.composition, titre: tr(grille.composition.libelle) });
    grille.autres.forEach((e) => liste.push({ evaluation: e, titre: tr(e.libelle) }));
    return liste;
  }, [grille]);

  const colonnes = onglet === "devoirs" ? colonnesDevoirs : onglet === "composition" ? colonnesComposition : [];

  useEffect(() => {
    if (colonnes.length && !colonnes.some((c) => String(c.evaluation.id) === colonneFichier)) setColonneFichier(String(colonnes[0].evaluation.id));
  }, [colonnes, colonneFichier]);

  const verrouille = !!grille?.resultats_valides;
  const lectureSeule = verrouille && !peutCorriger;
  const modeDevoirs = grille?.interrogations?.mode === "devoirs";
  const modeDirect = grille?.interrogations?.mode === "direct";
  const horsModele = modeDirect || (grille?.autres.length ?? 0) > 0;

  const nbModifiees = (liste: Colonne[]) => [...modifiees].filter((k) => liste.some((c) => k.startsWith(`${c.evaluation.id}:`))).length;
  const modifieesOnglet = nbModifiees(colonnes);

  function valeurLue(evaluation: EvaluationGrille, etudiant: number): Lecture {
    return lire(texte[cle(evaluation.id, etudiant)] ?? "", Number(evaluation.bareme));
  }

  /** Moyenne des interrogations (devoirs) de chaque eleve, recalculee a chaque saisie. */
  const moyennesInterros = useMemo(() => {
    const resultats: Record<number, number | null> = {};
    if (!grille?.interrogations || !modeDevoirs) return resultats;
    const bareme = Number(grille.interrogations.bareme);
    for (const eleve of grille.eleves) {
      const elements: Element[] = grille.devoirs.map((d) => {
        const l = lire(texte[cle(d.id, eleve.etudiant)] ?? "", Number(d.bareme));
        return { notation: l === "MANQUANTE" || l === "INVALIDE" ? null : { statut: l.statut, valeur: l.valeur ?? 0 }, bareme: Number(d.bareme), poids: 1 };
      });
      const moyenne = moyennePonderee(elements, grille.regles);
      resultats[eleve.etudiant] = moyenne === null ? null : arrondir(moyenne * bareme / 20);
    }
    return resultats;
  }, [grille, texte, modeDevoirs]);

  const compteurs = useMemo(() => {
    let saisies = 0, manquantes = 0, erreurs = 0;
    for (const eleve of grille?.eleves ?? []) {
      for (const { evaluation } of colonnes) {
        const l = valeurLue(evaluation, eleve.etudiant);
        if (l === "MANQUANTE") manquantes += 1;
        else if (l === "INVALIDE") erreurs += 1;
        else saisies += 1;
      }
    }
    return { saisies, manquantes, erreurs };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grille, colonnes, texte]);

  function changer(evaluation: number, etudiant: number, valeur: string) {
    const k = cle(evaluation, etudiant);
    setTexte((t) => ({ ...t, [k]: valeur }));
    setModifiees((m) => new Set(m).add(k));
  }

  function naviguer(colonne: number, ligne: number, touche: string) {
    const cible = champs.current[`${colonne}:${touche === "ArrowUp" ? ligne - 1 : ligne + 1}`];
    cible?.focus();
    cible?.select();
  }

  /** Enregistre les cellules modifiees de l'onglet en cours (les autres onglets restent a part). */
  async function enregistrer() {
    if (!grille) return;
    if (compteurs.erreurs > 0) {
      notifierErreur(tr("{0} note(s) invalide(s) : corrigez avant d'enregistrer.", compteurs.erreurs));
      return;
    }
    if (verrouille && !motif.trim()) {
      notifierErreur(tr("Resultats valides : saisissez le motif de la correction."));
      return;
    }
    const notes = [...modifiees].filter((k) => colonnes.some((c) => k.startsWith(`${c.evaluation.id}:`))).map((k) => {
      const [evaluation, etudiant] = k.split(":").map(Number);
      const bareme = colonnes.find((c) => c.evaluation.id === evaluation)?.evaluation.bareme ?? "20";
      const l = lire(texte[k] ?? "", Number(bareme));
      if (l === "MANQUANTE" || l === "INVALIDE") return { evaluation, etudiant, statut: "MANQUANTE" };
      return l.statut === "SAISIE"
        ? { evaluation, etudiant, statut: "SAISIE", valeur: String(l.valeur) }
        : { evaluation, etudiant, statut: l.statut };
    });
    setEnCours(true);
    try {
      const { data } = await api.post(`${URL_EVALUATIONS}grille/`, { ...cours, notes, motif });
      afficher(data, true);
      setModifiees((m) => new Set([...m].filter((k) => !colonnes.some((c) => k.startsWith(`${c.evaluation.id}:`)))));
      setMotif("");
      notifierSucces(tr("Notes enregistrees ({0} nouvelle(s), {1} modifiee(s)).", data.bilan.creees, data.bilan.modifiees));
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  // --- parametres de la matiere : coefficient, nombre de devoirs, baremes
  const reference = grille ? enReglages(grille) : null;
  const devoirsCrees = !!grille?.interrogations;
  const compositionCreee = !!grille?.composition;
  const devoirsModifies = !devoirsCrees || (reference !== null && (reglages.nombre !== reference.nombre || reglages.baremeDevoirs !== reference.baremeDevoirs));
  const compositionModifiee = !compositionCreee || (reference !== null && reglages.baremeComposition !== reference.baremeComposition);
  const coefficientModifie = reference !== null && reglages.coefficient !== reference.coefficient;
  const baremeDevoirsFige = !!grille && [grille.interrogations, ...grille.devoirs].some((e) => e && e.nb_notes > 0);
  const baremeCompositionFige = (grille?.composition?.nb_notes ?? 0) > 0;

  async function appliquer(corps: Record<string, string>, message: string) {
    setEnCours(true);
    try {
      const { data } = await api.post(`${URL_EVALUATIONS}structure/`, { ...cours, ...corps });
      afficher(data, true);
      notifierSucces(message);
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  // --- Excel : une colonne a la fois
  const evaluationFichier = colonnes.find((c) => String(c.evaluation.id) === colonneFichier)?.evaluation;

  async function exporter() {
    if (!evaluationFichier) return;
    try {
      await telechargerFichier(`${URL_EVALUATIONS}${evaluationFichier.id}/exporter/`, `notes_${evaluationFichier.libelle}.xlsx`);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  const champReglage = (nom: keyof Reglages, valeur: string) => setReglages((r) => ({ ...r, [nom]: valeur }));
  const entete = "px-3 py-2 text-center";
  const nomMatiere = affectations.find((a) => String(a.matiere) === matiere)?.matiere_nom;

  function ongletBouton(id: Onglet, titre: string, enAttente = 0) {
    const actif = onglet === id;
    return (
      <button
        key={id} type="button" onClick={() => setOnglet(id)}
        className={`-mb-px border-b-2 px-4 py-2 text-sm ${actif ? "border-entete font-semibold text-entete" : "border-transparent text-texte-attenue hover:text-texte"}`}
      >
        {titre}
        {enAttente > 0 && <span className="ms-2 rounded-full bg-amber-100 px-1.5 text-xs text-amber-800">{enAttente}</span>}
      </button>
    );
  }

  /** Grille de saisie : une ligne par eleve, une colonne de saisie par evaluation de l'onglet. */
  function tableauSaisie(avecMoyenneInterros: boolean) {
    if (!grille) return null;
    return (
      <div className="overflow-x-auto rounded border border-bordure">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-fond-barre text-start text-texte-attenue">
              <th className="px-3 py-2 text-start">{tr("N°")}</th>
              <th className="px-3 py-2 text-start">{tr("N° d'inscription")}</th>
              <th className="px-3 py-2 text-start">{tr("Nom complet")}</th>
              {colonnes.map(({ evaluation, titre }) => (
                <th key={evaluation.id} className={entete}>
                  {titre}{evaluation.type === "EXAMEN" || evaluation.type === "INTERROGATION" ? ` (x${Number(evaluation.poids)})` : ""}
                  <span className="block text-xs font-normal">/{Number(evaluation.bareme)}</span>
                </th>
              ))}
              {avecMoyenneInterros && grille.interrogations && (
                <th className={`${entete} bg-fond`}>
                  {tr("Moy. Interros")} (x{Number(grille.interrogations.poids)})
                  <span className="block text-xs font-normal">/{Number(grille.interrogations.bareme)}</span>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {grille.eleves.map((eleve, ligne) => {
              const moyenne = moyennesInterros[eleve.etudiant];
              return (
                <tr key={eleve.etudiant} className="border-t border-bordure">
                  <td className="px-3 py-1.5">{eleve.numero}</td>
                  <td className="px-3 py-1.5 font-medium">{eleve.numero_inscription}</td>
                  <td className="px-3 py-1.5">{eleve.nom_complet}</td>
                  {colonnes.map(({ evaluation }, colonne) => {
                    const valeur = texte[cle(evaluation.id, eleve.etudiant)] ?? "";
                    const invalide = lire(valeur, Number(evaluation.bareme)) === "INVALIDE";
                    return (
                      <td key={evaluation.id} className="px-2 py-1 text-center">
                        <input
                          ref={(el) => { champs.current[`${colonne}:${ligne}`] = el; }}
                          inputMode="decimal"
                          className={`${CHAMP} w-16 text-center ${invalide ? "border-accent-rouge" : ""} ${modifiees.has(cle(evaluation.id, eleve.etudiant)) ? "bg-amber-50" : ""}`}
                          value={valeur}
                          disabled={lectureSeule}
                          onChange={(ev) => changer(evaluation.id, eleve.etudiant, ev.target.value)}
                          onKeyDown={(ev) => {
                            if (["Enter", "ArrowDown", "ArrowUp"].includes(ev.key)) {
                              ev.preventDefault();
                              naviguer(colonne, ligne, ev.key);
                            }
                          }}
                        />
                      </td>
                    );
                  })}
                  {avecMoyenneInterros && grille.interrogations && (
                    <td className="bg-fond px-3 py-1.5 text-center font-medium">{moyenne == null ? "-" : moyenne.toFixed(2)}</td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  /** Barre d'un onglet de saisie : compteurs, import/export Excel de la colonne choisie. */
  function barreSaisie() {
    return (
      <>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-4 text-sm">
            <span className="text-accent-vert">{tr("Notes saisies : {0}", compteurs.saisies)}</span>
            <span className={compteurs.manquantes ? "text-amber-700" : "text-texte-attenue"}>{tr("Notes manquantes : {0}", compteurs.manquantes)}</span>
            {compteurs.erreurs > 0 && <span className="text-accent-rouge">{tr("Invalides : {0}", compteurs.erreurs)}</span>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs text-texte-attenue">{tr("Fichier Excel de la colonne :")}</label>
            <select className={CHAMP} value={colonneFichier} onChange={(e) => setColonneFichier(e.target.value)}>
              {colonnes.map((c) => <option key={c.evaluation.id} value={c.evaluation.id}>{c.titre}</option>)}
            </select>
            <button className={BOUTON} onClick={() => setImportOuvert(true)} disabled={lectureSeule || !evaluationFichier}><Upload size={15} /> {tr("Importer Excel")}</button>
            <button className={BOUTON} onClick={exporter} disabled={!evaluationFichier}><FileSpreadsheet size={15} /> {tr("Exporter")}</button>
          </div>
        </div>
        <p className="mb-3 text-xs text-texte-attenue">
          {tx("Note (virgule ou point), {0} = absent, {1} = absent justifie, {2} = non applicable, vide = pas de note. Entree / fleches haut-bas : eleve suivant.", <b>A</b>, <b>AJ</b>, <b>NA</b>)}
        </p>
      </>
    );
  }

  function pied() {
    return (
      <div className="mt-3 flex items-center justify-end gap-3">
        {modifieesOnglet > 0 && <span className="text-xs text-amber-700">{tr("{0} cellule(s) modifiee(s), non enregistree(s).", modifieesOnglet)}</span>}
        <button className={BOUTON_PRIMAIRE} onClick={enregistrer} disabled={enCours || modifieesOnglet === 0 || lectureSeule}>
          <Save size={15} /> {tr("Enregistrer les notes")}
        </button>
      </div>
    );
  }

  const trimestreCourant = Number(trimestre);

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold text-texte">{tr("Saisie des notes")}</h1>

      <div className={`${CARTE} mb-4 grid grid-cols-2 gap-3 md:grid-cols-4`}>
        <div>
          <label className={ETIQUETTE}>{tr("Annee scolaire")}</label>
          <select className={`${CHAMP} w-full`} value={annee} onChange={(e) => { setAnnee(e.target.value); setClasse(""); setMatiere(""); }}>
            {annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Trimestre")}</label>
          <select className={`${CHAMP} w-full`} value={trimestre} onChange={(e) => setTrimestre(e.target.value)}>
            <option value="1">{tr("1er trimestre")}</option>
            <option value="2">{tr("2e trimestre")}</option>
            <option value="3">{tr("3e trimestre")}</option>
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Classe")}</label>
          <select className={`${CHAMP} w-full`} value={classe} onChange={(e) => { setClasse(e.target.value); setMatiere(""); }}>
            <option value="">--</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Matiere")}</label>
          <select className={`${CHAMP} w-full`} value={matiere} onChange={(e) => setMatiere(e.target.value)} disabled={!classe}>
            <option value="">--</option>
            {affectations.map((a) => <option key={a.matiere} value={a.matiere}>{a.matiere_nom}</option>)}
          </select>
        </div>
      </div>

      {grille && (
        <div className={CARTE}>
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <p className="font-medium text-texte">
              {nomMatiere} - {classes.find((c) => String(c.id) === classe)?.nom} (T{trimestre})
            </p>
            <div className="flex items-end gap-2">
              <div>
                <label className={ETIQUETTE}>{tr("Coefficient de la matiere")}</label>
                <input
                  className={`${CHAMP} w-24`} inputMode="decimal" value={reglages.coefficient}
                  disabled={!grille.peut_modifier_coefficient || verrouille}
                  title={grille.peut_modifier_coefficient ? undefined : tr("Seule la direction ou la pedagogie peut modifier le coefficient.")}
                  onChange={(e) => champReglage("coefficient", e.target.value)}
                />
              </div>
              <button className={BOUTON} disabled={enCours || !coefficientModifie || !grille.peut_modifier_coefficient || verrouille}
                      onClick={() => appliquer({ coefficient: reglages.coefficient }, tr("Parametres enregistres."))}>
                {tr("Modifier")}
              </button>
            </div>
          </div>

          <div className="mb-4 flex gap-1 border-b border-bordure">
            {ongletBouton("devoirs", tr("Devoirs"), nbModifiees(colonnesDevoirs))}
            {ongletBouton("composition", tr("Composition"), nbModifiees(colonnesComposition))}
            {ongletBouton("resultat", tr("Resultat"))}
          </div>

          {verrouille && onglet !== "resultat" && (
            <div className="mb-3 rounded border border-accent-orange bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {peutCorriger
                ? tr("Resultats valides : toute correction exige un motif et est tracee dans le journal d'audit.")
                : tr("Resultats valides : seule la direction peut corriger une note.")}
              {peutCorriger && (
                <input className={`${CHAMP} mt-2 w-full`} placeholder={tr("Motif de la correction")} value={motif} onChange={(e) => setMotif(e.target.value)} />
              )}
            </div>
          )}

          {horsModele && onglet !== "resultat" && (
            <div className="mb-3 rounded border border-accent-orange bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {tr("Anciennes donnees hors modele (moyenne des interrogations saisie directement, ou plusieurs compositions dans un trimestre) : l'administrateur peut les aligner avec « python manage.py normaliser_evaluations ».")}
            </div>
          )}

          {onglet === "devoirs" && (
            <>
              <div className="mb-3 grid grid-cols-2 items-end gap-3 md:grid-cols-4">
                <div>
                  <label className={ETIQUETTE}>{tr("Nombre de devoirs")}</label>
                  <input
                    className={`${CHAMP} w-full`} type="number" min={1} max={grille.max_devoirs} value={reglages.nombre}
                    disabled={modeDirect || verrouille || lectureSeule}
                    title={modeDirect ? tr("Moyenne des interrogations saisie directement (anciennes donnees) : elle contient deja des notes.") : undefined}
                    onChange={(e) => champReglage("nombre", e.target.value)}
                  />
                </div>
                <div>
                  <label className={ETIQUETTE}>{tr("Bareme des devoirs")}</label>
                  <input
                    className={`${CHAMP} w-full`} inputMode="decimal" value={reglages.baremeDevoirs}
                    disabled={modeDirect || baremeDevoirsFige || verrouille || lectureSeule}
                    title={baremeDevoirsFige ? tr("Le bareme ne peut plus etre modifie : des notes sont deja saisies.") : undefined}
                    onChange={(e) => champReglage("baremeDevoirs", e.target.value)}
                  />
                  <p className="mt-1 text-xs text-texte-attenue">{tr("Par defaut : {0}", Number(grille.bareme_defaut))}</p>
                </div>
                <div>
                  <button
                    className={`${BOUTON_PRIMAIRE} w-full justify-center`} disabled={enCours || verrouille || lectureSeule || modeDirect || !devoirsModifies}
                    onClick={() => appliquer({ nombre_devoirs: reglages.nombre, bareme_devoirs: reglages.baremeDevoirs }, devoirsCrees ? tr("Parametres enregistres.") : tr("Devoirs crees."))}
                  >
                    {devoirsCrees ? tr("Appliquer") : tr("Creer les devoirs")}
                  </button>
                </div>
              </div>
              <p className="mb-3 text-xs text-texte-attenue">
                {tr("Moyenne des interrogations = somme des notes / nombre de devoirs, ponderee x{0}.", Number(grille.interrogations?.poids ?? 3))}
              </p>
              {!devoirsCrees ? (
                <p className="text-sm text-amber-700">{tr("Choisissez le nombre de devoirs puis creez-les : les colonnes 1er Dev, 2e Dev... et la moyenne des interrogations s'afficheront.")}</p>
              ) : (
                <>
                  {barreSaisie()}
                  {tableauSaisie(true)}
                  {pied()}
                </>
              )}
            </>
          )}

          {onglet === "composition" && (
            <>
              <div className="mb-3 grid grid-cols-2 items-end gap-3 md:grid-cols-4">
                <div>
                  <label className={ETIQUETTE}>{tr("Bareme de la composition")}</label>
                  <input
                    className={`${CHAMP} w-full`} inputMode="decimal" value={reglages.baremeComposition}
                    disabled={baremeCompositionFige || verrouille || lectureSeule}
                    title={baremeCompositionFige ? tr("Le bareme ne peut plus etre modifie : des notes sont deja saisies.") : undefined}
                    onChange={(e) => champReglage("baremeComposition", e.target.value)}
                  />
                  <p className="mt-1 text-xs text-texte-attenue">{tr("Par defaut : {0}", Number(grille.bareme_defaut))}</p>
                </div>
                <div>
                  <button
                    className={`${BOUTON_PRIMAIRE} w-full justify-center`} disabled={enCours || verrouille || lectureSeule || !compositionModifiee}
                    onClick={() => appliquer({ bareme_composition: reglages.baremeComposition }, compositionCreee ? tr("Parametres enregistres.") : tr("Composition creee."))}
                  >
                    {compositionCreee ? tr("Appliquer") : tr("Creer la composition")}
                  </button>
                </div>
              </div>
              <p className="mb-3 text-xs text-texte-attenue">
                {tr("Une seule composition par trimestre : {0} (x{1}).", tr(grille.composition_attendue.libelle), Number(grille.composition_attendue.poids))}
              </p>
              {compositionCreee && (
                <>
                  {barreSaisie()}
                  {tableauSaisie(false)}
                  {pied()}
                </>
              )}
            </>
          )}

          {onglet === "resultat" && (
            <>
              {modifiees.size > 0 && (
                <p className="mb-3 text-sm text-amber-700">{tr("Enregistrez d'abord les modifications en cours : le resultat ne tient compte que des notes enregistrees.")}</p>
              )}
              {resultat && resultat.trimestre === trimestreCourant ? (
                <>
                  <div className="overflow-x-auto rounded border border-bordure">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-fond-barre text-texte-attenue">
                          <th className="px-3 py-2 text-start">{tr("N°")}</th>
                          <th className="px-3 py-2 text-start">{tr("N° d'inscription")}</th>
                          <th className="px-3 py-2 text-start">{tr("Nom complet")}</th>
                          <th className={entete}>{tr("Moy. Interros")} (x{Number(resultat.interrogations?.poids ?? 3)})</th>
                          <th className={entete}>{tr(resultat.composition?.libelle ?? grille.composition_attendue.libelle)} (x{Number(resultat.composition?.poids ?? grille.composition_attendue.poids)})</th>
                          <th className={`${entete} bg-fond`}>{tr("Moy. matiere T{0}", trimestreCourant)}<span className="block text-xs font-normal">/20</span></th>
                          <th className={`${entete} bg-fond`}>{tr("Rang")}</th>
                          {[1, 2, 3].map((t) => (
                            <th key={t} className={`${entete} ${t === trimestreCourant ? "bg-fond" : ""}`}>{tr("Moy. T{0}", t)}</th>
                          ))}
                          <th className={`${entete} bg-fond`}>{tr("Moy. annuelle")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {resultat.eleves.map((e) => (
                          <tr key={e.etudiant} className="border-t border-bordure">
                            <td className="px-3 py-1.5">{e.numero}</td>
                            <td className="px-3 py-1.5 font-medium">{e.numero_inscription}</td>
                            <td className="px-3 py-1.5">{e.nom_complet}</td>
                            <td className="px-3 py-1.5 text-center">{afficherCellule(e.interrogations)}</td>
                            <td className="px-3 py-1.5 text-center">{afficherCellule(e.composition)}</td>
                            <td className="bg-fond px-3 py-1.5 text-center font-semibold">{e.moyenne ?? "-"}</td>
                            <td className="bg-fond px-3 py-1.5 text-center">{e.rang ?? "-"}</td>
                            {[1, 2, 3].map((t) => (
                              <td key={t} className={`px-3 py-1.5 text-center ${t === trimestreCourant ? "bg-fond" : ""}`}>{e.moyennes[String(t)] ?? "-"}</td>
                            ))}
                            <td className="bg-fond px-3 py-1.5 text-center font-semibold">{e.moyenne_annuelle ?? "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="mt-2 text-xs text-texte-attenue">
                    {tr("Moyenne de la matiere = (interrogations x{0} + composition x{1}) / ({0} + {1}). Poids des trimestres pour la moyenne annuelle : {2}.",
                      Number(resultat.interrogations?.poids ?? 3), Number(resultat.composition?.poids ?? grille.composition_attendue.poids),
                      resultat.poids_trimestres.map(Number).join(" / "))}
                  </p>
                </>
              ) : (
                <p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>
              )}
            </>
          )}
        </div>
      )}

      {evaluationFichier && onglet !== "resultat" && (
        <ImportExcel<LigneNote>
          titre={tr("Importer les notes depuis Excel")}
          ouverte={importOuvert}
          onFermer={() => setImportOuvert(false)}
          consignes={
            <ol className="list-decimal space-y-1 ps-5">
              <li>{tr("Telechargez le modele (eleves de la classe, notes deja saisies incluses).")}</li>
              <li>{tx("Saisissez la note (virgule ou point), ou {0} (absent), {1} (absent justifie), {2} (non applicable). Case vide = pas de note.", <b>A</b>, <b>AJ</b>, <b>NA</b>)}</li>
              <li>{tr("Importez, controlez l'apercu, puis confirmez : rien n'est enregistre avant.")}</li>
            </ol>
          }
          urlModele={`${URL_EVALUATIONS}${evaluationFichier.id}/modele-import/`}
          nomModele="modele_notes.xlsx"
          urlImport={`${URL_EVALUATIONS}${evaluationFichier.id}/importer/`}
          titreValeur={tr("Note")}
          motifRequis={verrouille}
          rendreValeur={(l) => (
            <>
              {l.ancienne && <span className="me-1 text-texte-attenue line-through">{l.ancienne}</span>}
              {l.valeur ?? l.statut ?? ""}
            </>
          )}
          onImporte={() => charger()}
        />
      )}
    </div>
  );
}
