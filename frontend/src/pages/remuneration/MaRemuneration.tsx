import { useNavigate } from "react-router-dom";
import { Eye, FileText } from "lucide-react";
import { useListe } from "../../hooks/useListe";
import { useNotifications } from "../../composants/Notifications";
import { TableauDonnees } from "../../composants/TableauDonnees";
import { Badge } from "../../composants/Badge";
import { formaterMontant, formaterMois, messageErreurFichier, telechargerFichier } from "../../services/fichiers";
import type { ReleveRemuneration } from "../../types";

const LIBELLES: Record<string, string> = { NON_PAYE: "Non paye", PARTIEL: "Paye partiellement", PAYE: "Paye" };

/** Espace du professeur : ses releves valides (heures, montants, paiements) et ses fiches de paiement. */
export function PageMaRemuneration() {
  const navigate = useNavigate();
  const { notifierErreur } = useNotifications();
  const { resultats, chargement, page, setPage, nombrePages } = useListe<ReleveRemuneration>("/remuneration/releves/");

  async function fiche(r: ReleveRemuneration) {
    try {
      await telechargerFichier(`/remuneration/releves/${r.id}/pdf/`, `fiche_paiement_${r.mois.slice(0, 7)}.pdf`);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold text-texte">Ma remuneration</h1>
      <p className="mb-3 text-sm text-texte-attenue">Releves mensuels valides par l&apos;administration, calcules a partir des heures reellement effectuees.</p>
      <TableauDonnees<ReleveRemuneration>
        colonnes={[
          { cle: "mois", titre: "Mois", rendu: (r) => <span className="capitalize">{formaterMois(r.mois)}</span> },
          { cle: "heures", titre: "Heures", alignerDroite: true, rendu: (r) => r.totaux.heures },
          { cle: "net", titre: "Net", alignerDroite: true, rendu: (r) => <b>{formaterMontant(r.totaux.net)}</b> },
          { cle: "paye", titre: "Deja paye", alignerDroite: true, rendu: (r) => formaterMontant(r.totaux.paye) },
          { cle: "solde", titre: "Solde", alignerDroite: true, rendu: (r) => formaterMontant(r.totaux.solde) },
          { cle: "statut", titre: "Paiement", rendu: (r) => <Badge statut={r.totaux.statut_paiement === "PAYE" ? "PRESENT" : r.totaux.statut_paiement === "PARTIEL" ? "RETARD" : "PLANIFIE"} />, },
          { cle: "libelle", titre: "", rendu: (r) => <span className="text-xs text-texte-attenue">{LIBELLES[r.totaux.statut_paiement]}</span> },
        ]}
        lignes={resultats}
        chargement={chargement}
        cleLigne={(r) => r.id}
        page={page}
        nombrePages={nombrePages}
        onChangerPage={setPage}
        videMessage="Aucun releve valide pour le moment."
        actions={(r) => (
          <div className="flex justify-end gap-2">
            <button title="Detail" className="text-texte-attenue hover:text-entete" onClick={() => navigate(`/remuneration/${r.id}`)}><Eye size={16} /></button>
            <button title="Fiche de paiement (PDF)" className="text-texte-attenue hover:text-entete" onClick={() => fiche(r)}><FileText size={16} /></button>
          </div>
        )}
      />
    </div>
  );
}
