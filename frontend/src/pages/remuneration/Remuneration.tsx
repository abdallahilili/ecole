import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, FileSpreadsheet, FileText, RefreshCw, Undo2 } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useListe, useOptions } from "../../hooks/useListe";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { Modale } from "../../composants/Modale";
import { PageCrud } from "../../composants/PageCrud";
import { TableauDonnees } from "../../composants/TableauDonnees";
import { Badge } from "../../composants/Badge";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP } from "../../composants/styles";
import {
  aujourdhui, formaterDate, formaterMontant, formaterMois, messageErreurFichier, telechargerFichier,
} from "../../services/fichiers";
import type {
  EtatMensuel, HeuresMatiereClasse, PaiementProfesseur, Professeur, ReleveRemuneration, TarifProfesseurMatiere,
} from "../../types";

type Onglet = "etat" | "heures" | "paiements" | "tarifs";
const STATUT_PAIEMENT: Record<string, { libelle: string; classe: string }> = {
  NON_PAYE: { libelle: "Non paye", classe: "bg-gray-100 text-gray-700" },
  PARTIEL: { libelle: "Partiel", classe: "bg-amber-50 text-amber-700" },
  PAYE: { libelle: "Paye", classe: "bg-green-50 text-accent-vert" },
};

function Pastille({ statut }: { statut: string }) {
  const s = STATUT_PAIEMENT[statut];
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${s.classe}`}>{s.libelle}</span>;
}

function Chiffre({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div className="rounded border border-bordure bg-white px-3 py-2">
      <p className="text-xs text-texte-attenue">{libelle}</p>
      <p className="text-base font-semibold text-texte">{valeur}</p>
    </div>
  );
}

function EtatMensuelOnglet() {
  const navigate = useNavigate();
  const { notifierSucces, notifierErreur } = useNotifications();
  const professeurs = useOptions<Professeur>("/professeurs/professeurs/");
  const [mois, setMois] = useState(aujourdhui().slice(0, 7));
  const [filtres, setFiltres] = useState({ professeur: "", statut_paiement: "" });
  const [etat, setEtat] = useState<EtatMensuel | null>(null);
  const [chargement, setChargement] = useState(false);

  const charger = useCallback(async () => {
    if (!mois) return;
    setChargement(true);
    try {
      const { data } = await api.get("/remuneration/releves/etat/", { params: { mois } });
      setEtat(data);
    } catch (err) {
      setEtat(null);
      notifierErreur(messageErreur(err));
    } finally {
      setChargement(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mois]);

  useEffect(() => { charger(); }, [charger]);

  async function generer() {
    try {
      const { data } = await api.post("/remuneration/releves/generer/", { mois });
      notifierSucces(`${data.nombre} releve(s) genere(s) ou recalcule(s) a partir des seances effectuees.`);
      charger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function exporter(type: "excel" | "pdf") {
    try {
      const params = { mois, ...(filtres.professeur ? { professeur: filtres.professeur } : {}), ...(filtres.statut_paiement ? { statut_paiement: filtres.statut_paiement } : {}) };
      await telechargerFichier(`/remuneration/releves/etat/${type}/`, `etat_paiement_${mois}.${type === "excel" ? "xlsx" : "pdf"}`, params);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  const visibles = (etat?.releves ?? []).filter((r) =>
    (!filtres.professeur || String(r.professeur) === filtres.professeur)
    && (!filtres.statut_paiement || r.totaux.statut_paiement === filtres.statut_paiement));

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input type="month" className={CHAMP} value={mois} onChange={(e) => setMois(e.target.value)} />
        <select className={CHAMP} value={filtres.professeur} onChange={(e) => setFiltres({ ...filtres, professeur: e.target.value })}>
          <option value="">Tous les professeurs</option>
          {professeurs.map((p) => <option key={p.id} value={p.id}>{p.nom_complet}</option>)}
        </select>
        <select className={CHAMP} value={filtres.statut_paiement} onChange={(e) => setFiltres({ ...filtres, statut_paiement: e.target.value })}>
          <option value="">Tous les statuts de paiement</option>
          <option value="NON_PAYE">Non paye</option>
          <option value="PARTIEL">Paye partiellement</option>
          <option value="PAYE">Paye</option>
        </select>
        <div className="ml-auto flex gap-2">
          <button className={BOUTON_PRIMAIRE} onClick={generer}><RefreshCw size={15} /> Generer les releves du mois</button>
          <button className={BOUTON} onClick={() => exporter("excel")}><FileSpreadsheet size={15} /> Excel</button>
          <button className={BOUTON} onClick={() => exporter("pdf")}><FileText size={15} /> PDF</button>
        </div>
      </div>

      {etat && (
        <>
          <div className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-5">
            <Chiffre libelle="Heures effectuees" valeur={`${etat.total.heures} h`} />
            <Chiffre libelle="Montant brut" valeur={formaterMontant(etat.total.brut)} />
            <Chiffre libelle="Net a payer" valeur={formaterMontant(etat.total.net)} />
            <Chiffre libelle="Deja paye" valeur={formaterMontant(etat.total.paye)} />
            <Chiffre libelle="Solde restant" valeur={formaterMontant(etat.total.solde)} />
          </div>
          <p className="mb-3 text-xs text-texte-attenue">
            Les releves en brouillon sont recalcules en continu ; seuls les releves <b>valides</b> font foi
            (net valide : {formaterMontant(etat.total_valide.net)}, solde valide : {formaterMontant(etat.total_valide.solde)}).
          </p>
          {etat.sans_releve.length > 0 && (
            <div className="mb-3 rounded border border-accent-orange bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Heures effectuees sans releve pour {formaterMois(`${mois}-01`)} : {etat.sans_releve.map((s) => s.nom).join(", ")}.
              Cliquez sur « Generer les releves du mois ».
            </div>
          )}
        </>
      )}

      <TableauDonnees<ReleveRemuneration>
        colonnes={[
          { cle: "professeur_nom", titre: "Professeur" },
          { cle: "heures", titre: "Heures", alignerDroite: true, rendu: (r) => r.totaux.heures },
          { cle: "brut", titre: "Brut", alignerDroite: true, rendu: (r) => formaterMontant(r.totaux.brut) },
          { cle: "primes", titre: "Primes", alignerDroite: true, rendu: (r) => formaterMontant(r.totaux.primes) },
          { cle: "retenues", titre: "Retenues", alignerDroite: true, rendu: (r) => formaterMontant(r.totaux.retenues) },
          { cle: "net", titre: "Net", alignerDroite: true, rendu: (r) => <b>{formaterMontant(r.totaux.net)}</b> },
          { cle: "paye", titre: "Paye", alignerDroite: true, rendu: (r) => formaterMontant(r.totaux.paye) },
          { cle: "solde", titre: "Solde", alignerDroite: true, rendu: (r) => formaterMontant(r.totaux.solde) },
          { cle: "statut", titre: "Releve", rendu: (r) => <Badge statut={r.statut} /> },
          { cle: "statut_paiement", titre: "Paiement", rendu: (r) => <Pastille statut={r.totaux.statut_paiement} /> },
        ]}
        lignes={visibles}
        chargement={chargement}
        cleLigne={(r) => r.id}
        videMessage="Aucun releve pour ce mois : generez-les a partir des seances effectuees."
        actions={(r) => (
          <button title="Ouvrir le releve" className="text-texte-attenue hover:text-entete" onClick={() => navigate(`/remuneration/${r.id}`)}>
            <Eye size={16} />
          </button>
        )}
      />
    </div>
  );
}

function HeuresOnglet() {
  const { notifierErreur } = useNotifications();
  const professeurs = useOptions<Professeur>("/professeurs/professeurs/");
  const [professeur, setProfesseur] = useState("");
  const [du, setDu] = useState(`${aujourdhui().slice(0, 7)}-01`);
  const [au, setAu] = useState(aujourdhui());
  const [donnees, setDonnees] = useState<{ total_heures: string; detail: HeuresMatiereClasse[] } | null>(null);

  useEffect(() => {
    if (!professeur || !du || !au) {
      setDonnees(null);
      return;
    }
    api.get("/remuneration/releves/heures/", { params: { professeur, du, au } })
      .then(({ data }) => setDonnees(data)).catch((err) => notifierErreur(messageErreur(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [professeur, du, au]);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <select className={CHAMP} value={professeur} onChange={(e) => setProfesseur(e.target.value)}>
          <option value="">-- Professeur --</option>
          {professeurs.map((p) => <option key={p.id} value={p.id}>{p.nom_complet}</option>)}
        </select>
        <label className="flex items-center gap-1 text-sm text-texte-attenue">Du <input type="date" className={CHAMP} value={du} onChange={(e) => setDu(e.target.value)} /></label>
        <label className="flex items-center gap-1 text-sm text-texte-attenue">au <input type="date" className={CHAMP} value={au} onChange={(e) => setAu(e.target.value)} /></label>
      </div>
      <p className="mb-2 text-xs text-texte-attenue">
        Heures reellement enseignees (seances effectuees, en retard ou remplacees) ; une absence ou une annulation n&apos;est jamais comptee.
      </p>
      <TableauDonnees<HeuresMatiereClasse>
        colonnes={[
          { cle: "matiere_nom", titre: "Matiere" },
          { cle: "classe_nom", titre: "Classe" },
          { cle: "seances", titre: "Seances", alignerDroite: true },
          { cle: "heures", titre: "Heures", alignerDroite: true },
          { cle: "heures_comptabilisees", titre: "Deja dans un releve", alignerDroite: true },
          { cle: "heures_a_comptabiliser", titre: "A comptabiliser", alignerDroite: true },
        ]}
        lignes={donnees?.detail ?? []}
        cleLigne={(l) => `${l.matiere}-${l.classe}`}
        videMessage={professeur ? "Aucune heure sur la periode." : "Choisissez un professeur."}
      />
      {donnees && <p className="mt-2 text-right text-sm font-semibold text-texte">Total : {donnees.total_heures} h</p>}
    </div>
  );
}

function PaiementsOnglet() {
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const peutAnnuler = utilisateur?.role === "ADMINISTRATEUR" || utilisateur?.role === "DIRECTEUR";
  const professeurs = useOptions<Professeur>("/professeurs/professeurs/");
  const [filtres, setFiltres] = useState<Record<string, string>>({});
  const { resultats, chargement, page, setPage, nombrePages, recharger } = useListe<PaiementProfesseur>("/remuneration/paiements/", filtres);
  const [aAnnuler, setAAnnuler] = useState<PaiementProfesseur | null>(null);
  const [motif, setMotif] = useState("");
  const maj = (cle: string, valeur: string) => setFiltres((f) => ({ ...f, [cle]: valeur }));

  async function annuler() {
    if (!aAnnuler) return;
    try {
      await api.post(`/remuneration/paiements/${aAnnuler.id}/annuler/`, { motif });
      notifierSucces("Paiement annule par un paiement inverse.");
      setAAnnuler(null);
      setMotif("");
      recharger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <select className={CHAMP} value={filtres.professeur ?? ""} onChange={(e) => maj("professeur", e.target.value)}>
          <option value="">Tous les professeurs</option>
          {professeurs.map((p) => <option key={p.id} value={p.id}>{p.nom_complet}</option>)}
        </select>
        <input type="month" className={CHAMP} value={filtres.mois ?? ""} onChange={(e) => maj("mois", e.target.value)} title="Mois du releve" />
        <label className="flex items-center gap-1 text-sm text-texte-attenue">Du <input type="date" className={CHAMP} value={filtres.du ?? ""} onChange={(e) => maj("du", e.target.value)} /></label>
        <label className="flex items-center gap-1 text-sm text-texte-attenue">au <input type="date" className={CHAMP} value={filtres.au ?? ""} onChange={(e) => maj("au", e.target.value)} /></label>
      </div>
      <TableauDonnees<PaiementProfesseur>
        colonnes={[
          { cle: "reference", titre: "Reference" },
          { cle: "date_paiement", titre: "Date", rendu: (p) => formaterDate(p.date_paiement) },
          { cle: "professeur_nom", titre: "Professeur" },
          { cle: "mois", titre: "Mois", rendu: (p) => formaterMois(p.mois) },
          { cle: "type", titre: "Type", rendu: (p) => (p.type === "ANNULATION" ? <span className="text-accent-rouge">Annulation</span> : p.type === "SOLDE" ? "Solde" : "Acompte / partiel") },
          { cle: "montant", titre: "Montant", alignerDroite: true, rendu: (p) => <span className={Number(p.montant) < 0 ? "text-accent-rouge" : ""}>{formaterMontant(p.montant)}</span> },
          { cle: "mode_paiement", titre: "Mode" },
          { cle: "annule_par", titre: "Etat", rendu: (p) => (p.annule_par ? <span className="text-texte-attenue">annule ({p.annule_par})</span> : "") },
        ]}
        lignes={resultats}
        chargement={chargement}
        cleLigne={(p) => p.id}
        page={page}
        nombrePages={nombrePages}
        onChangerPage={setPage}
        actions={peutAnnuler ? (p) => (p.annulable ? (
          <button title="Annuler ce paiement" className="text-texte-attenue hover:text-accent-rouge" onClick={() => setAAnnuler(p)}><Undo2 size={16} /></button>
        ) : null) : undefined}
      />
      <Modale titre="Annuler un paiement" ouverte={!!aAnnuler} onFermer={() => setAAnnuler(null)}>
        <p className="mb-2 text-sm text-texte-attenue">
          Le paiement {aAnnuler?.reference} ({formaterMontant(aAnnuler?.montant)}) reste dans l&apos;historique ; un paiement inverse est enregistre.
        </p>
        <textarea className={`${CHAMP} w-full`} rows={3} placeholder="Motif (obligatoire)" value={motif} onChange={(e) => setMotif(e.target.value)} />
        <div className="mt-3 flex justify-end gap-2">
          <button className={BOUTON} onClick={() => setAAnnuler(null)}>Fermer</button>
          <button className={BOUTON_PRIMAIRE} disabled={!motif.trim()} onClick={annuler}>Annuler le paiement</button>
        </div>
      </Modale>
    </div>
  );
}

export function PageRemuneration() {
  const [onglet, setOnglet] = useState<Onglet>("etat");
  const style = (actif: boolean) =>
    `px-3 py-1.5 text-sm border-b-2 ${actif ? "border-entete font-medium text-entete" : "border-transparent text-texte-attenue hover:text-texte"}`;
  return (
    <div>
      <h1 className="mb-3 text-lg font-semibold text-texte">Remuneration des professeurs</h1>
      <div className="mb-4 flex gap-2 border-b border-bordure">
        <button className={style(onglet === "etat")} onClick={() => setOnglet("etat")}>Etat mensuel</button>
        <button className={style(onglet === "heures")} onClick={() => setOnglet("heures")}>Heures effectuees</button>
        <button className={style(onglet === "paiements")} onClick={() => setOnglet("paiements")}>Historique des paiements</button>
        <button className={style(onglet === "tarifs")} onClick={() => setOnglet("tarifs")}>Tarifs par matiere</button>
      </div>
      {onglet === "etat" && <EtatMensuelOnglet />}
      {onglet === "heures" && <HeuresOnglet />}
      {onglet === "paiements" && <PaiementsOnglet />}
      {onglet === "tarifs" && (
        <div>
          <p className={`${CARTE} mb-3 text-sm text-texte-attenue`}>
            Le tarif d&apos;une matiere prime sur le tarif horaire general de la fiche du professeur. Sans tarif specifique, le tarif general s&apos;applique.
          </p>
          <PageCrud<TarifProfesseurMatiere>
            titre="Tarifs horaires par matiere"
            url="/remuneration/tarifs-matiere/"
            cleLigne={(t) => t.id}
            champRecherche={false}
            colonnes={[
              { cle: "professeur_nom", titre: "Professeur" },
              { cle: "matiere_nom", titre: "Matiere" },
              { cle: "tarif_horaire", titre: "Tarif horaire", alignerDroite: true, rendu: (t) => formaterMontant(t.tarif_horaire) },
            ]}
            champs={[
              { nom: "professeur", label: "Professeur", type: "select", requis: true, colonnePleine: true, optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => p.nom_complet },
              { nom: "matiere", label: "Matiere", type: "select", requis: true, optionsUrl: "/referentiels/matieres/", optionLabel: (m) => m.nom },
              { nom: "tarif_horaire", label: "Tarif horaire (UM)", type: "decimal", requis: true },
            ]}
          />
        </div>
      )}
    </div>
  );
}
