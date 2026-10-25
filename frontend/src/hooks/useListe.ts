import { tr } from "../i18n";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../services/api";
import type { ListePaginee } from "../types";

interface OptionsListe {
  parPage?: number;
  pagine?: boolean;
}

export function useListe<T>(url: string, parametres: Record<string, any> = {}, options: OptionsListe = {}) {
  const [resultats, setResultats] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [nombrePages, setNombrePages] = useState(1);
  const [champs, setChamps] = useState<string[]>([]);
  const [inactifsDisponibles, setInactifsDisponibles] = useState(false);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const parametresRef = useRef(parametres);
  parametresRef.current = parametres;

  const recharger = useCallback(async () => {
    setChargement(true);
    setErreur(null);
    try {
      const reponse = await api.get(url, { params: { page, ...parametresRef.current } });
      if (options.pagine === false) {
        setResultats(reponse.data);
        setTotal(reponse.data.length);
        setNombrePages(1);
      } else {
        const donnees = reponse.data as ListePaginee<T>;
        setResultats(donnees.resultats ?? []);
        setTotal(donnees.total ?? 0);
        setNombrePages(donnees.nombre_pages ?? 1);
        setChamps(donnees.champs ?? []);
        setInactifsDisponibles(!!donnees.inactifs_disponibles);
      }
    } catch (e: any) {
      setErreur(tr("Impossible de charger les donnees."));
    } finally {
      setChargement(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, page, JSON.stringify(parametres)]);

  useEffect(() => {
    recharger();
  }, [recharger]);

  useEffect(() => {
    setPage(1);
  }, [JSON.stringify(parametres)]);

  return { resultats, total, page, setPage, nombrePages, champs, inactifsDisponibles, chargement, erreur, recharger };
}

/** Liste serveur avec recherche globale, tri, filtres par colonne et selection multiple.
 * `proprietesTableau` se passe tel quel a <TableauDonnees />. Les parametres envoyes au serveur
 * (`parametres`) servent aussi a l'export du resultat filtre. */
export function useListeAvancee<T>(url: string, parametresBase: Record<string, any> = {}) {
  const [recherche, setRecherche] = useState("");
  const [tri, setTri] = useState("");
  const [filtres, setFiltres] = useState<Record<string, string>>({});
  const [selection, setSelection] = useState<Set<string | number>>(new Set());

  const cleBase = JSON.stringify(parametresBase);
  const parametres = useMemo(() => ({
    ...parametresBase,
    ...(recherche ? { recherche } : {}),
    ...(tri ? { tri } : {}),
    ...Object.fromEntries(Object.entries(filtres).filter(([, v]) => v !== "").map(([k, v]) => [`col_${k}`, v])),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [cleBase, recherche, tri, filtres]);

  const liste = useListe<T>(url, parametres);
  const cleParametres = JSON.stringify(parametres);

  // Une nouvelle recherche, un nouveau tri ou une autre page remet la selection a zero.
  useEffect(() => { setSelection(new Set()); }, [cleParametres, liste.page]);

  return {
    ...liste, parametres, recherche, setRecherche, tri, setTri, filtres, setFiltres, selection, setSelection,
    proprietesTableau: {
      champsServeur: liste.champs,
      tri,
      onTri: setTri,
      filtresColonnes: filtres,
      onFiltreColonne: (cle: string, valeur: string) => setFiltres((f) => ({ ...f, [cle]: valeur })),
      selection,
      onSelection: setSelection,
    },
  };
}

export function useOptions<T>(url: string, actif = true) {
  const [options, setOptions] = useState<T[]>([]);
  useEffect(() => {
    if (!actif) return;
    api.get(url, { params: { taille_page: 500 } }).then((reponse) => {
      const donnees = reponse.data;
      setOptions(Array.isArray(donnees) ? donnees : donnees.resultats ?? []);
    }).catch(() => setOptions([]));
  }, [url, actif]);
  return options;
}
