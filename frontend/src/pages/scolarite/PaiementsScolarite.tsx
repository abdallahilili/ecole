import { useState } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";
import { PageCrud } from "../../composants/PageCrud";
import { api, messageErreur } from "../../services/api";
import { useNotifications } from "../../composants/Notifications";
import type { PaiementScolarite, SituationScolarite } from "../../types";

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
      <h2 className="mb-2 text-sm font-semibold text-texte">Situation de scolarite d'un eleve (par N° d'inscription)</h2>
      <div className="flex items-center gap-2">
        <input
          value={idInscription}
          onChange={(e) => setIdInscription(e.target.value)}
          placeholder="N° d'inscription"
          className="w-48 rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
        />
        <button onClick={rechercher} className="flex items-center gap-1.5 rounded bg-entete px-3 py-1.5 text-sm text-white hover:bg-entete-fonce">
          <Search size={14} /> Verifier
        </button>
      </div>
      {situation && (
        <div className="mt-3 text-sm text-texte">
          <p><strong>{situation.etudiant}</strong> ({situation.matricule}) - {situation.classe} - {situation.annee_scolaire}</p>
          <p className="mt-1">
            Frais d'inscription : {situation.frais_inscription_paye
              ? <span className="text-accent-vert">paye</span>
              : <span className="text-accent-rouge">non paye</span>}
          </p>
          {situation.montant_mensuel && (
            <p className="mt-1">Mensualite : <strong>{situation.montant_mensuel} UM</strong></p>
          )}
          <p className="mt-1">Mois payes ({situation.mois_payes.length}/{situation.nombre_mois ?? "-"}) : {situation.mois_payes.join(", ") || "aucun"}</p>
          <p className="mt-1">Total verse : <strong>{situation.total_paye}</strong></p>
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
          Gerer les grilles de frais par niveau &rarr;
        </Link>
      </div>
      <PanneauSituation />
      <PageCrud<PaiementScolarite>
        titre="Paiements de scolarite"
        url="/scolarite/paiements/"
        cleLigne={(p) => p.id}
        champRecherche={false}
        peutModifier={false}
        valeursParDefaut={{ type_frais: "MENSUALITE", mode_paiement: "ESPECES" }}
        titreForm={() => "Nouveau paiement"}
        colonnes={[
          { cle: "reference", titre: "Reference" },
          { cle: "etudiant_matricule", titre: "Matricule" },
          { cle: "etudiant_nom", titre: "Etudiant" },
          { cle: "classe_nom", titre: "Classe" },
          { cle: "type_frais", titre: "Type" },
          { cle: "mois_concerne", titre: "Mois" },
          { cle: "montant", titre: "Montant", alignerDroite: true },
          { cle: "date_paiement", titre: "Date" },
        ]}
        champs={[
          {
            nom: "inscription", label: "Inscription", type: "select", requis: true,
            optionsUrl: "/etudiants/inscriptions/", optionLabel: (i) => `${i.etudiant_nom} (${i.etudiant_matricule}) - ${i.classe_nom}`,
          },
          {
            nom: "type_frais", label: "Type de frais", type: "select", requis: true, optionsStatiques: [
              { value: "INSCRIPTION", label: "Frais d'inscription" },
              { value: "MENSUALITE", label: "Mensualite" },
              { value: "AUTRE", label: "Autre frais" },
            ],
          },
          { nom: "mois_concerne", label: "Mois concerne (si mensualite)", type: "mois" },
          { nom: "montant", label: "Montant", type: "decimal", requis: true },
          {
            nom: "mode_paiement", label: "Mode de paiement", type: "select", optionsStatiques: [
              { value: "ESPECES", label: "Especes" },
              { value: "VIREMENT", label: "Virement" },
              { value: "CHEQUE", label: "Cheque" },
              { value: "MOBILE", label: "Paiement mobile" },
            ],
          },
          { nom: "date_paiement", label: "Date de paiement", type: "date", requis: true },
          { nom: "observations", label: "Observations", type: "textarea", colonnePleine: true },
        ]}
      />
    </div>
  );
}
