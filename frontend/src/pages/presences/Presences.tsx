import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  CheckCircle2, FileSpreadsheet, FileText, History, ListChecks, Printer, Save, Unlock, Upload,
} from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { useConfirmation } from "../../composants/Confirmation";
import { Modale } from "../../composants/Modale";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import {
  aujourdhui, formaterDate, imprimerPdf, messageErreurFichier, telechargerFichier,
} from "../../services/fichiers";
import type {
  AnneeScolaire, Classe, EleveListe, Matiere, Professeur, Seance, StatutPresence,
} from "../../types";
import { ImportPresences } from "./ImportPresences";

interface Saisie { statut: StatutPresence | null; observation: string }

const STATUTS: { valeur: StatutPresence; libelle: string; actif: string }[] = [
  { valeur: "PRESENT", libelle: "Present", actif: "bg-accent-vert text-white border-accent-vert" },
  { valeur: "ABSENT", libelle: "Absent", actif: "bg-accent-rouge text-white border-accent-rouge" },
  { valeur: "RETARD", libelle: "Retard", actif: "bg-accent-orange text-white border-accent-orange" },
];

export function PagePresences() {
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();
  const [parametresUrl] = useSearchParams();

  const peutRouvrir = utilisateur?.role === "ADMINISTRATEUR" || utilisateur?.role === "DIRECTEUR";
  const peutChoisirProfesseur = ["ADMINISTRATEUR", "DIRECTEUR", "RESPONSABLE_PEDAGOGIQUE"].includes(utilisateur?.role ?? "");

  // --- selection du cours
  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [annee, setAnnee] = useState("");
  const classes = useOptions<Classe>(`/referentiels/classes/?annee_scolaire=${annee}`, !!annee);
  const matieres = useOptions<Matiere>("/referentiels/matieres/");
  const professeurs = useOptions<Professeur>("/professeurs/professeurs/", peutChoisirProfesseur);
  const [classe, setClasse] = useState("");
  const [matiere, setMatiere] = useState("");
  const [professeur, setProfesseur] = useState("");
  const [date, setDate] = useState(aujourdhui());
  const [heureDebut, setHeureDebut] = useState("");
  const [heureFin, setHeureFin] = useState("");

  // --- liste d'appel
  const [seance, setSeance] = useState<Seance | null>(null);
  const [eleves, setEleves] = useState<EleveListe[]>([]);
  const [saisie, setSaisie] = useState<Record<number, Saisie>>({});
  const [modifie, setModifie] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [importOuvert, setImportOuvert] = useState(false);
  const [motifOuvert, setMotifOuvert] = useState(false);
  const [motif, setMotif] = useState("");

  useEffect(() => {
    if (!annee && annees.length > 0) setAnnee(String((annees.find((a) => a.active) ?? annees[0]).id));
  }, [annees, annee]);

  function charger(donnees: { seance: Seance; eleves: EleveListe[] }) {
    setSeance(donnees.seance);
    setEleves(donnees.eleves);
    setSaisie(Object.fromEntries(donnees.eleves.map((e) => [e.etudiant, { statut: e.statut, observation: e.observation }])));
    setModifie(false);
  }

  // Ouverture directe depuis l'historique : /presences?seance=12
  const idSeanceUrl = parametresUrl.get("seance");
  useEffect(() => {
    if (!idSeanceUrl) return;
    api.get(`/presences/seances/${idSeanceUrl}/liste/`).then(({ data }) => {
      const s: Seance = data.seance;
      setAnnee(String(s.annee_scolaire));
      setClasse(String(s.classe));
      setMatiere(String(s.matiere));
      setProfesseur(s.professeur ? String(s.professeur) : "");
      setDate(s.date);
      setHeureDebut(s.heure_debut.slice(0, 5));
      setHeureFin(s.heure_fin.slice(0, 5));
      charger(data);
    }).catch((err) => notifierErreur(messageErreur(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSeanceUrl]);

  const cours: Record<string, string> = {
    annee_scolaire: annee, classe, matiere, date, heure_debut: heureDebut, heure_fin: heureFin,
    ...(professeur ? { professeur } : {}),
  };

  async function ouvrir(e: FormEvent) {
    e.preventDefault();
    setEnCours(true);
    try {
      const { data } = await api.post("/presences/seances/ouvrir/", cours);
      charger(data);
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  const verrouille = !!seance?.presences_validees;

  function marquer(etudiant: number, statut: StatutPresence | null) {
    if (verrouille) return;
    setSaisie((s) => ({ ...s, [etudiant]: { observation: s[etudiant]?.observation ?? "", statut } }));
    setModifie(true);
  }

  function observer(etudiant: number, observation: string) {
    if (verrouille) return;
    setSaisie((s) => ({ ...s, [etudiant]: { statut: s[etudiant]?.statut ?? null, observation } }));
    setModifie(true);
  }

  function toutPresent() {
    if (verrouille) return;
    setSaisie((s) => Object.fromEntries(eleves.map((e): [number, Saisie] => [
      e.etudiant, { observation: s[e.etudiant]?.observation ?? "", statut: s[e.etudiant]?.statut ?? "PRESENT" },
    ])));
    setModifie(true);
  }

  const compteurs = useMemo(() => {
    const valeurs = eleves.map((e) => saisie[e.etudiant]?.statut ?? null);
    return {
      presents: valeurs.filter((v) => v === "PRESENT").length,
      absents: valeurs.filter((v) => v === "ABSENT").length,
      retards: valeurs.filter((v) => v === "RETARD").length,
      manquants: valeurs.filter((v) => v === null).length,
    };
  }, [eleves, saisie]);

  async function enregistrer(silencieux = false) {
    if (!seance) return false;
    setEnCours(true);
    try {
      const presences = eleves.map((e) => ({
        etudiant: e.etudiant, statut: saisie[e.etudiant]?.statut ?? "", observation: saisie[e.etudiant]?.observation ?? "",
      }));
      const { data } = await api.post(`/presences/seances/${seance.id}/enregistrer/`, { presences });
      charger(data);
      if (!silencieux) notifierSucces("Presences enregistrees (brouillon, a valider).");
      return true;
    } catch (err) {
      notifierErreur(messageErreur(err));
      return false;
    } finally {
      setEnCours(false);
    }
  }

  async function valider() {
    if (!seance) return;
    if (compteurs.manquants > 0) {
      notifierErreur(`${compteurs.manquants} eleve(s) n'ont pas de statut : marquez-les avant de valider.`);
      return;
    }
    const confirme = await demanderConfirmation({
      titre: "Valider les presences",
      message: `${compteurs.absents} absent(s), ${compteurs.retards} retard(s). Apres validation la liste est verrouillee et les parents des absents sont notifies (si WhatsApp est active).`,
    });
    if (!confirme) return;
    if (modifie && !(await enregistrer(true))) return;
    setEnCours(true);
    try {
      const { data } = await api.post(`/presences/seances/${seance.id}/valider/`);
      charger(data);
      const n = data.notifications;
      let message = "Presences validees.";
      if (n.actif) message += ` ${n.creees} notification(s) WhatsApp mise(s) en file.`;
      if (n.sans_telephone?.length) message += ` Sans numero valide : ${n.sans_telephone.join(", ")}.`;
      notifierSucces(message);
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  async function rouvrir() {
    if (!seance) return;
    try {
      const { data } = await api.post(`/presences/seances/${seance.id}/rouvrir/`, { motif });
      charger(data);
      setMotifOuvert(false);
      setMotif("");
      notifierSucces("Seance rouverte.");
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function sortie(action: "imprimer" | "pdf" | "excel" | "vierge") {
    try {
      if (action === "vierge") {
        await telechargerFichier("/presences/seances/modele-vierge/pdf/", "liste_presence_vierge.pdf");
        return;
      }
      if (!seance) return;
      if (modifie && !verrouille && !(await enregistrer(true))) return;
      const base = `/presences/seances/${seance.id}`;
      const nom = `presence_${seance.classe_nom}_${seance.date}`;
      if (action === "imprimer") await imprimerPdf(`${base}/pdf/`);
      if (action === "pdf") await telechargerFichier(`${base}/pdf/`, `${nom}.pdf`);
      if (action === "excel") await telechargerFichier(`${base}/excel/`, `${nom}.xlsx`);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  const coursComplet = annee && classe && matiere && date && heureDebut && heureFin;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-texte">Presences des etudiants</h1>
        <div className="flex gap-2">
          <button onClick={() => sortie("vierge")} className={BOUTON}>
            <FileText size={15} /> Modele vierge
          </button>
          <Link to="/presences/historique" className={BOUTON}>
            <History size={15} /> Historique
          </Link>
        </div>
      </div>

      <form onSubmit={ouvrir} className={`${CARTE} mb-4 grid grid-cols-2 gap-3 md:grid-cols-4`}>
        <div>
          <label className={ETIQUETTE}>Annee scolaire *</label>
          <select className={`${CHAMP} w-full`} value={annee} required
                  onChange={(e) => { setAnnee(e.target.value); setClasse(""); }}>
            <option value="">--</option>
            {annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>Classe *</label>
          <select className={`${CHAMP} w-full`} value={classe} required onChange={(e) => setClasse(e.target.value)}>
            <option value="">--</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>Matiere *</label>
          <select className={`${CHAMP} w-full`} value={matiere} required onChange={(e) => setMatiere(e.target.value)}>
            <option value="">--</option>
            {matieres.map((m) => <option key={m.id} value={m.id}>{m.nom}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>Date *</label>
          <input type="date" className={`${CHAMP} w-full`} value={date} required onChange={(e) => setDate(e.target.value)} />
        </div>
        <div>
          <label className={ETIQUETTE}>Heure de debut *</label>
          <input type="time" className={`${CHAMP} w-full`} value={heureDebut} required onChange={(e) => setHeureDebut(e.target.value)} />
        </div>
        <div>
          <label className={ETIQUETTE}>Heure de fin *</label>
          <input type="time" className={`${CHAMP} w-full`} value={heureFin} required onChange={(e) => setHeureFin(e.target.value)} />
        </div>
        {peutChoisirProfesseur && (
          <div>
            <label className={ETIQUETTE}>Professeur</label>
            <select className={`${CHAMP} w-full`} value={professeur} onChange={(e) => setProfesseur(e.target.value)}>
              <option value="">-- Non precise --</option>
              {professeurs.map((p) => <option key={p.id} value={p.id}>{p.nom_complet}</option>)}
            </select>
          </div>
        )}
        <div className="flex items-end gap-2">
          <button type="submit" disabled={enCours || !coursComplet} className={BOUTON_PRIMAIRE}>
            <ListChecks size={15} /> Afficher la liste
          </button>
          <button type="button" disabled={!coursComplet} onClick={() => setImportOuvert(true)} className={BOUTON}>
            <Upload size={15} /> Importer Excel
          </button>
        </div>
      </form>

      {seance && (
        <div className={CARTE}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-medium text-texte">
                {seance.classe_nom} - {seance.matiere_nom} - {formaterDate(seance.date)} ({seance.heure_debut.slice(0, 5)} - {seance.heure_fin.slice(0, 5)})
              </p>
              <p className="text-sm text-texte-attenue">
                {seance.professeur_nom ? `Professeur : ${seance.professeur_nom} - ` : ""}{eleves.length} eleve(s)
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => sortie("imprimer")} className={BOUTON}><Printer size={15} /> Imprimer</button>
              <button onClick={() => sortie("pdf")} className={BOUTON}><FileText size={15} /> PDF</button>
              <button onClick={() => sortie("excel")} className={BOUTON}><FileSpreadsheet size={15} /> Excel</button>
            </div>
          </div>

          {verrouille && (
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded border border-accent-vert bg-green-50 px-3 py-2 text-sm text-accent-vert">
              <span className="flex items-center gap-1.5"><CheckCircle2 size={16} /> Presences validees : la liste est verrouillee.</span>
              {peutRouvrir && (
                <button onClick={() => setMotifOuvert(true)} className="flex items-center gap-1 underline">
                  <Unlock size={14} /> Rouvrir
                </button>
              )}
            </div>
          )}

          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
            <div className="flex flex-wrap gap-4">
              <span className="text-accent-vert">Presents : {compteurs.presents}</span>
              <span className="text-accent-rouge">Absents : {compteurs.absents}</span>
              <span className="text-accent-orange">Retards : {compteurs.retards}</span>
              <span className={compteurs.manquants ? "text-texte" : "text-texte-attenue"}>Non renseignes : {compteurs.manquants}</span>
            </div>
            {!verrouille && (
              <button onClick={toutPresent} className={BOUTON}>Marquer les non renseignes presents</button>
            )}
          </div>

          <div className="overflow-x-auto rounded border border-bordure">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-fond-barre text-left text-texte-attenue">
                  <th className="px-3 py-2">N°</th>
                  <th className="px-3 py-2">Matricule</th>
                  <th className="px-3 py-2">Nom complet</th>
                  <th className="px-3 py-2">Statut</th>
                  <th className="px-3 py-2">Observation</th>
                </tr>
              </thead>
              <tbody>
                {eleves.length === 0 && (
                  <tr><td colSpan={5} className="px-3 py-6 text-center text-texte-attenue">Aucun eleve actif dans cette classe.</td></tr>
                )}
                {eleves.map((e) => {
                  const ligne = saisie[e.etudiant];
                  return (
                    <tr key={e.etudiant} className="border-t border-bordure hover:bg-fond">
                      <td className="px-3 py-1.5">{e.numero}</td>
                      <td className="px-3 py-1.5">{e.matricule}</td>
                      <td className="px-3 py-1.5">{e.nom_complet}</td>
                      <td className="px-3 py-1.5">
                        <div className="flex gap-1">
                          {STATUTS.map((s) => (
                            <button
                              key={s.valeur}
                              type="button"
                              disabled={verrouille}
                              onClick={() => marquer(e.etudiant, ligne?.statut === s.valeur ? null : s.valeur)}
                              className={`rounded border px-2 py-0.5 text-xs ${
                                ligne?.statut === s.valeur ? s.actif : "border-bordure bg-white text-texte hover:bg-fond"
                              } disabled:opacity-60`}
                            >
                              {s.libelle}
                            </button>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-1.5">
                        <input
                          className={`${CHAMP} w-full`}
                          value={ligne?.observation ?? ""}
                          disabled={verrouille}
                          onChange={(ev) => observer(e.etudiant, ev.target.value)}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {!verrouille && (
            <div className="mt-3 flex justify-end gap-2">
              <button onClick={() => enregistrer()} disabled={enCours || !modifie} className={BOUTON}>
                <Save size={15} /> Enregistrer le brouillon
              </button>
              <button onClick={valider} disabled={enCours || eleves.length === 0} className={BOUTON_PRIMAIRE}>
                <CheckCircle2 size={15} /> Valider les presences
              </button>
            </div>
          )}
        </div>
      )}

      <ImportPresences
        cours={cours}
        ouverte={importOuvert}
        onFermer={() => setImportOuvert(false)}
        onImporte={(id) => api.get(`/presences/seances/${id}/liste/`).then(({ data }) => charger(data))}
      />

      <Modale titre="Rouvrir la seance" ouverte={motifOuvert} onFermer={() => setMotifOuvert(false)}>
        <p className="mb-2 text-sm text-texte-attenue">
          Les presences redeviennent modifiables. Le motif est conserve dans le journal d&apos;audit.
        </p>
        <textarea className={`${CHAMP} w-full`} rows={3} value={motif} onChange={(e) => setMotif(e.target.value)} placeholder="Motif (obligatoire)" />
        <div className="mt-3 flex justify-end gap-2">
          <button onClick={() => setMotifOuvert(false)} className={BOUTON}>Annuler</button>
          <button onClick={rouvrir} disabled={!motif.trim()} className={BOUTON_PRIMAIRE}>Rouvrir</button>
        </div>
      </Modale>
    </div>
  );
}
