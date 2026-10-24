import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { messageErreur } from "../services/api";

export function PageConnexion() {
  const { connecter } = useAuth();
  const navigate = useNavigate();
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await connecter(identifiant, motDePasse);
      navigate("/");
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-fond px-4">
      <div className="w-full max-w-sm rounded-md border border-bordure bg-fond-carte p-6 shadow-carte">
        <div className="mb-6 flex flex-col items-center">
          <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-md bg-entete text-white">
            <GraduationCap size={22} />
          </div>
          <h1 className="text-lg font-semibold text-texte">Gestion Ecole</h1>
          <p className="text-sm text-texte-attenue">Connectez-vous a votre espace</p>
        </div>
        <form onSubmit={soumettre} className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-texte">Identifiant</label>
            <input
              className="w-full rounded border border-bordure px-3 py-2 text-sm focus:border-entete focus:outline-none"
              value={identifiant}
              onChange={(e) => setIdentifiant(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-texte">Mot de passe</label>
            <input
              type="password"
              className="w-full rounded border border-bordure px-3 py-2 text-sm focus:border-entete focus:outline-none"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              required
            />
          </div>
          {erreur && <p className="text-sm text-accent-rouge">{erreur}</p>}
          <button
            type="submit"
            disabled={enCours}
            className="w-full rounded bg-entete py-2 text-sm font-medium text-white hover:bg-entete-fonce disabled:opacity-50"
          >
            {enCours ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
