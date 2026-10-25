import { NavLink, useNavigate } from "react-router-dom";
import { Search, User, LogOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { ChangerMotDePasse } from "../composants/ChangerMotDePasse";
import { MENU } from "./menu";
import { SelecteurLangue } from "../composants/SelecteurLangue";

import { tr, estArabe } from "../i18n";
interface ResultatRecherche { type: string; libelle: string; detail: string; chemin: string; recherche: string }

/** Recherche transversale : etudiants, professeurs, classes, matieres (selon les droits du role). */
function RechercheGlobale() {
  const navigate = useNavigate();
  const [terme, setTerme] = useState("");
  const [resultats, setResultats] = useState<ResultatRecherche[]>([]);
  const [ouvert, setOuvert] = useState(false);
  const conteneur = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (terme.trim().length < 2) {
      setResultats([]);
      return;
    }
    const minuteur = setTimeout(() => {
      api.get("/tableau-de-bord/recherche/", { params: { q: terme.trim() } })
        .then(({ data }) => { setResultats(data.resultats); setOuvert(true); })
        .catch(() => setResultats([]));
    }, 300);
    return () => clearTimeout(minuteur);
  }, [terme]);

  useEffect(() => {
    const fermer = (e: MouseEvent) => { if (!conteneur.current?.contains(e.target as Node)) setOuvert(false); };
    document.addEventListener("mousedown", fermer);
    return () => document.removeEventListener("mousedown", fermer);
  }, []);

  function ouvrir(r: ResultatRecherche) {
    setOuvert(false);
    setTerme("");
    navigate(`${r.chemin}?q=${encodeURIComponent(r.recherche)}`);
  }

  return (
    <div ref={conteneur} className="relative hidden sm:block">
      <div className="flex items-center gap-2 rounded bg-white/15 px-2.5 py-1.5">
        <Search size={14} />
        <input
          value={terme}
          onChange={(e) => setTerme(e.target.value)}
          onFocus={() => resultats.length > 0 && setOuvert(true)}
          placeholder={tr("Rechercher (etudiant, professeur, classe)...")}
          className="w-64 bg-transparent text-sm placeholder-white/70 focus:outline-none"
        />
      </div>
      {ouvert && terme.trim().length >= 2 && (
        <ul className="absolute start-0 top-full z-50 mt-1 w-80 overflow-hidden rounded-md border border-bordure bg-white text-sm text-texte shadow-xl">
          {resultats.length === 0 && <li className="px-3 py-2 text-texte-attenue">{tr("Aucun resultat.")}</li>}
          {resultats.map((r) => (
            <li key={`${r.type}-${r.detail}`}>
              <button onClick={() => ouvrir(r)} className="flex w-full items-center justify-between gap-2 px-3 py-2 text-start hover:bg-fond">
                <span className="truncate">{r.libelle} <span className="text-xs text-texte-attenue">{r.detail}</span></span>
                <span className="shrink-0 rounded bg-fond-barre px-1.5 py-0.5 text-xs text-texte-attenue">{r.type}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Mise en page simple et professionnelle : barre superieure, sidebar
 * a icones, contenu sur fond clair. Pas de surcharge visuelle (cf.
 * cahier des charges section 10). */
export function MiseEnPagePrincipale({ children }: { children: ReactNode }) {
  const { utilisateur, deconnecter } = useAuth();
  const [reduit, setReduit] = useState(false);
  const [motDePasseOuvert, setMotDePasseOuvert] = useState(false);

  // Deux entrees du menu partagent le module "etudiants" et deux le
  // module "professeurs" (listes distinctes au sein d'un meme domaine) :
  // on deduplique par chemin, pas par module, pour les afficher toutes.
  const visibles = MENU.filter((e) => utilisateur?.modules.includes(e.module));

  return (
    <div className="flex h-screen flex-col bg-fond">
      <header className="flex h-14 shrink-0 items-center justify-between bg-entete px-4 text-white">
        <div className="flex items-center gap-4">
          <span className="text-lg font-bold tracking-tight">{tr("Gestion Ecole")}</span>
          <RechercheGlobale />
        </div>
        <div className="flex items-center gap-4 text-sm">
          <SelecteurLangue />
          <button
            onClick={() => setMotDePasseOuvert(true)}
            className="flex items-center gap-1.5 rounded px-2 py-1 hover:bg-white/15"
            title={tr("Changer mon mot de passe")}
          >
            <User size={16} />
            <span>{utilisateur?.prenom} {utilisateur?.nom}</span>
          </button>
          <button onClick={deconnecter} className="flex items-center gap-1 rounded px-2 py-1 hover:bg-white/15" title={tr("Deconnexion")}>
            <LogOut size={16} />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <nav className={`flex shrink-0 flex-col border-e border-bordure bg-fond-barre transition-all ${reduit ? "w-14" : "w-56"}`}>
          <div className="flex-1 overflow-y-auto py-2">
            {visibles.map((e) => (
              <NavLink
                key={e.chemin}
                to={e.chemin}
                end={e.chemin === "/"}
                title={e.libelle}
                className={({ isActive }) =>
                  `mx-2 mb-0.5 flex items-center gap-3 rounded px-2.5 py-2 text-sm ${
                    isActive ? "bg-entete text-white" : "text-texte hover:bg-fond"
                  }`
                }
              >
                <e.icone size={17} className="shrink-0" />
                {!reduit && <span className="truncate">{e.libelle}</span>}
              </NavLink>
            ))}
          </div>
          <button
            onClick={() => setReduit((r) => !r)}
            className="border-t border-bordure px-2.5 py-2 text-start text-xs text-texte-attenue hover:bg-fond"
          >
            {reduit ? (estArabe ? "«" : "»") : tr("« Reduire")}
          </button>
        </nav>

        <main className="flex-1 overflow-y-auto p-5">
          {children}
        </main>
      </div>

      <ChangerMotDePasse ouverte={motDePasseOuvert} onFermer={() => setMotDePasseOuvert(false)} />
    </div>
  );
}
