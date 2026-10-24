import axios from "axios";
import type { AxiosError, InternalAxiosRequestConfig } from "axios";

const URL_BASE = (import.meta.env.VITE_URL_API as string) || "http://localhost:8000/api";

let jetonAcces: string | null = null;

export function definirJetonAcces(jeton: string | null) {
  jetonAcces = jeton;
}

export function obtenirJetonAcces() {
  return jetonAcces;
}

export const api = axios.create({ baseURL: URL_BASE });

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (jetonAcces) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${jetonAcces}`;
  }
  return config;
});

let rafraichissementEnCours: Promise<string | null> | null = null;

async function rafraichirJeton(): Promise<string | null> {
  const refresh = localStorage.getItem("jeton_rafraichissement");
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${URL_BASE}/auth/rafraichir/`, { refresh });
    definirJetonAcces(data.access);
    return data.access;
  } catch {
    localStorage.removeItem("jeton_rafraichissement");
    definirJetonAcces(null);
    return null;
  }
}

api.interceptors.response.use(
  (reponse) => reponse,
  async (erreur: AxiosError) => {
    const requeteOriginale = erreur.config as InternalAxiosRequestConfig & { _retentative?: boolean };
    if (erreur.response?.status === 401 && requeteOriginale && !requeteOriginale._retentative) {
      requeteOriginale._retentative = true;
      if (!rafraichissementEnCours) {
        rafraichissementEnCours = rafraichirJeton().finally(() => {
          rafraichissementEnCours = null;
        });
      }
      const nouveauJeton = await rafraichissementEnCours;
      if (nouveauJeton) {
        requeteOriginale.headers = requeteOriginale.headers ?? {};
        requeteOriginale.headers.Authorization = `Bearer ${nouveauJeton}`;
        return api(requeteOriginale);
      }
    }
    return Promise.reject(erreur);
  }
);

export function messageErreur(erreur: unknown): string {
  if (axios.isAxiosError(erreur)) {
    const data = erreur.response?.data as any;
    if (data?.detail) return data.detail;
    if (typeof data === "string") return data;
    if (data && typeof data === "object") {
      const premiereCle = Object.keys(data)[0];
      const valeur = data[premiereCle];
      return Array.isArray(valeur) ? `${premiereCle}: ${valeur[0]}` : String(valeur);
    }
  }
  return "Une erreur inattendue s'est produite.";
}
