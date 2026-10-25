import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarPlus, Copy, Eye, FileText, Send, Sparkles, Trash2, Wand2 } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useListe, useOptions } from "../../hooks/useListe";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { useConfirmation } from "../../composants/Confirmation";
import { Modale } from "../../composants/Modale";
import { TableauDonnees } from "../../composants/TableauDonnees";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import { aujourdhui, formaterDate, messageErreurFichier, telechargerFichier } from "../../services/fichiers";
import type { AnneeScolaire, EmploiDuTemps, VersionEmploi } from "../../types";
import { RapportGenerationPanneau } from "./RapportGeneration";

import { tr, tx } from "../../i18n";
const STATUT_COULEUR: Record<string, string> = {
  BROUILLON: "bg-gray-100 text-gray-700", PUBLIE: "bg-green-50 text-accent-vert", ARCHIVE: "bg-amber-50 text-amber-700",
};
const STATUT_LIBELLE: Record<string, string> = { BROUILLON: tr("Brouillon"), PUBLIE: tr("Publie"), ARCHIVE: tr("Archive") };

export function PageEmploisDuTemps() {
  const navigate = useNavigate();
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();
  const peutGerer = ["ADMINISTRATEUR", "DIRECTEUR", "RESPONSABLE_PEDAGOGIQUE"].includes(utilisateur?.role ?? "");

  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [annee, setAnnee] = useState("");
  const { resultats, chargement, page, setPage, nombrePages, recharger } =
    useListe<EmploiDuTemps>("/emplois-du-temps/emplois/", annee ? { annee_scolaire: annee } : {});
  const [versions, setVersions] = useState<VersionEmploi[]>([]);

  const [nouveau, setNouveau] = useState(false);
  const [nom, setNom] = useState("");
  const [generation, setGeneration] = useState(false);
  const [params, setParams] = useState({ nom: "", temps_max: "20", graine: "" });
  const [enCours, setEnCours] = useState(false);
  const [rapport, setRapport] = useState<{ emploi: EmploiDuTemps } | null>(null);
  const [seancesPour, setSeancesPour] = useState<EmploiDuTemps | null>(null);
  const [dates, setDates] = useState({ du: aujourdhui(), au: aujourdhui() });

  useEffect(() => {
    if (!annee && annees.length > 0) setAnnee(String((annees.find((a) => a.active) ?? annees[0]).id));
  }, [annees, annee]);

  useEffect(() => {
    if (!annee) return;
    api.get("/emplois-du-temps/emplois/versions/", { params: { annee_scolaire: annee } })
      .then(({ data }) => setVersions(data)).catch(() => setVersions([]));
  }, [annee, resultats]);

  async function creer(e: FormEvent) {
    e.preventDefault();
    try {
      const { data } = await api.post("/emplois-du-temps/emplois/", { annee_scolaire: annee, nom });
      setNouveau(false);
      setNom("");
      navigate(`/emplois-du-temps/${data.id}`);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function generer(e: FormEvent) {
    e.preventDefault();
    setEnCours(true);
    try {
      const { data } = await api.post("/emplois-du-temps/emplois/generer/", {
        annee_scolaire: annee, nom: params.nom || undefined, temps_max: Number(params.temps_max) || 20,
        graine: params.graine === "" ? undefined : Number(params.graine),
      });
      setGeneration(false);
      setRapport({ emploi: data });
      recharger();
    } catch (err: any) {
      const diagnostics: string[] = err?.response?.data?.diagnostics ?? [];
      notifierErreur(messageErreur(err) + (diagnostics.length ? ` ${diagnostics.join(" ")}` : ""));
    } finally {
      setEnCours(false);
    }
  }

  /** `action` retourne le message de succes, ou null si l'utilisateur a annule. */
  async function executer(action: () => Promise<string | null>) {
    try {
      const message = await action();
      if (message) {
        notifierSucces(message);
        recharger();
      }
    } catch (err: any) {
      notifierErreur(messageErreur(err));
    }
  }

  const publier = (e: EmploiDuTemps) => executer(async () => {
    const ok = await demanderConfirmation({
      titre: tr("Publier l'emploi du temps"),
      message: tr("« {0} » deviendra l'emploi du temps officiel de {1} (l'actuel est archive) et ne sera plus modifiable.", e.nom, e.annee_scolaire_libelle),
    });
    if (!ok) return null;
    const { data } = await api.post(`/emplois-du-temps/emplois/${e.id}/publier/`, {});
    return data.detail;
  });

  const dupliquer = (e: EmploiDuTemps) => executer(async () => {
    await api.post(`/emplois-du-temps/emplois/${e.id}/dupliquer/`, {});
    return tr("Brouillon cree a partir de l'emploi du temps.");
  });

  const supprimer = (e: EmploiDuTemps) => executer(async () => {
    const ok = await demanderConfirmation({ titre: tr("Supprimer le brouillon"), message: tr("Supprimer « {0} » ?", e.nom) });
    if (!ok) return null;
    await api.delete(`/emplois-du-temps/emplois/${e.id}/`);
    return tr("Brouillon supprime.");
  });

  async function genererSeances(e: FormEvent) {
    e.preventDefault();
    if (!seancesPour) return;
    try {
      const { data } = await api.post(`/emplois-du-temps/emplois/${seancesPour.id}/generer-seances/`, dates);
      notifierSucces(tr("{0} seance(s) de presence creee(s), {1} deja existante(s).", data.creees, data.ignorees));
      setSeancesPour(null);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function pdf(e: EmploiDuTemps) {
    try {
      await telechargerFichier(`/emplois-du-temps/emplois/${e.id}/pdf/`, `emploi_du_temps_${e.id}.pdf`, { toutes: "classe" });
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-texte">{tr("Emplois du temps")}</h1>
        <div className="flex flex-wrap items-center gap-2">
          <select className={CHAMP} value={annee} onChange={(e) => setAnnee(e.target.value)}>
            {annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
          </select>
          {peutGerer && (
            <>
              <button className={BOUTON} onClick={() => setNouveau(true)}><CalendarPlus size={15} /> {tr("Nouvel emploi vide")}</button>
              <button className={BOUTON_PRIMAIRE} onClick={() => setGeneration(true)}><Wand2 size={15} /> {tr("Generer automatiquement")}</button>
            </>
          )}
        </div>
      </div>

      <TableauDonnees<EmploiDuTemps>
        colonnes={[
          { cle: "nom", titre: tr("Nom") },
          {
            cle: "statut", titre: tr("Statut"),
            rendu: (e) => <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUT_COULEUR[e.statut]}`}>{STATUT_LIBELLE[e.statut]}</span>,
          },
          { cle: "origine", titre: tr("Origine"), rendu: (e) => (e.origine === "GENETIQUE" ? <span className="flex items-center gap-1"><Sparkles size={13} /> {tr("Automatique")}</span> : tr("Manuel")) },
          { cle: "nb_seances", titre: tr("Seances"), alignerDroite: true },
          { cle: "cree_le", titre: tr("Cree le"), rendu: (e) => formaterDate(e.cree_le) },
          { cle: "publie_le", titre: tr("Publie le"), rendu: (e) => formaterDate(e.publie_le) },
        ]}
        lignes={resultats}
        chargement={chargement}
        cleLigne={(e) => e.id}
        page={page}
        nombrePages={nombrePages}
        onChangerPage={setPage}
        videMessage={tr("Aucun emploi du temps pour cette annee.")}
        actions={(e) => (
          <div className="flex justify-end gap-2">
            <button title={tr("Ouvrir")} className="text-texte-attenue hover:text-entete" onClick={() => navigate(`/emplois-du-temps/${e.id}`)}><Eye size={16} /></button>
            <button title={tr("PDF (toutes les classes)")} className="text-texte-attenue hover:text-entete" onClick={() => pdf(e)}><FileText size={16} /></button>
            {peutGerer && e.statut === "BROUILLON" && (
              <button title={tr("Publier")} className="text-texte-attenue hover:text-accent-vert" onClick={() => publier(e)}><Send size={16} /></button>
            )}
            {peutGerer && e.statut === "PUBLIE" && (
              <button title={tr("Creer les seances de presence")} className="text-texte-attenue hover:text-entete" onClick={() => setSeancesPour(e)}><CalendarPlus size={16} /></button>
            )}
            {peutGerer && (
              <button title={tr("Dupliquer")} className="text-texte-attenue hover:text-entete" onClick={() => dupliquer(e)}><Copy size={16} /></button>
            )}
            {peutGerer && e.statut === "BROUILLON" && (
              <button title={tr("Supprimer")} className="text-texte-attenue hover:text-accent-rouge" onClick={() => supprimer(e)}><Trash2 size={16} /></button>
            )}
          </div>
        )}
      />

      <div className={`${CARTE} mt-6`}>
        <h2 className="mb-2 text-sm font-semibold text-texte">{tr("Versions publiees")}</h2>
        {versions.length === 0 ? (
          <p className="text-sm text-texte-attenue">{tr("Aucune version publiee pour cette annee.")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-start text-texte-attenue"><th className="py-1">{tr("Version")}</th><th>{tr("Emploi du temps")}</th><th>{tr("Publie le")}</th><th>{tr("Par")}</th><th>{tr("Commentaire")}</th><th className="text-end">{tr("Seances")}</th></tr></thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.numero} className="border-t border-bordure">
                  <td className="py-1.5 font-medium">v{v.numero}</td><td>{v.emploi_nom}</td><td>{formaterDate(v.publie_le)}</td>
                  <td>{v.publie_par ?? "-"}</td><td>{v.commentaire}</td><td className="text-end">{v.nb_seances}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modale titre={tr("Nouvel emploi du temps")} ouverte={nouveau} onFermer={() => setNouveau(false)}>
        <form onSubmit={creer}>
          <label className={ETIQUETTE}>{tr("Nom *")}</label>
          <input className={`${CHAMP} w-full`} required value={nom} onChange={(e) => setNom(e.target.value)} placeholder={tr("Ex. Rentree 2025-2026")} />
          <div className="mt-3 flex justify-end gap-2">
            <button type="button" className={BOUTON} onClick={() => setNouveau(false)}>{tr("Annuler")}</button>
            <button type="submit" className={BOUTON_PRIMAIRE}>{tr("Creer et ouvrir")}</button>
          </div>
        </form>
      </Modale>

      <Modale titre={tr("Generation automatique (algorithme genetique)")} ouverte={generation} onFermer={() => setGeneration(false)}>
        <form onSubmit={generer} className="space-y-3">
          <p className="text-sm text-texte-attenue">
            {tx("Utilise les affectations des professeurs, le nombre de seances et le volume horaire de chaque matiere, les salles, le cadre horaire et les disponibilites. Le resultat est un {0} a controler avant publication.", <b>{tr("brouillon")}</b>)}
          </p>
          <div>
            <label className={ETIQUETTE}>{tr("Nom")}</label>
            <input className={`${CHAMP} w-full`} value={params.nom} onChange={(e) => setParams({ ...params, nom: e.target.value })} placeholder={tr("Emploi genere")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={ETIQUETTE}>{tr("Duree maximale (secondes)")}</label>
              <input type="number" min={1} max={120} className={`${CHAMP} w-full`} value={params.temps_max} onChange={(e) => setParams({ ...params, temps_max: e.target.value })} />
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Graine (optionnelle)")}</label>
              <input type="number" className={`${CHAMP} w-full`} value={params.graine} onChange={(e) => setParams({ ...params, graine: e.target.value })} placeholder={tr("resultat reproductible")} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className={BOUTON} onClick={() => setGeneration(false)}>{tr("Annuler")}</button>
            <button type="submit" disabled={enCours} className={BOUTON_PRIMAIRE}><Wand2 size={15} /> {enCours ? tr("Generation en cours...") : tr("Generer")}</button>
          </div>
        </form>
      </Modale>

      <Modale titre={tr("Resultat de la generation")} ouverte={!!rapport} onFermer={() => setRapport(null)} largeur="max-w-2xl">
        {rapport && (
          <>
            <RapportGenerationPanneau rapport={rapport.emploi.rapport} />
            <div className="mt-4 flex justify-end gap-2">
              <button className={BOUTON} onClick={() => setRapport(null)}>{tr("Fermer")}</button>
              <button className={BOUTON_PRIMAIRE} onClick={() => navigate(`/emplois-du-temps/${rapport.emploi.id}`)}>{tr("Ouvrir l'apercu")}</button>
            </div>
          </>
        )}
      </Modale>

      <Modale titre={tr("Creer les seances de presence")} ouverte={!!seancesPour} onFermer={() => setSeancesPour(null)}>
        <form onSubmit={genererSeances} className="space-y-3">
          <p className="text-sm text-texte-attenue">
            {tr("Cree, pour chaque cours de l'emploi du temps publie, la seance correspondante (liste d'appel et heures du professeur). Les vacances sont ignorees et les seances deja existantes ne sont pas dupliquees.")}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={ETIQUETTE}>{tr("Du")}</label>
              <input type="date" className={`${CHAMP} w-full`} required value={dates.du} onChange={(e) => setDates({ ...dates, du: e.target.value })} />
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Au")}</label>
              <input type="date" className={`${CHAMP} w-full`} required value={dates.au} onChange={(e) => setDates({ ...dates, au: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className={BOUTON} onClick={() => setSeancesPour(null)}>{tr("Annuler")}</button>
            <button type="submit" className={BOUTON_PRIMAIRE}>{tr("Creer les seances")}</button>
          </div>
        </form>
      </Modale>
    </div>
  );
}

