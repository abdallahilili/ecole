
import { tr } from "../i18n";/** Jours de la semaine (0 = lundi, comme `date.weekday()` cote backend). */
export const JOURS = [
  { value: 0, label: tr("Lundi") },
  { value: 1, label: tr("Mardi") },
  { value: 2, label: tr("Mercredi") },
  { value: 3, label: tr("Jeudi") },
  { value: 4, label: tr("Vendredi") },
  { value: 5, label: tr("Samedi") },
  { value: 6, label: tr("Dimanche") },
];

export const NOM_JOUR: Record<number, string> = Object.fromEntries(JOURS.map((j) => [j.value, j.label]));
