import { useState } from "react";
import { Plus, Pencil, Trash2, Search } from "lucide-react";
import { api, messageErreur } from "../services/api";
import { useListe, useOptions } from "../hooks/useListe";
import { useNotifications } from "./Notifications";
import { useConfirmation } from "./Confirmation";
import { Modale } from "./Modale";
import { TableauDonnees } from "./TableauDonnees";
import type { Colonne } from "./TableauDonnees";

export interface OptionChamp { value: string | number; label: string }

export interface ChampFormulaire {
  nom: string;
  label: string;
  type?: "texte" | "nombre" | "decimal" | "select" | "checkbox" | "textarea" | "email" | "date" | "mois" | "heure";
  requis?: boolean;
  optionsUrl?: string;
  optionsStatiques?: OptionChamp[];
  optionLabel?: (item: any) => string;
  placeholder?: string;
  colonnePleine?: boolean;
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
}

function ChampEntree({ champ, valeur, onChange }: { champ: ChampFormulaire; valeur: any; onChange: (v: any) => void }) {
  const options = useOptions<any>(champ.optionsUrl ?? "", !!champ.optionsUrl);
  const listeOptions = champ.optionsStatiques ?? options.map((o) => ({
    value: o.id, label: champ.optionLabel ? champ.optionLabel(o) : o.nom,
  }));

  if (champ.type === "select") {
    return (
      <select
        className="w-full rounded border border-bordure px-2.5 py-1.5 text-sm focus:border-entete focus:outline-none"
        value={valeur ?? ""}
        onChange={(e) => onChange(e.target.value)}
        required={champ.requis}
      >
        <option value="">-- Selectionner --</option>
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
          : "text"
      }
      step={champ.type === "decimal" ? "0.01" : undefined}
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
  titreForm,
}: Props<T>) {
  const [recherche, setRecherche] = useState("");
  const parametres = { ...parametresFiltre, ...(champRecherche && recherche ? { recherche } : {}) };
  const { resultats, chargement, page, setPage, nombrePages, recharger } = useListe<T>(url, parametres);
  const { notifierSucces, notifierErreur } = useNotifications();
  const { demanderConfirmation } = useConfirmation();

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

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setEnvoiEnCours(true);
    try {
      if (enModification) {
        await api.patch(`${url}${cleLigne(enModification)}/`, valeursForm);
        notifierSucces("Modification enregistree.");
      } else {
        await api.post(url, valeursForm);
        notifierSucces("Creation effectuee.");
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
      titre: "Confirmer la suppression",
      message: "Cette action est definitive. Voulez-vous continuer ?",
    });
    if (!confirme) return;
    try {
      await api.delete(`${url}${cleLigne(ligne)}/`);
      notifierSucces("Suppression effectuee.");
      recharger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-texte">{titre}</h1>
        {peutCreer && (
          <button
            onClick={ouvrirCreation}
            className="flex items-center gap-1.5 rounded bg-entete px-3 py-1.5 text-sm font-medium text-white hover:bg-entete-fonce"
          >
            <Plus size={16} /> Nouveau
          </button>
        )}
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        {champRecherche && (
          <div className="relative">
            <Search size={15} className="absolute left-2.5 top-2.5 text-texte-attenue" />
            <input
              value={recherche}
              onChange={(e) => setRecherche(e.target.value)}
              placeholder="Rechercher..."
              className="rounded border border-bordure py-1.5 pl-8 pr-3 text-sm focus:border-entete focus:outline-none"
            />
          </div>
        )}
        {filtres}
      </div>

      <TableauDonnees
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

      <Modale
        titre={titreForm ? titreForm(!!enModification) : enModification ? "Modifier" : "Nouveau"}
        ouverte={modaleOuverte}
        onFermer={() => setModaleOuverte(false)}
      >
        <form onSubmit={soumettre} className="grid grid-cols-2 gap-3">
          {champs.map((champ) => (
            <div key={champ.nom} className={champ.colonnePleine ? "col-span-2" : ""}>
              <label className="mb-1 block text-sm font-medium text-texte">
                {champ.label} {champ.requis && <span className="text-accent-rouge">*</span>}
              </label>
              <ChampEntree
                champ={champ}
                valeur={valeursForm[champ.nom]}
                onChange={(v) => setValeursForm((s) => ({ ...s, [champ.nom]: v }))}
              />
            </div>
          ))}
          <div className="col-span-2 mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setModaleOuverte(false)}
              className="rounded border border-bordure px-3 py-1.5 text-sm hover:bg-fond"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={envoiEnCours}
              className="rounded bg-entete px-3 py-1.5 text-sm font-medium text-white hover:bg-entete-fonce disabled:opacity-50"
            >
              Enregistrer
            </button>
          </div>
        </form>
      </Modale>
    </div>
  );
}
