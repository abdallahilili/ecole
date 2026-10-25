import { useRef, useState } from "react";
import { Download, Upload, FileSpreadsheet } from "lucide-react";
import { PageCrud } from "../../composants/PageCrud";
import { api, messageErreur } from "../../services/api";
import { useNotifications } from "../../composants/Notifications";
import type { Etudiant } from "../../types";

import { tr } from "../../i18n";
function BarreImportExport({ onImporte }: { onImporte: () => void }) {
  const { notifierSucces, notifierErreur } = useNotifications();
  const entreeFichier = useRef<HTMLInputElement>(null);
  const [enCours, setEnCours] = useState(false);

  async function telecharger(url: string, nomFichier: string) {
    try {
      const reponse = await api.get(url, { responseType: "blob" });
      const lien = document.createElement("a");
      lien.href = URL.createObjectURL(reponse.data);
      lien.download = nomFichier;
      lien.click();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  async function importer(fichier: File) {
    setEnCours(true);
    try {
      const donnees = new FormData();
      donnees.append("fichier", fichier);
      const { data } = await api.post("/etudiants/etudiants/importer/", donnees, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      notifierSucces(data.detail);
      onImporte();
    } catch (err: any) {
      const corps = err?.response?.data;
      if (corps?.erreurs?.length) {
        const resume = corps.erreurs.slice(0, 5).map((e: any) => tr("Ligne {0} : {1}", e.ligne, e.erreurs.join(", "))).join(" | ");
        notifierErreur(`${corps.detail} ${resume}`);
      } else {
        notifierErreur(messageErreur(err));
      }
    } finally {
      setEnCours(false);
      if (entreeFichier.current) entreeFichier.current.value = "";
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => telecharger("/etudiants/etudiants/modele-import/", "modele_import_etudiants.xlsx")}
        className="flex items-center gap-1.5 rounded border border-bordure px-3 py-1.5 text-sm hover:bg-fond"
      >
        <FileSpreadsheet size={15} /> {tr("Modele")}
      </button>
      <button
        onClick={() => telecharger("/etudiants/etudiants/exporter/", "etudiants.xlsx")}
        className="flex items-center gap-1.5 rounded border border-bordure px-3 py-1.5 text-sm hover:bg-fond"
      >
        <Download size={15} /> {tr("Exporter")}
      </button>
      <button
        disabled={enCours}
        onClick={() => entreeFichier.current?.click()}
        className="flex items-center gap-1.5 rounded border border-bordure px-3 py-1.5 text-sm hover:bg-fond disabled:opacity-50"
      >
        <Upload size={15} /> {enCours ? tr("Import en cours...") : tr("Importer")}
      </button>
      <input
        ref={entreeFichier}
        type="file"
        accept=".xlsx"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && importer(e.target.files[0])}
      />
    </div>
  );
}

export function PageEtudiants() {
  const [cle, setCle] = useState(0);
  return (
    <PageCrud<Etudiant>
      key={cle}
      titre={tr("Etudiants")}
      url="/etudiants/etudiants/"
      cleLigne={(e) => e.id}
      valeursParDefaut={{ sexe: "M", actif: true }}
      filtres={<BarreImportExport onImporte={() => setCle((c) => c + 1)} />}
      colonnes={[
        { cle: "matricule", titre: tr("Matricule") },
        { cle: "nom_complet", titre: tr("Nom complet") },
        { cle: "sexe", titre: tr("Sexe") },
        { cle: "date_naissance", titre: tr("Naissance") },
        { cle: "telephone_principal", titre: tr("Telephone") },
        {
          cle: "actif", titre: tr("Statut"),
          rendu: (e) => (
            <span className={e.actif ? "text-accent-vert" : "text-accent-rouge"}>
              {e.actif ? tr("Actif") : tr("Inactif")}
            </span>
          ),
        },
      ]}
      champs={[
        { nom: "matricule", label: tr("Matricule"), requis: true },
        { nom: "nom", label: tr("Nom"), requis: true },
        { nom: "prenom", label: tr("Prenom"), requis: true },
        { nom: "sexe", label: tr("Sexe"), type: "select", optionsStatiques: [{ value: "M", label: tr("Masculin") }, { value: "F", label: tr("Feminin") }] },
        { nom: "date_naissance", label: tr("Date de naissance"), type: "date" },
        { nom: "lieu_naissance", label: tr("Lieu de naissance") },
        { nom: "numero_national", label: tr("Numero national") },
        { nom: "adresse", label: tr("Adresse"), colonnePleine: true },
        { nom: "nom_pere", label: tr("Nom du pere") },
        { nom: "telephone_pere", label: tr("Telephone du pere") },
        { nom: "nom_mere", label: tr("Nom de la mere") },
        { nom: "telephone_mere", label: tr("Telephone de la mere") },
        { nom: "nom_tuteur", label: tr("Nom du tuteur") },
        { nom: "telephone_tuteur", label: tr("Telephone du tuteur") },
        { nom: "telephone_principal", label: tr("Telephone principal (notifications)"), colonnePleine: true },
        { nom: "actif", label: tr("Actif"), type: "checkbox" },
      ]}
    />
  );
}
