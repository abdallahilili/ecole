import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { Banknote, CheckCircle2, FileText, Pencil, Plus, RefreshCw, Trash2, Unlock } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { useConfirmation } from "../../composants/Confirmation";
import { Modale } from "../../composants/Modale";
import { Badge } from "../../composants/Badge";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import {
  aujourdhui, formaterDate, formaterMontant, formaterMois, imprimerPdf, messageErreurFichier, telechargerFichier, UNITE_HEURE,
} from "../../services/fichiers";
import type { LigneReleve, ReleveDetail } from "../../types";

import { tr, FLECHE, tx } from "../../i18n";
const LIBELLES_PAIEMENT: Record<string, string> = { NON_PAYE: tr("Non paye"), PARTIEL: tr("Paye partiellement"), PAYE: tr("Paye") };

function Chiffre({ libelle, valeur, fort }: { libelle: string; valeur: string; fort?: boolean }) {
  return (
    <div className="rounded border border-bordure bg-white px-3 py-2">
      <p className="text-xs text-texte-attenue">{libelle}</p>
      <p className={`text-base ${fort ? "font-bold text-entete" : "font-semibold text-texte"}`}>{valeur}</p>
    </div>
  );
}

export function PageReleveDetail() {
  const { id } = useParams();
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();
  const role = utilisateur?.role ?? "";
  const peutEcrire = ["ADMINISTRATEUR", "DIRECTEUR", "COMPTABLE"].includes(role);
  const peutDecider = ["ADMINISTRATEUR", "DIRECTEUR"].includes(role);

  const [releve, setReleve] = useState<ReleveDetail | null>(null);
  const [ajustement, setAjustement] = useState({ type: "PRIME", libelle: "", montant: "" });
  const [paiement, setPaiement] = useState<{ montant: string; mode_paiement: string; date_paiement: string; observations: string } | null>(null);
  const [correction, setCorrection] = useState<{ ligne: LigneReleve; heures: string; motif: string } | null>(null);
  const [reouverture, setReouverture] = useState<string | null>(null);

  const charger = useCallback(async () => {
    try {
      const { data } = await api.get(`/remuneration/releves/${id}/`);
      setReleve(data);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => { charger(); }, [charger]);

  /** Execute une action serveur qui retourne le releve a jour. */
  async function agir(requete: () => Promise<{ data: ReleveDetail }>, succes: string) {
    try {
      const { data } = await requete();
      setReleve(data);
      notifierSucces(succes);
      return true;
    } catch (err) {
      notifierErreur(messageErreur(err));
      return false;
    }
  }

  if (!releve) return <p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>;

  const brouillon = releve.statut === "BROUILLON";
  const t = releve.totaux;
  const base = `/remuneration/releves/${releve.id}`;

  async function recalculer() {
    await agir(async () => {
      await api.post("/remuneration/releves/generer/", { mois: releve!.mois.slice(0, 7), professeur: releve!.professeur });
      return api.get(`${base}/`);
    }, tr("Releve recalcule a partir des seances effectuees."));
  }

  async function valider() {
    const ok = await demanderConfirmation({
      titre: tr("Valider le releve d'heures"),
      message: tr("{0} h - net {1}. Apres validation, les montants sont figes : seules des corrections d'heures motivees et tracees restent possibles.", t.heures, formaterMontant(t.net)),
    });
    if (ok) await agir(() => api.post(`${base}/valider/`), tr("Releve valide : les paiements sont possibles."));
  }

  async function ajouterAjustement(e: FormEvent) {
    e.preventDefault();
    if (await agir(() => api.post(`${base}/ajustement/`, ajustement), tr("Ajustement ajoute."))) setAjustement({ ...ajustement, libelle: "", montant: "" });
  }

  async function enregistrerPaiement(e: FormEvent) {
    e.preventDefault();
    if (paiement && await agir(() => api.post(`${base}/paiement/`, paiement), tr("Paiement enregistre."))) setPaiement(null);
  }

  async function corriger(e: FormEvent) {
    e.preventDefault();
    if (correction && await agir(() => api.post(`${base}/corriger-heures/`, { ligne: correction.ligne.id, heures: correction.heures, motif: correction.motif }), tr("Heures corrigees et tracees."))) setCorrection(null);
  }

  async function rouvrir() {
    if (reouverture !== null && await agir(() => api.post(`${base}/rouvrir/`, { motif: reouverture }), tr("Releve rouvert."))) setReouverture(null);
  }

  async function pdf(imprimer: boolean) {
    try {
      if (imprimer) await imprimerPdf(`${base}/pdf/`);
      else await telechargerFichier(`${base}/pdf/`, `fiche_paiement_${releve!.professeur_matricule}_${releve!.mois.slice(0, 7)}.pdf`);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  return (
    <div>
      <div className="mb-3">
        <Link to={peutEcrire ? "/remuneration" : "/ma-remuneration"} className="text-sm text-entete hover:underline">{tr("← Retour")}</Link>
      </div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold capitalize text-texte">{releve.professeur_nom} - {formaterMois(releve.mois)}</h1>
          <p className="flex items-center gap-2 text-sm text-texte-attenue">
            <Badge statut={releve.statut} /> {releve.mode_remuneration === "FIXE" ? tr("Salaire fixe") : tr("Au nombre d'heures")} - {LIBELLES_PAIEMENT[t.statut_paiement]}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {peutEcrire && brouillon && <button className={BOUTON} onClick={recalculer}><RefreshCw size={15} /> {tr("Recalculer")}</button>}
          {peutDecider && brouillon && <button className={BOUTON_PRIMAIRE} onClick={valider}><CheckCircle2 size={15} /> {tr("Valider le releve")}</button>}
          {peutEcrire && !brouillon && Number(t.solde) > 0 && (
            <button className={BOUTON_PRIMAIRE} onClick={() => setPaiement({ montant: t.solde, mode_paiement: "ESPECES", date_paiement: aujourdhui(), observations: "" })}>
              <Banknote size={15} /> {tr("Enregistrer un paiement")}
            </button>
          )}
          {peutDecider && !brouillon && releve.paiements.length === 0 && (
            <button className={BOUTON} onClick={() => setReouverture("")}><Unlock size={15} /> {tr("Rouvrir")}</button>
          )}
          <button className={BOUTON} onClick={() => pdf(true)}>{tr("Imprimer")}</button>
          <button className={BOUTON} onClick={() => pdf(false)}><FileText size={15} /> {tr("Fiche PDF")}</button>
        </div>
      </div>

      {brouillon && (
        <div className="mb-3 rounded border border-accent-orange bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {tr("Releve provisoire : il se recalcule tant qu'il n'est pas valide. Verifiez les heures puis validez-le pour permettre les paiements.")}
        </div>
      )}

      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-7">
        <Chiffre libelle={tr("Heures")} valeur={`${t.heures} ${UNITE_HEURE}`} />
        <Chiffre libelle={tr("Montant brut")} valeur={formaterMontant(t.brut)} />
        <Chiffre libelle={tr("Primes")} valeur={formaterMontant(t.primes)} />
        <Chiffre libelle={tr("Retenues")} valeur={formaterMontant(t.retenues)} />
        <Chiffre libelle={tr("Net a payer")} valeur={formaterMontant(t.net)} fort />
        <Chiffre libelle={tr("Paye")} valeur={formaterMontant(t.paye)} />
        <Chiffre libelle={tr("Solde restant")} valeur={formaterMontant(t.solde)} />
      </div>

      <div className={`${CARTE} mb-4`}>
        <h2 className="mb-2 text-sm font-semibold text-texte">{tr("Seances comptees ({0})", releve.lignes.length)}</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-start text-texte-attenue">
                <th className="py-1">{tr("Date")}</th><th>{tr("Classe")}</th><th>{tr("Matiere")}</th>
                <th className="text-end">{tr("Heures")}</th><th className="text-end">{tr("Tarif")}</th><th className="text-end">{tr("Montant")}</th>
                {peutDecider && !brouillon && <th />}
              </tr>
            </thead>
            <tbody>
              {releve.lignes.length === 0 && <tr><td colSpan={7} className="py-3 text-center text-texte-attenue">{tr("Aucune seance.")}</td></tr>}
              {releve.lignes.map((l) => (
                <tr key={l.id} className="border-t border-bordure">
                  <td className="py-1.5">{formaterDate(l.date)}</td><td>{l.classe_nom}</td><td>{l.matiere_nom}</td>
                  <td className="text-end">{l.heures}</td><td className="text-end">{formaterMontant(l.tarif)}</td><td className="text-end">{formaterMontant(l.montant)}</td>
                  {peutDecider && !brouillon && (
                    <td className="text-end">
                      <button title={tr("Corriger les heures (motif obligatoire)")} className="text-texte-attenue hover:text-entete"
                              onClick={() => setCorrection({ ligne: l, heures: l.heures, motif: "" })}><Pencil size={14} /></button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className={CARTE}>
          <h2 className="mb-2 text-sm font-semibold text-texte">{tr("Primes et retenues")}</h2>
          {releve.ajustements.length === 0 && <p className="text-sm text-texte-attenue">{tr("Aucun ajustement.")}</p>}
          {releve.ajustements.map((a) => (
            <div key={a.id} className="flex items-center justify-between border-b border-bordure py-1.5 text-sm last:border-0">
              <span><Badge statut={a.type === "PRIME" ? "PRESENT" : "ABSENT"} /> <span className="ms-1">{a.libelle}</span></span>
              <span className="flex items-center gap-2">
                {a.type === "PRIME" ? "+" : "-"} {formaterMontant(a.montant)}
                {peutEcrire && brouillon && (
                  <button title={tr("Supprimer")} className="text-texte-attenue hover:text-accent-rouge"
                          onClick={() => agir(() => api.post(`${base}/supprimer-ajustement/`, { ajustement: a.id }), tr("Ajustement supprime."))}><Trash2 size={14} /></button>
                )}
              </span>
            </div>
          ))}
          {peutEcrire && brouillon && (
            <form onSubmit={ajouterAjustement} className="mt-3 grid grid-cols-[auto_1fr_8rem_auto] items-end gap-2">
              <select className={CHAMP} value={ajustement.type} onChange={(e) => setAjustement({ ...ajustement, type: e.target.value })}>
                <option value="PRIME">{tr("Prime")}</option><option value="RETENUE">{tr("Retenue")}</option>
              </select>
              <input className={CHAMP} placeholder={tr("Libelle")} required value={ajustement.libelle} onChange={(e) => setAjustement({ ...ajustement, libelle: e.target.value })} />
              <input className={CHAMP} placeholder={tr("Montant")} required inputMode="decimal" value={ajustement.montant} onChange={(e) => setAjustement({ ...ajustement, montant: e.target.value })} />
              <button type="submit" className={BOUTON}><Plus size={15} /></button>
            </form>
          )}
        </div>

        <div className={CARTE}>
          <h2 className="mb-2 text-sm font-semibold text-texte">{tr("Paiements")}</h2>
          {releve.paiements.length === 0 && <p className="text-sm text-texte-attenue">{tr("Aucun paiement enregistre.")}</p>}
          {releve.paiements.map((p) => (
            <div key={p.id} className="border-b border-bordure py-1.5 text-sm last:border-0">
              <div className="flex items-center justify-between">
                <span>{p.reference} - {formaterDate(p.date_paiement)} - {p.type === "ANNULATION" ? tr("Annulation") : p.type === "SOLDE" ? tr("Solde") : tr("Acompte / partiel")}</span>
                <span className={Number(p.montant) < 0 ? "text-accent-rouge" : "font-medium"}>{formaterMontant(p.montant)}</span>
              </div>
              {(p.observations || p.annule_par) && <p className="text-xs text-texte-attenue">{p.observations} {p.annule_par && tr("(annule par {0})", p.annule_par)}</p>}
            </div>
          ))}
        </div>
      </div>

      {releve.corrections.length > 0 && (
        <div className={CARTE}>
          <h2 className="mb-2 text-sm font-semibold text-texte">{tr("Corrections d'heures (historique)")}</h2>
          <table className="w-full text-sm">
            <thead><tr className="text-start text-texte-attenue"><th className="py-1">{tr("Seance")}</th><th>{tr("Heures")}</th><th>{tr("Montant")}</th><th>{tr("Motif")}</th><th>{tr("Par")}</th><th>{tr("Le")}</th></tr></thead>
            <tbody>
              {releve.corrections.map((c) => (
                <tr key={c.id} className="border-t border-bordure">
                  <td className="py-1.5">{formaterDate(c.date_seance)}</td><td>{c.anciennes_heures} {FLECHE} {c.nouvelles_heures}</td>
                  <td>{formaterMontant(c.ancien_montant)} {FLECHE} {formaterMontant(c.nouveau_montant)}</td><td>{c.motif}</td>
                  <td>{c.corrige_par_nom ?? "-"}</td><td>{formaterDate(c.corrige_le)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modale titre={tr("Enregistrer un paiement")} ouverte={!!paiement} onFermer={() => setPaiement(null)}>
        {paiement && (
          <form onSubmit={enregistrerPaiement} className="grid grid-cols-2 gap-3">
            <p className="col-span-2 text-sm text-texte-attenue">{tx("Solde restant : {0}. Un montant inferieur enregistre un acompte (paiement partiel).", <b>{formaterMontant(t.solde)}</b>)}</p>
            <div>
              <label className={ETIQUETTE}>{tr("Montant (UM) *")}</label>
              <input className={`${CHAMP} w-full`} required inputMode="decimal" value={paiement.montant} onChange={(e) => setPaiement({ ...paiement, montant: e.target.value })} />
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Date *")}</label>
              <input type="date" className={`${CHAMP} w-full`} required value={paiement.date_paiement} onChange={(e) => setPaiement({ ...paiement, date_paiement: e.target.value })} />
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Mode de paiement")}</label>
              <select className={`${CHAMP} w-full`} value={paiement.mode_paiement} onChange={(e) => setPaiement({ ...paiement, mode_paiement: e.target.value })}>
                <option value="ESPECES">{tr("Especes")}</option><option value="VIREMENT">{tr("Virement")}</option>
                <option value="CHEQUE">{tr("Cheque")}</option><option value="MOBILE">{tr("Paiement mobile")}</option>
              </select>
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Observations")}</label>
              <input className={`${CHAMP} w-full`} value={paiement.observations} onChange={(e) => setPaiement({ ...paiement, observations: e.target.value })} />
            </div>
            <div className="col-span-2 flex justify-end gap-2">
              <button type="button" className={BOUTON} onClick={() => setPaiement(null)}>{tr("Annuler")}</button>
              <button type="submit" className={BOUTON_PRIMAIRE}>{tr("Enregistrer")}</button>
            </div>
          </form>
        )}
      </Modale>

      <Modale titre={tr("Corriger des heures validees")} ouverte={!!correction} onFermer={() => setCorrection(null)}>
        {correction && (
          <form onSubmit={corriger} className="space-y-3">
            <p className="text-sm text-texte-attenue"> {tr("Seance du {0} ({1}, {2}) : {3} h. La correction est conservee dans l'historique avec son motif.", formaterDate(correction.ligne.date), correction.ligne.matiere_nom, correction.ligne.classe_nom, correction.ligne.heures)} </p>
            <div>
              <label className={ETIQUETTE}>{tr("Nouvelles heures *")}</label>
              <input className={`${CHAMP} w-full`} required inputMode="decimal" value={correction.heures} onChange={(e) => setCorrection({ ...correction, heures: e.target.value })} />
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Motif *")}</label>
              <textarea className={`${CHAMP} w-full`} rows={3} required value={correction.motif} onChange={(e) => setCorrection({ ...correction, motif: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className={BOUTON} onClick={() => setCorrection(null)}>{tr("Annuler")}</button>
              <button type="submit" className={BOUTON_PRIMAIRE}>{tr("Corriger")}</button>
            </div>
          </form>
        )}
      </Modale>

      <Modale titre={tr("Rouvrir le releve")} ouverte={reouverture !== null} onFermer={() => setReouverture(null)}>
        <p className="mb-2 text-sm text-texte-attenue">{tr("Le releve redevient un brouillon recalculable. Possible uniquement sans paiement enregistre.")}</p>
        <textarea className={`${CHAMP} w-full`} rows={3} placeholder={tr("Motif (obligatoire)")} value={reouverture ?? ""} onChange={(e) => setReouverture(e.target.value)} />
        <div className="mt-3 flex justify-end gap-2">
          <button className={BOUTON} onClick={() => setReouverture(null)}>{tr("Annuler")}</button>
          <button className={BOUTON_PRIMAIRE} disabled={!(reouverture ?? "").trim()} onClick={rouvrir}>{tr("Rouvrir")}</button>
        </div>
      </Modale>
    </div>
  );
}
