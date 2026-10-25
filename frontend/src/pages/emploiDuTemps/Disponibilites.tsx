import { PageCrud } from "../../composants/PageCrud";
import { Badge } from "../../composants/Badge";
import { useAuth } from "../../hooks/useAuth";
import { formaterHeure } from "../../services/fichiers";
import { JOURS, NOM_JOUR } from "../../services/jours";
import type { DisponibiliteProfesseur } from "../../types";

import { tr } from "../../i18n";
/** Indisponibilites (contrainte obligatoire) et creneaux preferes (souple) des
 * professeurs. Un professeur ne gere que les siens (impose cote serveur). */
export function PageDisponibilites() {
  const { utilisateur } = useAuth();
  const estProfesseur = utilisateur?.role === "PROFESSEUR";
  return (
    <PageCrud<DisponibiliteProfesseur>
      titre={estProfesseur ? tr("Mes disponibilites") : tr("Disponibilites des professeurs")}
      url="/emplois-du-temps/disponibilites-professeurs/"
      cleLigne={(d) => d.id}
      champRecherche={false}
      valeursParDefaut={{ type: "INDISPONIBLE", jour: 0 }}
      colonnes={[
        ...(estProfesseur ? [] : [{ cle: "professeur_nom", titre: tr("Professeur") }]),
        { cle: "jour", titre: tr("Jour"), rendu: (d: DisponibiliteProfesseur) => NOM_JOUR[d.jour] },
        { cle: "horaire", titre: tr("Horaire"), rendu: (d: DisponibiliteProfesseur) => `${formaterHeure(d.heure_debut)} - ${formaterHeure(d.heure_fin)}` },
        {
          cle: "type", titre: tr("Type"),
          rendu: (d: DisponibiliteProfesseur) => d.type === "INDISPONIBLE"
            ? <Badge statut="ABSENT" /> : <span className="text-accent-vert">{tr("Prefere")}</span>,
        },
        { cle: "commentaire", titre: tr("Commentaire") },
      ]}
      champs={[
        ...(estProfesseur ? [] : [{
          nom: "professeur", label: tr("Professeur"), type: "select" as const, requis: true, colonnePleine: true,
          optionsUrl: "/professeurs/professeurs/", optionLabel: (p: any) => p.nom_complet,
        }]),
        { nom: "jour", label: tr("Jour"), type: "select", requis: true, optionsStatiques: JOURS },
        {
          nom: "type", label: tr("Type"), type: "select", requis: true, optionsStatiques: [
            { value: "INDISPONIBLE", label: tr("Indisponible (obligatoire)") },
            { value: "PREFERE", label: tr("Creneau prefere (souhait)") },
          ],
        },
        { nom: "heure_debut", label: tr("De"), type: "heure", requis: true },
        { nom: "heure_fin", label: "A", type: "heure", requis: true },
        { nom: "commentaire", label: tr("Commentaire"), colonnePleine: true },
      ]}
    />
  );
}
