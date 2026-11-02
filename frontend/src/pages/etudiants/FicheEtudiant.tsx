import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { FileText, Printer, Receipt, Undo2 } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { useConfirmation } from "../../composants/Confirmation";
import { Modale } from "../../composants/Modale";
import { Badge } from "../../composants/Badge";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import {
  aujourdhui, formaterDate, formaterMois, formaterMontant, imprimerPdf, messageErreurFichier, telechargerFichier, UNITE_MONETAIRE,
} from "../../services/fichiers";
import type { Etudiant, FicheScolarite, Inscription, LigneFiche } from "../../types";

import { tr, tx, FLECHE_RETOUR } from "../../i18n";

const MODES: Record<string, string> = {
  ESPECES: tr("Especes"), VIREMENT: tr("Virement"), CHEQUE: tr("Cheque"), MOBILE: tr("Paiement mobile"),
};
const TYPES: Record<Inscription["type_inscription"], string> = {
  INSCRIPTION: tr("Nouvelle inscription"), REINSCRIPTION: tr("Reinscription"), TRANSFERT: tr("Transfert"),
};

function Info({ libelle, valeur }: { libelle: string; valeur: ReactNode }) {
  return (
    <div>
      <p className="text-xs text-texte-attenue">{libelle}</p>
      <p className="text-sm text-texte">{valeur || "-"}</p>
    </div>
  );
}

function Chiffre({ libelle, valeur, fort }: { libelle: string; valeur: string; fort?: boolean }) {
  return (
    <div className="rounded border border-bordure bg-white px-3 py-2">
      <p className="text-xs text-texte-attenue">{libelle}</p>
      <p className={`text-base ${fort ? "font-bold text-entete" : "font-semibold text-texte"}`}>{valeur}</p>
    </div>
  );
}

/** Telephone : toujours ecrit de gauche a droite, meme dans une page en arabe. */
function Telephone({ numero }: { numero: string }) {
  return numero ? <span dir="ltr">{numero}</span> : <>-</>;
}

function Personne({ nom, telephone }: { nom: string; telephone: string }) {
  if (!nom && !telephone) return <>-</>;
  return <>{nom}{nom && telephone ? " - " : ""}{telephone && <Telephone numero={telephone} />}</>;
}

/** Detail d'un etudiant : ses informations, son inscription et sa fiche de paiement mois par mois
 * (changement d'etat, impression d'un recu ou de la fiche de tous les mois). */
export function PageFicheEtudiant() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [parametres, setParametres] = useSearchParams();
  const { peut, utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();
  const voirPaiements = peut("scolarite");
  const peutEcrire = ["ADMINISTRATEUR", "DIRECTEUR", "COMPTABLE"].includes(utilisateur?.role ?? "");

  const [etudiant, setEtudiant] = useState<Etudiant | null>(null);
  const [inscriptions, setInscriptions] = useState<Inscription[] | null>(null);
  const [fiche, setFiche] = useState<FicheScolarite | null>(null);
  const [paiement, setPaiement] = useState<{ ligne: LigneFiche; date_paiement: string; mode_paiement: string; observations: string } | null>(null);
  const [montantGeneration, setMontantGeneration] = useState("");

  useEffect(() => {
    setEtudiant(null);
    setInscriptions(null);
    api.get(`/etudiants/etudiants/${id}/`).then(({ data }) => setEtudiant(data)).catch((err) => notifierErreur(messageErreur(err)));
    api.get("/etudiants/inscriptions/", { params: { etudiant: id, inactifs: 1, taille_page: 100 } })
      .then(({ data }) => setInscriptions(data.resultats ?? data))
      .catch((err) => notifierErreur(messageErreur(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Inscription affichee : celle de l'adresse (?inscription=), sinon l'inscription active, sinon la plus recente.
  const inscription = useMemo(() => {
    if (!inscriptions?.length) return null;
    return inscriptions.find((i) => String(i.id) === parametres.get("inscription"))
      ?? inscriptions.find((i) => i.statut === "ACTIVE")
      ?? inscriptions[0];
  }, [inscriptions, parametres]);

  const chargerFiche = useCallback(async () => {
    if (!inscription || !voirPaiements) return;
    try {
      const { data } = await api.get<FicheScolarite>(`/scolarite/fiches/${inscription.id}/`);
      setFiche(data);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inscription?.id, voirPaiements]);

  useEffect(() => {
    setFiche(null);
    setMontantGeneration(inscription?.montant_mensuel ?? "");
    chargerFiche();
  }, [chargerFiche, inscription?.montant_mensuel]);

  if (!etudiant || !inscriptions) return <p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>;

  const base = inscription ? `/scolarite/fiches/${inscription.id}` : "";

  /** Execute une action serveur qui retourne la fiche a jour. */
  async function agir(requete: () => Promise<{ data: FicheScolarite }>, succes: string) {
    try {
      const { data } = await requete();
      setFiche(data);
      notifierSucces(succes);
      return true;
    } catch (err) {
      notifierErreur(messageErreur(err));
      return false;
    }
  }

  async function imprimerOuTelecharger(imprimer: boolean, chemin: "pdf" | "recu", nomFichier: string, echeance?: number) {
    try {
      if (imprimer) await imprimerPdf(`${base}/${chemin}/`, { echeance });
      else await telechargerFichier(`${base}/${chemin}/`, nomFichier, { echeance });
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  async function enregistrerPaiement(e: FormEvent) {
    e.preventDefault();
    if (!paiement) return;
    const { ligne, ...donnees } = paiement;
    if (await agir(() => api.post(`${base}/payer/`, { echeance: ligne.id, ...donnees }), tr("Paiement enregistre."))) setPaiement(null);
  }

  async function annulerPaiement(ligne: LigneFiche) {
    const confirme = await demanderConfirmation({
      titre: tr("Annuler le paiement"),
      message: tr("Remettre le mois de {0} en « non paye » ? L'annulation est conservee dans l'historique des paiements.", formaterMois(ligne.mois)),
    });
    if (confirme) await agir(() => api.post(`${base}/annuler/`, { echeance: ligne.id }), tr("Paiement annule : le mois est de nouveau non paye."));
  }

  async function genererFiche(e: FormEvent) {
    e.preventDefault();
    await agir(() => api.post(`${base}/generer/`, { montant_mensuel: montantGeneration }), tr("Fiche de paiement creee."));
  }

  const nomFichierFiche = `fiche_scolarite_${etudiant.matricule}.pdf`;

  return (
    <div className="space-y-4">
      <button onClick={() => navigate(-1)} className="text-sm text-entete hover:underline">{FLECHE_RETOUR} {tr("Retour")}</button>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-texte">{etudiant.nom_complet}</h1>
          <p className="text-sm text-texte-attenue">
            {inscription && <>{tr("N° d'inscription")} : <strong className="text-texte">{inscription.numero_inscription}</strong> · </>}
            {tr("Matricule")} : {etudiant.matricule}
          </p>
        </div>
        <Badge statut={etudiant.actif ? "ACTIF" : "INACTIF"} />
      </div>

      <section className={CARTE}>
        <h2 className="mb-3 text-sm font-semibold text-texte">{tr("Informations de l'etudiant")}</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
          <Info libelle={tr("Sexe")} valeur={etudiant.sexe === "F" ? tr("Feminin") : tr("Masculin")} />
          <Info libelle={tr("Date de naissance")} valeur={formaterDate(etudiant.date_naissance)} />
          <Info libelle={tr("Lieu de naissance")} valeur={etudiant.lieu_naissance} />
          <Info libelle={tr("Numero national")} valeur={etudiant.numero_national} />
          <Info libelle={tr("Adresse")} valeur={etudiant.adresse} />
          <Info libelle={tr("Telephone principal (notifications)")} valeur={<Telephone numero={etudiant.telephone_principal} />} />
          <Info libelle={tr("Pere")} valeur={<Personne nom={etudiant.nom_pere} telephone={etudiant.telephone_pere} />} />
          <Info libelle={tr("Mere")} valeur={<Personne nom={etudiant.nom_mere} telephone={etudiant.telephone_mere} />} />
          <Info libelle={tr("Tuteur")} valeur={<Personne nom={etudiant.nom_tuteur} telephone={etudiant.telephone_tuteur} />} />
        </div>
      </section>

      <section className={CARTE}>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-texte">{tr("Inscription")}</h2>
          {inscriptions.length > 1 && (
            <select
              className={CHAMP}
              value={inscription?.id ?? ""}
              onChange={(e) => setParametres({ inscription: e.target.value }, { replace: true })}
            >
              {inscriptions.map((i) => <option key={i.id} value={i.id}>{i.annee_scolaire_libelle} - {i.classe_nom}</option>)}
            </select>
          )}
        </div>
        {!inscription ? (
          <p className="text-sm text-texte-attenue">{tr("Cet etudiant n'a aucune inscription.")}</p>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            <Info libelle={tr("N° d'inscription")} valeur={inscription.numero_inscription} />
            <Info libelle={tr("Annee scolaire")} valeur={inscription.annee_scolaire_libelle} />
            <Info libelle={tr("Classe")} valeur={inscription.classe_nom} />
            <Info libelle={tr("Groupe")} valeur={inscription.groupe_nom} />
            <Info libelle={tr("Type")} valeur={TYPES[inscription.type_inscription]} />
            <Info libelle={tr("Statut")} valeur={<Badge statut={inscription.statut} />} />
            <Info libelle={tr("Date d'inscription")} valeur={formaterDate(inscription.date_inscription)} />
            <Info libelle={tr("Montant mensuel")} valeur={inscription.montant_mensuel ? formaterMontant(inscription.montant_mensuel) : ""} />
          </div>
        )}
      </section>

      {inscription && voirPaiements && (
        <section className={CARTE}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-texte">{tr("Fiche de paiement de la scolarite")}</h2>
            {fiche && fiche.lignes.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <button className={BOUTON} onClick={() => imprimerOuTelecharger(true, "pdf", nomFichierFiche)}>
                  <Printer size={15} /> {tr("Imprimer la fiche")}
                </button>
                <button className={BOUTON} onClick={() => imprimerOuTelecharger(false, "pdf", nomFichierFiche)}>
                  <FileText size={15} /> {tr("Fiche PDF")}
                </button>
              </div>
            )}
          </div>

          {!fiche ? (
            <p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>
          ) : fiche.lignes.length === 0 ? (
            <div>
              <p className="text-sm text-texte-attenue">{tr("Aucune fiche de paiement n'a ete generee pour cette inscription.")}</p>
              {peutEcrire && (
                <form onSubmit={genererFiche} className="mt-3 flex flex-wrap items-end gap-2">
                  <div>
                    <label className={ETIQUETTE}>{tr("Montant mensuel")} ({UNITE_MONETAIRE})</label>
                    <input
                      className={CHAMP}
                      inputMode="decimal"
                      value={montantGeneration}
                      placeholder={tr("Tarif de la classe")}
                      onChange={(e) => setMontantGeneration(e.target.value)}
                    />
                  </div>
                  <button type="submit" className={BOUTON_PRIMAIRE}>{tr("Generer la fiche")}</button>
                </form>
              )}
            </div>
          ) : (
            <>
              <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4">
                <Chiffre libelle={tr("Total du")} valeur={formaterMontant(fiche.totaux.du)} />
                <Chiffre libelle={tr("Total paye")} valeur={formaterMontant(fiche.totaux.paye)} />
                <Chiffre libelle={tr("Reste a payer")} valeur={formaterMontant(fiche.totaux.reste)} fort />
                <Chiffre libelle={tr("Mois payes")} valeur={`${fiche.totaux.mois_payes} / ${fiche.totaux.nombre_mois}`} />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-start text-texte-attenue">
                      <th className="py-1">{tr("N°")}</th><th>{tr("Mois")}</th>
                      <th className="text-end">{tr("Montant")}</th><th className="text-end">{tr("Paye")}</th>
                      <th>{tr("Etat")}</th><th>{tr("Date")}</th><th>{tr("Mode")}</th><th>{tr("Recu")}</th><th />
                    </tr>
                  </thead>
                  <tbody>
                    {fiche.lignes.map((l, index) => (
                      <tr key={l.id} className="border-t border-bordure">
                        <td className="py-1.5">{index + 1}</td>
                        <td className="capitalize">{formaterMois(l.mois)}</td>
                        <td className="text-end">{formaterMontant(l.montant)}</td>
                        <td className="text-end">{l.statut === "NON_PAYE" ? "-" : formaterMontant(l.paye)}</td>
                        <td><Badge statut={l.statut} /></td>
                        <td>{formaterDate(l.date_paiement) || "-"}</td>
                        <td>{l.mode_paiement ? MODES[l.mode_paiement] : "-"}</td>
                        <td>{l.reference ?? "-"}</td>
                        <td>
                          <div className="flex items-center justify-end gap-2">
                            {peutEcrire && l.statut !== "PAYE" && (
                              <button
                                className="rounded bg-entete px-2 py-1 text-xs font-medium text-white hover:bg-entete-fonce"
                                onClick={() => setPaiement({ ligne: l, date_paiement: aujourdhui(), mode_paiement: "ESPECES", observations: "" })}
                              >
                                {tr("Marquer paye")}
                              </button>
                            )}
                            {l.statut !== "NON_PAYE" && (
                              <button
                                className="text-texte-attenue hover:text-entete"
                                title={tr("Imprimer le recu")}
                                onClick={() => imprimerOuTelecharger(true, "recu", "", l.id)}
                              >
                                <Receipt size={16} />
                              </button>
                            )}
                            {peutEcrire && l.statut !== "NON_PAYE" && (
                              <button className="text-texte-attenue hover:text-accent-rouge" title={tr("Annuler le paiement")} onClick={() => annulerPaiement(l)}>
                                <Undo2 size={15} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}

      <Modale titre={tr("Marquer le mois comme paye")} ouverte={!!paiement} onFermer={() => setPaiement(null)}>
        {paiement && (
          <form onSubmit={enregistrerPaiement} className="grid grid-cols-2 gap-3">
            <p className="col-span-2 text-sm text-texte-attenue">
              {tx("{0} : montant a regler {1}.", <b className="capitalize">{formaterMois(paiement.ligne.mois)}</b>, <b>{formaterMontant(paiement.ligne.reste)}</b>)}
            </p>
            <div>
              <label className={ETIQUETTE}>{tr("Date de paiement")} <span className="text-accent-rouge">*</span></label>
              <input
                type="date" required className={`${CHAMP} w-full`} value={paiement.date_paiement}
                onChange={(e) => setPaiement({ ...paiement, date_paiement: e.target.value })}
              />
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Mode de paiement")}</label>
              <select
                className={`${CHAMP} w-full`} value={paiement.mode_paiement}
                onChange={(e) => setPaiement({ ...paiement, mode_paiement: e.target.value })}
              >
                {Object.entries(MODES).map(([valeur, libelle]) => <option key={valeur} value={valeur}>{libelle}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className={ETIQUETTE}>{tr("Observations")}</label>
              <input
                className={`${CHAMP} w-full`} value={paiement.observations}
                onChange={(e) => setPaiement({ ...paiement, observations: e.target.value })}
              />
            </div>
            <div className="col-span-2 flex justify-end gap-2">
              <button type="button" className={BOUTON} onClick={() => setPaiement(null)}>{tr("Annuler")}</button>
              <button type="submit" className={BOUTON_PRIMAIRE}>{tr("Enregistrer")}</button>
            </div>
          </form>
        )}
      </Modale>
    </div>
  );
}
