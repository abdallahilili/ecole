import { api, definirJetonAcces } from "./api";
import type { Utilisateur } from "../types";

export async function connecter(identifiant: string, mot_de_passe: string) {
  const { data } = await api.post("/auth/connexion/", { identifiant, mot_de_passe });
  definirJetonAcces(data.access);
  localStorage.setItem("jeton_rafraichissement", data.refresh);
  return data.utilisateur as Utilisateur;
}

export function deconnecter() {
  definirJetonAcces(null);
  localStorage.removeItem("jeton_rafraichissement");
}

export async function obtenirProfil() {
  const { data } = await api.get("/auth/moi/");
  return data as Utilisateur;
}

export async function restaurerSession(): Promise<Utilisateur | null> {
  const refresh = localStorage.getItem("jeton_rafraichissement");
  if (!refresh) return null;
  try {
    const { data } = await api.post("/auth/rafraichir/", { refresh });
    definirJetonAcces(data.access);
    return await obtenirProfil();
  } catch {
    deconnecter();
    return null;
  }
}
