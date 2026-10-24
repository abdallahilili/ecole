import { useEffect, useState } from "react";
import { GraduationCap, UserCog, School, Wallet } from "lucide-react";
import { api } from "../services/api";
import { CarteKpi } from "../composants/CarteKpi";
import { useAuth } from "../hooks/useAuth";

interface Cartes {
  etudiantsActifs: number | null;
  professeursActifs: number | null;
  classes: number | null;
  paiementsCeMois: number | null;
}

/** Tableau de bord base sur des donnees reelles de la base (jamais de
 * chiffres fictifs) : simples comptages via les totaux de pagination
 * des listes deja exposees par l'API. */
export function PageTableauDeBord() {
  const { utilisateur } = useAuth();
  const [cartes, setCartes] = useState<Cartes>({
    etudiantsActifs: null, professeursActifs: null, classes: null, paiementsCeMois: null,
  });

  useEffect(() => {
    Promise.allSettled([
      api.get("/etudiants/etudiants/", { params: { taille_page: 1, actif: true } }),
      api.get("/professeurs/professeurs/", { params: { taille_page: 1, statut: "ACTIF" } }),
      api.get("/referentiels/classes/", { params: { taille_page: 1 } }),
      api.get("/scolarite/paiements/", { params: { taille_page: 1 } }),
    ]).then(([etudiants, professeurs, classes, paiements]) => {
      setCartes({
        etudiantsActifs: etudiants.status === "fulfilled" ? etudiants.value.data.total : null,
        professeursActifs: professeurs.status === "fulfilled" ? professeurs.value.data.total : null,
        classes: classes.status === "fulfilled" ? classes.value.data.total : null,
        paiementsCeMois: paiements.status === "fulfilled" ? paiements.value.data.total : null,
      });
    });
  }, []);

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold text-texte">
        Bonjour {utilisateur?.prenom || utilisateur?.identifiant}
      </h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <CarteKpi
          valeur={cartes.etudiantsActifs ?? "-"}
          libelle="Etudiants actifs"
          icone={<GraduationCap size={22} />}
          accent="vert"
        />
        <CarteKpi
          valeur={cartes.professeursActifs ?? "-"}
          libelle="Professeurs actifs"
          icone={<UserCog size={22} />}
          accent="neutre"
        />
        <CarteKpi
          valeur={cartes.classes ?? "-"}
          libelle="Classes ouvertes"
          icone={<School size={22} />}
          accent="neutre"
        />
        <CarteKpi
          valeur={cartes.paiementsCeMois ?? "-"}
          libelle="Paiements enregistres"
          icone={<Wallet size={22} />}
          accent="vert"
        />
      </div>
      <p className="mt-6 text-sm text-texte-attenue">
        Les modules Presences, Evaluations, Emplois du temps et Remuneration des
        professeurs seront ajoutes dans une prochaine livraison.
      </p>
    </div>
  );
}
