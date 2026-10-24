import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { FileSpreadsheet, Upload } from "lucide-react";
import { api, messageErreur } from "../services/api";
import { messageErreurFichier, telechargerFichier } from "../services/fichiers";
import { useNotifications } from "./Notifications";
import { Modale } from "./Modale";
import { BOUTON, BOUTON_PRIMAIRE, CHAMP } from "./styles";

export interface LigneApercu {
  ligne: number;
  matricule: string;
  nom_complet: string;
  etat: "NOUVEAU" | "IDENTIQUE" | "MODIFIE" | "ERREUR" | "VIDE";
  anomalies: string[];
}

export interface ApercuGenerique<L extends LigneApercu = LigneApercu> {
  anomalies_fichier: string[];
  lignes: L[];
  non_renseignes: string[];
  blocages: string[];
  resume: Record<string, number>;
}

interface Props<L extends LigneApercu> {
  titre: string;
  consignes: ReactNode;
  ouverte: boolean;
  onFermer: () => void;
  /** Modele Excel a telecharger (GET) et ses parametres. */
  urlModele: string;
  nomModele: string;
  /** Point d'import (POST multipart) ; `champs` = parametres du cours/de l'evaluation. */
  urlImport: string;
  champs?: Record<string, string>;
  parametresModele?: Record<string, string>;
  /** Colonne "valeur" de l'apercu (statut, note...). */
  titreValeur: string;
  rendreValeur: (ligne: L) => ReactNode;
  /** Un motif est obligatoire (ex. resultats deja valides). */
  motifRequis?: boolean;
  onImporte: (donnees: any) => void;
}

const COULEUR_ETAT: Record<string, string> = {
  NOUVEAU: "text-accent-vert", IDENTIQUE: "text-texte-attenue", MODIFIE: "text-amber-700",
  ERREUR: "text-accent-rouge", VIDE: "text-texte-attenue",
};

/** Import Excel en 3 temps : modele -> apercu (rien n'est ecrit) -> confirmation.
 * Une valeur deja saisie n'est remplacee que sur demande explicite. */
export function ImportExcel<L extends LigneApercu>({
  titre, consignes, ouverte, onFermer, urlModele, nomModele, urlImport, champs = {}, parametresModele,
  titreValeur, rendreValeur, motifRequis, onImporte,
}: Props<L>) {
  const { notifierSucces, notifierErreur } = useNotifications();
  const entree = useRef<HTMLInputElement>(null);
  const [fichier, setFichier] = useState<File | null>(null);
  const [apercu, setApercu] = useState<ApercuGenerique<L> | null>(null);
  const [remplacer, setRemplacer] = useState(false);
  const [motif, setMotif] = useState("");
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    if (!ouverte) {
      setFichier(null);
      setApercu(null);
      setRemplacer(false);
      setMotif("");
    }
  }, [ouverte]);

  function formulaire(confirmer: boolean, courant: File) {
    const donnees = new FormData();
    Object.entries(champs).forEach(([cle, valeur]) => valeur && donnees.append(cle, valeur));
    donnees.append("fichier", courant);
    if (remplacer) donnees.append("remplacer", "true");
    if (motif.trim()) donnees.append("motif", motif.trim());
    if (confirmer) donnees.append("confirmer", "true");
    return donnees;
  }

  async function analyser(courant: File | null = fichier) {
    if (!courant) return;
    setEnCours(true);
    try {
      const { data } = await api.post(urlImport, formulaire(false, courant), { headers: { "Content-Type": "multipart/form-data" } });
      setApercu(data);
    } catch (err) {
      setApercu(null);
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  // Changer le remplacement ou le motif recalcule les blocages cote serveur
  // (motif : apres une courte pause, pour ne pas analyser a chaque frappe).
  useEffect(() => {
    if (fichier && apercu) analyser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remplacer]);

  useEffect(() => {
    if (!fichier || !apercu || !motifRequis) return;
    const minuteur = setTimeout(() => analyser(), 500);
    return () => clearTimeout(minuteur);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [motif]);

  async function confirmer() {
    if (!fichier) return;
    setEnCours(true);
    try {
      const { data } = await api.post(urlImport, formulaire(true, fichier), { headers: { "Content-Type": "multipart/form-data" } });
      notifierSucces(data.detail);
      onImporte(data);
      onFermer();
    } catch (err: any) {
      const corps = err?.response?.data;
      if (corps?.lignes) setApercu(corps);
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  async function telechargerModele() {
    try {
      await telechargerFichier(urlModele, nomModele, parametresModele ?? champs);
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    }
  }

  const blocages = apercu?.blocages ?? [];

  return (
    <Modale titre={titre} ouverte={ouverte} onFermer={onFermer} largeur="max-w-4xl">
      <div className="mb-3 text-sm text-texte-attenue">{consignes}</div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button type="button" onClick={telechargerModele} className={BOUTON}>
          <FileSpreadsheet size={15} /> Telecharger le modele
        </button>
        <button type="button" onClick={() => entree.current?.click()} className={BOUTON}>
          <Upload size={15} /> {fichier ? fichier.name : "Choisir le fichier rempli"}
        </button>
        <input
          ref={entree}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(e) => {
            const choisi = e.target.files?.[0] ?? null;
            setFichier(choisi);
            setApercu(null);
            if (choisi) analyser(choisi);
          }}
        />
      </div>

      {motifRequis && (
        <div className="mb-3">
          <input className={`${CHAMP} w-full`} placeholder="Motif de la correction (resultats valides)" value={motif}
                 onChange={(e) => setMotif(e.target.value)} />
        </div>
      )}

      {enCours && <p className="text-sm text-texte-attenue">Analyse en cours...</p>}

      {apercu && (
        <div>
          <div className="mb-2 flex flex-wrap gap-4 text-sm">
            <span className="text-accent-vert">{apercu.resume.nouveaux} nouveau(x)</span>
            <span className="text-texte-attenue">{apercu.resume.identiques} identique(s)</span>
            <span className="text-amber-700">{apercu.resume.modifies} a remplacer</span>
            <span className="text-accent-rouge">{apercu.resume.erreurs} erreur(s)</span>
          </div>

          {blocages.length > 0 && (
            <ul className="mb-3 list-disc rounded border border-accent-rouge bg-red-50 py-2 pl-7 pr-3 text-sm text-accent-rouge">
              {blocages.map((b) => <li key={b}>{b}</li>)}
            </ul>
          )}

          {apercu.resume.modifies > 0 && (
            <label className="mb-3 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={remplacer} onChange={(e) => setRemplacer(e.target.checked)} />
              Remplacer les valeurs deja saisies ({apercu.resume.modifies}) par celles du fichier
            </label>
          )}

          <div className="max-h-72 overflow-auto rounded border border-bordure">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-fond-barre text-left text-texte-attenue">
                  <th className="px-2 py-1.5">Ligne</th>
                  <th className="px-2 py-1.5">Matricule</th>
                  <th className="px-2 py-1.5">Nom</th>
                  <th className="px-2 py-1.5">{titreValeur}</th>
                  <th className="px-2 py-1.5">Etat</th>
                  <th className="px-2 py-1.5">Anomalies</th>
                </tr>
              </thead>
              <tbody>
                {apercu.lignes.map((l) => (
                  <tr key={l.ligne} className="border-t border-bordure">
                    <td className="px-2 py-1.5">{l.ligne}</td>
                    <td className="px-2 py-1.5">{l.matricule}</td>
                    <td className="px-2 py-1.5">{l.nom_complet}</td>
                    <td className="px-2 py-1.5">{rendreValeur(l)}</td>
                    <td className={`px-2 py-1.5 font-medium ${COULEUR_ETAT[l.etat]}`}>{l.etat}</td>
                    <td className="px-2 py-1.5 text-accent-rouge">{l.anomalies.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {apercu.non_renseignes.length > 0 && (
            <p className="mt-2 text-xs text-texte-attenue">
              Eleves absents du fichier ou sans valeur : {apercu.non_renseignes.join(", ")}.
            </p>
          )}
        </div>
      )}

      <div className="mt-4 flex justify-end gap-2">
        <button type="button" onClick={onFermer} className={BOUTON}>Annuler</button>
        <button type="button" disabled={!apercu || blocages.length > 0 || enCours} onClick={confirmer} className={BOUTON_PRIMAIRE}>
          Confirmer l&apos;import
        </button>
      </div>
    </Modale>
  );
}
