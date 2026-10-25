import { useState } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";
import { PageCrud } from "../../composants/PageCrud";
import { api, messageErreur } from "../../services/api";
import { useNotifications } from "../../composants/Notifications";
import type { PaiementScolarite, SituationScolarite } from "../../types";

import { tr, tx } from "../../i18n";
import { UNITE_MONETAIRE } from "../../services/fichiers";
function PanneauSituation() {
  const { notifierErreur } = useNotifications();
  const [idInscription, setIdInscription] = useState("");
  const [situation, setSituation] = useState<SituationScolarite | null>(null);

  async function rechercher() {
    if (!idInscription) return;
    try {
      const { data } = await api.get<SituationScolarite>(`/scolarite/paiements/situation/${idInscription}/`);
      setSituation(data);
    } catch (err) {
      setSituation(null);
      notifierErreur(messageErreur(err));
    }
  }

  return (
    <div className="mb-4 rounded-md border border-bordure bg-fond-carte p-4 shadow-carte">
      <h2 className="mb-2 text-sm font-semibold text-texte">{tr("Situation de scolarite d'un eleve (par N° d'inscription)")}</h2>
      <div className="flex items-center gap-2">
        <input
          value={idInscription}
          onChange={(e) => setIdInscription(e.target.value)}
          placeholder={tr("N° d'inscription")}
          className="w-48 rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
        />
        <button onClick={rechercher} className="flex items-center gap-1.5 rounded bg-entete px-3 py-1.5 text-sm text-white hover:bg-entete-fonce">
          <Search size={14} /> {tr("Verifier")}
        </button>
      </div>
      {situation && (
        <div className="mt-3 text-sm text-texte">
          <p><strong>{situation.etudiant}</strong> ({situation.matricule}) - {situation.classe} - {situation.annee_scolaire}</p>
          <p className="mt-1">{tx("Frais d'inscription : {0}", situation.frais_inscription_paye
              ? <span className="text-accent-vert">{tr("paye")}</span>
              : <span className="text-accent-rouge">{tr("non paye")}</span>)}</p>
          {situation.montant_mensuel && (
            <p className="mt-1">{tx("Mensualite : {0}", <strong>{situation.montant_mensuel} {UNITE_MONETAIRE}</strong>)}</p>
          )}
          <p className="mt-1">{tr("Mois payes ({0}/{1}) : {2}", situation.mois_payes.length, situation.nombre_mois ?? "-", situation.mois_payes.join(", ") || tr("aucun"))}</p>
          <p className="mt-1">{tx("Total verse : {0}", <strong>{situation.total_paye}</strong>)}</p>
        </div>
      )}
    </div>
  );
}

export function PagePaiementsScolarite() {
  return (
    <div>
      <div className="mb-3">
        <Link to="/scolarite/grilles-frais" className="text-sm text-entete hover:underline">
          {tr("Gerer les grilles de frais par niveau →")}
        </Link>
      </div>
      <PanneauSituation />
      <PageCrud<PaiementScolarite>
        titre={tr("Paiements de scolarite")}
        url="/scolarite/paiements/"
        cleLigne={(p) => p.id}
        champRecherche={false}
        peutModifier={false}
        valeursParDefaut={{ type_frais: "MENSUALITE", mode_paiement: "ESPECES" }}
        titreForm={() => tr("Nouveau paiement")}
        colonnes={[
          { cle: "reference", titre: tr("Reference") },
          { cle: "etudiant_matricule", titre: tr("Matricule") },
          { cle: "etudiant_nom", titre: tr("Etudiant") },
          { cle: "classe_nom", titre: tr("Classe") },
          { cle: "type_frais", titre: tr("Type") },
          { cle: "mois_concerne", titre: tr("Mois") },
          { cle: "montant", titre: tr("Montant"), alignerDroite: true },
          { cle: "date_paiement", titre: tr("Date") },
        ]}
        champs={[
          {
            nom: "inscription", label: tr("Inscription"), type: "select", requis: true,
            optionsUrl: "/etudiants/inscriptions/", optionLabel: (i) => `${i.etudiant_nom} (${i.etudiant_matricule}) - ${i.classe_nom}`,
          },
          {
            nom: "type_frais", label: tr("Type de frais"), type: "select", requis: true, optionsStatiques: [
              { value: "INSCRIPTION", label: tr("Frais d'inscription") },
              { value: "MENSUALITE", label: tr("Mensualite") },
              { value: "AUTRE", label: tr("Autre frais") },
            ],
          },
          { nom: "mois_concerne", label: tr("Mois concerne (si mensualite)"), type: "mois" },
          { nom: "montant", label: tr("Montant"), type: "decimal", requis: true },
          {
            nom: "mode_paiement", label: tr("Mode de paiement"), type: "select", optionsStatiques: [
              { value: "ESPECES", label: tr("Especes") },
              { value: "VIREMENT", label: tr("Virement") },
              { value: "CHEQUE", label: tr("Cheque") },
              { value: "MOBILE", label: tr("Paiement mobile") },
            ],
          },
          { nom: "date_paiement", label: tr("Date de paiement"), type: "date", requis: true },
          { nom: "observations", label: tr("Observations"), type: "textarea", colonnePleine: true },
        ]}
      />
    </div>
  );
}
