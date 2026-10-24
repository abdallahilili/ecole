import type { ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export interface Colonne<T> {
  cle: string;
  titre: string;
  rendu?: (ligne: T) => ReactNode;
  alignerDroite?: boolean;
}

interface Props<T> {
  colonnes: Colonne<T>[];
  lignes: T[];
  chargement?: boolean;
  cleLigne: (ligne: T) => string | number;
  actions?: (ligne: T) => ReactNode;
  page?: number;
  nombrePages?: number;
  onChangerPage?: (page: number) => void;
  videMessage?: string;
}

export function TableauDonnees<T>({
  colonnes, lignes, chargement, cleLigne, actions, page = 1, nombrePages = 1, onChangerPage,
  videMessage = "Aucune donnee.",
}: Props<T>) {
  return (
    <div className="overflow-hidden rounded-md border border-bordure bg-fond-carte shadow-carte">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-bordure bg-fond-barre text-left text-texte-attenue">
              {colonnes.map((c) => (
                <th key={c.cle} className={`px-3 py-2 font-medium ${c.alignerDroite ? "text-right" : ""}`}>
                  {c.titre}
                </th>
              ))}
              {actions && <th className="px-3 py-2 text-right font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {chargement && (
              <tr>
                <td colSpan={colonnes.length + (actions ? 1 : 0)} className="px-3 py-6 text-center text-texte-attenue">
                  Chargement...
                </td>
              </tr>
            )}
            {!chargement && lignes.length === 0 && (
              <tr>
                <td colSpan={colonnes.length + (actions ? 1 : 0)} className="px-3 py-6 text-center text-texte-attenue">
                  {videMessage}
                </td>
              </tr>
            )}
            {!chargement && lignes.map((ligne) => (
              <tr key={cleLigne(ligne)} className="border-b border-bordure last:border-0 hover:bg-fond">
                {colonnes.map((c) => (
                  <td key={c.cle} className={`px-3 py-2 text-texte ${c.alignerDroite ? "text-right" : ""}`}>
                    {c.rendu ? c.rendu(ligne) : String((ligne as any)[c.cle] ?? "")}
                  </td>
                ))}
                {actions && <td className="px-3 py-2 text-right">{actions(ligne)}</td>}
              </tr>
            ))}
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
            <ChevronLeft size={16} /> Precedent
          </button>
          <span className="text-sm text-texte-attenue">Page {page} / {nombrePages}</span>
          <button
            disabled={page >= nombrePages}
            onClick={() => onChangerPage(page + 1)}
            className="flex items-center gap-1 rounded px-2 py-1 text-sm text-texte-attenue disabled:opacity-40 hover:bg-fond"
          >
            Suivant <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
