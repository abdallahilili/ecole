import { Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { FournisseurAuth, useAuth } from "./hooks/useAuth";
import { FournisseurNotifications } from "./composants/Notifications";
import { FournisseurConfirmation } from "./composants/Confirmation";
import { MiseEnPagePrincipale } from "./miseEnPage/MiseEnPagePrincipale";
import { PageConnexion } from "./pages/Connexion";
import { routesProtegees } from "./routes";

import { tr } from "./i18n";
function EspaceProtege() {
  const { utilisateur, chargement, peut } = useAuth();

  if (chargement) {
    return <div className="flex h-screen items-center justify-center text-sm text-texte-attenue">{tr("Chargement...")}</div>;
  }
  if (!utilisateur) return <Navigate to="/connexion" replace />;

  return (
    <MiseEnPagePrincipale>
      <Suspense fallback={<p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>}>
        <Routes>
          {routesProtegees.map((r) => (
            <Route
              key={r.chemin}
              path={r.chemin}
              element={peut(r.module) || r.chemin === "*" ? r.element : <Navigate to="/" replace />}
            />
          ))}
        </Routes>
      </Suspense>
    </MiseEnPagePrincipale>
  );
}

export default function App() {
  return (
    <FournisseurNotifications>
      <FournisseurConfirmation>
        <BrowserRouter>
          <FournisseurAuth>
            <Routes>
              <Route path="/connexion" element={<PageConnexion />} />
              <Route path="/*" element={<EspaceProtege />} />
            </Routes>
          </FournisseurAuth>
        </BrowserRouter>
      </FournisseurConfirmation>
    </FournisseurNotifications>
  );
}
