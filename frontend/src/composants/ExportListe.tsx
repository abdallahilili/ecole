import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { Modale } from "./Modale";
import { useNotifications } from "./Notifications";
import { BOUTON, BOUTON_PRIMAIRE } from "./styles";
import { messageErreurFichier, telechargerFichier } from "../services/fichiers";

import { tr } from "../i18n";
type Cle = string | number;
type Portee = "tout" | "page" | "selection";
type Format = "xlsx" | "csv" | "pdf";

interface Props {
  ouverte: boolean;
  onFermer: () => void;
  /** URL de la liste (ex. "/etudiants/etudiants/") : l'export est servi par `<url>export/`. */
  url: string;
  titre: string;
  colonnes: { cle: string; titre: string }[];
  /** Parametres actuels de la liste (recherche, tri, filtres) : l'export les reprend. */
  parametres: Record<string, any>;
  total: number;
  idsPage: Cle[];
  selection: Set<Cle>;
}

/** Export Excel / CSV / PDF : resultat filtre complet, page courante ou lignes selectionnees,
 * avec choix des colonnes. L'export est calcule par le serveur (memes droits que la liste). */
export function ExportListe({ ouverte, onFermer, url, titre, colonnes, parametres, total, idsPage, selection }: Props) {
  const { notifierErreur, notifierSucces } = useNotifications();
  const [portee, setPortee] = useState<Portee>("tout");
  const [format, setFormat] = useState<Format>("pdf");
  const [choisies, setChoisies] = useState<string[]>([]);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    if (ouverte) {
      setChoisies(colonnes.map((c) => c.cle));
      setPortee(selection.size > 0 ? "selection" : "tout");
      setFormat("pdf");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ouverte]);

  const bascule = (cle: string) => setChoisies((c) => (c.includes(cle) ? c.filter((x) => x !== cle) : [...c, cle]));

  async function exporter() {
    setEnCours(true);
    try {
      const ids = portee === "page" ? idsPage : portee === "selection" ? [...selection] : [];
      const params: Record<string, any> = {
        ...parametres,
        fichier: format,
        titre,
        colonnes: JSON.stringify(colonnes.filter((c) => choisies.includes(c.cle))),
        ...(portee !== "tout" ? { ids: ids.join(",") } : {}),
      };
      await telechargerFichier(`${url}export/`, `export_${titre.toLowerCase().replace(/\s+/g, "_")}.${format}`, params);
      notifierSucces(tr("Export genere."));
      onFermer();
    } catch (err) {
      notifierErreur(await messageErreurFichier(err));
    } finally {
      setEnCours(false);
    }
  }

  const option = (valeur: Portee, libelle: string, desactive = false) => (
    <label className={`flex items-center gap-2 text-sm ${desactive ? "text-texte-attenue" : ""}`}>
      <input type="radio" name="portee" checked={portee === valeur} disabled={desactive} onChange={() => setPortee(valeur)} />
      {libelle}
    </label>
  );

  return (
    <Modale titre={tr("Exporter - {0}", titre)} ouverte={ouverte} onFermer={onFermer}>
      <div className="space-y-4">
        <div>
          <p className="mb-1 text-sm font-semibold text-texte">{tr("Lignes")}</p>
          <div className="space-y-1">
            {option("tout", tr("Tous les resultats filtres ({0})", total))}
            {option("page", tr("Page courante ({0})", idsPage.length), idsPage.length === 0)}
            {option("selection", tr("Lignes selectionnees ({0})", selection.size), selection.size === 0)}
          </div>
        </div>
        <div>
          <p className="mb-1 text-sm font-semibold text-texte">{tr("Format")}</p>
          <div className="flex gap-4">
            {(["xlsx", "csv", "pdf"] as Format[]).map((f) => (
              <label key={f} className="flex items-center gap-1.5 text-sm">
                <input type="radio" name="format" checked={format === f} onChange={() => setFormat(f)} />
                {f === "xlsx" ? tr("Excel (.xlsx)") : f === "csv" ? "CSV" : "PDF"}
              </label>
            ))}
          </div>
        </div>
        <div>
          <p className="mb-1 flex items-center justify-between text-sm font-semibold text-texte">
            {tr("Colonnes")}
            <button className="text-xs font-normal text-entete hover:underline"
                    onClick={() => setChoisies(choisies.length === colonnes.length ? [] : colonnes.map((c) => c.cle))}>
              {choisies.length === colonnes.length ? tr("Tout decocher") : tr("Tout cocher")}
            </button>
          </p>
          <div className="grid max-h-40 grid-cols-2 gap-x-4 gap-y-1 overflow-y-auto">
            {colonnes.map((c) => (
              <label key={c.cle} className="flex items-center gap-1.5 text-sm">
                <input type="checkbox" checked={choisies.includes(c.cle)} onChange={() => bascule(c.cle)} />
                <span className="truncate">{c.titre || c.cle}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button className={BOUTON} onClick={onFermer}>{tr("Annuler")}</button>
          <button className={BOUTON_PRIMAIRE} disabled={enCours || choisies.length === 0} onClick={exporter}>
            <Download size={15} /> {tr("Exporter")}
          </button>
        </div>
      </div>
    </Modale>
  );
}
