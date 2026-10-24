import { createContext, useCallback, useContext, useState } from "react";
import type { ReactNode } from "react";

interface OptionsConfirmation {
  titre: string;
  message: string;
}

interface ContexteConfirmation {
  demanderConfirmation: (options: OptionsConfirmation) => Promise<boolean>;
}

const Contexte = createContext<ContexteConfirmation | undefined>(undefined);

export function FournisseurConfirmation({ children }: { children: ReactNode }) {
  const [etat, setEtat] = useState<(OptionsConfirmation & { resoudre: (v: boolean) => void }) | null>(null);

  const demanderConfirmation = useCallback((options: OptionsConfirmation) => {
    return new Promise<boolean>((resoudre) => {
      setEtat({ ...options, resoudre });
    });
  }, []);

  function repondre(valeur: boolean) {
    etat?.resoudre(valeur);
    setEtat(null);
  }

  return (
    <Contexte.Provider value={{ demanderConfirmation }}>
      {children}
      {etat && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
          <div className="w-full max-w-sm rounded-md bg-white p-5 shadow-xl">
            <h2 className="text-base font-semibold text-texte">{etat.titre}</h2>
            <p className="mt-2 text-sm text-texte-attenue">{etat.message}</p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => repondre(false)}
                className="rounded border border-bordure px-3 py-1.5 text-sm hover:bg-fond"
              >
                Annuler
              </button>
              <button
                onClick={() => repondre(true)}
                className="rounded bg-entete px-3 py-1.5 text-sm text-white hover:bg-entete-fonce"
              >
                Confirmer
              </button>
            </div>
          </div>
        </div>
      )}
    </Contexte.Provider>
  );
}

export function useConfirmation() {
  const ctx = useContext(Contexte);
  if (!ctx) throw new Error("useConfirmation doit etre utilise dans FournisseurConfirmation");
  return ctx;
}
