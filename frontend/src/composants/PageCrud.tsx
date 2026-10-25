import { Fragment, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus, Pencil, Trash2, Search, Download } from "lucide-react";
import { api, messageErreur } from "../services/api";
import { useListeAvancee, useOptions } from "../hooks/useListe";
import { useNotifications } from "./Notifications";
import { useConfirmation } from "./Confirmation";
import { Modale } from "./Modale";
import { ExportListe } from "./ExportListe";
import { TableauDonnees } from "./TableauDonnees";
import type { Colonne } from "./TableauDonnees";

import { tr } from "../i18n";
export interface OptionChamp { value: string | number; label: string }

export interface ChampFormulaire {
  nom: string;
  label: string;
  type?: "texte" | "nombre" | "decimal" | "select" | "checkbox" | "textarea" | "email" | "date" | "mois" | "heure" | "motdepasse";
  requis?: boolean;
  optionsUrl?: string;
  optionsStatiques?: OptionChamp[];
  optionLabel?: (item: any) => string;
  placeholder?: string;
  colonnePleine?: boolean;
  /** Sens d'ecriture du champ (ex. "rtl" pour un nom saisi en arabe). */
  direction?: "rtl" | "ltr";
  /** Titre de groupe affiche au-dessus de ce champ (debut d'une section du formulaire). */
  section?: string;
}

interface Props<T> {
  titre: string;
  url: string;
  colonnes: Colonne<T>[];
  champs: ChampFormulaire[];
  cleLigne: (ligne: T) => string | number;
  peutCreer?: boolean;
  peutModifier?: boolean;
  peutSupprimer?: boolean;
  filtres?: React.ReactNode;
  parametresFiltre?: Record<string, any>;
  valeursParDefaut?: Record<string, any>;
  champRecherche?: boolean;
  titreForm?: (modif: boolean) => string;
  /** Boutons supplementaires dans l'en-tete ; recoit `recharger` pour rafraichir la liste. */
  enteteExtra?: (recharger: () => void) => React.ReactNode;
  /** Appele a chaque saisie ; les valeurs renvoyees sont fusionnees dans le formulaire (champs calcules). */
  surChangement?: (nom: string, valeur: any, valeurs: Record<string, any>) => Record<string, any> | void;
  largeurForm?: string;
  /** Remplace le message de confirmation de suppression (ex. quand "supprimer" archive). */
  messageSuppression?: string;
}

function ChampEntree({ champ, valeur, onChange }: { champ: ChampFormulaire; valeur: any; onChange: (v: any) => void }) {
  const options = useOptions<any>(champ.optionsUrl ?? "", !!champ.optionsUrl);
  const listeOptions = champ.optionsStatiques ?? options.map((o) => ({
    value: o.id, label: champ.optionLabel ? champ.optionLabel(o) : (o.nom_affiche ?? o.nom),
  }));

  if (champ.type === "select") {
    return (
      <select
        className="w-full rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
        value={valeur ?? ""}
        onChange={(e) => onChange(e.target.value)}
        required={champ.requis}
      >
        <option value="">{tr("-- Selectionner --")}</option>
        {listeOptions.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    );
  }
  if (champ.type === "checkbox") {
    return (
      <input type="checkbox" checked={!!valeur} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4" />
    );
  }
  if (champ.type === "textarea") {
    return (
      <textarea
        className="w-full rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
        value={valeur ?? ""}
        onChange={(e) => onChange(e.target.value)}
        required={champ.requis}
      />
    );
  }
  if (champ.type === "mois") {
    // Selecteur de mois : la valeur envoyee est toujours le 1er jour du mois (YYYY-MM-01).
    return (
      <input
        type="month"
        className="w-full rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
        value={valeur ? String(valeur).slice(0, 7) : ""}
        onChange={(e) => onChange(e.target.value ? `${e.target.value}-01` : "")}
        required={champ.requis}
      />
    );
  }
  return (
    <input
      type={
        champ.type === "nombre" || champ.type === "decimal" ? "number"
          : champ.type === "email" ? "email"
          : champ.type === "date" ? "date"
          : champ.type === "heure" ? "time"
          : champ.type === "motdepasse" ? "password"
          : "text"
      }
      autoComplete={champ.type === "motdepasse" ? "new-password" : undefined}
      step={champ.type === "decimal" ? "0.01" : undefined}
      dir={champ.direction}
      className="w-full rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
      value={valeur ?? ""}
      placeholder={champ.placeholder}
      onChange={(e) => onChange(e.target.value)}
      required={champ.requis}
    />
  );
}

export function PageCrud<T extends Record<string, any>>({
  titre, url, colonnes, champs, cleLigne,
  peutCreer = true, peutModifier = true, peutSupprimer = true,
  filtres, parametresFiltre = {}, valeursParDefaut = {}, champRecherche = true,
  titreForm, enteteExtra, surChangement, largeurForm, messageSuppression,
}: Props<T>) {
  const {
    resultats, chargement, page, setPage, nombrePages, total, recharger, parametres,
    recherche, setRecherche, selection, setSelection, proprietesTableau,
  } = useListeAvancee<T>(url, parametresFiltre);
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();
  const [exportOuvert, setExportOuvert] = useState(false);

  // La recherche globale du haut de page ouvre la liste avec le terme deja saisi (?q=...).
  const [parametresUrl] = useSearchParams();
  const termeUrl = parametresUrl.get("q") ?? "";
  useEffect(() => { if (termeUrl && champRecherche) setRecherche(termeUrl); }, [termeUrl, champRecherche, setRecherche]);

  async function supprimerSelection() {
    const confirme = await demanderConfirmation({
      titre: tr("Supprimer la selection"),
      message: messageSuppression
        ? tr("{0} ({1} element(s) selectionne(s))", messageSuppression, selection.size)
        : tr("Supprimer {0} element(s) ? Si l'un d'eux ne peut pas etre supprime, aucun ne l'est.", selection.size),
    });
    if (!confirme) return;
    try {
      const { data } = await api.post(`${url}supprimer-multiple/`, { ids: [...selection].map(Number) });
      notifierSucces(tr("{0} element(s) supprime(s).", data.supprimes));
      setSelection(new Set());
      recharger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  const [modaleOuverte, setModaleOuverte] = useState(false);
  const [enModification, setEnModification] = useState<T | null>(null);
  const [valeursForm, setValeursForm] = useState<Record<string, any>>({});
  const [envoiEnCours, setEnvoiEnCours] = useState(false);

  function ouvrirCreation() {
    setEnModification(null);
    setValeursForm({ ...valeursParDefaut });
    setModaleOuverte(true);
  }

  function ouvrirModification(ligne: T) {
    setEnModification(ligne);
    setValeursForm({ ...ligne });
    setModaleOuverte(true);
  }

  function modifierChamp(nom: string, valeur: any) {
    setValeursForm((s) => {
      const suivant = { ...s, [nom]: valeur };
      return { ...suivant, ...surChangement?.(nom, valeur, suivant) };
    });
  }

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setEnvoiEnCours(true);
    try {
      if (enModification) {
        await api.patch(`${url}${cleLigne(enModification)}/`, valeursForm);
        notifierSucces(tr("Modification enregistree."));
      } else {
        await api.post(url, valeursForm);
        notifierSucces(tr("Creation effectuee."));
      }
      setModaleOuverte(false);
      recharger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnvoiEnCours(false);
    }
  }

  async function supprimer(ligne: T) {
    const confirme = await demanderConfirmation({
      titre: tr("Confirmer la suppression"),
      message: messageSuppression ?? tr("Cette action est definitive. Voulez-vous continuer ?"),
    });
    if (!confirme) return;
    try {
      await api.delete(`${url}${cleLigne(ligne)}/`);
      notifierSucces(tr("Suppression effectuee."));
      recharger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-texte">{titre}</h1>
        <div className="flex items-center gap-2">
          {enteteExtra?.(recharger)}
          {peutCreer && (
            <button
              onClick={ouvrirCreation}
              className="flex items-center gap-1.5 rounded bg-entete px-3 py-1.5 text-sm font-medium text-white hover:bg-entete-fonce"
            >
              <Plus size={16} /> {tr("Nouveau")}
            </button>
          )}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        {champRecherche && (
          <div className="relative">
            <Search size={15} className="absolute start-2.5 top-2.5 text-texte-attenue" />
            <input
              value={recherche}
              onChange={(e) => setRecherche(e.target.value)}
              placeholder={tr("Rechercher...")}
              className="rounded border border-bordure py-1.5 ps-8 pe-3 text-sm focus:border-entete focus:outline-none"
            />
          </div>
        )}
        {filtres}
      </div>

      <TableauDonnees
        {...proprietesTableau}
        stockage={url}
        barreOutils={(
          <>
            {peutSupprimer && selection.size > 0 && (
              <button
                onClick={supprimerSelection}
                className="flex items-center gap-1 rounded border border-accent-rouge px-2 py-1 text-xs text-accent-rouge hover:bg-red-50"
              >
                <Trash2 size={13} /> {tr("Supprimer la selection (")}{selection.size})
              </button>
            )}
            <button
              onClick={() => setExportOuvert(true)}
              className="flex items-center gap-1 rounded border border-bordure px-2 py-1 text-xs hover:bg-fond"
              title={tr("Exporter en Excel, CSV ou PDF")}
            >
              <Download size={13} /> {tr("Exporter")}
            </button>
          </>
        )}
        colonnes={colonnes}
        lignes={resultats}
        chargement={chargement}
        cleLigne={cleLigne}
        page={page}
        nombrePages={nombrePages}
        onChangerPage={setPage}
        actions={
          peutModifier || peutSupprimer
            ? (ligne) => (
                <div className="flex justify-end gap-2">
                  {peutModifier && (
                    <button onClick={() => ouvrirModification(ligne)} className="text-texte-attenue hover:text-entete">
                      <Pencil size={15} />
                    </button>
                  )}
                  {peutSupprimer && (
                    <button onClick={() => supprimer(ligne)} className="text-texte-attenue hover:text-accent-rouge">
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
              )
            : undefined
        }
      />

      <ExportListe
        ouverte={exportOuvert}
        onFermer={() => setExportOuvert(false)}
        url={url}
        titre={titre}
        colonnes={colonnes.map((c) => ({ cle: c.cle, titre: c.titre }))}
        parametres={parametres}
        total={total}
        idsPage={resultats.map(cleLigne)}
        selection={selection}
      />

      <Modale
        titre={titreForm ? titreForm(!!enModification) : enModification ? tr("Modifier") : tr("Nouveau")}
        ouverte={modaleOuverte}
        onFermer={() => setModaleOuverte(false)}
        largeur={largeurForm}
      >
        <form onSubmit={soumettre} className="grid grid-cols-2 gap-3">
          {champs.map((champ) => (
            <Fragment key={champ.nom}>
              {champ.section && (
                <h3 className="col-span-2 mt-2 border-b border-bordure pb-1 text-sm font-semibold text-entete">
                  {champ.section}
                </h3>
              )}
              <div className={champ.colonnePleine ? "col-span-2" : ""}>
                <label className="mb-1 block text-sm font-medium text-texte">
                  {champ.label} {champ.requis && <span className="text-accent-rouge">*</span>}
                </label>
                <ChampEntree
                  champ={champ}
                  valeur={valeursForm[champ.nom]}
                  onChange={(v) => modifierChamp(champ.nom, v)}
                />
              </div>
            </Fragment>
          ))}
          <div className="col-span-2 mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setModaleOuverte(false)}
              className="rounded border border-bordure px-3 py-1.5 text-sm hover:bg-fond"
            >
              {tr("Annuler")}
            </button>
            <button
              type="submit"
              disabled={envoiEnCours}
              className="rounded bg-entete px-3 py-1.5 text-sm font-medium text-white hover:bg-entete-fonce disabled:opacity-50"
            >
              {tr("Enregistrer")}
            </button>
          </div>
        </form>
      </Modale>
    </div>
  );
}
