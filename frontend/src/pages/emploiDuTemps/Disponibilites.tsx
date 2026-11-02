import { PageCrud } from "../../composants/PageCrud";
import { Badge } from "../../composants/Badge";
import { useAuth } from "../../hooks/useAuth";
import { formaterHeure } from "../../services/fichiers";
import { JOURS, NOM_JOUR } from "../../services/jours";
import type { DisponibiliteProfesseur } from "../../types";

import { tr } from "../../i18n";
/** Creneaux disponibles (le professeur n'enseigne que dedans), indisponibilites (contraintes obligatoires) et creneaux
 * preferes (souple) des professeurs. Un professeur ne gere que les siens (impose cote serveur). Les creneaux disponibles
 * se saisissent aussi a la creation d'un emploi du temps. */
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
            ? <Badge statut="ABSENT" />
            : <span className="text-accent-vert">{d.type === "DISPONIBLE" ? tr("Disponible") : tr("Prefere")}</span>,
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
            { value: "DISPONIBLE", label: tr("Disponible (uniquement ces creneaux)") },
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
