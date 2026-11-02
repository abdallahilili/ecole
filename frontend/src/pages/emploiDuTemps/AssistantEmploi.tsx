import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Trash2, WandSparkles } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { useNotifications } from "../../composants/Notifications";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import { NOM_JOUR } from "../../services/jours";
import type { AnneeScolaire, Classe, CreneauDisponible, DonneesAssistant, EmploiDuTemps } from "../../types";

import { tr } from "../../i18n";

/** Ordre des jours dans l'ecole : la semaine commence le samedi. */
const ORDRE_JOURS = [5, 6, 0, 1, 2, 3, 4];

interface LigneMatiere { matiere: string; heures: number }          // matiere "" : pas encore choisie
interface BlocProfesseur { cle: number; professeur: string; matieres: LigneMatiere[]; disponibilites: CreneauDisponible[] }
interface Echec { message: string; diagnostics: string[]; conflits: string[] }

/** « 2 h + 2 h + 1 h » : des seances de 2 h, plus une seance d'1 h si le volume est impair. */
function seancesTexte(heures: number): string {
  if (!(heures >= 1)) return "-";
  const seances = Array.from({ length: Math.floor(heures / 2) }, () => 2);
  if (heures % 2) seances.push(1);
  return seances.map((h) => tr("{0} h", h)).join(" + ");
}

export function PageAssistantEmploi() {
  const navigate = useNavigate();
  const { notifierSucces } = useNotifications();
  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [annee, setAnnee] = useState("");
  const classes = useOptions<Classe>(`/referentiels/classes/?annee_scolaire=${annee}`, !!annee);
  const [classe, setClasse] = useState("");
  const [donnees, setDonnees] = useState<DonneesAssistant | null>(null);
  const [nom, setNom] = useState("");
  const [blocs, setBlocs] = useState<BlocProfesseur[]>([]);
  const [enCours, setEnCours] = useState(false);
  const [echec, setEchec] = useState<Echec | null>(null);
  const compteur = useRef(0);
  const nouvelleCle = () => ++compteur.current;

  useEffect(() => {
    if (!annee && annees.length > 0) setAnnee(String((annees.find((a) => a.active) ?? annees[0]).id));
  }, [annees, annee]);

  useEffect(() => {
    setEchec(null);
    if (!classe) { setDonnees(null); setBlocs([]); return; }
    api.get("/emplois-du-temps/emplois/assistant/", { params: { classe } })
      .then(({ data }: { data: DonneesAssistant }) => {
        const disponibilites = new Map(data.professeurs.map((p) => [p.id, p.disponibilites]));
        setDonnees(data);
        setNom(data.nom_propose);
        // Professeurs deja affectes a la classe : la saisie est pre-remplie, avec leurs disponibilites connues.
        setBlocs(data.initial.map((ini) => ({
          cle: nouvelleCle(), professeur: String(ini.professeur),
          matieres: ini.matieres.map((m) => ({ matiere: String(m.matiere), heures: m.heures })),
          disponibilites: (disponibilites.get(ini.professeur) ?? []).map((d) => ({ ...d })),
        })));
      })
      .catch((err) => setEchec({ message: messageErreur(err), diagnostics: [], conflits: [] }));
  }, [classe]);

  const majBloc = (cle: number, partiel: Partial<BlocProfesseur>) =>
    setBlocs((anciens) => anciens.map((b) => (b.cle === cle ? { ...b, ...partiel } : b)));
  const choisirProfesseur = (cle: number, identifiant: string) => {
    const connu = donnees?.professeurs.find((p) => String(p.id) === identifiant);
    majBloc(cle, { professeur: identifiant, disponibilites: (connu?.disponibilites ?? []).map((d) => ({ ...d })) });
  };

  const professeursPris = new Set(blocs.map((b) => b.professeur).filter(Boolean));
  const matieresPrises = new Set(blocs.flatMap((b) => b.matieres.map((m) => m.matiere)).filter(Boolean));
  const sansProfesseur = (donnees?.matieres ?? []).filter((m) => !matieresPrises.has(String(m.id)));
  const jours = (donnees?.cadre.jours ?? []);
  const totalHeures = blocs.filter((b) => b.professeur).flatMap((b) => b.matieres)
    .reduce((somme, m) => somme + (m.matiere && m.heures >= 1 ? m.heures : 0), 0);
  const pret = blocs.some((b) => b.professeur && b.matieres.some((m) => m.matiere && m.heures >= 1));

  async function creer() {
    setEnCours(true);
    setEchec(null);
    try {
      const { data } = await api.post<EmploiDuTemps>("/emplois-du-temps/emplois/creer-classe/", {
        classe: Number(classe), nom,
        professeurs: blocs.filter((b) => b.professeur).map((b) => ({
          professeur: Number(b.professeur),
          matieres: b.matieres.filter((m) => m.matiere).map((m) => ({ matiere: Number(m.matiere), heures: m.heures })),
          disponibilites: b.disponibilites.filter((d) => d.debut && d.fin),
        })),
      });
      notifierSucces(tr("Emploi du temps cree : {0} seance(s).", data.nb_seances));
      navigate(`/emplois-du-temps/${data.id}`);
    } catch (err: any) {
      const reponse = err?.response?.data ?? {};
      setEchec({ message: messageErreur(err), diagnostics: reponse.diagnostics ?? [], conflits: reponse.conflits ?? [] });
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-texte">{tr("Nouvel emploi du temps")}</h1>
        <Link to="/emplois-du-temps" className="text-sm text-entete hover:underline">{tr("← Retour aux emplois du temps")}</Link>
      </div>

      <div className={`${CARTE} grid grid-cols-1 gap-3 md:grid-cols-3`}>
        <div>
          <label className={ETIQUETTE}>{tr("Annee scolaire")}</label>
          <select className={`${CHAMP} w-full`} value={annee} onChange={(e) => { setAnnee(e.target.value); setClasse(""); }}>
            {annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Classe")} <span className="text-accent-rouge">*</span></label>
          <select className={`${CHAMP} w-full`} value={classe} onChange={(e) => setClasse(e.target.value)}>
            <option value="">--</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Nom de l'emploi du temps")}</label>
          <input className={`${CHAMP} w-full`} value={nom} disabled={!donnees} maxLength={120} onChange={(e) => setNom(e.target.value)} />
        </div>
      </div>

      {!donnees && !echec && <p className="text-sm text-texte-attenue">{tr("Choisissez la classe, puis ses professeurs.")}</p>}

      {donnees && (
        <>
          <p className="text-xs text-texte-attenue">
            {tr("Horaires de l'ecole : {0}, de {1} a {2}.", ORDRE_JOURS.filter((j) => jours.includes(j)).map((j) => NOM_JOUR[j]).join(", "), donnees.cadre.debut, donnees.cadre.fin)}
            {donnees.cadre.pauses.length > 0 && ` ${tr("Pause : {0}.", donnees.cadre.pauses.map((p) => `${p.debut}-${p.fin}`).join(", "))}`}
            {" "}{tr("Les seances durent 2 h ; une seance d'1 h seulement quand le nombre d'heures est impair.")}
          </p>

          {blocs.map((bloc) => {
            const lesJours = ORDRE_JOURS.filter((j) => jours.includes(j) || bloc.disponibilites.some((d) => d.jour === j));
            return (
              <div key={bloc.cle} className={CARTE}>
                <div className="mb-3 flex items-end gap-2">
                  <div className="flex-1">
                    <label className={ETIQUETTE}>{tr("Professeur")}</label>
                    <select className={`${CHAMP} w-full max-w-md`} value={bloc.professeur} onChange={(e) => choisirProfesseur(bloc.cle, e.target.value)}>
                      <option value="">{tr("-- Choisir un professeur --")}</option>
                      {donnees.professeurs.filter((p) => String(p.id) === bloc.professeur || !professeursPris.has(String(p.id))).map((p) => (
                        <option key={p.id} value={p.id}>{p.nom}{p.specialite ? ` (${p.specialite})` : ""}</option>
                      ))}
                    </select>
                  </div>
                  <button type="button" className="mb-1 text-texte-attenue hover:text-accent-rouge" title={tr("Retirer ce professeur")}
                          onClick={() => setBlocs((anciens) => anciens.filter((b) => b.cle !== bloc.cle))}>
                    <Trash2 size={18} />
                  </button>
                </div>

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <div>
                    <p className="mb-1 text-sm font-medium text-texte">{tr("Matieres enseignees (heures par semaine)")}</p>
                    {bloc.matieres.map((ligne, i) => (
                      <div key={i} className="mb-2 flex flex-wrap items-center gap-2">
                        <select className={`${CHAMP} min-w-44 flex-1`} value={ligne.matiere}
                                onChange={(e) => majBloc(bloc.cle, { matieres: bloc.matieres.map((m, k) => (k === i ? { ...m, matiere: e.target.value } : m)) })}>
                          <option value="">{tr("-- Matiere --")}</option>
                          {donnees.matieres.filter((m) => String(m.id) === ligne.matiere || !matieresPrises.has(String(m.id))).map((m) => (
                            <option key={m.id} value={m.id}>{m.nom}</option>
                          ))}
                        </select>
                        <input type="number" min={1} max={40} step={1} className={`${CHAMP} w-20`} value={ligne.heures} title={tr("Heures par semaine")}
                               onChange={(e) => majBloc(bloc.cle, { matieres: bloc.matieres.map((m, k) => (k === i ? { ...m, heures: Math.floor(Number(e.target.value)) } : m)) })} />
                        <span className="w-28 text-xs text-texte-attenue">{seancesTexte(ligne.heures)}</span>
                        <button type="button" className="text-texte-attenue hover:text-accent-rouge" title={tr("Retirer")}
                                onClick={() => majBloc(bloc.cle, { matieres: bloc.matieres.filter((_, k) => k !== i) })}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ))}
                    <button type="button" className={BOUTON} disabled={sansProfesseur.length === 0 && bloc.matieres.every((m) => m.matiere)}
                            onClick={() => majBloc(bloc.cle, { matieres: [...bloc.matieres, { matiere: "", heures: 2 }] })}>
                      <Plus size={15} /> {tr("Ajouter une matiere")}
                    </button>
                  </div>

                  <div>
                    <p className="mb-1 text-sm font-medium text-texte">{tr("Disponibilites du professeur")}</p>
                    {bloc.disponibilites.length === 0 && (
                      <p className="mb-2 text-xs text-texte-attenue">{tr("Aucun creneau : disponible pendant tous les horaires de l'ecole.")}</p>
                    )}
                    {bloc.disponibilites.map((d, i) => {
                      const modifier = (partiel: Partial<CreneauDisponible>) =>
                        majBloc(bloc.cle, { disponibilites: bloc.disponibilites.map((x, k) => (k === i ? { ...x, ...partiel } : x)) });
                      return (
                        <div key={i} className="mb-2 flex flex-wrap items-center gap-2">
                          <select className={CHAMP} value={d.jour} onChange={(e) => modifier({ jour: Number(e.target.value) })}>
                            {lesJours.map((j) => <option key={j} value={j}>{NOM_JOUR[j]}</option>)}
                          </select>
                          <input type="time" className={CHAMP} value={d.debut} onChange={(e) => modifier({ debut: e.target.value })} />
                          <span className="text-sm text-texte-attenue">{tr("a")}</span>
                          <input type="time" className={CHAMP} value={d.fin} onChange={(e) => modifier({ fin: e.target.value })} />
                          <button type="button" className="text-texte-attenue hover:text-accent-rouge" title={tr("Retirer")}
                                  onClick={() => majBloc(bloc.cle, { disponibilites: bloc.disponibilites.filter((_, k) => k !== i) })}>
                            <Trash2 size={16} />
                          </button>
                        </div>
                      );
                    })}
                    <button type="button" className={BOUTON}
                            onClick={() => majBloc(bloc.cle, { disponibilites: [...bloc.disponibilites, { jour: lesJours[0] ?? 0, debut: donnees.cadre.debut, fin: donnees.cadre.fin }] })}>
                      <Plus size={15} /> {tr("Ajouter un creneau")}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <button type="button" className={BOUTON} onClick={() => setBlocs((anciens) => [...anciens, {
              cle: nouvelleCle(), professeur: "", matieres: [{ matiere: "", heures: 2 }], disponibilites: [],
            }])}>
              <Plus size={15} /> {tr("Ajouter un professeur")}
            </button>
            <p className="text-sm text-texte-attenue">{tr("{0} h par semaine pour cette classe", totalHeures)}</p>
          </div>

          {blocs.length > 0 && sansProfesseur.length > 0 && (
            <p className="rounded border border-accent-orange bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {tr("Matieres sans professeur (non programmees) : {0}", sansProfesseur.map((m) => m.nom).join(", "))}
            </p>
          )}
        </>
      )}

      {echec && (
        <div className="rounded border border-accent-rouge bg-red-50 px-3 py-2 text-sm text-accent-rouge">
          {echec.conflits.length + echec.diagnostics.length === 0 ? <p>{echec.message}</p> : (
            <>
              <p className="font-medium">{tr("Impossible de programmer cette classe sans conflit.")}</p>
              <ul className="mt-1 list-disc ps-5">
                {[...echec.diagnostics, ...echec.conflits].map((m) => <li key={m}>{m}</li>)}
              </ul>
              <p className="mt-1 text-xs">{tr("Rien n'a ete cree ni enregistre. Modifiez les disponibilites, les heures ou le professeur, puis relancez.")}</p>
            </>
          )}
        </div>
      )}

      {donnees && (
        <div className="flex justify-end gap-2">
          <button type="button" className={BOUTON} onClick={() => navigate("/emplois-du-temps")}>{tr("Annuler")}</button>
          <button type="button" className={BOUTON_PRIMAIRE} disabled={!pret || enCours} onClick={creer}>
            <WandSparkles size={15} /> {enCours ? tr("Generation en cours...") : tr("Creer l'emploi du temps")}
          </button>
        </div>
      )}
    </div>
  );
}
