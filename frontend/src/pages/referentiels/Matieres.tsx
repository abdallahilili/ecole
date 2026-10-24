import { Link } from "react-router-dom";
import { PageCrud } from "../../composants/PageCrud";
import type { Matiere } from "../../types";

export function PageMatieres() {
  return (
    <div>
      <div className="mb-3">
        <Link to="/matieres/coefficients" className="text-sm text-entete hover:underline">
          Gerer les coefficients et volumes horaires par classe &rarr;
        </Link>
      </div>
      <PageCrud<Matiere>
      titre="Matieres"
      url="/referentiels/matieres/"
      cleLigne={(m) => m.id}
      colonnes={[
        { cle: "nom", titre: "Nom" },
        { cle: "code", titre: "Code" },
        { cle: "description", titre: "Description" },
      ]}
      champs={[
        { nom: "nom", label: "Nom", requis: true, colonnePleine: true },
        { nom: "code", label: "Code", requis: true },
        { nom: "description", label: "Description", type: "textarea", colonnePleine: true },
      ]}
      />
    </div>
  );
}
