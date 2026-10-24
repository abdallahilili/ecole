import { PageCrud } from "../../composants/PageCrud";
import { Badge } from "../../composants/Badge";
import { useAuth } from "../../hooks/useAuth";
import { formaterHeure } from "../../services/fichiers";
import { JOURS, NOM_JOUR } from "../../services/jours";
import type { DisponibiliteProfesseur } from "../../types";

/** Indisponibilites (contrainte obligatoire) et creneaux preferes (souple) des
 * professeurs. Un professeur ne gere que les siens (impose cote serveur). */
export function PageDisponibilites() {
  const { utilisateur } = useAuth();
  const estProfesseur = utilisateur?.role === "PROFESSEUR";
  return (
    <PageCrud<DisponibiliteProfesseur>
      titre={estProfesseur ? "Mes disponibilites" : "Disponibilites des professeurs"}
      url="/emplois-du-temps/disponibilites-professeurs/"
      cleLigne={(d) => d.id}
      champRecherche={false}
      valeursParDefaut={{ type: "INDISPONIBLE", jour: 0 }}
      colonnes={[
        ...(estProfesseur ? [] : [{ cle: "professeur_nom", titre: "Professeur" }]),
        { cle: "jour", titre: "Jour", rendu: (d: DisponibiliteProfesseur) => NOM_JOUR[d.jour] },
        { cle: "horaire", titre: "Horaire", rendu: (d: DisponibiliteProfesseur) => `${formaterHeure(d.heure_debut)} - ${formaterHeure(d.heure_fin)}` },
        {
          cle: "type", titre: "Type",
          rendu: (d: DisponibiliteProfesseur) => d.type === "INDISPONIBLE"
            ? <Badge statut="ABSENT" /> : <span className="text-accent-vert">Prefere</span>,
        },
        { cle: "commentaire", titre: "Commentaire" },
      ]}
      champs={[
        ...(estProfesseur ? [] : [{
          nom: "professeur", label: "Professeur", type: "select" as const, requis: true, colonnePleine: true,
          optionsUrl: "/professeurs/professeurs/", optionLabel: (p: any) => p.nom_complet,
        }]),
        { nom: "jour", label: "Jour", type: "select", requis: true, optionsStatiques: JOURS },
        {
          nom: "type", label: "Type", type: "select", requis: true, optionsStatiques: [
            { value: "INDISPONIBLE", label: "Indisponible (obligatoire)" },
            { value: "PREFERE", label: "Creneau prefere (souhait)" },
          ],
        },
        { nom: "heure_debut", label: "De", type: "heure", requis: true },
        { nom: "heure_fin", label: "A", type: "heure", requis: true },
        { nom: "commentaire", label: "Commentaire", colonnePleine: true },
      ]}
    />
  );
}
