import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { Utilisateur } from "../types";
import * as authService from "../services/auth";

interface ContexteAuth {
  utilisateur: Utilisateur | null;
  chargement: boolean;
  connecter: (identifiant: string, motDePasse: string) => Promise<void>;
  deconnecter: () => void;
  peut: (module: string) => boolean;
}

const ContexteAuthDefaut = createContext<ContexteAuth | undefined>(undefined);

export function FournisseurAuth({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    authService.restaurerSession().then((u) => {
      setUtilisateur(u);
      setChargement(false);
    });
  }, []);

  async function connecter(identifiant: string, motDePasse: string) {
    const u = await authService.connecter(identifiant, motDePasse);
    setUtilisateur(u);
  }

  function deconnecter() {
    authService.deconnecter();
    setUtilisateur(null);
  }

  function peut(module: string) {
    return utilisateur?.modules.includes(module) ?? false;
  }

  return (
    <ContexteAuthDefaut.Provider value={{ utilisateur, chargement, connecter, deconnecter, peut }}>
      {children}
    </ContexteAuthDefaut.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(ContexteAuthDefaut);
  if (!ctx) throw new Error("useAuth doit etre utilise dans FournisseurAuth");
  return ctx;
}
