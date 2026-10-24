import { PageCrud } from "../../composants/PageCrud";
import type { Salle } from "../../types";

export function PageSalles() {
  return (
    <PageCrud<Salle>
      titre="Salles"
      url="/referentiels/salles/"
      cleLigne={(s) => s.id}
      valeursParDefaut={{ disponible: true, capacite: 30 }}
      colonnes={[
        { cle: "nom", titre: "Nom" },
        { cle: "capacite", titre: "Capacite" },
        { cle: "type_salle", titre: "Type" },
        {
          cle: "disponible", titre: "Disponible",
          rendu: (s) => (
            <span className={s.disponible ? "text-accent-vert" : "text-accent-rouge"}>
              {s.disponible ? "Oui" : "Non"}
            </span>
          ),
        },
      ]}
      champs={[
        { nom: "nom", label: "Nom", requis: true, colonnePleine: true },
        { nom: "capacite", label: "Capacite", type: "nombre", requis: true },
        { nom: "type_salle", label: "Type de salle" },
        { nom: "equipements", label: "Equipements", colonnePleine: true },
        { nom: "disponible", label: "Disponible", type: "checkbox" },
      ]}
    />
  );
}
