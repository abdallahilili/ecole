/** Calendrier par defaut d'une annee scolaire ("2026-2027" -> A = 2026). Toutes les dates restent modifiables.
 *
 *  - L'annee dure 9 mois : du 1er lundi d'octobre (A) au 30 juin (A+1).
 *  - Deux petites vacances de 2 semaines (du samedi au dimanche) : la premiere fin decembre / debut janvier,
 *    la seconde fin mars. Le 2e et le 3e trimestre commencent le lundi qui suit chacune d'elles.
 *  - Un examen par trimestre : la semaine (lundi-vendredi) qui precede chaque vacance, et pour le 3e
 *    trimestre le dernier lundi-vendredi avant la fin de l'annee. */

const JOUR_MS = 86_400_000;
const DUREE_VACANCES_JOURS = 15; // samedi -> dimanche, deux semaines plus tard

export interface CalendrierScolaire {
  date_debut: string;
  debut_trimestre2: string;
  debut_trimestre3: string;
  date_fin: string;
  debut_vacances: string;
  fin_vacances: string;
  debut_vacances2: string;
  fin_vacances2: string;
  debut_examen1: string;
  fin_examen1: string;
  debut_examen2: string;
  fin_examen2: string;
  debut_examen3: string;
  fin_examen3: string;
}

// Dates en UTC pour eviter tout decalage lie au fuseau horaire ou a l'heure d'ete.
const date = (annee: number, mois: number, jour: number) => new Date(Date.UTC(annee, mois - 1, jour));
const ajouter = (d: Date, jours: number) => new Date(d.getTime() + jours * JOUR_MS);
const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Premier jour de la semaine `jourSemaine` (0 = dimanche) a partir de `d` (inclus). */
function jourSuivant(d: Date, jourSemaine: number) {
  return ajouter(d, (jourSemaine - d.getUTCDay() + 7) % 7);
}

/** Dernier jour de la semaine `jourSemaine` jusqu'a `d` (inclus). */
function jourPrecedent(d: Date, jourSemaine: number) {
  return ajouter(d, -((d.getUTCDay() - jourSemaine + 7) % 7));
}

export function calendrierParDefaut(annee: number): CalendrierScolaire {
  const debut = jourSuivant(date(annee, 10, 1), 1);
  const fin = date(annee + 1, 6, 30);

  const vacances1 = jourSuivant(date(annee, 12, 20), 6);
  const vacances2 = jourSuivant(date(annee + 1, 3, 25), 6);
  const finVacances1 = ajouter(vacances1, DUREE_VACANCES_JOURS);
  const finVacances2 = ajouter(vacances2, DUREE_VACANCES_JOURS);

  const vendrediFin = jourPrecedent(fin, 5);
  return {
    date_debut: iso(debut),
    debut_trimestre2: iso(ajouter(finVacances1, 1)),
    debut_trimestre3: iso(ajouter(finVacances2, 1)),
    date_fin: iso(fin),
    debut_vacances: iso(vacances1),
    fin_vacances: iso(finVacances1),
    debut_vacances2: iso(vacances2),
    fin_vacances2: iso(finVacances2),
    debut_examen1: iso(ajouter(vacances1, -5)),
    fin_examen1: iso(ajouter(vacances1, -1)),
    debut_examen2: iso(ajouter(vacances2, -5)),
    fin_examen2: iso(ajouter(vacances2, -1)),
    debut_examen3: iso(ajouter(vendrediFin, -4)),
    fin_examen3: iso(vendrediFin),
  };
}

/** Annee de debut d'un libelle "2026-2027" ; null si le libelle n'a pas ce format (ou n'est pas consecutif). */
export function anneeDuLibelle(libelle: string): number | null {
  const m = /^\s*(\d{4})\s*-\s*(\d{4})\s*$/.exec(libelle);
  return m && Number(m[2]) === Number(m[1]) + 1 ? Number(m[1]) : null;
}
