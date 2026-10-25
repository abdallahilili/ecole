import { useEffect, useState } from "react";
import { PageCrud } from "../../composants/PageCrud";
import { Badge } from "../../composants/Badge";
import { CARTE, CHAMP } from "../../composants/styles";
import { api } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { formaterDate, formaterHeure, UNITE_HEURE } from "../../services/fichiers";
import type { Professeur, Seance } from "../../types";

import { tr, tx } from "../../i18n";
interface Resume {
  seances: number;
  heures_effectuees: string;
  par_professeur: { professeur: number; nom: string; heures: string; seances: number }[];
}

const STATUTS = [
  { value: "PLANIFIE", label: tr("Planifie") },
  { value: "EFFECTUE", label: tr("Effectue") },
  { value: "RETARD", label: tr("Retard du professeur") },
  { value: "ABSENT", label: tr("Professeur absent") },
  { value: "ANNULE", label: tr("Cours annule") },
  { value: "REMPLACE", label: tr("Remplace") },
];

/** Presence des professeurs par seance : seules les seances effectuees
 * (ou remplacees) comptent en heures ; absence et annulation = 0 h. */
export function PagePresencesProfesseurs() {
  const professeurs = useOptions<Professeur>("/professeurs/professeurs/");
  const [filtres, setFiltres] = useState<Record<string, string>>({});
  const [resume, setResume] = useState<Resume | null>(null);
  const [cle, setCle] = useState(0);

  useEffect(() => {
    api.get("/presences/seances/resume/", { params: Object.fromEntries(Object.entries(filtres).filter(([, v]) => v)) })
      .then(({ data }) => setResume(data))
      .catch(() => setResume(null));
  }, [filtres, cle]);

  const maj = (nom: string, valeur: string) => setFiltres((f) => ({ ...f, [nom]: valeur }));

  return (
    <div>
      {resume && (
        <div className={`${CARTE} mb-4`}>
          <p className="text-sm text-texte">
            {tx("{0} seance(s) - {1} effectuee(s) sur la selection.", <b>{resume.seances}</b>, <b>{resume.heures_effectuees} {UNITE_HEURE}</b>)}
          </p>
          {resume.par_professeur.length > 0 && (
            <p className="mt-1 text-xs text-texte-attenue">
              {resume.par_professeur.map((p) => tr("{0} : {1} h ({2} seance(s))", p.nom, p.heures, p.seances)).join(" - ")}
            </p>
          )}
        </div>
      )}
      <PageCrud<Seance>
        titre={tr("Presences des professeurs")}
        url="/presences/seances/"
        cleLigne={(s) => s.id}
        champRecherche={false}
        parametresFiltre={filtres}
        valeursParDefaut={{ statut_professeur: "PLANIFIE" }}
        titreForm={(modif) => (modif ? tr("Presence du professeur") : tr("Nouvelle seance"))}
        filtres={
          <div className="flex flex-wrap items-center gap-2">
            <select className={CHAMP} value={filtres.professeur ?? ""} onChange={(e) => maj("professeur", e.target.value)}>
              <option value="">{tr("Tous les professeurs")}</option>
              {professeurs.map((p) => <option key={p.id} value={p.id}>{p.nom_complet}</option>)}
            </select>
            <select className={CHAMP} value={filtres.statut_professeur ?? ""} onChange={(e) => maj("statut_professeur", e.target.value)}>
              <option value="">{tr("Tous les statuts")}</option>
              {STATUTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <label className="flex items-center gap-1 text-sm text-texte-attenue">
              {tr("Du")} <input type="date" className={CHAMP} value={filtres.du ?? ""} onChange={(e) => maj("du", e.target.value)} />
            </label>
            <label className="flex items-center gap-1 text-sm text-texte-attenue">
              au <input type="date" className={CHAMP} value={filtres.au ?? ""} onChange={(e) => maj("au", e.target.value)} />
            </label>
            <button className="text-sm text-entete hover:underline" onClick={() => setCle((c) => c + 1)}>{tr("Actualiser les totaux")}</button>
          </div>
        }
        colonnes={[
          { cle: "date", titre: tr("Date"), rendu: (s) => formaterDate(s.date) },
          { cle: "horaire", titre: tr("Horaire prevu"), rendu: (s) => `${formaterHeure(s.heure_debut)} - ${formaterHeure(s.heure_fin)}` },
          { cle: "classe_nom", titre: tr("Classe") },
          { cle: "matiere_nom", titre: tr("Matiere") },
          {
            cle: "professeur_nom", titre: tr("Professeur"),
            rendu: (s) => (
              <span>
                {s.professeur_nom ?? "-"}
                {s.remplacant_nom && <span className="block text-xs text-texte-attenue">{tr("remplace par {0}", s.remplacant_nom)}</span>}
              </span>
            ),
          },
          { cle: "statut_professeur", titre: tr("Statut"), rendu: (s) => <Badge statut={s.statut_professeur} /> },
          {
            cle: "reel", titre: tr("Horaire reel"),
            rendu: (s) => (s.heure_reelle_debut || s.heure_reelle_fin
              ? `${formaterHeure(s.heure_reelle_debut) || "?"} - ${formaterHeure(s.heure_reelle_fin) || "?"}` : "-"),
          },
          { cle: "heures_effectuees", titre: tr("Heures"), alignerDroite: true },
        ]}
        champs={[
          {
            nom: "annee_scolaire", label: tr("Annee scolaire"), type: "select", requis: true,
            optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
          },
          {
            nom: "classe", label: tr("Classe"), type: "select", requis: true,
            optionsUrl: "/referentiels/classes/?annee_active=1", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
          },
          { nom: "matiere", label: tr("Matiere"), type: "select", requis: true, optionsUrl: "/referentiels/matieres/", optionLabel: (m) => m.nom_affiche ?? m.nom },
          { nom: "professeur", label: tr("Professeur prevu"), type: "select", optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => p.nom_complet },
          { nom: "date", label: tr("Date"), type: "date", requis: true },
          { nom: "heure_debut", label: tr("Heure de debut prevue"), type: "heure", requis: true },
          { nom: "heure_fin", label: tr("Heure de fin prevue"), type: "heure", requis: true },
          { nom: "statut_professeur", label: tr("Statut du professeur"), type: "select", optionsStatiques: STATUTS },
          { nom: "professeur_remplacant", label: tr("Remplacant (si remplace)"), type: "select", optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => p.nom_complet },
          { nom: "heure_reelle_debut", label: tr("Heure reelle de debut"), type: "heure" },
          { nom: "heure_reelle_fin", label: tr("Heure reelle de fin"), type: "heure" },
          { nom: "observations_professeur", label: tr("Observations"), colonnePleine: true },
        ]}
      />
    </div>
  );
}
