import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, GraduationCap } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { messageErreur } from "../services/api";
import { SelecteurLangue } from "../composants/SelecteurLangue";

import { tr } from "../i18n";
export function PageConnexion() {
  const { connecter } = useAuth();
  const navigate = useNavigate();
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [afficher, setAfficher] = useState(false);
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
    <div className="flex min-h-screen flex-col items-center justify-center bg-fond px-4">
      <div className="mb-4"><SelecteurLangue ton="fonce" /></div>
      <div className="w-full max-w-sm rounded-md border border-bordure bg-fond-carte p-6 shadow-carte">
        <div className="mb-6 flex flex-col items-center">
          <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-md bg-entete text-white">
            <GraduationCap size={22} />
          </div>
          <h1 className="text-lg font-semibold text-texte">{tr("Gestion Ecole")}</h1>
          <p className="text-sm text-texte-attenue">{tr("Connectez-vous a votre espace")}</p>
        </div>
        <form onSubmit={soumettre} className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-texte">{tr("Identifiant")}</label>
            <input
              className="w-full rounded border border-bordure px-3 py-2 text-sm focus:border-entete focus:outline-none"
              value={identifiant}
              onChange={(e) => setIdentifiant(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-texte">{tr("Mot de passe")}</label>
            <div className="relative">
              <input
                type={afficher ? "text" : "password"}
                className="w-full rounded border border-bordure py-2 pe-10 ps-3 text-sm focus:border-entete focus:outline-none"
                value={motDePasse}
                onChange={(e) => setMotDePasse(e.target.value)}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setAfficher((a) => !a)}
                aria-label={afficher ? tr("Masquer le mot de passe") : tr("Afficher le mot de passe")}
                title={afficher ? tr("Masquer le mot de passe") : tr("Afficher le mot de passe")}
                className="absolute inset-y-0 end-0 flex items-center px-3 text-texte-attenue hover:text-entete"
              >
                {afficher ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          {erreur && <p className="text-sm text-accent-rouge">{erreur}</p>}
          <button
            type="submit"
            disabled={enCours}
            className="w-full rounded bg-entete py-2 text-sm font-medium text-white hover:bg-entete-fonce disabled:opacity-50"
          >
            {enCours ? tr("Connexion...") : tr("Se connecter")}
          </button>
        </form>
      </div>
    </div>
  );
}
