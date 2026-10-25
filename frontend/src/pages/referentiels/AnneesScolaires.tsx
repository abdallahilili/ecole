import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { PageCrud } from "../../composants/PageCrud";
import { api, messageErreur } from "../../services/api";
import { useNotifications } from "../../composants/Notifications";
import { useOptions } from "../../hooks/useListe";
import { anneeDuLibelle, calendrierParDefaut } from "../../services/calendrierScolaire";
import type { AnneeScolaire } from "../../types";

import { tr } from "../../i18n";
/** Annee proposee a la creation : la suivante de la plus recente deja saisie (sinon celle de la date du jour). */
function prochaineAnnee(existantes: AnneeScolaire[]) {
  const debuts = existantes.map((a) => anneeDuLibelle(a.libelle)).filter((a): a is number => a !== null);
  if (debuts.length) return Math.max(...debuts) + 1;
  const aujourdhui = new Date();
  return aujourdhui.getMonth() >= 8 ? aujourdhui.getFullYear() : aujourdhui.getFullYear() - 1;
}

export function PageAnneesScolaires() {
  const { notifierSucces, notifierErreur } = useNotifications();
  const [cle, setCle] = useState(0);
  const existantes = useOptions<AnneeScolaire>("/referentiels/annees-scolaires/");
  const annee = prochaineAnnee(existantes);
  const valeursParDefaut = { libelle: `${annee}-${annee + 1}`, ...calendrierParDefaut(annee) };

  async function activer(a: AnneeScolaire) {
    try {
      await api.post(`/referentiels/annees-scolaires/${a.id}/activer/`);
      notifierSucces(tr("{0} est maintenant l'annee active.", a.libelle));
      setCle((c) => c + 1);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  return (
    <PageCrud<AnneeScolaire>
      key={cle}
      titre={tr("Annees scolaires")}
      url="/referentiels/annees-scolaires/"
      cleLigne={(a) => a.id}
      champRecherche={false}
      colonnes={[
        { cle: "libelle", titre: tr("Annee") },
        { cle: "date_debut", titre: tr("Debut") },
        { cle: "date_fin", titre: tr("Fin") },
        {
          cle: "active", titre: tr("Statut"),
          rendu: (a) => a.active
            ? <span className="inline-flex items-center gap-1 text-accent-vert"><CheckCircle2 size={14} /> {tr("Active")}</span>
            : (
              <button onClick={() => activer(a)} className="text-sm text-entete hover:underline">
                {tr("Activer")}
              </button>
            ),
        },
        {
          cle: "cloturee", titre: tr("Cloturee"),
          rendu: (a) => a.cloturee ? tr("Oui") : tr("Non"),
        },
      ]}
      largeurForm="max-w-2xl"
      messageSuppression={tr("Cette annee sera archivee : toutes ses donnees (classes, inscriptions, notes...) sont conservees et son nom pourra etre reutilise pour une nouvelle annee. Continuer ?")}
      valeursParDefaut={valeursParDefaut}
      surChangement={(nom, valeur) => {
        // Le libelle "2026-2027" recalcule tout le calendrier par defaut (dates ensuite modifiables).
        const annee = nom === "libelle" ? anneeDuLibelle(String(valeur)) : null;
        return annee ? calendrierParDefaut(annee) : undefined;
      }}
      champs={[
        { section: tr("Annee scolaire"), nom: "libelle", label: tr("Libelle (ex: 2025-2026)"), requis: true, colonnePleine: true },
        { nom: "date_debut", label: tr("Debut du 1er trimestre"), type: "date", requis: true },
        { nom: "date_fin", label: tr("Fin du 3e trimestre"), type: "date", requis: true },
        { section: tr("Trimestres"), nom: "debut_trimestre2", label: tr("Debut du 2e trimestre"), type: "date" },
        { nom: "debut_trimestre3", label: tr("Debut du 3e trimestre"), type: "date" },
        { section: tr("Petites vacances"), nom: "debut_vacances", label: tr("Vacances 1 : debut"), type: "date" },
        { nom: "fin_vacances", label: tr("Vacances 1 : fin"), type: "date" },
        { nom: "debut_vacances2", label: tr("Vacances 2 : debut"), type: "date" },
        { nom: "fin_vacances2", label: tr("Vacances 2 : fin"), type: "date" },
        { section: tr("Examens"), nom: "debut_examen1", label: tr("Examen 1 (1er trimestre) : debut"), type: "date" },
        { nom: "fin_examen1", label: tr("Examen 1 : fin"), type: "date" },
        { nom: "debut_examen2", label: tr("Examen 2 (2e trimestre) : debut"), type: "date" },
        { nom: "fin_examen2", label: tr("Examen 2 : fin"), type: "date" },
        { nom: "debut_examen3", label: tr("Examen 3 (3e trimestre) : debut"), type: "date" },
        { nom: "fin_examen3", label: tr("Examen 3 : fin"), type: "date" },
        { section: tr("Etat"), nom: "cloturee", label: tr("Cloturee"), type: "checkbox" },
      ]}
    />
  );
}
