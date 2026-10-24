import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { FileSpreadsheet, Pencil, Plus, Save, Trash2, Upload } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { useConfirmation } from "../../composants/Confirmation";
import { Modale } from "../../composants/Modale";
import { ImportExcel } from "../../composants/ImportExcel";
import type { LigneApercu } from "../../composants/ImportExcel";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import { messageErreurFichier, telechargerFichier } from "../../services/fichiers";
import type {
  AffectationMatiereClasse, AnneeScolaire, Classe, EleveNote, Evaluation, StatutNote, TypeEvaluation,
} from "../../types";

interface Saisie { statut: StatutNote; valeur: string }
interface LigneNote extends LigneApercu { statut: StatutNote | null; valeur: string | null; ancienne: string | null }

const STATUTS: { valeur: StatutNote; libelle: string }[] = [
  { valeur: "SAISIE", libelle: "Note" },
  { valeur: "ABSENT", libelle: "Absent" },
  { valeur: "ABSENT_JUSTIFIE", libelle: "Absent justifie" },
  { valeur: "NON_APPLICABLE", libelle: "Non applicable" },
];

// Modeles inspires du bulletin papier : interrogations x3, composition 1 x1, composition 2 x2.
const MODELES: { libelle: string; type: TypeEvaluation; poids: string }[] = [
  { libelle: "Interrogations", type: "INTERROGATION", poids: "3" },
  { libelle: "Composition 1", type: "EXAMEN", poids: "1" },
  { libelle: "Composition 2", type: "EXAMEN", poids: "2" },
  { libelle: "Devoir", type: "DEVOIR", poids: "1" },
];

function nombre(texte: string): number {
  return Number(texte.trim().replace(",", "."));
}

export function PageNotes() {
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();
  const peutCorriger = utilisateur?.role === "ADMINISTRATEUR" || utilisateur?.role === "DIRECTEUR";

  // --- selection
  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [annee, setAnnee] = useState("");
  const [trimestre, setTrimestre] = useState("1");
  const classes = useOptions<Classe>(`/referentiels/classes/?annee_scolaire=${annee}`, !!annee);
  const [classe, setClasse] = useState("");
  const affectations = useOptions<AffectationMatiereClasse>(`/referentiels/affectations-matiere-classe/?classe=${classe}`, !!classe);
  const [matiere, setMatiere] = useState("");
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [idEvaluation, setIdEvaluation] = useState("");

  // --- grille
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [eleves, setEleves] = useState<EleveNote[]>([]);
  const [saisie, setSaisie] = useState<Record<number, Saisie>>({});
  const [modifie, setModifie] = useState(false);
  const [motif, setMotif] = useState("");
  const [enCours, setEnCours] = useState(false);
  const champs = useRef<(HTMLInputElement | null)[]>([]);

  // --- modales
  const [formOuvert, setFormOuvert] = useState(false);
  const [edition, setEdition] = useState<Evaluation | null>(null);
  const [form, setForm] = useState({ libelle: "", type: "DEVOIR" as TypeEvaluation, date: "", bareme: "20", poids: "1" });
  const [importOuvert, setImportOuvert] = useState(false);

  useEffect(() => {
    if (!annee && annees.length > 0) setAnnee(String((annees.find((a) => a.active) ?? annees[0]).id));
  }, [annees, annee]);

  const chargerEvaluations = useCallback(async (aSelectionner?: number) => {
    if (!annee || !classe || !matiere) {
      setEvaluations([]);
      return;
    }
    try {
      const { data } = await api.get("/evaluations/evaluations/", {
        params: { annee_scolaire: annee, classe, matiere, trimestre, taille_page: 100 },
      });
      setEvaluations(data.resultats);
      if (aSelectionner) setIdEvaluation(String(aSelectionner));
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [annee, classe, matiere, trimestre]);

  useEffect(() => {
    setIdEvaluation("");
    chargerEvaluations();
  }, [chargerEvaluations]);

  function charger(donnees: { evaluation: Evaluation; eleves: EleveNote[] }) {
    setEvaluation(donnees.evaluation);
    setEleves(donnees.eleves);
    setSaisie(Object.fromEntries(donnees.eleves.map((e): [number, Saisie] => [
      e.etudiant, { statut: e.statut === "MANQUANTE" ? "SAISIE" : e.statut, valeur: e.valeur ?? "" },
    ])));
    setModifie(false);
    setMotif("");
  }

  const chargerGrille = useCallback(async () => {
    if (!idEvaluation) {
      setEvaluation(null);
      setEleves([]);
      return;
    }
    try {
      const { data } = await api.get(`/evaluations/evaluations/${idEvaluation}/notes/`);
      charger(data);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idEvaluation]);

  useEffect(() => { chargerGrille(); }, [chargerGrille]);

  const verrouille = !!evaluation?.resultats_valides;
  const lectureSeule = verrouille && !peutCorriger;
  const bareme = evaluation ? Number(evaluation.bareme) : 20;

  function changer(etudiant: number, modif: Partial<Saisie>) {
    setSaisie((s) => ({ ...s, [etudiant]: { ...s[etudiant], ...modif } }));
    setModifie(true);
  }

  function invalide(ligne?: Saisie) {
    if (!ligne || ligne.statut !== "SAISIE" || ligne.valeur.trim() === "") return false;
    const n = nombre(ligne.valeur);
    return !Number.isFinite(n) || n < 0 || n > bareme;
  }

  const compteurs = useMemo(() => {
    const lignes = eleves.map((e) => saisie[e.etudiant]).filter(Boolean);
    return {
      saisies: lignes.filter((l) => l.statut === "SAISIE" && l.valeur.trim() !== "").length,
      manquantes: lignes.filter((l) => l.statut === "SAISIE" && l.valeur.trim() === "").length,
      erreurs: lignes.filter(invalide).length,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eleves, saisie, bareme]);

  function naviguer(index: number, touche: string) {
    const cible = touche === "ArrowUp" ? index - 1 : index + 1;
    champs.current[cible]?.focus();
    champs.current[cible]?.select();
  }

  async function enregistrer() {
    if (!evaluation) return;
    if (compteurs.erreurs > 0) {
      notifierErreur(`${compteurs.erreurs} note(s) invalide(s) (0 a ${bareme}) : corrigez avant d'enregistrer.`);
      return;
    }
    if (verrouille && !motif.trim()) {
      notifierErreur("Resultats valides : saisissez le motif de la correction.");
      return;
    }
    setEnCours(true);
    try {
      const notes = eleves.map((e) => {
        const s = saisie[e.etudiant];
        if (s.statut !== "SAISIE") return { etudiant: e.etudiant, statut: s.statut };
        return s.valeur.trim() === ""
          ? { etudiant: e.etudiant, statut: "MANQUANTE" }
          : { etudiant: e.etudiant, statut: "SAISIE", valeur: s.valeur.trim() };
      });
      const { data } = await api.post(`/evaluations/evaluations/${evaluation.id}/notes/`, { notes, motif });
      charger(data);
      chargerEvaluations();
      notifierSucces(`Notes enregistrees (${data.bilan.creees} nouvelle(s), ${data.bilan.modifiees} modifiee(s)).`);
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  function ouvrirForm(existante: Evaluation | null) {
    setEdition(existante);
    setForm(existante
      ? { libelle: existante.libelle, type: existante.type, date: existante.date ?? "", bareme: existante.bareme, poids: existante.poids }
      : { libelle: "", type: "DEVOIR", date: "", bareme: "20", poids: "1" });
    setFormOuvert(true);
  }

  async function soumettreForm(e: FormEvent) {
    e.preventDefault();
    try {
      const corps = { ...form, date: form.date || null };
      const { data } = edition
        ? await api.patch(`/evaluations/evaluations/${edition.id}/`, corps)
        : await api.post("/evaluations/evaluations/", { ...corps, annee_scolaire: annee, classe, matiere, trimestre });
      setFormOuvert(false);
      notifierSucces(edition ? "Evaluation modifiee." : "Evaluation creee.");
      await chargerEvaluations(data.id);
      if (edition) chargerGrille();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function supprimerEvaluation() {
    if (!evaluation) return;
    const ok = await demanderConfirmation({
      titre: "Supprimer l'evaluation", message: `Supprimer « ${evaluation.libelle} » ? Possible uniquement si aucune note n'est saisie.`,
    });
    if (!ok) return;
    try {
      await api.delete(`/evaluations/evaluations/${evaluation.id}/`);
      notifierSucces("Evaluation supprimee.");
      setIdEvaluation("");
      chargerEvaluations();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function exporter() {
    if (!evaluation) return;
    try {
      await telechargerFichier(`/evaluations/evaluations/${evaluation.id}/exporter/`, `notes_${evaluation.classe_nom}_${evaluation.libelle}.xlsx`);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  const selectionComplete = annee && classe && matiere;

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold text-texte">Saisie des notes</h1>

      <div className={`${CARTE} mb-4 grid grid-cols-2 gap-3 md:grid-cols-5`}>
        <div>
          <label className={ETIQUETTE}>Annee scolaire</label>
          <select className={`${CHAMP} w-full`} value={annee} onChange={(e) => { setAnnee(e.target.value); setClasse(""); setMatiere(""); }}>
            {annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>Trimestre</label>
          <select className={`${CHAMP} w-full`} value={trimestre} onChange={(e) => setTrimestre(e.target.value)}>
            <option value="1">1er trimestre</option>
            <option value="2">2e trimestre</option>
            <option value="3">3e trimestre</option>
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>Classe</label>
          <select className={`${CHAMP} w-full`} value={classe} onChange={(e) => { setClasse(e.target.value); setMatiere(""); }}>
            <option value="">--</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>Matiere</label>
          <select className={`${CHAMP} w-full`} value={matiere} onChange={(e) => setMatiere(e.target.value)} disabled={!classe}>
            <option value="">--</option>
            {affectations.map((a) => <option key={a.matiere} value={a.matiere}>{a.matiere_nom}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>Evaluation</label>
          <select className={`${CHAMP} w-full`} value={idEvaluation} onChange={(e) => setIdEvaluation(e.target.value)} disabled={!selectionComplete}>
            <option value="">--</option>
            {evaluations.map((ev) => (
              <option key={ev.id} value={ev.id}>{ev.libelle} (x{Number(ev.poids)}, /{Number(ev.bareme)})</option>
            ))}
          </select>
        </div>
        <div className="col-span-full flex flex-wrap gap-2">
          <button type="button" className={BOUTON} disabled={!selectionComplete} onClick={() => ouvrirForm(null)}>
            <Plus size={15} /> Nouvelle evaluation
          </button>
          {evaluation && (
            <>
              <button type="button" className={BOUTON} onClick={() => ouvrirForm(evaluation)} disabled={lectureSeule}>
                <Pencil size={15} /> Modifier
              </button>
              <button type="button" className={BOUTON} onClick={supprimerEvaluation} disabled={lectureSeule}>
                <Trash2 size={15} /> Supprimer
              </button>
            </>
          )}
        </div>
      </div>

      {evaluation && (
        <div className={CARTE}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-medium text-texte">
                {evaluation.matiere_nom} - {evaluation.libelle} - {evaluation.classe_nom} (T{evaluation.trimestre})
              </p>
              <p className="text-sm text-texte-attenue">Bareme /{Number(evaluation.bareme)} - poids {Number(evaluation.poids)}</p>
            </div>
            <div className="flex gap-2">
              <button className={BOUTON} onClick={() => setImportOuvert(true)} disabled={lectureSeule}><Upload size={15} /> Importer Excel</button>
              <button className={BOUTON} onClick={exporter}><FileSpreadsheet size={15} /> Exporter</button>
            </div>
          </div>

          {verrouille && (
            <div className="mb-3 rounded border border-accent-orange bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {peutCorriger
                ? "Resultats valides : toute correction exige un motif et est tracee dans le journal d'audit."
                : "Resultats valides : seule la direction peut corriger une note."}
              {peutCorriger && (
                <input className={`${CHAMP} mt-2 w-full`} placeholder="Motif de la correction" value={motif} onChange={(e) => setMotif(e.target.value)} />
              )}
            </div>
          )}

          <div className="mb-3 flex flex-wrap gap-4 text-sm">
            <span className="text-accent-vert">Notes saisies : {compteurs.saisies}</span>
            <span className={compteurs.manquantes ? "text-amber-700" : "text-texte-attenue"}>Notes manquantes : {compteurs.manquantes}</span>
            {compteurs.erreurs > 0 && <span className="text-accent-rouge">Invalides : {compteurs.erreurs}</span>}
            <span className="text-xs text-texte-attenue">Entree / fleches haut-bas pour passer a l&apos;eleve suivant ; virgule ou point decimal.</span>
          </div>

          <div className="overflow-x-auto rounded border border-bordure">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-fond-barre text-left text-texte-attenue">
                  <th className="px-3 py-2">N°</th>
                  <th className="px-3 py-2">Matricule</th>
                  <th className="px-3 py-2">Nom complet</th>
                  <th className="px-3 py-2">Note /{Number(evaluation.bareme)}</th>
                  <th className="px-3 py-2">Statut</th>
                </tr>
              </thead>
              <tbody>
                {eleves.map((e, index) => {
                  const ligne = saisie[e.etudiant] ?? { statut: "SAISIE", valeur: "" };
                  const manquante = ligne.statut === "SAISIE" && ligne.valeur.trim() === "";
                  return (
                    <tr key={e.etudiant} className={`border-t border-bordure ${manquante ? "bg-amber-50" : ""}`}>
                      <td className="px-3 py-1.5">{e.numero}</td>
                      <td className="px-3 py-1.5">{e.matricule}</td>
                      <td className="px-3 py-1.5">{e.nom_complet}</td>
                      <td className="px-3 py-1.5">
                        <input
                          ref={(el) => { champs.current[index] = el; }}
                          inputMode="decimal"
                          className={`${CHAMP} w-24 ${invalide(ligne) ? "border-accent-rouge" : ""}`}
                          value={ligne.valeur}
                          disabled={lectureSeule || ligne.statut !== "SAISIE"}
                          onChange={(ev) => changer(e.etudiant, { valeur: ev.target.value })}
                          onKeyDown={(ev) => {
                            if (["Enter", "ArrowDown", "ArrowUp"].includes(ev.key)) {
                              ev.preventDefault();
                              naviguer(index, ev.key);
                            }
                          }}
                        />
                      </td>
                      <td className="px-3 py-1.5">
                        <select className={CHAMP} value={ligne.statut} disabled={lectureSeule}
                                onChange={(ev) => changer(e.etudiant, { statut: ev.target.value as StatutNote })}>
                          {STATUTS.map((s) => <option key={s.valeur} value={s.valeur}>{s.libelle}</option>)}
                        </select>
                        {manquante && <span className="ml-2 text-xs text-amber-700">manquante</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex justify-end">
            <button className={BOUTON_PRIMAIRE} onClick={enregistrer} disabled={enCours || !modifie || lectureSeule}>
              <Save size={15} /> Enregistrer les notes
            </button>
          </div>
        </div>
      )}

      <Modale titre={edition ? "Modifier l'evaluation" : "Nouvelle evaluation"} ouverte={formOuvert} onFermer={() => setFormOuvert(false)}>
        <form onSubmit={soumettreForm} className="grid grid-cols-2 gap-3">
          {!edition && (
            <div className="col-span-2 flex flex-wrap items-center gap-2">
              <span className="text-xs text-texte-attenue">Modeles :</span>
              {MODELES.map((m) => (
                <button key={m.libelle} type="button" className="rounded border border-bordure px-2 py-0.5 text-xs hover:bg-fond"
                        onClick={() => setForm((f) => ({ ...f, libelle: m.libelle, type: m.type, poids: m.poids }))}>
                  {m.libelle} (x{m.poids})
                </button>
              ))}
            </div>
          )}
          <div className="col-span-2">
            <label className={ETIQUETTE}>Libelle *</label>
            <input className={`${CHAMP} w-full`} required value={form.libelle} onChange={(e) => setForm({ ...form, libelle: e.target.value })} />
          </div>
          <div>
            <label className={ETIQUETTE}>Type</label>
            <select className={`${CHAMP} w-full`} value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as TypeEvaluation })}>
              <option value="DEVOIR">Devoir</option>
              <option value="INTERROGATION">Interrogation</option>
              <option value="EXAMEN">Examen / composition</option>
              <option value="AUTRE">Autre</option>
            </select>
          </div>
          <div>
            <label className={ETIQUETTE}>Date</label>
            <input type="date" className={`${CHAMP} w-full`} value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          </div>
          <div>
            <label className={ETIQUETTE}>Bareme *</label>
            <input className={`${CHAMP} w-full`} required inputMode="decimal" value={form.bareme} onChange={(e) => setForm({ ...form, bareme: e.target.value })} />
          </div>
          <div>
            <label className={ETIQUETTE}>Poids dans la moyenne *</label>
            <input className={`${CHAMP} w-full`} required inputMode="decimal" value={form.poids} onChange={(e) => setForm({ ...form, poids: e.target.value })} />
          </div>
          <div className="col-span-2 mt-2 flex justify-end gap-2">
            <button type="button" className={BOUTON} onClick={() => setFormOuvert(false)}>Annuler</button>
            <button type="submit" className={BOUTON_PRIMAIRE}>Enregistrer</button>
          </div>
        </form>
      </Modale>

      {evaluation && (
        <ImportExcel<LigneNote>
          titre="Importer les notes depuis Excel"
          ouverte={importOuvert}
          onFermer={() => setImportOuvert(false)}
          consignes={
            <ol className="list-decimal space-y-1 pl-5">
              <li>Telechargez le modele (eleves de la classe, notes deja saisies incluses).</li>
              <li>Saisissez la note (virgule ou point), ou <b>A</b> (absent), <b>AJ</b> (absent justifie), <b>NA</b> (non applicable). Case vide = pas de note.</li>
              <li>Importez, controlez l&apos;apercu, puis confirmez : rien n&apos;est enregistre avant.</li>
            </ol>
          }
          urlModele={`/evaluations/evaluations/${evaluation.id}/modele-import/`}
          nomModele="modele_notes.xlsx"
          urlImport={`/evaluations/evaluations/${evaluation.id}/importer/`}
          titreValeur="Note"
          motifRequis={verrouille}
          rendreValeur={(l) => (
            <>
              {l.ancienne && <span className="mr-1 text-texte-attenue line-through">{l.ancienne}</span>}
              {l.valeur ?? l.statut ?? ""}
            </>
          )}
          onImporte={() => { chargerGrille(); chargerEvaluations(); }}
        />
      )}
    </div>
  );
}
