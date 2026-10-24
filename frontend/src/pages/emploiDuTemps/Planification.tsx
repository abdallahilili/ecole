import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { Plus, Save, Trash2 } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import { PageCrud } from "../../composants/PageCrud";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import { formaterHeure } from "../../services/fichiers";
import { JOURS, NOM_JOUR } from "../../services/jours";
import type { AnneeScolaire, ConfigurationHoraires, IndisponibiliteSalle } from "../../types";

type Onglet = "horaires" | "salles";

function FormulaireHoraires() {
  const { utilisateur } = useAuth();
  const { notifierSucces, notifierErreur } = useNotifications();
  const peutModifier = utilisateur?.role === "ADMINISTRATEUR" || utilisateur?.role === "DIRECTEUR";
  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [annee, setAnnee] = useState("");
  const [config, setConfig] = useState<ConfigurationHoraires | null>(null);

  useEffect(() => {
    if (!annee && annees.length > 0) setAnnee(String((annees.find((a) => a.active) ?? annees[0]).id));
  }, [annees, annee]);

  useEffect(() => {
    if (!annee) return;
    api.get(`/emplois-du-temps/configuration/annee/${annee}/`)
      .then(({ data }) => setConfig({ ...data, heure_debut: formaterHeure(data.heure_debut), heure_fin: formaterHeure(data.heure_fin) }))
      .catch((err) => notifierErreur(messageErreur(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [annee]);

  if (!config) return <p className="text-sm text-texte-attenue">Chargement...</p>;

  const jours = config.jours.split(",").filter(Boolean).map(Number);
  const maj = (partiel: Partial<ConfigurationHoraires>) => setConfig({ ...config, ...partiel });
  const basculerJour = (jour: number) => {
    const nouveaux = jours.includes(jour) ? jours.filter((j) => j !== jour) : [...jours, jour].sort();
    maj({ jours: nouveaux.join(",") });
  };
  const majPause = (index: number, partiel: Partial<{ debut: string; fin: string }>) =>
    maj({ pauses: config.pauses.map((p, i) => (i === index ? { ...p, ...partiel } : p)) });

  async function enregistrer(e: FormEvent) {
    e.preventDefault();
    try {
      await api.patch(`/emplois-du-temps/configuration/${config!.id}/`, config);
      notifierSucces("Cadre horaire enregistre.");
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  const nombre = (cle: keyof ConfigurationHoraires, label: string, aide?: string) => (
    <div>
      <label className={ETIQUETTE}>{label}</label>
      <input type="number" min={1} className={`${CHAMP} w-full`} disabled={!peutModifier} value={config[cle] as number}
             onChange={(e) => maj({ [cle]: Number(e.target.value) } as Partial<ConfigurationHoraires>)} />
      {aide && <p className="mt-0.5 text-xs text-texte-attenue">{aide}</p>}
    </div>
  );

  return (
    <form onSubmit={enregistrer} className="max-w-3xl space-y-4">
      <div className={`${CARTE} grid grid-cols-1 gap-3 md:grid-cols-2`}>
        <div className="col-span-full">
          <label className={ETIQUETTE}>Annee scolaire</label>
          <select className={CHAMP} value={annee} onChange={(e) => setAnnee(e.target.value)}>
            {annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
          </select>
        </div>
        <div className="col-span-full">
          <label className={ETIQUETTE}>Jours ouvrables</label>
          <div className="flex flex-wrap gap-3">
            {JOURS.map((j) => (
              <label key={j.value} className="flex items-center gap-1.5 text-sm">
                <input type="checkbox" disabled={!peutModifier} checked={jours.includes(j.value)} onChange={() => basculerJour(j.value)} />
                {j.label}
              </label>
            ))}
          </div>
        </div>
        <div>
          <label className={ETIQUETTE}>Debut de journee</label>
          <input type="time" className={`${CHAMP} w-full`} disabled={!peutModifier} value={config.heure_debut}
                 onChange={(e) => maj({ heure_debut: e.target.value })} />
        </div>
        <div>
          <label className={ETIQUETTE}>Fin de journee</label>
          <input type="time" className={`${CHAMP} w-full`} disabled={!peutModifier} value={config.heure_fin}
                 onChange={(e) => maj({ heure_fin: e.target.value })} />
        </div>
        {nombre("duree_creneau", "Duree d'un creneau (min)", "Grille de base : toutes les seances sont des multiples du creneau.")}
        <div />
        {nombre("duree_min_seance", "Duree minimale d'une seance (min)")}
        {nombre("duree_max_seance", "Duree maximale d'une seance (min)")}
        {nombre("max_creneaux_jour_professeur", "Creneaux max. par jour et par professeur", "Preference : depassement penalise a la generation.")}
        {nombre("max_creneaux_consecutifs_professeur", "Creneaux consecutifs max. par professeur")}
      </div>

      <div className={CARTE}>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-texte">Pauses</h2>
          {peutModifier && (
            <button type="button" className={BOUTON} onClick={() => maj({ pauses: [...config.pauses, { debut: "10:00", fin: "11:00" }] })}>
              <Plus size={15} /> Ajouter une pause
            </button>
          )}
        </div>
        <p className="mb-2 text-xs text-texte-attenue">Une pause doit coincider avec la grille de creneaux. Aucune seance ne peut la chevaucher.</p>
        {config.pauses.length === 0 && <p className="text-sm text-texte-attenue">Aucune pause.</p>}
        {config.pauses.map((p, i) => (
          <div key={i} className="mb-2 flex items-center gap-2">
            <input type="time" className={CHAMP} disabled={!peutModifier} value={p.debut} onChange={(e) => majPause(i, { debut: e.target.value })} />
            <span className="text-sm text-texte-attenue">a</span>
            <input type="time" className={CHAMP} disabled={!peutModifier} value={p.fin} onChange={(e) => majPause(i, { fin: e.target.value })} />
            {peutModifier && (
              <button type="button" className="text-texte-attenue hover:text-accent-rouge" title="Retirer"
                      onClick={() => maj({ pauses: config.pauses.filter((_, k) => k !== i) })}>
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
      </div>

      {peutModifier && <button type="submit" className={BOUTON_PRIMAIRE}><Save size={15} /> Enregistrer</button>}
    </form>
  );
}

export function PagePlanification() {
  const [onglet, setOnglet] = useState<Onglet>("horaires");
  const style = (actif: boolean) =>
    `px-3 py-1.5 text-sm border-b-2 ${actif ? "border-entete font-medium text-entete" : "border-transparent text-texte-attenue hover:text-texte"}`;
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-texte">Planification</h1>
        <div className="flex gap-3 text-sm">
          <Link to="/disponibilites" className="text-entete hover:underline">Disponibilites des professeurs &rarr;</Link>
          <Link to="/emplois-du-temps" className="text-entete hover:underline">Emplois du temps &rarr;</Link>
        </div>
      </div>
      <div className="mb-4 flex gap-2 border-b border-bordure">
        <button className={style(onglet === "horaires")} onClick={() => setOnglet("horaires")}>Cadre horaire</button>
        <button className={style(onglet === "salles")} onClick={() => setOnglet("salles")}>Salles indisponibles</button>
      </div>
      {onglet === "horaires" ? (
        <FormulaireHoraires />
      ) : (
        <PageCrud<IndisponibiliteSalle>
          titre="Indisponibilites des salles"
          url="/emplois-du-temps/indisponibilites-salles/"
          cleLigne={(i) => i.id}
          champRecherche={false}
          valeursParDefaut={{ jour: 0 }}
          colonnes={[
            { cle: "salle_nom", titre: "Salle" },
            { cle: "jour", titre: "Jour", rendu: (i) => NOM_JOUR[i.jour] },
            { cle: "horaire", titre: "Horaire", rendu: (i) => `${formaterHeure(i.heure_debut)} - ${formaterHeure(i.heure_fin)}` },
            { cle: "motif", titre: "Motif" },
          ]}
          champs={[
            { nom: "salle", label: "Salle", type: "select", requis: true, colonnePleine: true, optionsUrl: "/referentiels/salles/", optionLabel: (s) => `${s.nom} (${s.capacite} places)` },
            { nom: "jour", label: "Jour", type: "select", requis: true, optionsStatiques: JOURS },
            { nom: "heure_debut", label: "De", type: "heure", requis: true },
            { nom: "heure_fin", label: "A", type: "heure", requis: true },
            { nom: "motif", label: "Motif", colonnePleine: true },
          ]}
        />
      )}
    </div>
  );
}
