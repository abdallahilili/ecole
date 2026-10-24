import type { ReactNode } from "react";
import { X } from "lucide-react";

interface Props {
  titre: string;
  ouverte: boolean;
  onFermer: () => void;
  children: ReactNode;
  largeur?: string;
}

export function Modale({ titre, ouverte, onFermer, children, largeur = "max-w-lg" }: Props) {
  if (!ouverte) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 px-4">
      <div className={`w-full ${largeur} rounded-md bg-white shadow-xl`}>
        <div className="flex items-center justify-between border-b border-bordure px-4 py-3">
          <h2 className="text-base font-semibold text-texte">{titre}</h2>
          <button onClick={onFermer} className="text-texte-attenue hover:text-texte">
            <X size={18} />
          </button>
        </div>
        <div className="max-h-[75vh] overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}
