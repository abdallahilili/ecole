import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, FileSpreadsheet, FileText, MessageSquare, Printer, Unlock } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { useConfirmation } from "../../composants/Confirmation";
import { Modale } from "../../composants/Modale";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import { imprimerPdf, messageErreurFichier, telechargerFichier } from "../../services/fichiers";
import type { AnneeScolaire, Classe, LigneResultat, ResultatsClasse } from "../../types";

import { estArabe, tr } from "../../i18n";
const PERIODES = [
  { valeur: "1", libelle: tr("1er trimestre") },
  { valeur: "2", libelle: tr("2e trimestre") },
  { valeur: "3", libelle: tr("3e trimestre") },
  { valeur: "0", libelle: tr("Annuel") },
];
const DECISIONS = [
  { valeur: "", libelle: tr("-- Aucune --") },
  { valeur: "ADMIS", libelle: tr("Admis(e)") },
  { valeur: "REDOUBLE", libelle: tr("Redouble") },
  { valeur: "EXCLU", libelle: tr("Exclu(e)") },
];

function Stat({ libelle, valeur }: { libelle: string; valeur: string | null }) {
  return (
    <div className="rounded border border-bordure bg-white px-3 py-1.5">
      <p className="text-xs text-texte-attenue">{libelle}</p>
      <p className="text-base font-semibold text-texte">{valeur ?? "-"}</p>
    </div>
  );
}

export function PageResultats() {
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();
  const role = utilisateur?.role ?? "";
  const peutValider = ["ADMINISTRATEUR", "DIRECTEUR", "RESPONSABLE_PEDAGOGIQUE"].includes(role);
  const peutRouvrir = ["ADMINISTRATEUR", "DIRECTEUR"].includes(role);

  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [annee, setAnnee] = useState("");
  const classes = useOptions<Classe>(`/referentiels/classes/?annee_scolaire=${annee}`, !!annee);
  const [classe, setClasse] = useState("");
  const [periode, setPeriode] = useState("1");
  const [donnees, setDonnees] = useState<ResultatsClasse | null>(null);
  const [chargement, setChargement] = useState(false);
  const [appreciation, setAppreciation] = useState<LigneResultat | null>(null);
  const [motifOuvert, setMotifOuvert] = useState(false);
  const [motif, setMotif] = useState("");

  useEffect(() => {
    if (!annee && annees.length > 0) setAnnee(String((annees.find((a) => a.active) ?? annees[0]).id));
  }, [annees, annee]);

  const charger = useCallback(async () => {
    if (!classe) {
      setDonnees(null);
      return;
    }
    setChargement(true);
    try {
      const { data } = await api.get("/evaluations/resultats/", { params: { classe, periode } });
      setDonnees(data);
    } catch (err) {
      setDonnees(null);
      notifierErreur(messageErreur(err));
    } finally {
      setChargement(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classe, periode]);

  useEffect(() => { charger(); }, [charger]);

  const annuel = periode === "0";

  async function valider(accepterIncomplet = false): Promise<void> {
    try {
      await api.post("/evaluations/resultats/valider/", { classe, periode: Number(periode), accepter_incomplet: accepterIncomplet });
      notifierSucces(tr("Resultats valides : les bulletins ne sont plus provisoires."));
      charger();
    } catch (err: any) {
      const detail: string = err?.response?.data?.detail ?? "";
      if (!accepterIncomplet && detail.includes("manquant")) {
        const ok = await demanderConfirmation({
          titre: tr("Resultats incomplets"), message: tr("{0} Valider quand meme ?", detail),
        });
        if (ok) await valider(true);
        return;
      }
      notifierErreur(messageErreur(err));
    }
  }

  async function lancerValidation() {
    const ok = await demanderConfirmation({
      titre: tr("Valider les resultats"),
      message: tr("Apres validation, les notes de la classe sont verrouillees pour ce trimestre et les bulletins ne sont plus provisoires."),
    });
    if (ok) await valider(false);
  }

  async function rouvrir() {
    try {
      await api.post("/evaluations/resultats/rouvrir/", { classe, periode: Number(periode), motif });
      setMotifOuvert(false);
      setMotif("");
      notifierSucces(tr("Resultats rouverts."));
      charger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function sortie(type: "excel" | "pdf" | "imprimer", etudiant?: number) {
    try {
      const params = { classe, periode, ...(etudiant ? { etudiants: etudiant } : {}) };
      const nom = `${donnees?.classe_nom ?? "classe"}_${annuel ? "annuel" : `T${periode}`}`;
      if (type === "excel") await telechargerFichier("/evaluations/resultats/exporter/", `classement_${nom}.xlsx`, params);
      if (type === "pdf") await telechargerFichier("/evaluations/resultats/bulletins/", `bulletins_${nom}.pdf`, params);
      if (type === "imprimer") await imprimerPdf("/evaluations/resultats/bulletins/", params);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  async function enregistrerAppreciation() {
    if (!appreciation) return;
    try {
      const { data } = await api.post("/evaluations/resultats/appreciations/", {
        classe, periode: Number(periode),
        appreciations: [{
          etudiant: appreciation.etudiant, decision: appreciation.decision,
          observation_professeurs: appreciation.observation_professeurs, observation_directeur: appreciation.observation_directeur,
        }],
      });
      setDonnees(data);
      setAppreciation(null);
      notifierSucces(tr("Appreciation enregistree."));
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  const trier = (donnees?.etudiants ?? []).slice().sort((a, b) => (a.rang ?? 1e9) - (b.rang ?? 1e9) || a.nom_complet.localeCompare(b.nom_complet));
  const verrouillable = !annuel && !!donnees && !donnees.validee;

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold text-texte">{tr("Resultats et bulletins")}</h1>

      <div className={`${CARTE} mb-4 grid grid-cols-2 gap-3 md:grid-cols-4`}>
        <div>
          <label className={ETIQUETTE}>{tr("Annee scolaire")}</label>
          <select className={`${CHAMP} w-full`} value={annee} onChange={(e) => { setAnnee(e.target.value); setClasse(""); }}>
            {annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Classe")}</label>
          <select className={`${CHAMP} w-full`} value={classe} onChange={(e) => setClasse(e.target.value)}>
            <option value="">--</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Periode")}</label>
          <select className={`${CHAMP} w-full`} value={periode} onChange={(e) => setPeriode(e.target.value)}>
            {PERIODES.map((p) => <option key={p.valeur} value={p.valeur}>{p.libelle}</option>)}
          </select>
        </div>
      </div>

      {chargement && <p className="text-sm text-texte-attenue">{tr("Calcul en cours...")}</p>}

      {donnees && !chargement && (
        <>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <Stat libelle={tr("Effectif")} valeur={String(donnees.effectif)} />
              <Stat libelle={tr("Moyenne de la classe")} valeur={donnees.statistiques.moyenne_classe} />
              <Stat libelle={tr("Plus haute")} valeur={donnees.statistiques.plus_haute} />
              <Stat libelle={tr("Plus basse")} valeur={donnees.statistiques.plus_basse} />
              <Stat libelle={tr("Taux de reussite")} valeur={donnees.statistiques.taux_reussite ? `${donnees.statistiques.taux_reussite}${estArabe ? "%" : " %"}` : null} />
            </div>
            <div className="flex flex-wrap gap-2">
              <button className={BOUTON} onClick={() => sortie("imprimer")}><Printer size={15} /> {tr("Imprimer les bulletins")}</button>
              <button className={BOUTON} onClick={() => sortie("pdf")}><FileText size={15} /> {tr("Bulletins PDF")}</button>
              <button className={BOUTON} onClick={() => sortie("excel")}><FileSpreadsheet size={15} /> {tr("Classement Excel")}</button>
            </div>
          </div>

          <div className={`mb-3 flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-2 text-sm ${
            donnees.validee ? "border-accent-vert bg-green-50 text-accent-vert" : "border-accent-orange bg-amber-50 text-amber-800"
          }`}>
            <span className="flex items-center gap-1.5">
              {donnees.validee ? <CheckCircle2 size={16} /> : null}
              {donnees.validee
                ? (annuel ? tr("Les trois trimestres sont valides.") : tr("Resultats valides : notes verrouillees."))
                : (annuel ? tr("Resultat annuel provisoire : tous les trimestres ne sont pas encore valides.") : tr("Resultats provisoires : les bulletins portent la mention PROVISOIRE."))}
            </span>
            <span className="flex gap-2">
              {verrouillable && peutValider && (
                <button className={BOUTON_PRIMAIRE} onClick={lancerValidation}><CheckCircle2 size={15} /> {tr("Valider les resultats")}</button>
              )}
              {!annuel && donnees.validee && peutRouvrir && (
                <button className={BOUTON} onClick={() => setMotifOuvert(true)}><Unlock size={15} /> {tr("Rouvrir")}</button>
              )}
            </span>
          </div>

          <div className="overflow-x-auto rounded-md border border-bordure bg-fond-carte shadow-carte">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bordure bg-fond-barre text-start text-texte-attenue">
                  <th className="px-3 py-2">{tr("Rang")}</th>
                  <th className="px-3 py-2">{tr("Eleve")}</th>
                  {donnees.matieres.map((m) => (
                    <th key={m.id} className="px-3 py-2 text-end" title={m.nom}>
                      {m.nom}<span className="block text-xs font-normal">{tr("coef {0}", Number(m.coefficient))}</span>
                    </th>
                  ))}
                  {annuel && ["T1", "T2", "T3"].map((t) => <th key={t} className="px-3 py-2 text-end">{tr(t)}</th>)}
                  <th className="px-3 py-2 text-end">{tr("Total")}</th>
                  <th className="px-3 py-2 text-end">{tr("Moyenne")}</th>
                  <th className="px-3 py-2">{tr("Decision")}</th>
                  <th className="px-3 py-2 text-end">{tr("Actions")}</th>
                </tr>
              </thead>
              <tbody>
                {trier.length === 0 && (
                  <tr><td colSpan={9 + donnees.matieres.length} className="px-3 py-6 text-center text-texte-attenue">{tr("Aucun eleve.")}</td></tr>
                )}
                {trier.map((l) => (
                  <tr key={l.etudiant} className="border-b border-bordure last:border-0 hover:bg-fond">
                    <td className="px-3 py-2 font-medium">{l.rang ?? "-"}</td>
                    <td className="px-3 py-2">{l.nom_complet}<span className="block text-xs text-texte-attenue">{l.matricule}</span></td>
                    {donnees.matieres.map((m) => {
                      const d = l.matieres[String(m.id)];
                      return (
                        <td key={m.id} className={`px-3 py-2 text-end ${d?.incomplete ? "text-amber-700" : ""}`}>
                          {d?.moyenne ?? "-"}{d?.incomplete && d.moyenne ? "*" : ""}
                        </td>
                      );
                    })}
                    {annuel && ["1", "2", "3"].map((t) => <td key={t} className="px-3 py-2 text-end">{l.moyennes_trimestres?.[t] ?? "-"}</td>)}
                    <td className="px-3 py-2 text-end">{l.total_points}</td>
                    <td className={`px-3 py-2 text-end font-semibold ${l.incomplet ? "text-amber-700" : ""}`}>
                      {l.moyenne_generale ?? "-"}{l.incomplet && l.moyenne_generale ? "*" : ""}
                    </td>
                    <td className="px-3 py-2">{DECISIONS.find((d) => d.valeur === l.decision)?.libelle.replace(tr("-- Aucune --"), "")}</td>
                    <td className="px-3 py-2 text-end">
                      <div className="flex justify-end gap-2">
                        <button title={tr("Bulletin PDF")} className="text-texte-attenue hover:text-entete" onClick={() => sortie("pdf", l.etudiant)}><FileText size={16} /></button>
                        {peutValider && (
                          <button title={tr("Appreciations et decision")} className="text-texte-attenue hover:text-entete" onClick={() => setAppreciation({ ...l })}>
                            <MessageSquare size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-texte-attenue">
            {tr("* Moyenne provisoire : des notes ou matieres sont manquantes. Une note manquante n'est jamais comptee comme zero (sauf regle contraire dans les Parametres). Classement etabli sur la moyenne arrondie au centieme.")}
          </p>
        </>
      )}

      <Modale titre={tr("Appreciations - {0}", appreciation?.nom_complet ?? "")} ouverte={!!appreciation} onFermer={() => setAppreciation(null)}>
        {appreciation && (
          <div className="space-y-3">
            <div>
              <label className={ETIQUETTE}>{tr("Decision du conseil de classe")}</label>
              <select className={`${CHAMP} w-full`} value={appreciation.decision}
                      onChange={(e) => setAppreciation({ ...appreciation, decision: e.target.value as LigneResultat["decision"] })}>
                {DECISIONS.map((d) => <option key={d.valeur} value={d.valeur}>{d.libelle}</option>)}
              </select>
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Observations des professeurs")}</label>
              <textarea className={`${CHAMP} w-full`} rows={3} maxLength={500} value={appreciation.observation_professeurs}
                        onChange={(e) => setAppreciation({ ...appreciation, observation_professeurs: e.target.value })} />
            </div>
            <div>
              <label className={ETIQUETTE}>{tr("Observation du directeur")}</label>
              <textarea className={`${CHAMP} w-full`} rows={3} maxLength={500} value={appreciation.observation_directeur}
                        onChange={(e) => setAppreciation({ ...appreciation, observation_directeur: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <button className={BOUTON} onClick={() => setAppreciation(null)}>{tr("Annuler")}</button>
              <button className={BOUTON_PRIMAIRE} onClick={enregistrerAppreciation}>{tr("Enregistrer")}</button>
            </div>
          </div>
        )}
      </Modale>

      <Modale titre={tr("Rouvrir les resultats")} ouverte={motifOuvert} onFermer={() => setMotifOuvert(false)}>
        <p className="mb-2 text-sm text-texte-attenue">{tr("Les notes redeviennent modifiables. Le motif est conserve dans le journal d'audit.")}</p>
        <textarea className={`${CHAMP} w-full`} rows={3} value={motif} onChange={(e) => setMotif(e.target.value)} placeholder={tr("Motif (obligatoire)")} />
        <div className="mt-3 flex justify-end gap-2">
          <button className={BOUTON} onClick={() => setMotifOuvert(false)}>{tr("Annuler")}</button>
          <button className={BOUTON_PRIMAIRE} disabled={!motif.trim()} onClick={rouvrir}>{tr("Rouvrir")}</button>
        </div>
      </Modale>
    </div>
  );
}
