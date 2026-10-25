import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, Upload, FileSpreadsheet, ClipboardCheck } from "lucide-react";
import { PageCrud } from "../../composants/PageCrud";
import { BOUTON } from "../../composants/styles";
import { api, messageErreur } from "../../services/api";
import { messageErreurFichier, telechargerFichier } from "../../services/fichiers";
import { useAuth } from "../../hooks/useAuth";
import { useNotifications } from "../../composants/Notifications";
import type { Classe, Etudiant } from "../../types";

import { tr, FLECHE_RETOUR } from "../../i18n";

/** `classeId` : liste d'une classe, l'import inscrit les etudiants dans cette classe et l'export ne reprend qu'elle. */
function BarreImportExport({ onImporte, classeId }: { onImporte: () => void; classeId?: number }) {
  const parametreClasse = classeId ? `?classe=${classeId}` : "";
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
      const { data } = await api.post(`/etudiants/etudiants/importer/${parametreClasse}`, donnees, {
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
        onClick={() => telecharger(`/etudiants/etudiants/exporter/${parametreClasse}`, "etudiants.xlsx")}
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

/** Boutons d'impression du registre de presence mensuel de la classe (noms des eleves + colonnes des jours). */
function ModelesPresence({ classe }: { classe: Classe }) {
  const { notifierErreur } = useNotifications();

  async function telecharger(format: "pdf" | "xlsx") {
    try {
      await telechargerFichier("/presences/seances/modele-classe/", `registre_presence_${classe.nom}.${format}`, { classe: classe.id, fichier: format });
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  return (
    <>
      <button onClick={() => telecharger("pdf")} className={BOUTON} title={tr("Registre de presence mensuel de la classe, avec les noms des etudiants")}>
        <ClipboardCheck size={15} /> {tr("Modele de presence")} PDF
      </button>
      <button onClick={() => telecharger("xlsx")} className={BOUTON} title={tr("Registre de presence mensuel de la classe, avec les noms des etudiants")}>
        <ClipboardCheck size={15} /> {tr("Modele de presence")} Excel
      </button>
    </>
  );
}

function ListeEtudiants({ classe }: { classe?: Classe }) {
  const [cle, setCle] = useState(0);
  const { peut } = useAuth();
  return (
    <PageCrud<Etudiant>
      key={cle}
      titre={classe ? `${classe.nom} - ${classe.annee_scolaire_libelle}` : tr("Tous les etudiants")}
      url="/etudiants/etudiants/"
      cleLigne={(e) => e.id}
      parametresFiltre={classe ? { classe: classe.id } : undefined}
      valeursParDefaut={{ sexe: "M", actif: true, ...(classe ? { classe_inscription: classe.id } : {}) }}
      filtres={<BarreImportExport classeId={classe?.id} onImporte={() => setCle((c) => c + 1)} />}
      enteteExtra={classe && peut("presences") ? () => <ModelesPresence classe={classe} /> : undefined}
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

/** Tous les etudiants, y compris ceux qui ne sont inscrits dans aucune classe. */
export function PageEtudiants() {
  return <ListeEtudiants />;
}

/** Etudiants d'une classe : creation, modification, import et export se font ici, dans le contexte de la classe. */
export function PageEtudiantsClasse() {
  const { id } = useParams();
  const { notifierErreur } = useNotifications();
  const [classe, setClasse] = useState<Classe | null>(null);

  useEffect(() => {
    setClasse(null);
    api.get(`/referentiels/classes/${id}/`).then(({ data }) => setClasse(data)).catch((err) => notifierErreur(messageErreur(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return (
    <div>
      <Link
        to={classe ? `/etudiants?annee=${classe.annee_scolaire}` : "/etudiants"}
        className="mb-2 inline-flex items-center gap-1 text-sm text-entete hover:underline"
      >
        {FLECHE_RETOUR} {tr("Classes")}
      </Link>
      {classe ? <ListeEtudiants key={classe.id} classe={classe} /> : <p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>}
    </div>
  );
}
