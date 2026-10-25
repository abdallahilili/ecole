import axios from "axios";
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
  } catch (erreur) {
    // Seul un refus explicite du serveur invalide la session. Une panne passagere (reseau, 5xx, limite de
    // requetes) ne doit pas deconnecter : le jeton est conserve et le prochain rechargement reessaiera.
    if (estRefusAuthentification(erreur)) deconnecter();
    else definirJetonAcces(null);
    return null;
  }
}

export function estRefusAuthentification(erreur: unknown): boolean {
  const statut = axios.isAxiosError(erreur) ? erreur.response?.status : undefined;
  return statut === 400 || statut === 401 || statut === 403;
}
