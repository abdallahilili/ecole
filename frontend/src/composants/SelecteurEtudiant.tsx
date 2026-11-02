import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { api } from "../services/api";
import type { Etudiant } from "../types";

import { tr } from "../i18n";

const PAR_PAGE = 8;

function telephoneDe(e: Etudiant) {
  return e.telephone_principal || e.telephone_pere || e.telephone_mere || e.telephone_tuteur;
}

function Identite({ etudiant }: { etudiant: Etudiant }) {
  const telephone = telephoneDe(etudiant);
  return (
    <span className="min-w-0">
      <span className="block truncate text-sm font-medium text-texte">{etudiant.nom_complet}</span>
      <span className="block truncate text-xs text-texte-attenue">
        {tr("Matricule")} {etudiant.matricule}{telephone ? ` · ${tr("Telephone")} ${telephone}` : ""}
      </span>
    </span>
  );
}

/** Choix d'un etudiant par recherche (matricule, nom ou numero de telephone) ; `valeur` est l'identifiant choisi. */
export function SelecteurEtudiant({ valeur, onChange }: { valeur: number | string | undefined; onChange: (id: number | "") => void }) {
  const [terme, setTerme] = useState("");
  const [resultats, setResultats] = useState<Etudiant[]>([]);
  const [chargement, setChargement] = useState(false);
  const [choisi, setChoisi] = useState<Etudiant | null>(null);

  // Etudiant deja choisi (ex. modification d'une inscription) : sa fiche est chargee pour l'afficher.
  useEffect(() => {
    if (!valeur) { setChoisi(null); return; }
    if (choisi?.id === Number(valeur)) return;
    api.get(`/etudiants/etudiants/${valeur}/`).then(({ data }) => setChoisi(data)).catch(() => setChoisi(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valeur]);

  useEffect(() => {
    if (valeur) return;
    const minuteur = setTimeout(async () => {
      setChargement(true);
      try {
        const { data } = await api.get("/etudiants/etudiants/", { params: { recherche: terme.trim(), taille_page: PAR_PAGE, tri: "nom_complet" } });
        setResultats(data.resultats ?? []);
      } catch {
        setResultats([]);
      } finally {
        setChargement(false);
      }
    }, 250);
    return () => clearTimeout(minuteur);
  }, [terme, valeur]);

  function choisir(etudiant: Etudiant) {
    setChoisi(etudiant);
    onChange(etudiant.id);
  }

  if (valeur) {
    return (
      <div className="flex items-center justify-between gap-3 rounded border border-entete bg-fond px-3 py-2">
        {choisi ? <Identite etudiant={choisi} /> : <span className="text-sm text-texte-attenue">{tr("Chargement...")}</span>}
        <button
          type="button"
          onClick={() => { setChoisi(null); setTerme(""); onChange(""); }}
          className="flex shrink-0 items-center gap-1 text-xs text-texte-attenue hover:text-entete"
        >
          <X size={14} /> {tr("Changer")}
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="relative">
        <Search size={15} className="absolute start-2.5 top-2.5 text-texte-attenue" />
        <input
          autoFocus
          value={terme}
          onChange={(e) => setTerme(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;
            e.preventDefault();   // Entree choisit le premier resultat au lieu de valider le formulaire
            if (resultats[0]) choisir(resultats[0]);
          }}
          placeholder={tr("Rechercher par matricule, nom ou telephone...")}
          className="w-full rounded border border-bordure py-1.5 ps-8 pe-3 text-sm focus:border-entete focus:outline-none"
        />
      </div>
      <ul className="mt-2 max-h-64 divide-y divide-bordure overflow-y-auto rounded border border-bordure">
        {resultats.map((etudiant) => (
          <li key={etudiant.id}>
            <button
              type="button"
              onClick={() => choisir(etudiant)}
              className="flex w-full items-center justify-between gap-3 px-3 py-2 text-start hover:bg-fond"
            >
              <Identite etudiant={etudiant} />
              {etudiant.numero_inscription && (
                <span className="shrink-0 rounded bg-fond-barre px-1.5 py-0.5 text-xs text-texte-attenue">
                  {tr("Inscrit : {0}", etudiant.numero_inscription)}
                </span>
              )}
            </button>
          </li>
        ))}
        {!chargement && resultats.length === 0 && (
          <li className="px-3 py-3 text-sm text-texte-attenue">{tr("Aucun etudiant trouve.")}</li>
        )}
      </ul>
    </div>
  );
}
