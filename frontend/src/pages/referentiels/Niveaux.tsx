import { PageCrud } from "../../composants/PageCrud";
import type { Niveau } from "../../types";

export function PageNiveaux() {
  return (
    <PageCrud<Niveau>
      titre="Niveaux"
      url="/referentiels/niveaux/"
      cleLigne={(n) => n.id}
      colonnes={[
        { cle: "ordre", titre: "Ordre" },
        { cle: "nom", titre: "Nom" },
        { cle: "code", titre: "Code" },
      ]}
      champs={[
        { nom: "nom", label: "Nom", requis: true, colonnePleine: true },
        { nom: "code", label: "Code", requis: true },
        { nom: "ordre", label: "Ordre pedagogique", type: "nombre" },
      ]}
    />
  );
}
