import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { DragEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle, CheckCircle2, Copy, FileSpreadsheet, FileText, Minus, Plus, Printer, Send, Trash2,
} from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { useConfirmation } from "../../composants/Confirmation";
import { Modale } from "../../composants/Modale";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import { imprimerPdf, messageErreurFichier, telechargerFichier } from "../../services/fichiers";
import type {
  Classe, ConflitEmploi, Groupe, Matiere, Professeur, Salle, SeanceGrille, VueEmploi,
} from "../../types";
import { RapportGenerationPanneau } from "./RapportGeneration";

import { NOM_JOUR } from "../../services/jours";
import { tr } from "../../i18n";
type Mode = "classe" | "professeur" | "salle" | "matiere";
const MODES: { valeur: Mode; libelle: string }[] = [
  { valeur: "classe", libelle: tr("Classe") },
  { valeur: "professeur", libelle: tr("Professeur") },
  { valeur: "salle", libelle: tr("Salle") },
  { valeur: "matiere", libelle: tr("Matiere") },
];
const COULEURS = ["#e8f1f4", "#fdf1dc", "#e6f4ea", "#f3e8f7", "#fde8e8", "#e8ecfb", "#f1f4e0", "#e3f4f1"];

const minutes = (hhmm: string) => Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3, 5));
const hhmm = (valeur: number) => `${String(Math.floor(valeur / 60)).padStart(2, "0")}:${String(valeur % 60).padStart(2, "0")}`;

interface Formulaire {
  id?: number;
  classe: string;
  groupe: string;
  matiere: string;
  professeur: string;
  salle: string;
  jour: string;
  heure_debut: string;
  heure_fin: string;
}

function lignesCarte(s: SeanceGrille, mode: Mode): string[] {
  const classe = s.classe_nom + (s.groupe_nom ? ` (${s.groupe_nom})` : "");
  const salle = s.salle_nom ? tr("Salle {0}", s.salle_nom) : tr("Sans salle");
  if (mode === "classe") return [s.professeur_nom, salle];
  if (mode === "professeur") return [classe, salle];
  if (mode === "salle") return [classe, s.professeur_nom];
  return [classe, s.professeur_nom, salle];
}

/** Editeur visuel : glisser-deposer d'une seance vers un autre creneau (Alt/Ctrl = copier).
 * Chaque modification est verifiee cote serveur ; un conflit obligatoire est refuse et explique. */
export function PageEditeurEmploi() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();
  const role = utilisateur?.role ?? "";
  const estProfesseur = role === "PROFESSEUR";
  const peutGerer = ["ADMINISTRATEUR", "DIRECTEUR", "RESPONSABLE_PEDAGOGIQUE"].includes(role);

  const [vue, setVue] = useState<VueEmploi | null>(null);
  const [conflits, setConflits] = useState<ConflitEmploi[]>([]);
  const [refus, setRefus] = useState<ConflitEmploi[]>([]);
  const [mode, setMode] = useState<Mode>("classe");
  const [cible, setCible] = useState("");
  const [survol, setSurvol] = useState<string | null>(null);
  const [formulaire, setFormulaire] = useState<Formulaire | null>(null);
  const [copie, setCopie] = useState({ jour: "0", debut: "" });
  const glisse = useRef<SeanceGrille | null>(null);

  const modifiable = !!vue?.emploi.modifiable && peutGerer;
  // L'annee vient de l'emploi lui-meme (et non de la grille) : la grille ne peut se charger qu'une fois une classe
  // choisie, et la liste des classes depend de l'annee.
  const [anneeEmploi, setAnneeEmploi] = useState<number | undefined>(undefined);
  const annee = anneeEmploi ?? vue?.emploi.annee_scolaire;
  useEffect(() => {
    if (estProfesseur) return;
    api.get(`/emplois-du-temps/emplois/${id}/`).then(({ data }) => setAnneeEmploi(data.annee_scolaire)).catch((err) => notifierErreur(messageErreur(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, estProfesseur]);
  // Le professeur voit sa propre grille (filtre impose par le serveur) : aucune liste a charger.
  const classes = useOptions<Classe>(`/referentiels/classes/?annee_scolaire=${annee}`, !!annee && !estProfesseur);
  const professeurs = useOptions<Professeur>("/professeurs/professeurs/", peutGerer);
  const salles = useOptions<Salle>("/referentiels/salles/", !estProfesseur);
  const matieres = useOptions<Matiere>("/referentiels/matieres/", !estProfesseur);
  const groupes = useOptions<Groupe>(`/referentiels/groupes/?classe=${formulaire?.classe}`, !!formulaire?.classe);

  const options = useMemo(() => {
    if (mode === "classe") return classes.map((c) => ({ id: c.id, nom: c.nom }));
    if (mode === "professeur") return professeurs.map((p) => ({ id: p.id, nom: p.nom_complet }));
    if (mode === "salle") return salles.map((s) => ({ id: s.id, nom: s.nom }));
    return matieres.map((m) => ({ id: m.id, nom: m.nom_affiche ?? m.nom }));
  }, [mode, classes, professeurs, salles, matieres]);

  useEffect(() => {
    if (!estProfesseur && !options.some((o) => String(o.id) === cible)) setCible(options[0] ? String(options[0].id) : "");
  }, [options, cible, estProfesseur]);

  const charger = useCallback(async () => {
    if (!estProfesseur && !cible) return;
    try {
      const [grille, verification] = await Promise.all([
        api.get(`/emplois-du-temps/emplois/${id}/vue/`, { params: estProfesseur ? {} : { [mode]: cible } }),
        peutGerer ? api.get(`/emplois-du-temps/emplois/${id}/verifier/`) : Promise.resolve(null),
      ]);
      setVue(grille.data);
      setConflits(verification?.data.conflits ?? []);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, mode, cible, estProfesseur, peutGerer]);

  useEffect(() => { charger(); }, [charger]);

  // --- grille : seances par creneau de depart, avec fusion des cellules d'une seance longue
  const { parDepart, spans, couverts } = useMemo(() => {
    const parDepart = new Map<string, SeanceGrille[]>();
    const spans = new Map<string, number>();
    const couverts = new Set<string>();
    if (!vue) return { parDepart, spans, couverts };
    const origine = minutes(vue.cadre.debut);
    const pas = vue.cadre.duree_creneau;
    const index = (heure: string) => Math.floor((minutes(heure) - origine) / pas);
    for (const s of vue.seances) {
      const cle = `${s.jour}-${index(s.heure_debut)}`;
      parDepart.set(cle, [...(parDepart.get(cle) ?? []), s]);
    }
    const pauses = new Set(vue.cadre.creneaux.filter((c) => c.pause).map((c) => c.index));
    for (const [cle, liste] of parDepart) {
      if (liste.length !== 1) continue;
      const [jour, depart] = cle.split("-").map(Number);
      const longueur = Math.round((minutes(liste[0].heure_fin) - minutes(liste[0].heure_debut)) / pas);
      if (longueur <= 1) continue;
      const libre = Array.from({ length: longueur - 1 }, (_, k) => depart + k + 1)
        .every((k) => !pauses.has(k) && !parDepart.has(`${jour}-${k}`));
      if (!libre) continue;
      spans.set(cle, longueur);
      for (let k = 1; k < longueur; k++) couverts.add(`${jour}-${depart + k}`);
    }
    return { parDepart, spans, couverts };
  }, [vue]);

  async function appliquer(action: () => Promise<unknown>, succes?: string) {
    setRefus([]);
    try {
      await action();
      if (succes) notifierSucces(succes);
    } catch (err: any) {
      const donnees = err?.response?.data;
      if (donnees?.conflits) setRefus(donnees.conflits);
      notifierErreur(messageErreur(err));
    }
    await charger();
  }

  const deplacer = (s: SeanceGrille, jour: number, debut: string, fin: string) =>
    appliquer(() => api.patch(`/emplois-du-temps/seances/${s.id}/`, { jour, heure_debut: debut, heure_fin: fin }), tr("Seance deplacee."));

  const copier = (s: SeanceGrille, jour: number, debut: string, fin?: string) =>
    appliquer(() => api.post(`/emplois-du-temps/seances/${s.id}/copier/`, { jour, heure_debut: debut, ...(fin ? { heure_fin: fin } : {}) }), tr("Seance copiee."));

  function changerDuree(s: SeanceGrille, delta: number) {
    if (!vue) return;
    const fin = minutes(s.heure_fin) + delta * vue.cadre.duree_creneau;
    if (fin <= minutes(s.heure_debut)) return;
    appliquer(() => api.patch(`/emplois-du-temps/seances/${s.id}/`, { heure_fin: hhmm(fin) }));
  }

  function surDepot(e: DragEvent, jour: number, debut: string) {
    e.preventDefault();
    setSurvol(null);
    const s = glisse.current;
    glisse.current = null;
    if (!s || !modifiable) return;
    const duree = minutes(s.heure_fin) - minutes(s.heure_debut);
    const fin = hhmm(minutes(debut) + duree);
    if (e.altKey || e.ctrlKey) copier(s, jour, debut, fin);
    else deplacer(s, jour, debut, fin);
  }

  function ouvrirFormulaire(s?: SeanceGrille) {
    if (!vue) return;
    const premier = vue.cadre.creneaux.find((c) => !c.pause);
    setRefus([]);
    setCopie({ jour: String(vue.cadre.jours[0]?.id ?? 0), debut: premier?.debut ?? "" });
    setFormulaire(s ? {
      id: s.id, classe: String(s.classe), groupe: s.groupe ? String(s.groupe) : "", matiere: String(s.matiere),
      professeur: String(s.professeur), salle: s.salle ? String(s.salle) : "", jour: String(s.jour),
      heure_debut: s.heure_debut.slice(0, 5), heure_fin: s.heure_fin.slice(0, 5),
    } : {
      classe: mode === "classe" ? cible : "", groupe: "", matiere: mode === "matiere" ? cible : "",
      professeur: mode === "professeur" ? cible : "", salle: mode === "salle" ? cible : "",
      jour: String(vue.cadre.jours[0]?.id ?? 0), heure_debut: premier?.debut ?? "", heure_fin: premier?.fin ?? "",
    });
  }

  async function enregistrerFormulaire() {
    if (!formulaire || !vue) return;
    const corps = {
      emploi: vue.emploi.id, classe: formulaire.classe, groupe: formulaire.groupe || null, matiere: formulaire.matiere,
      professeur: formulaire.professeur, salle: formulaire.salle || null, jour: Number(formulaire.jour),
      heure_debut: formulaire.heure_debut, heure_fin: formulaire.heure_fin,
    };
    setRefus([]);
    try {
      if (formulaire.id) await api.patch(`/emplois-du-temps/seances/${formulaire.id}/`, corps);
      else await api.post("/emplois-du-temps/seances/", corps);
      setFormulaire(null);
      notifierSucces(tr("Seance enregistree."));
      await charger();
    } catch (err: any) {
      if (err?.response?.data?.conflits) setRefus(err.response.data.conflits);
      notifierErreur(messageErreur(err));
    }
  }

  async function supprimerSeance() {
    if (!formulaire?.id) return;
    const ok = await demanderConfirmation({ titre: tr("Supprimer la seance"), message: tr("Retirer ce cours de l'emploi du temps ?") });
    if (!ok) return;
    await appliquer(() => api.delete(`/emplois-du-temps/seances/${formulaire.id}/`), tr("Seance supprimee."));
    setFormulaire(null);
  }

  async function publier() {
    if (!vue) return;
    const ok = await demanderConfirmation({
      titre: tr("Publier l'emploi du temps"),
      message: tr("Il deviendra l'emploi du temps officiel (l'actuel sera archive) et ne sera plus modifiable. Les conflits sont verifies une derniere fois."),
    });
    if (!ok) return;
    await appliquer(async () => {
      const { data } = await api.post(`/emplois-du-temps/emplois/${vue.emploi.id}/publier/`, {});
      notifierSucces(data.detail);
    });
  }

  async function dupliquer() {
    if (!vue) return;
    try {
      const { data } = await api.post(`/emplois-du-temps/emplois/${vue.emploi.id}/dupliquer/`, {});
      notifierSucces(tr("Brouillon cree."));
      navigate(`/emplois-du-temps/${data.id}`);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function sortie(type: "imprimer" | "pdf" | "excel", toutes = false) {
    if (!vue) return;
    const params = toutes ? { toutes: mode } : estProfesseur ? {} : { [mode]: cible };
    const base = `/emplois-du-temps/emplois/${vue.emploi.id}`;
    try {
      if (type === "imprimer") await imprimerPdf(`${base}/pdf/`, params);
      if (type === "pdf") await telechargerFichier(`${base}/pdf/`, `emploi_du_temps_${vue.emploi.id}.pdf`, params);
      if (type === "excel") await telechargerFichier(`${base}/excel/`, `emploi_du_temps_${vue.emploi.id}.xlsx`, params);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  if (!vue) return <p className="text-sm text-texte-attenue">{tr("Chargement de l'emploi du temps...")}</p>;

  const creneauxUtiles = vue.cadre.creneaux.filter((c) => !c.pause);
  const f = formulaire;
  const maj = (partiel: Partial<Formulaire>) => setFormulaire((courant) => (courant ? { ...courant, ...partiel } : courant));

  return (
    <div>
      <div className="mb-3">
        <Link to="/emplois-du-temps" className="text-sm text-entete hover:underline">{tr("← Retour aux emplois du temps")}</Link>
      </div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-texte">{vue.emploi.nom}</h1>
          <p className="text-sm text-texte-attenue">
            {vue.emploi.statut === "BROUILLON" ? tr("Brouillon - modifiable") : vue.emploi.statut === "PUBLIE" ? tr("Publie - lecture seule") : tr("Archive - lecture seule")}
            {vue.emploi.origine === "GENETIQUE" && tr(" - genere automatiquement")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {modifiable && (
            <>
              <button className={BOUTON} onClick={() => ouvrirFormulaire()}><Plus size={15} /> {tr("Nouvelle seance")}</button>
              <button className={BOUTON_PRIMAIRE} onClick={publier}><Send size={15} /> {tr("Publier")}</button>
            </>
          )}
          {peutGerer && !vue.emploi.modifiable && (
            <button className={BOUTON} onClick={dupliquer}><Copy size={15} /> {tr("Dupliquer pour modifier")}</button>
          )}
          <button className={BOUTON} onClick={() => sortie("imprimer")}><Printer size={15} /> {tr("Imprimer")}</button>
          <button className={BOUTON} onClick={() => sortie("pdf")}><FileText size={15} /> {tr("PDF")}</button>
          <button className={BOUTON} onClick={() => sortie("excel")}><FileSpreadsheet size={15} /> {tr("Excel")}</button>
          {!estProfesseur && <button className={BOUTON} onClick={() => sortie("pdf", true)}><FileText size={15} /> {mode === "classe" ? tr("PDF de toutes les classes") : mode === "professeur" ? tr("PDF de tous les professeurs") : mode === "salle" ? tr("PDF de toutes les salles") : tr("PDF de toutes les matieres")}</button>}
        </div>
      </div>

      {!estProfesseur && (
        <div className={`${CARTE} mb-3 flex flex-wrap items-center gap-2`}>
          <span className="text-sm text-texte-attenue">{tr("Afficher par")}</span>
          <select className={CHAMP} value={mode} onChange={(e) => { setMode(e.target.value as Mode); setCible(""); }}>
            {MODES.map((m) => <option key={m.valeur} value={m.valeur}>{m.libelle}</option>)}
          </select>
          <select className={CHAMP} value={cible} onChange={(e) => setCible(e.target.value)}>
            {options.map((o) => <option key={o.id} value={o.id}>{o.nom}</option>)}
          </select>
          {modifiable && <span className="text-xs text-texte-attenue">{tr("Glissez une seance vers un creneau pour la deplacer (Alt ou Ctrl enfonce : copier). Clic : modifier.")}</span>}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_20rem]">
        <div className="overflow-x-auto rounded-md border border-bordure bg-fond-carte shadow-carte">
          <table className="w-full table-fixed border-collapse text-xs">
            <thead>
              <tr className="bg-fond-barre text-texte-attenue">
                <th className="w-24 border border-bordure px-2 py-1.5 text-start">{tr("Horaire")}</th>
                {vue.cadre.jours.map((j) => <th key={j.id} className="border border-bordure px-2 py-1.5">{NOM_JOUR[j.id] ?? j.nom}</th>)}
              </tr>
            </thead>
            <tbody>
              {vue.cadre.creneaux.map((c) => {
                if (c.pause) {
                  return (
                    <tr key={c.index}>
                      <td className="border border-bordure bg-fond-barre px-2 py-1.5 text-texte-attenue">{c.debut}-{c.fin}</td>
                      <td colSpan={vue.cadre.jours.length} className="border border-bordure bg-fond-barre px-2 py-1.5 text-center text-texte-attenue">{tr("Pause")}</td>
                    </tr>
                  );
                }
                return (
                  <tr key={c.index} className="h-16 align-top">
                    <td className="border border-bordure bg-fond-barre px-2 py-1.5 text-texte-attenue">{c.debut}-{c.fin}</td>
                    {vue.cadre.jours.map((j) => {
                      const cle = `${j.id}-${c.index}`;
                      if (couverts.has(cle)) return null;
                      const occupants = parDepart.get(cle) ?? [];
                      return (
                        <td
                          key={cle}
                          rowSpan={spans.get(cle) ?? 1}
                          onDragOver={(e) => { if (modifiable) { e.preventDefault(); setSurvol(cle); } }}
                          onDragLeave={() => setSurvol((s) => (s === cle ? null : s))}
                          onDrop={(e) => surDepot(e, j.id, c.debut)}
                          className={`border border-bordure p-0.5 ${survol === cle ? "bg-amber-100" : ""}`}
                        >
                          <div className="flex h-full flex-col gap-0.5">
                            {occupants.map((s) => (
                              <div
                                key={s.id}
                                draggable={modifiable}
                                onDragStart={() => { glisse.current = s; }}
                                onDragEnd={() => { glisse.current = null; setSurvol(null); }}
                                onClick={() => peutGerer && ouvrirFormulaire(s)}
                                title={s.conflits.join("\n")}
                                style={{ background: COULEURS[s.matiere % COULEURS.length] }}
                                className={`flex-1 rounded border px-1.5 py-1 ${modifiable ? "cursor-grab" : ""} ${s.conflits.length ? "border-accent-rouge ring-1 ring-accent-rouge" : "border-transparent"}`}
                              >
                                <div className="flex items-start justify-between gap-1">
                                  <span className="font-semibold text-texte">{s.matiere_nom}</span>
                                  {s.conflits.length > 0 && <AlertTriangle size={13} className="shrink-0 text-accent-rouge" />}
                                </div>
                                {lignesCarte(s, mode).map((l) => <div key={l} className="truncate text-texte-attenue">{l}</div>)}
                                {modifiable && (
                                  <div className="mt-0.5 flex gap-1">
                                    <button title={tr("Allonger d'un creneau")} className="rounded bg-white/70 px-1 hover:bg-white"
                                            onClick={(e) => { e.stopPropagation(); changerDuree(s, 1); }}><Plus size={11} /></button>
                                    <button title={tr("Raccourcir d'un creneau")} className="rounded bg-white/70 px-1 hover:bg-white"
                                            onClick={(e) => { e.stopPropagation(); changerDuree(s, -1); }}><Minus size={11} /></button>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <aside className="space-y-3">
          {refus.length > 0 && (
            <div className="rounded border border-accent-rouge bg-red-50 p-3 text-sm text-accent-rouge">
              <p className="mb-1 font-semibold">{tr("Modification refusee")}</p>
              <ul className="list-disc space-y-1 ps-4">{refus.map((c) => <li key={c.message}>{c.message}</li>)}</ul>
            </div>
          )}
          {peutGerer && (
            <div className={CARTE}>
              <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-texte">
                {conflits.length === 0 ? <CheckCircle2 size={16} className="text-accent-vert" /> : <AlertTriangle size={16} className="text-accent-rouge" />}
                {conflits.length === 0 ? tr("Aucun conflit") : tr("{0} conflit(s)", conflits.length)}
              </p>
              {conflits.length === 0 ? (
                <p className="text-xs text-texte-attenue">{tr("Toutes les contraintes obligatoires sont respectees (la publication verifie aussi qu'une salle est attribuee).")}</p>
              ) : (
                <ul className="max-h-80 list-disc space-y-1 overflow-y-auto ps-4 text-xs text-accent-rouge">
                  {conflits.map((c, i) => <li key={`${c.message}${i}`}>{c.message}</li>)}
                </ul>
              )}
            </div>
          )}
          {peutGerer && vue.emploi.rapport.unites !== undefined && (
            <details className={CARTE}>
              <summary className="cursor-pointer text-sm font-semibold text-texte">{tr("Rapport de generation")}</summary>
              <div className="mt-2"><RapportGenerationPanneau rapport={vue.emploi.rapport} /></div>
            </details>
          )}
        </aside>
      </div>

      <Modale titre={f?.id ? tr("Modifier la seance") : tr("Nouvelle seance")} ouverte={!!f} onFermer={() => setFormulaire(null)} largeur="max-w-2xl">
        {f && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={ETIQUETTE}>{tr("Classe *")}</label>
                <select className={`${CHAMP} w-full`} value={f.classe} onChange={(e) => maj({ classe: e.target.value, groupe: "" })}>
                  <option value="">--</option>
                  {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
                </select>
              </div>
              <div>
                <label className={ETIQUETTE}>{tr("Groupe (optionnel)")}</label>
                <select className={`${CHAMP} w-full`} value={f.groupe} onChange={(e) => maj({ groupe: e.target.value })} disabled={!f.classe}>
                  <option value="">{tr("Classe entiere")}</option>
                  {groupes.map((g) => <option key={g.id} value={g.id}>{g.nom}</option>)}
                </select>
              </div>
              <div>
                <label className={ETIQUETTE}>{tr("Matiere *")}</label>
                <select className={`${CHAMP} w-full`} value={f.matiere} onChange={(e) => maj({ matiere: e.target.value })}>
                  <option value="">--</option>
                  {matieres.map((m) => <option key={m.id} value={m.id}>{m.nom_affiche ?? m.nom}</option>)}
                </select>
              </div>
              <div>
                <label className={ETIQUETTE}>{tr("Professeur *")}</label>
                <select className={`${CHAMP} w-full`} value={f.professeur} onChange={(e) => maj({ professeur: e.target.value })}>
                  <option value="">--</option>
                  {professeurs.map((p) => <option key={p.id} value={p.id}>{p.nom_complet}</option>)}
                </select>
              </div>
              <div>
                <label className={ETIQUETTE}>{tr("Salle")}</label>
                <select className={`${CHAMP} w-full`} value={f.salle} onChange={(e) => maj({ salle: e.target.value })}>
                  <option value="">{tr("-- Aucune --")}</option>
                  {salles.map((s) => <option key={s.id} value={s.id}>{tr("{0} ({1} places)", s.nom, s.capacite)}</option>)}
                </select>
              </div>
              <div>
                <label className={ETIQUETTE}>{tr("Jour *")}</label>
                <select className={`${CHAMP} w-full`} value={f.jour} onChange={(e) => maj({ jour: e.target.value })}>
                  {vue.cadre.jours.map((j) => <option key={j.id} value={j.id}>{NOM_JOUR[j.id] ?? j.nom}</option>)}
                </select>
              </div>
              <div>
                <label className={ETIQUETTE}>{tr("Debut *")}</label>
                <select className={`${CHAMP} w-full`} value={f.heure_debut} onChange={(e) => maj({ heure_debut: e.target.value })}>
                  {creneauxUtiles.map((c) => <option key={c.index} value={c.debut}>{c.debut}</option>)}
                </select>
              </div>
              <div>
                <label className={ETIQUETTE}>{tr("Fin *")}</label>
                <select className={`${CHAMP} w-full`} value={f.heure_fin} onChange={(e) => maj({ heure_fin: e.target.value })}>
                  {creneauxUtiles.map((c) => <option key={c.index} value={c.fin}>{c.fin}</option>)}
                </select>
              </div>
            </div>

            {refus.length > 0 && (
              <ul className="list-disc space-y-1 rounded border border-accent-rouge bg-red-50 py-2 ps-7 pe-3 text-sm text-accent-rouge">
                {refus.map((c) => <li key={c.message}>{c.message}</li>)}
              </ul>
            )}

            {f.id && vue.seances.find((s) => s.id === f.id) && (
              <div className="flex flex-wrap items-end gap-2 rounded border border-bordure bg-fond-barre p-2">
                <span className="text-sm text-texte-attenue">{tr("Copier vers")}</span>
                <select className={CHAMP} value={copie.jour} onChange={(e) => setCopie({ ...copie, jour: e.target.value })}>
                  {vue.cadre.jours.map((j) => <option key={j.id} value={j.id}>{NOM_JOUR[j.id] ?? j.nom}</option>)}
                </select>
                <select className={CHAMP} value={copie.debut} onChange={(e) => setCopie({ ...copie, debut: e.target.value })}>
                  {creneauxUtiles.map((c) => <option key={c.index} value={c.debut}>{c.debut}</option>)}
                </select>
                <button type="button" className={BOUTON} onClick={async () => {
                  const source = vue.seances.find((s) => s.id === f.id)!;
                  await copier(source, Number(copie.jour), copie.debut);
                }}><Copy size={15} /> {tr("Copier")}</button>
              </div>
            )}

            <div className="flex justify-between gap-2">
              <div>
                {f.id && <button type="button" className={`${BOUTON} text-accent-rouge`} onClick={supprimerSeance}><Trash2 size={15} /> {tr("Supprimer")}</button>}
              </div>
              <div className="flex gap-2">
                <button type="button" className={BOUTON} onClick={() => setFormulaire(null)}>{tr("Annuler")}</button>
                <button type="button" className={BOUTON_PRIMAIRE} onClick={enregistrerFormulaire}
                        disabled={!f.classe || !f.matiere || !f.professeur || !f.heure_debut || !f.heure_fin}>{tr("Enregistrer")}</button>
              </div>
            </div>
          </div>
        )}
      </Modale>
    </div>
  );
}
