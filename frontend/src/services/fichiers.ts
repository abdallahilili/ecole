import axios from "axios";
import { api, messageErreur } from "./api";

type Parametres = Record<string, string | number | boolean | undefined | null>;

/** Nettoie les parametres vides pour ne pas les envoyer dans l'URL. */
function nettoyer(parametres?: Parametres) {
  return Object.fromEntries(Object.entries(parametres ?? {}).filter(([, v]) => v !== "" && v != null));
}

async function recuperer(url: string, parametres?: Parametres) {
  const reponse = await api.get(url, { responseType: "blob", params: nettoyer(parametres) });
  return reponse.data as Blob;
}

export async function telechargerFichier(url: string, nomFichier: string, parametres?: Parametres) {
  const blob = await recuperer(url, parametres);
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(blob);
  lien.download = nomFichier;
  lien.click();
  setTimeout(() => URL.revokeObjectURL(lien.href), 10_000);
}

/** Ouvre le PDF dans un nouvel onglet et lance l'impression. */
export async function imprimerPdf(url: string, parametres?: Parametres) {
  const blob = await recuperer(url, parametres);
  const adresse = URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
  const fenetre = window.open(adresse, "_blank");
  fenetre?.addEventListener("load", () => fenetre.print());
}

/** Avec responseType "blob", une erreur JSON arrive sous forme de Blob : on la relit. */
export async function messageErreurFichier(erreur: unknown): Promise<string> {
  if (axios.isAxiosError(erreur) && erreur.response?.data instanceof Blob) {
    try {
      const corps = JSON.parse(await erreur.response.data.text());
      if (corps?.detail) return corps.detail;
    } catch {
      /* corps non JSON : message generique ci-dessous */
    }
  }
  return messageErreur(erreur);
}

export function aujourdhui(): string {
  const d = new Date();
  const deuxChiffres = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${deuxChiffres(d.getMonth() + 1)}-${deuxChiffres(d.getDate())}`;
}

export function formaterDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const [a, m, j] = iso.slice(0, 10).split("-");
  return `${j}/${m}/${a}`;
}

/** '15600.00' -> '15 600,00 UM' */
export function formaterMontant(valeur: string | number | null | undefined): string {
  if (valeur === null || valeur === undefined || valeur === "") return "-";
  return `${Number(valeur).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} UM`;
}

/** '2025-10-01' -> 'octobre 2025' */
export function formaterMois(iso: string): string {
  const [annee, mois] = iso.split("-").map(Number);
  return new Date(annee, mois - 1, 1).toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
}

export function formaterHeure(heure: string | null | undefined): string {
  return heure ? heure.slice(0, 5) : "";
}
