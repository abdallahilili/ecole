import { useEffect, useState } from "react";
import { PageCrud } from "../../composants/PageCrud";
import { Badge } from "../../composants/Badge";
import { CARTE, CHAMP } from "../../composants/styles";
import { api } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { formaterDate, formaterHeure } from "../../services/fichiers";
import type { Professeur, Seance } from "../../types";

interface Resume {
  seances: number;
  heures_effectuees: string;
  par_professeur: { professeur: number; nom: string; heures: string; seances: number }[];
}

const STATUTS = [
  { value: "PLANIFIE", label: "Planifie" },
  { value: "EFFECTUE", label: "Effectue" },
  { value: "RETARD", label: "Retard du professeur" },
  { value: "ABSENT", label: "Professeur absent" },
  { value: "ANNULE", label: "Cours annule" },
  { value: "REMPLACE", label: "Remplace" },
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
            <b>{resume.seances}</b> seance(s) - <b>{resume.heures_effectuees} h</b> effectuee(s) sur la selection.
          </p>
          {resume.par_professeur.length > 0 && (
            <p className="mt-1 text-xs text-texte-attenue">
              {resume.par_professeur.map((p) => `${p.nom} : ${p.heures} h (${p.seances} seance(s))`).join(" - ")}
            </p>
          )}
        </div>
      )}
      <PageCrud<Seance>
        titre="Presences des professeurs"
        url="/presences/seances/"
        cleLigne={(s) => s.id}
        champRecherche={false}
        parametresFiltre={filtres}
        valeursParDefaut={{ statut_professeur: "PLANIFIE" }}
        titreForm={(modif) => (modif ? "Presence du professeur" : "Nouvelle seance")}
        filtres={
          <div className="flex flex-wrap items-center gap-2">
            <select className={CHAMP} value={filtres.professeur ?? ""} onChange={(e) => maj("professeur", e.target.value)}>
              <option value="">Tous les professeurs</option>
              {professeurs.map((p) => <option key={p.id} value={p.id}>{p.nom_complet}</option>)}
            </select>
            <select className={CHAMP} value={filtres.statut_professeur ?? ""} onChange={(e) => maj("statut_professeur", e.target.value)}>
              <option value="">Tous les statuts</option>
              {STATUTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <label className="flex items-center gap-1 text-sm text-texte-attenue">
              Du <input type="date" className={CHAMP} value={filtres.du ?? ""} onChange={(e) => maj("du", e.target.value)} />
            </label>
            <label className="flex items-center gap-1 text-sm text-texte-attenue">
              au <input type="date" className={CHAMP} value={filtres.au ?? ""} onChange={(e) => maj("au", e.target.value)} />
            </label>
            <button className="text-sm text-entete hover:underline" onClick={() => setCle((c) => c + 1)}>Actualiser les totaux</button>
          </div>
        }
        colonnes={[
          { cle: "date", titre: "Date", rendu: (s) => formaterDate(s.date) },
          { cle: "horaire", titre: "Horaire prevu", rendu: (s) => `${formaterHeure(s.heure_debut)} - ${formaterHeure(s.heure_fin)}` },
          { cle: "classe_nom", titre: "Classe" },
          { cle: "matiere_nom", titre: "Matiere" },
          {
            cle: "professeur_nom", titre: "Professeur",
            rendu: (s) => (
              <span>
                {s.professeur_nom ?? "-"}
                {s.remplacant_nom && <span className="block text-xs text-texte-attenue">remplace par {s.remplacant_nom}</span>}
              </span>
            ),
          },
          { cle: "statut_professeur", titre: "Statut", rendu: (s) => <Badge statut={s.statut_professeur} /> },
          {
            cle: "reel", titre: "Horaire reel",
            rendu: (s) => (s.heure_reelle_debut || s.heure_reelle_fin
              ? `${formaterHeure(s.heure_reelle_debut) || "?"} - ${formaterHeure(s.heure_reelle_fin) || "?"}` : "-"),
          },
          { cle: "heures_effectuees", titre: "Heures", alignerDroite: true },
        ]}
        champs={[
          {
            nom: "annee_scolaire", label: "Annee scolaire", type: "select", requis: true,
            optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
          },
          {
            nom: "classe", label: "Classe", type: "select", requis: true,
            optionsUrl: "/referentiels/classes/", optionLabel: (c) => `${c.nom} (${c.annee_scolaire_libelle})`,
          },
          { nom: "matiere", label: "Matiere", type: "select", requis: true, optionsUrl: "/referentiels/matieres/", optionLabel: (m) => m.nom },
          { nom: "professeur", label: "Professeur prevu", type: "select", optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => p.nom_complet },
          { nom: "date", label: "Date", type: "date", requis: true },
          { nom: "heure_debut", label: "Heure de debut prevue", type: "heure", requis: true },
          { nom: "heure_fin", label: "Heure de fin prevue", type: "heure", requis: true },
          { nom: "statut_professeur", label: "Statut du professeur", type: "select", optionsStatiques: STATUTS },
          { nom: "professeur_remplacant", label: "Remplacant (si remplace)", type: "select", optionsUrl: "/professeurs/professeurs/", optionLabel: (p) => p.nom_complet },
          { nom: "heure_reelle_debut", label: "Heure reelle de debut", type: "heure" },
          { nom: "heure_reelle_fin", label: "Heure reelle de fin", type: "heure" },
          { nom: "observations_professeur", label: "Observations", colonnePleine: true },
        ]}
      />
    </div>
  );
}
