import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, Eye } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useListeAvancee, useOptions } from "../../hooks/useListe";
import { useNotifications } from "../../composants/Notifications";
import { Badge } from "../../composants/Badge";
import { TableauDonnees } from "../../composants/TableauDonnees";
import { CHAMP } from "../../composants/styles";
import { formaterDate, formaterHeure } from "../../services/fichiers";
import type { AnneeScolaire, Classe, Matiere, PresenceHistorique, Seance } from "../../types";

import { tr } from "../../i18n";
type Onglet = "seances" | "absences";

function Filtres({ valeurs, onChange, avecStatut, avecRecherche }: {
  valeurs: Record<string, string>;
  onChange: (v: Record<string, string>) => void;
  avecStatut?: boolean;
  avecRecherche?: boolean;
}) {
  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  // Les classes suivent l'annee filtree ; sans filtre d'annee, seules celles de l'annee active sont proposees.
  const classes = useOptions<Classe>(
    `/referentiels/classes/?${valeurs.annee_scolaire ? `annee_scolaire=${valeurs.annee_scolaire}` : "annee_active=1"}`);
  const matieres = useOptions<Matiere>("/referentiels/matieres/");
  const maj = (cle: string, valeur: string) => onChange({ ...valeurs, [cle]: valeur });
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      {avecRecherche && (
        <input className={CHAMP} placeholder={tr("Etudiant (nom, matricule)...")} value={valeurs.recherche ?? ""}
               onChange={(e) => maj("recherche", e.target.value)} />
      )}
      <select className={CHAMP} value={valeurs.annee_scolaire ?? ""} onChange={(e) => maj("annee_scolaire", e.target.value)}>
        <option value="">{tr("Toutes les annees")}</option>
        {annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
      </select>
      <select className={CHAMP} value={valeurs.classe ?? ""} onChange={(e) => maj("classe", e.target.value)}>
        <option value="">{tr("Toutes les classes")}</option>
        {classes.map((c) => <option key={c.id} value={c.id}>{c.nom} ({c.annee_scolaire_libelle})</option>)}
      </select>
      <select className={CHAMP} value={valeurs.matiere ?? ""} onChange={(e) => maj("matiere", e.target.value)}>
        <option value="">{tr("Toutes les matieres")}</option>
        {matieres.map((m) => <option key={m.id} value={m.id}>{m.nom_affiche ?? m.nom}</option>)}
      </select>
      {avecStatut && (
        <select className={CHAMP} value={valeurs.statut ?? ""} onChange={(e) => maj("statut", e.target.value)}>
          <option value="">{tr("Tous les statuts")}</option>
          <option value="ABSENT">{tr("Absents")}</option>
          <option value="RETARD">{tr("Retards")}</option>
          <option value="PRESENT">{tr("Presents")}</option>
        </select>
      )}
      <label className="flex items-center gap-1 text-sm text-texte-attenue">
        {tr("Du")} <input type="date" className={CHAMP} value={valeurs.du ?? ""} onChange={(e) => maj("du", e.target.value)} />
      </label>
      <label className="flex items-center gap-1 text-sm text-texte-attenue">
        au <input type="date" className={CHAMP} value={valeurs.au ?? ""} onChange={(e) => maj("au", e.target.value)} />
      </label>
    </div>
  );
}

function ListeSeances() {
  const navigate = useNavigate();
  const [filtres, setFiltres] = useState<Record<string, string>>({});
  const { resultats, chargement, page, setPage, nombrePages, proprietesTableau } = useListeAvancee<Seance>("/presences/seances/", filtres);
  return (
    <>
      <Filtres valeurs={filtres} onChange={setFiltres} />
      <TableauDonnees<Seance>
        {...proprietesTableau}
        stockage="presences-seances"
        colonnes={[
          { cle: "date", titre: tr("Date"), rendu: (s) => formaterDate(s.date) },
          { cle: "horaire", titre: tr("Horaire"), rendu: (s) => `${formaterHeure(s.heure_debut)} - ${formaterHeure(s.heure_fin)}` },
          { cle: "classe_nom", titre: tr("Classe") },
          { cle: "matiere_nom", titre: tr("Matiere") },
          { cle: "professeur_nom", titre: tr("Professeur"), rendu: (s) => s.professeur_nom ?? "-" },
          { cle: "nb_presents", titre: tr("Presents"), alignerDroite: true },
          { cle: "nb_absents", titre: tr("Absents"), alignerDroite: true },
          { cle: "nb_retards", titre: tr("Retards"), alignerDroite: true },
          { cle: "statut", titre: tr("Etat"), rendu: (s) => <Badge statut={s.presences_validees ? "VALIDE" : "BROUILLON"} /> },
        ]}
        lignes={resultats}
        chargement={chargement}
        cleLigne={(s) => s.id}
        page={page}
        nombrePages={nombrePages}
        onChangerPage={setPage}
        actions={(s) => (
          <button onClick={() => navigate(`/presences?seance=${s.id}`)} className="text-texte-attenue hover:text-entete" title={tr("Ouvrir")}>
            <Eye size={16} />
          </button>
        )}
      />
    </>
  );
}

function ListeAbsences() {
  const { notifierSucces, notifierErreur } = useNotifications();
  const [filtres, setFiltres] = useState<Record<string, string>>({ statut: "ABSENT" });
  const { resultats, chargement, page, setPage, nombrePages, recharger, proprietesTableau } =
    useListeAvancee<PresenceHistorique>("/presences/historique/", filtres);

  async function notifier(p: PresenceHistorique) {
    try {
      await api.post("/presences/notifications/manuelle/", { presence: p.id });
      notifierSucces(tr("Notification mise en file (voir la page Notifications)."));
      recharger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  return (
    <>
      <Filtres valeurs={filtres} onChange={setFiltres} avecStatut avecRecherche />
      <TableauDonnees<PresenceHistorique>
        {...proprietesTableau}
        stockage="presences-historique"
        colonnes={[
          { cle: "date", titre: tr("Date"), rendu: (p) => formaterDate(p.date) },
          { cle: "horaire", titre: tr("Horaire"), rendu: (p) => `${formaterHeure(p.heure_debut)} - ${formaterHeure(p.heure_fin)}` },
          { cle: "etudiant_nom", titre: tr("Etudiant"), rendu: (p) => `${p.etudiant_nom} (${p.etudiant_matricule})` },
          { cle: "classe_nom", titre: tr("Classe") },
          { cle: "matiere_nom", titre: tr("Matiere") },
          { cle: "statut", titre: tr("Statut"), rendu: (p) => <Badge statut={p.statut} /> },
          { cle: "observation", titre: tr("Observation") },
          {
            cle: "notification_statut", titre: tr("WhatsApp"),
            rendu: (p) => p.notification_statut ? <Badge statut={p.notification_statut} /> : <span className="text-texte-attenue">-</span>,
          },
        ]}
        lignes={resultats}
        chargement={chargement}
        cleLigne={(p) => p.id}
        page={page}
        nombrePages={nombrePages}
        onChangerPage={setPage}
        actions={(p) =>
          p.seance_validee && p.statut !== "PRESENT" && !p.notification_statut ? (
            <button onClick={() => notifier(p)} className="text-texte-attenue hover:text-entete" title={tr("Notifier le parent par WhatsApp")}>
              <Bell size={16} />
            </button>
          ) : null
        }
      />
    </>
  );
}

export function PageHistoriquePresences() {
  const [onglet, setOnglet] = useState<Onglet>("seances");
  const styleOnglet = (actif: boolean) =>
    `px-3 py-1.5 text-sm border-b-2 ${actif ? "border-entete font-medium text-entete" : "border-transparent text-texte-attenue hover:text-texte"}`;
  return (
    <div>
      <div className="mb-3">
        <Link to="/presences" className="text-sm text-entete hover:underline">{tr("← Retour a la saisie des presences")}</Link>
      </div>
      <h1 className="mb-3 text-lg font-semibold text-texte">{tr("Historique des presences")}</h1>
      <div className="mb-3 flex gap-2 border-b border-bordure">
        <button className={styleOnglet(onglet === "seances")} onClick={() => setOnglet("seances")}>{tr("Seances")}</button>
        <button className={styleOnglet(onglet === "absences")} onClick={() => setOnglet("absences")}>{tr("Presences par etudiant")}</button>
      </div>
      {onglet === "seances" ? <ListeSeances /> : <ListeAbsences />}
    </div>
  );
}
