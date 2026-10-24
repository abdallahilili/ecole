import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { PageCrud } from "../../composants/PageCrud";
import { api, messageErreur } from "../../services/api";
import { useNotifications } from "../../composants/Notifications";
import type { AnneeScolaire } from "../../types";

export function PageAnneesScolaires() {
  const { notifierSucces, notifierErreur } = useNotifications();
  const [cle, setCle] = useState(0);

  async function activer(a: AnneeScolaire) {
    try {
      await api.post(`/referentiels/annees-scolaires/${a.id}/activer/`);
      notifierSucces(`${a.libelle} est maintenant l'annee active.`);
      setCle((c) => c + 1);
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  return (
    <PageCrud<AnneeScolaire>
      key={cle}
      titre="Annees scolaires"
      url="/referentiels/annees-scolaires/"
      cleLigne={(a) => a.id}
      champRecherche={false}
      colonnes={[
        { cle: "libelle", titre: "Annee" },
        { cle: "date_debut", titre: "Debut" },
        { cle: "date_fin", titre: "Fin" },
        {
          cle: "active", titre: "Statut",
          rendu: (a) => a.active
            ? <span className="inline-flex items-center gap-1 text-accent-vert"><CheckCircle2 size={14} /> Active</span>
            : (
              <button onClick={() => activer(a)} className="text-sm text-entete hover:underline">
                Activer
              </button>
            ),
        },
        {
          cle: "cloturee", titre: "Cloturee",
          rendu: (a) => a.cloturee ? "Oui" : "Non",
        },
      ]}
      champs={[
        { nom: "libelle", label: "Libelle (ex: 2025-2026)", requis: true, colonnePleine: true },
        { nom: "date_debut", label: "Debut du 1er trimestre", type: "date", requis: true },
        { nom: "debut_trimestre2", label: "Debut du 2e trimestre", type: "date" },
        { nom: "debut_trimestre3", label: "Debut du 3e trimestre", type: "date" },
        { nom: "date_fin", label: "Fin du 3e trimestre", type: "date", requis: true },
        { nom: "debut_vacances", label: "Debut des vacances", type: "date" },
        { nom: "fin_vacances", label: "Fin des vacances", type: "date" },
        { nom: "debut_examen1", label: "Debut de l'examen 1 (1er trimestre)", type: "date" },
        { nom: "fin_examen1", label: "Fin de l'examen 1", type: "date" },
        { nom: "debut_examen2", label: "Debut de l'examen 2 (2e trimestre)", type: "date" },
        { nom: "fin_examen2", label: "Fin de l'examen 2", type: "date" },
        { nom: "debut_examen3", label: "Debut de l'examen 3 (3e trimestre)", type: "date" },
        { nom: "fin_examen3", label: "Fin de l'examen 3", type: "date" },
        { nom: "cloturee", label: "Cloturee", type: "checkbox" },
      ]}
    />
  );
}
