/** Jours de la semaine (0 = lundi, comme `date.weekday()` cote backend). */
export const JOURS = [
  { value: 0, label: "Lundi" },
  { value: 1, label: "Mardi" },
  { value: 2, label: "Mercredi" },
  { value: 3, label: "Jeudi" },
  { value: 4, label: "Vendredi" },
  { value: 5, label: "Samedi" },
  { value: 6, label: "Dimanche" },
];

export const NOM_JOUR: Record<number, string> = Object.fromEntries(JOURS.map((j) => [j.value, j.label]));
