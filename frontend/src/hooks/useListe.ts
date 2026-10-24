import { useCallback, useEffect, useRef, useState } from "react";
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
      }
    } catch (e: any) {
      setErreur("Impossible de charger les donnees.");
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

  return { resultats, total, page, setPage, nombrePages, chargement, erreur, recharger };
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
