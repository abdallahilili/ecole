import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { School, Users } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useOptions } from "../../hooks/useListe";
import { useNotifications } from "../../composants/Notifications";
import { BOUTON, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";
import type { AnneeScolaire, Classe } from "../../types";

import { tr } from "../../i18n";

/** Registre des etudiants, etape 1 : les classes d'une annee scolaire (l'annee en cours par defaut, les annees
 * precedentes au choix). Un clic sur une classe ouvre la liste de ses etudiants, ou ils se gerent. */
export function PageRegistreEtudiants() {
  const { notifierErreur } = useNotifications();
  const [parametres, setParametres] = useSearchParams();
  const annees = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const [classes, setClasses] = useState<Classe[]>([]);
  const [chargement, setChargement] = useState(true);
  const [inactifs, setInactifs] = useState(false);

  // Annee choisie (?annee=) sinon annee active sinon la plus recente.
  const anneeChoisie = parametres.get("annee");
  const annee = useMemo(
    () => annees.find((a) => String(a.id) === anneeChoisie) ?? annees.find((a) => a.active) ?? annees[0],
    [annees, anneeChoisie],
  );

  useEffect(() => {
    if (!annee) return;
    setChargement(true);
    api.get("/referentiels/classes/", { params: { annee_scolaire: annee.id, taille_page: 500, ...(inactifs ? { inactifs: 1 } : {}) } })
      .then(({ data }) => setClasses(data.resultats ?? data))
      .catch((err) => notifierErreur(messageErreur(err)))
      .finally(() => setChargement(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [annee?.id, inactifs]);

  const parNiveau = useMemo(() => {
    const groupes = new Map<string, Classe[]>();
    for (const classe of classes) groupes.set(classe.niveau_nom, [...(groupes.get(classe.niveau_nom) ?? []), classe]);
    return [...groupes.entries()];
  }, [classes]);
  const effectifTotal = classes.reduce((somme, c) => somme + c.effectif, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-texte">{tr("Etudiants")}</h1>
        <Link to="/etudiants/tous" className={BOUTON}>
          <Users size={15} /> {tr("Tous les etudiants")}
        </Link>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className={ETIQUETTE}>{tr("Annee scolaire")}</label>
          <select
            className={`${CHAMP} min-w-52`}
            value={annee?.id ?? ""}
            onChange={(e) => setParametres({ annee: e.target.value })}
          >
            {annees.map((a) => (
              <option key={a.id} value={a.id}>{a.active ? `${a.libelle} - ${tr("annee en cours")}` : a.libelle}</option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-1.5 pb-2 text-sm text-texte-attenue">
          <input type="checkbox" checked={inactifs} onChange={(e) => setInactifs(e.target.checked)} />
          {tr("Afficher les inactifs (non utilises)")}
        </label>
        {!chargement && classes.length > 0 && (
          <p className="pb-2 text-sm text-texte-attenue">{tr("{0} classe(s), {1} etudiant(s)", classes.length, effectifTotal)}</p>
        )}
      </div>

      {chargement ? (
        <p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>
      ) : classes.length === 0 ? (
        <p className={`${CARTE} text-sm text-texte-attenue`}>{tr("Aucune classe pour cette annee.")}</p>
      ) : (
        parNiveau.map(([niveau, liste]) => (
          <section key={niveau}>
            <h2 className="mb-2 text-sm font-semibold text-texte-attenue">{niveau}</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {liste.map((classe) => (
                <Link
                  key={classe.id}
                  to={`/etudiants/classe/${classe.id}`}
                  className={`${CARTE} flex items-center gap-3 transition hover:border-entete hover:shadow-md ${classe.actif === false ? "opacity-60" : ""}`}
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-fond-barre text-entete">
                    <School size={20} />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate font-semibold text-texte">{classe.nom}</span>
                    <span className="block text-xs text-texte-attenue">{tr("{0} / {1} eleves", classe.effectif, classe.capacite)}</span>
                  </span>
                </Link>
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
