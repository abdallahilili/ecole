const COULEURS: Record<string, string> = {
  BROUILLON: "bg-gray-100 text-gray-700",
  VALIDE: "bg-green-50 text-accent-vert",
  ANNULE: "bg-red-50 text-accent-rouge",
  ANNULEE: "bg-red-50 text-accent-rouge",
  EN_ATTENTE: "bg-amber-50 text-amber-700",
  EN_COURS: "bg-blue-50 text-accent-bleu",
  TERMINEE: "bg-indigo-50 text-indigo-700",
  LIVREE: "bg-green-50 text-accent-vert",
  OUVERTE: "bg-green-50 text-accent-vert",
  FERMEE: "bg-gray-100 text-gray-700",
  ACTIVE: "bg-green-50 text-accent-vert",
  TRANSFEREE: "bg-blue-50 text-accent-bleu",
  ABANDON: "bg-red-50 text-accent-rouge",
  DIPLOME: "bg-indigo-50 text-indigo-700",
  ACTIF: "bg-green-50 text-accent-vert",
  INACTIF: "bg-gray-100 text-gray-700",
  PRESENT: "bg-green-50 text-accent-vert",
  ABSENT: "bg-red-50 text-accent-rouge",
  RETARD: "bg-amber-50 text-amber-700",
  PLANIFIE: "bg-gray-100 text-gray-700",
  EFFECTUE: "bg-green-50 text-accent-vert",
  REMPLACE: "bg-blue-50 text-accent-bleu",
  ENVOYE: "bg-blue-50 text-accent-bleu",
  LIVRE: "bg-green-50 text-accent-vert",
  ECHEC: "bg-red-50 text-accent-rouge",
};
import { tr } from "../i18n";

const LIBELLES: Record<string, string> = {
  BROUILLON: tr("Brouillon"),
  VALIDE: tr("Valide"),
  ANNULE: tr("Annule"),
  ANNULEE: tr("Annulee"),
  EN_ATTENTE: tr("En attente"),
  EN_COURS: tr("En cours"),
  TERMINEE: tr("Terminee"),
  LIVREE: tr("Livree"),
  OUVERTE: tr("Ouverte"),
  FERMEE: tr("Fermee"),
  ACTIVE: tr("Active"),
  TRANSFEREE: tr("Transferee"),
  ABANDON: tr("Abandon"),
  DIPLOME: tr("Diplome"),
  ACTIF: tr("Actif"),
  INACTIF: tr("Inactif"),
  PRESENT: tr("Present"),
  ABSENT: tr("Absent"),
  RETARD: tr("Retard"),
  PLANIFIE: tr("Planifie"),
  EFFECTUE: tr("Effectue"),
  REMPLACE: tr("Remplace"),
  ENVOYE: tr("Envoye"),
  LIVRE: tr("Livre"),
  ECHEC: tr("Echec"),
};

export function Badge({ statut }: { statut: string }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${COULEURS[statut] ?? "bg-gray-100 text-gray-700"}`}>
      {LIBELLES[statut] ?? statut}
    </span>
  );
}
