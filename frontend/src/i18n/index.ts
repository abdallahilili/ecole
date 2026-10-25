/** Internationalisation (francais / arabe).
 *
 * La cle d'un texte est son libelle francais : le francais fonctionne donc sans dictionnaire, et l'arabe
 * (`ar.ts`) associe a chaque libelle sa traduction. `{0}`, `{1}`... sont remplaces par les valeurs passees.
 * Le changement de langue recharge la page : `tr()` reste ainsi une simple fonction utilisable partout
 * (composants, constantes de module, services). */
import { createElement, Fragment } from "react";
import type { ReactNode } from "react";
import { ar } from "./ar";

export type Langue = "fr" | "ar";
const CLE_STOCKAGE = "langue";

function langueInitiale(): Langue {
  try {
    const stockee = localStorage.getItem(CLE_STOCKAGE);
    if (stockee === "ar" || stockee === "fr") return stockee;
  } catch { /* stockage indisponible : langue par defaut */ }
  return "fr";
}

export const langue: Langue = langueInitiale();
export const estArabe = langue === "ar";

/** Langue des dates et nombres (chiffres latins dans les deux langues, comme sur les documents de l'ecole). */
export const LOCALE = estArabe ? "ar-u-nu-latn" : "fr-FR";

/** Fleche « vers l'avant » et « vers l'arriere » selon le sens de lecture. */
export const FLECHE = estArabe ? "←" : "→";
export const FLECHE_RETOUR = estArabe ? "→" : "←";

document.documentElement.lang = langue;
document.documentElement.dir = estArabe ? "rtl" : "ltr";

declare global {
  interface Window { __i18nManquants?: Set<string> }
}

function lireTraduction(cle: string): string {
  if (!estArabe) return cle;
  const texte = ar[cle];
  if (texte === undefined) {
    // Aide a la mise au point : les textes sans traduction sont listes dans window.__i18nManquants.
    (window.__i18nManquants ??= new Set()).add(cle);
    return cle;
  }
  return texte;
}

type Valeur = string | number | null | undefined;

export function tr(cle: string, ...valeurs: Valeur[]): string {
  const texte = lireTraduction(cle);
  return valeurs.length ? texte.replace(/\{(\d+)\}/g, (_, i) => String(valeurs[Number(i)] ?? "")) : texte;
}

/** Comme `tr`, mais les valeurs peuvent etre des elements React (ex. un mot en gras). */
export function tx(cle: string, ...noeuds: ReactNode[]): ReactNode {
  const morceaux = lireTraduction(cle).split(/(\{\d+\})/);
  return createElement(Fragment, null, ...morceaux.map((m, i) => {
    const trouve = /^\{(\d+)\}$/.exec(m);
    return createElement(Fragment, { key: i }, trouve ? noeuds[Number(trouve[1])] : m);
  }));
}

export function definirLangue(nouvelle: Langue) {
  try { localStorage.setItem(CLE_STOCKAGE, nouvelle); } catch { /* ignore */ }
  window.location.reload();
}
document.title = tr("Gestion Ecole");
