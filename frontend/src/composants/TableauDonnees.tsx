import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowDown, ArrowUp, ArrowUpDown, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Columns3, Filter, GripVertical,
  Maximize2, Minimize2,
} from "lucide-react";

import { tr } from "../i18n";
export interface Colonne<T> {
  cle: string;
  titre: string;
  rendu?: (ligne: T) => ReactNode;
  alignerDroite?: boolean;
  /** Largeur initiale en pixels (redimensionnable par l'utilisateur). */
  largeur?: number;
}

type Cle = string | number;

interface Props<T> {
  colonnes: Colonne<T>[];
  lignes: T[];
  chargement?: boolean;
  cleLigne: (ligne: T) => Cle;
  actions?: (ligne: T) => ReactNode;
  page?: number;
  nombrePages?: number;
  onChangerPage?: (page: number) => void;
  videMessage?: string;
  /** Cle de memorisation des preferences d'affichage (ordre, colonnes masquees, largeurs). */
  stockage?: string;
  /** Colonnes triables / filtrables cote serveur (liste `champs` de l'API). */
  champsServeur?: string[];
  tri?: string;
  onTri?: (tri: string) => void;
  filtresColonnes?: Record<string, string>;
  onFiltreColonne?: (cle: string, valeur: string) => void;
  selection?: Set<Cle>;
  onSelection?: (selection: Set<Cle>) => void;
  /** Contenu a droite de la barre d'outils (export, suppression multiple...). */
  barreOutils?: ReactNode;
}

interface Preferences { ordre: string[]; masquees: string[]; largeurs: Record<string, number> }

function lirePreferences(cle: string): Preferences | null {
  try {
    const brut = localStorage.getItem(`tableau:${cle}`);
    return brut ? (JSON.parse(brut) as Preferences) : null;
  } catch {
    return null;
  }
}

function ecrirePreferences(cle: string, prefs: Preferences) {
  try {
    localStorage.setItem(`tableau:${cle}`, JSON.stringify(prefs));
  } catch {
    /* stockage indisponible (navigation privee...) : les preferences ne sont simplement pas gardees */
  }
}

function ChampFiltre({ valeur, onChange }: { valeur: string; onChange: (v: string) => void }) {
  const [local, setLocal] = useState(valeur);
  useEffect(() => setLocal(valeur), [valeur]);
  useEffect(() => {
    if (local === valeur) return;
    const minuteur = setTimeout(() => onChange(local), 400);   // evite une requete a chaque frappe
    return () => clearTimeout(minuteur);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local]);
  return (
    <input
      value={local}
      onChange={(e) => setLocal(e.target.value)}
      placeholder={tr("Filtrer...")}
      className="w-full rounded border border-bordure px-1.5 py-0.5 text-xs font-normal focus:border-entete focus:outline-none"
    />
  );
}

export function TableauDonnees<T>({
  colonnes, lignes, chargement, cleLigne, actions, page = 1, nombrePages = 1, onChangerPage,
  videMessage = tr("Aucune donnee."), stockage, champsServeur, tri = "", onTri, filtresColonnes, onFiltreColonne,
  selection, onSelection, barreOutils,
}: Props<T>) {
  const cleStockage = stockage ?? colonnes.map((c) => c.cle).join(",");
  const cles = colonnes.map((c) => c.cle);

  const [ordre, setOrdre] = useState<string[]>(cles);
  const [masquees, setMasquees] = useState<string[]>([]);
  const [largeurs, setLargeurs] = useState<Record<string, number>>(() => Object.fromEntries(colonnes.filter((c) => c.largeur).map((c) => [c.cle, c.largeur!])));
  const [menuOuvert, setMenuOuvert] = useState(false);
  const [filtresVisibles, setFiltresVisibles] = useState(false);
  const [pleinEcran, setPleinEcran] = useState(false);
  const [glisse, setGlisse] = useState<string | null>(null);

  // Restaure les preferences memorisees (en ignorant les colonnes qui n'existent plus).
  useEffect(() => {
    const prefs = lirePreferences(cleStockage);
    if (!prefs) return;
    const connues = prefs.ordre.filter((c) => cles.includes(c));
    setOrdre([...connues, ...cles.filter((c) => !connues.includes(c))]);
    setMasquees(prefs.masquees.filter((c) => cles.includes(c)));
    setLargeurs((l) => ({ ...l, ...prefs.largeurs }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cleStockage]);

  function memoriser(partiel: Partial<Preferences>) {
    ecrirePreferences(cleStockage, { ordre, masquees, largeurs, ...partiel });
  }

  const affichees = useMemo(
    () => ordre.map((c) => colonnes.find((x) => x.cle === c)).filter((c): c is Colonne<T> => !!c && !masquees.includes(c.cle)),
    [ordre, masquees, colonnes],
  );

  const triable = (cle: string) => !!onTri && !!champsServeur?.includes(cle);
  const filtrable = (cle: string) => !!onFiltreColonne && !!champsServeur?.includes(cle);

  function basculerTri(cle: string) {
    onTri?.(tri === cle ? `-${cle}` : tri === `-${cle}` ? "" : cle);
  }

  function deplacer(cle: string, cible: string) {
    if (cle === cible) return;
    const nouveau = ordre.filter((c) => c !== cle);
    nouveau.splice(nouveau.indexOf(cible), 0, cle);
    setOrdre(nouveau);
    memoriser({ ordre: nouveau });
  }

  function decaler(cle: string, sens: -1 | 1) {
    const index = ordre.indexOf(cle);
    const cibleIndex = index + sens;
    if (cibleIndex < 0 || cibleIndex >= ordre.length) return;
    const nouveau = [...ordre];
    [nouveau[index], nouveau[cibleIndex]] = [nouveau[cibleIndex], nouveau[index]];
    setOrdre(nouveau);
    memoriser({ ordre: nouveau });
  }

  function basculerVisibilite(cle: string) {
    const nouveau = masquees.includes(cle) ? masquees.filter((c) => c !== cle) : [...masquees, cle];
    if (nouveau.length >= cles.length) return;   // au moins une colonne visible
    setMasquees(nouveau);
    memoriser({ masquees: nouveau });
  }

  function reinitialiser() {
    setOrdre(cles);
    setMasquees([]);
    setLargeurs({});
    memoriser({ ordre: cles, masquees: [], largeurs: {} });
  }

  function redimensionner(e: React.MouseEvent, cle: string) {
    e.preventDefault();
    e.stopPropagation();
    const depart = e.clientX;
    const base = (e.currentTarget.parentElement as HTMLElement).offsetWidth;
    let derniere = base;
    const deplacement = (ev: MouseEvent) => {
      derniere = Math.max(60, base + ev.clientX - depart);
      setLargeurs((l) => ({ ...l, [cle]: derniere }));
    };
    const fin = () => {
      document.removeEventListener("mousemove", deplacement);
      document.removeEventListener("mouseup", fin);
      memoriser({ largeurs: { ...largeurs, [cle]: derniere } });
    };
    document.addEventListener("mousemove", deplacement);
    document.addEventListener("mouseup", fin);
  }

  const cleesPage = lignes.map(cleLigne);
  const toutesSelectionnees = !!selection && cleesPage.length > 0 && cleesPage.every((c) => selection.has(c));

  function basculerPage() {
    if (!selection || !onSelection) return;
    const nouvelle = new Set(selection);
    if (toutesSelectionnees) cleesPage.forEach((c) => nouvelle.delete(c));
    else cleesPage.forEach((c) => nouvelle.add(c));
    onSelection(nouvelle);
  }

  function basculerLigne(cle: Cle) {
    if (!selection || !onSelection) return;
    const nouvelle = new Set(selection);
    if (nouvelle.has(cle)) nouvelle.delete(cle);
    else nouvelle.add(cle);
    onSelection(nouvelle);
  }

  const avecSelection = !!selection && !!onSelection;
  const nbColonnesTotal = affichees.length + (avecSelection ? 1 : 0) + (actions ? 1 : 0);
  const decalageSticky = avecSelection ? 40 : 0;
  const filtresPossibles = !!onFiltreColonne && affichees.some((c) => filtrable(c.cle));

  const barreHaute = (
    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
      <div className="relative flex items-center gap-1.5">
        {filtresPossibles && (
          <button
            onClick={() => setFiltresVisibles((v) => !v)}
            className={`flex items-center gap-1 rounded border px-2 py-1 text-xs hover:bg-fond ${filtresVisibles ? "border-entete text-entete" : "border-bordure"}`}
            title={tr("Filtres par colonne")}
          >
            <Filter size={13} /> {tr("Filtres")}
          </button>
        )}
        <button
          onClick={() => setMenuOuvert((v) => !v)}
          className="flex items-center gap-1 rounded border border-bordure px-2 py-1 text-xs hover:bg-fond"
          title={tr("Afficher, masquer et ordonner les colonnes")}
        >
          <Columns3 size={13} /> {tr("Colonnes")}
        </button>
        <button
          onClick={() => setPleinEcran((v) => !v)}
          className="flex items-center gap-1 rounded border border-bordure px-2 py-1 text-xs hover:bg-fond"
          title={tr("Plein ecran")}
        >
          {pleinEcran ? <Minimize2 size={13} /> : <Maximize2 size={13} />} {pleinEcran ? tr("Reduire") : tr("Plein ecran")}
        </button>
        {selection && selection.size > 0 && (
          <span className="ms-2 text-xs text-texte-attenue">
            {selection.size} {tr("selectionne(s)")}{" "}
            <button className="text-entete hover:underline" onClick={() => onSelection?.(new Set())}>{tr("Tout deselectionner")}</button>
          </span>
        )}
        {menuOuvert && (
          <>
            <div className="fixed inset-0 z-30" onClick={() => setMenuOuvert(false)} />
            <div className="absolute start-0 top-full z-40 mt-1 w-64 rounded-md border border-bordure bg-white p-2 shadow-xl">
              <p className="mb-1 text-xs font-semibold text-texte">{tr("Colonnes")}</p>
              <ul className="max-h-64 overflow-y-auto">
                {ordre.map((cle) => {
                  const colonne = colonnes.find((c) => c.cle === cle);
                  if (!colonne) return null;
                  return (
                    <li key={cle} className="flex items-center justify-between gap-1 py-0.5 text-sm">
                      <label className="flex min-w-0 items-center gap-1.5">
                        <input type="checkbox" checked={!masquees.includes(cle)} onChange={() => basculerVisibilite(cle)} />
                        <span className="truncate">{colonne.titre || cle}</span>
                      </label>
                      <span className="flex shrink-0">
                        <button className="px-0.5 text-texte-attenue hover:text-texte" onClick={() => decaler(cle, -1)} title={tr("Monter")}><ChevronUp size={14} /></button>
                        <button className="px-0.5 text-texte-attenue hover:text-texte" onClick={() => decaler(cle, 1)} title={tr("Descendre")}><ChevronDown size={14} /></button>
                      </span>
                    </li>
                  );
                })}
              </ul>
              <button className="mt-2 text-xs text-entete hover:underline" onClick={reinitialiser}>{tr("Reinitialiser l'affichage")}</button>
            </div>
          </>
        )}
      </div>
      <div className="flex items-center gap-2">{barreOutils}</div>
    </div>
  );

  const contenu = (
    <>
      {barreHaute}
      <div className="overflow-hidden rounded-md border border-bordure bg-fond-carte shadow-carte">
        <div className={`overflow-auto ${pleinEcran ? "max-h-[calc(100vh-9rem)]" : "max-h-[68vh]"}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-bordure text-start text-texte-attenue">
                {avecSelection && (
                  <th className="sticky start-0 top-0 z-20 w-10 bg-fond-barre px-3 py-2">
                    <input type="checkbox" checked={toutesSelectionnees} onChange={basculerPage} title={tr("Selectionner la page")} />
                  </th>
                )}
                {affichees.map((c, index) => {
                  const active = tri === c.cle || tri === `-${c.cle}`;
                  const figee = index === 0;
                  return (
                    <th
                      key={c.cle}
                      style={{
                        ...(largeurs[c.cle] ? { width: largeurs[c.cle], minWidth: 60 } : {}),
                        ...(figee ? { left: decalageSticky } : {}),
                      }}
                      onDragOver={(e) => glisse && e.preventDefault()}
                      onDrop={() => { if (glisse) deplacer(glisse, c.cle); setGlisse(null); }}
                      className={`sticky top-0 select-none bg-fond-barre px-3 py-2 font-medium ${c.alignerDroite ? "text-end" : ""} ${
                        figee ? "z-20" : "z-10"
                      }`}
                    >
                      <span className="flex items-center gap-1" style={{ justifyContent: c.alignerDroite ? "flex-end" : "flex-start" }}>
                        <span draggable onDragStart={() => setGlisse(c.cle)} onDragEnd={() => setGlisse(null)} className="cursor-grab text-texte-attenue/60" title={tr("Glisser pour reordonner")}>
                          <GripVertical size={12} />
                        </span>
                        {triable(c.cle) ? (
                          <button onClick={() => basculerTri(c.cle)} className="flex items-center gap-1 hover:text-texte" title={tr("Trier")}>
                            {c.titre}
                            {tri === c.cle ? <ArrowUp size={12} /> : tri === `-${c.cle}` ? <ArrowDown size={12} /> : <ArrowUpDown size={12} className="opacity-40" />}
                          </button>
                        ) : c.titre}
                        {active && <span className="sr-only">{tr("tri actif")}</span>}
                      </span>
                      <span
                        onMouseDown={(e) => redimensionner(e, c.cle)}
                        className="absolute end-0 top-0 h-full w-1.5 cursor-col-resize hover:bg-entete/30"
                        title={tr("Redimensionner")}
                      />
                    </th>
                  );
                })}
                {actions && <th className="sticky end-0 top-0 z-20 bg-fond-barre px-3 py-2 text-end font-medium">{tr("Actions")}</th>}
              </tr>
              {filtresVisibles && filtresPossibles && (
                <tr className="border-b border-bordure bg-fond-barre">
                  {avecSelection && <th className="sticky start-0 z-20 bg-fond-barre" />}
                  {affichees.map((c) => (
                    <th key={c.cle} className="bg-fond-barre px-2 py-1">
                      {filtrable(c.cle) && (
                        <ChampFiltre valeur={filtresColonnes?.[c.cle] ?? ""} onChange={(v) => onFiltreColonne?.(c.cle, v)} />
                      )}
                    </th>
                  ))}
                  {actions && <th className="sticky end-0 bg-fond-barre" />}
                </tr>
              )}
            </thead>
            <tbody>
              {chargement && (
                <tr>
                  <td colSpan={nbColonnesTotal} className="px-3 py-6 text-center text-texte-attenue">{tr("Chargement...")}</td>
                </tr>
              )}
              {!chargement && lignes.length === 0 && (
                <tr>
                  <td colSpan={nbColonnesTotal} className="px-3 py-6 text-center text-texte-attenue">{videMessage}</td>
                </tr>
              )}
              {!chargement && lignes.map((ligne) => {
                const cle = cleLigne(ligne);
                const choisie = !!selection?.has(cle);
                const fond = choisie ? "bg-blue-50" : "bg-fond-carte";
                return (
                  <tr key={cle} className="border-b border-bordure last:border-0 hover:bg-fond">
                    {avecSelection && (
                      <td className={`sticky start-0 z-10 w-10 px-3 py-2 ${fond}`}>
                        <input type="checkbox" checked={choisie} onChange={() => basculerLigne(cle)} />
                      </td>
                    )}
                    {affichees.map((c, index) => (
                      <td
                        key={c.cle}
                        style={index === 0 ? { left: decalageSticky } : undefined}
                        className={`px-3 py-2 text-texte ${c.alignerDroite ? "text-end" : ""} ${index === 0 ? `sticky z-10 ${fond}` : choisie ? "bg-blue-50" : ""}`}
                      >
                        {c.rendu ? c.rendu(ligne) : String((ligne as any)[c.cle] ?? "")}
                      </td>
                    ))}
                    {actions && <td className={`sticky end-0 px-3 py-2 text-end ${fond}`}>{actions(ligne)}</td>}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {onChangerPage && nombrePages > 1 && (
          <div className="flex items-center justify-between border-t border-bordure px-3 py-2">
            <button
              disabled={page <= 1}
              onClick={() => onChangerPage(page - 1)}
              className="flex items-center gap-1 rounded px-2 py-1 text-sm text-texte-attenue disabled:opacity-40 hover:bg-fond"
            >
              <ChevronLeft size={16} className="rtl:rotate-180" /> {tr("Precedent")}
            </button>
            <span className="text-sm text-texte-attenue">{tr("Page {0} / {1}", page, nombrePages)}</span>
            <button
              disabled={page >= nombrePages}
              onClick={() => onChangerPage(page + 1)}
              className="flex items-center gap-1 rounded px-2 py-1 text-sm text-texte-attenue disabled:opacity-40 hover:bg-fond"
            >
              {tr("Suivant")} <ChevronRight size={16} className="rtl:rotate-180" />
            </button>
          </div>
        )}
      </div>
    </>
  );

  return pleinEcran
    ? <div className="fixed inset-0 z-40 overflow-auto bg-fond p-4">{contenu}</div>
    : <div>{contenu}</div>;
}
