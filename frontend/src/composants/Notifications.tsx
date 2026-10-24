import { createContext, useCallback, useContext, useState } from "react";
import type { ReactNode } from "react";
import { CheckCircle2, XCircle, X } from "lucide-react";

interface Notification {
  id: number;
  type: "succes" | "erreur";
  message: string;
}

interface ContexteNotifications {
  notifierSucces: (message: string) => void;
  notifierErreur: (message: string) => void;
}

const Contexte = createContext<ContexteNotifications | undefined>(undefined);

export function FournisseurNotifications({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const retirer = useCallback((id: number) => {
    setNotifications((n) => n.filter((x) => x.id !== id));
  }, []);

  const ajouter = useCallback((type: Notification["type"], message: string) => {
    const id = Date.now() + Math.random();
    setNotifications((n) => [...n, { id, type, message }]);
    setTimeout(() => retirer(id), 5000);
  }, [retirer]);

  const notifierSucces = useCallback((message: string) => ajouter("succes", message), [ajouter]);
  const notifierErreur = useCallback((message: string) => ajouter("erreur", message), [ajouter]);

  return (
    <Contexte.Provider value={{ notifierSucces, notifierErreur }}>
      {children}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-80">
        {notifications.map((n) => (
          <div
            key={n.id}
            className={`flex items-start gap-2 rounded-md border px-3 py-2 shadow-carte bg-white ${
              n.type === "succes" ? "border-accent-vert" : "border-accent-rouge"
            }`}
          >
            {n.type === "succes" ? (
              <CheckCircle2 size={18} className="text-accent-vert mt-0.5 shrink-0" />
            ) : (
              <XCircle size={18} className="text-accent-rouge mt-0.5 shrink-0" />
            )}
            <p className="text-sm text-texte flex-1">{n.message}</p>
            <button onClick={() => retirer(n.id)} className="text-texte-attenue hover:text-texte">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </Contexte.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(Contexte);
  if (!ctx) throw new Error("useNotifications doit etre utilise dans FournisseurNotifications");
  return ctx;
}
