import { useState } from "react";
import { Copy } from "lucide-react";
import { PageCrud } from "../../composants/PageCrud";
import { Modale } from "../../composants/Modale";
import { useNotifications } from "../../composants/Notifications";
import { useOptions } from "../../hooks/useListe";
import { api, messageErreur } from "../../services/api";
import type { AnneeScolaire, Classe } from "../../types";

import { tr } from "../../i18n";
/** Recopie les classes d'une annee scolaire source vers une annee de destination choisie. */
function CopieClasses({ recharger }: { recharger: () => void }) {
  const { notifierSucces, notifierErreur } = useNotifications();
  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [ouverte, setOuverte] = useState(false);
  const [source, setSource] = useState("");
  const [cible, setCible] = useState("");
  const [envoi, setEnvoi] = useState(false);

  function ouvrir() {
    const active = annees.find((a) => a.active);
    setSource("");
    setCible(active ? String(active.id) : "");
    setOuverte(true);
  }

  const memeAnnee = Boolean(source && cible && source === cible);
  const peutCopier = Boolean(source && cible && !memeAnnee && !envoi);

  async function copier(e: React.FormEvent) {
    e.preventDefault();
    if (!peutCopier) return;
    setEnvoi(true);
    try {
      const { data } = await api.post("/referentiels/classes/copier-annee/", {
        annee_source: Number(source),
        annee_cible: Number(cible),
      });
      notifierSucces(
        tr("{0} classe(s) copiée(s) de {1} vers {2}{3}.", data.copiees, data.source, data.cible, data.ignorees ? ` (${data.ignorees} déjà présente(s))` : "")
      );
      setOuverte(false);
      recharger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <>
      <button
        onClick={ouvrir}
        className="flex items-center gap-1.5 rounded border border-bordure px-3 py-1.5 text-sm hover:bg-fond"
      >
        <Copy size={15} /> {tr("Copier depuis une année")}
      </button>
      <Modale titre={tr("Copier les classes")} ouverte={ouverte} onFermer={() => setOuverte(false)}>
        <form onSubmit={copier} className="space-y-4">
          <p className="text-sm text-texte-attenue">
            {tr("Les classes (nom, niveau, capacité, salle principale) de l'année source choisie sont recopiées vers l'année de destination. Les classes déjà présentes dans l'année de destination sont conservées sans doublon.")}
          </p>

          <div>
            <label className="mb-1 block text-xs font-medium text-texte">
              {tr("Année source (origine / ressource)")} <span className="text-red-500">*</span>
            </label>
            <select
              className="w-full rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              required
            >
              <option value="">{tr("-- Sélectionner l'année source --")}</option>
              {annees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.libelle}
                  {a.active ? tr(" (Active)") : ""}
                  {a.cloturee ? tr(" (Clôturée)") : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-texte">
              {tr("Année de destination (qui va contenir les classes)")} <span className="text-red-500">*</span>
            </label>
            <select
              className="w-full rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
              value={cible}
              onChange={(e) => setCible(e.target.value)}
              required
            >
              <option value="">{tr("-- Sélectionner l'année de destination --")}</option>
              {annees.map((a) => (
                <option key={a.id} value={a.id} disabled={a.cloturee}>
                  {a.libelle}
                  {a.active ? tr(" (Active)") : ""}
                  {a.cloturee ? tr(" (Clôturée - lecture seule)") : ""}
                </option>
              ))}
            </select>
          </div>

          {memeAnnee && (
            <p className="text-xs text-red-600">
              {tr("L'année source et l'année de destination doivent être différentes.")}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setOuverte(false)}
              className="rounded border border-bordure px-3 py-1.5 text-sm hover:bg-fond"
            >
              {tr("Annuler")}
            </button>
            <button
              type="submit"
              disabled={!peutCopier}
              className="rounded bg-entete px-3 py-1.5 text-sm font-medium text-white hover:bg-entete-fonce disabled:opacity-50"
            >
              {envoi ? tr("Copie en cours...") : tr("Copier")}
            </button>
          </div>
        </form>
      </Modale>
    </>
  );
}

export function PageClasses() {
  return (
    <PageCrud<Classe>
      enteteExtra={(recharger) => <CopieClasses recharger={recharger} />}
      titre={tr("Classes")}
      url="/referentiels/classes/"
      cleLigne={(c) => c.id}
      valeursParDefaut={{ capacite: 40 }}
      colonnes={[
        { cle: "nom", titre: tr("Classe") },
        { cle: "niveau_nom", titre: tr("Niveau") },
        { cle: "annee_scolaire_libelle", titre: tr("Annee scolaire") },
        { cle: "effectif", titre: tr("Effectif"), alignerDroite: true },
        { cle: "capacite", titre: tr("Capacite"), alignerDroite: true },
      ]}
      champs={[
        { nom: "nom", label: tr("Nom de la classe"), requis: true, colonnePleine: true },
        {
          nom: "niveau", label: tr("Niveau"), type: "select", requis: true,
          optionsUrl: "/referentiels/niveaux/", optionLabel: (n) => n.nom_affiche ?? n.nom,
        },
        {
          nom: "annee_scolaire", label: tr("Annee scolaire"), type: "select", requis: true,
          optionsUrl: "/referentiels/annees-scolaires/", optionLabel: (a) => a.libelle,
        },
        { nom: "capacite", label: tr("Capacite maximale"), type: "nombre", requis: true },
        {
          nom: "salle_principale", label: tr("Salle principale"), type: "select",
          optionsUrl: "/referentiels/salles/", optionLabel: (s) => tr("{0} ({1} places)", s.nom, s.capacite),
        },
      ]}
    />
  );
}
