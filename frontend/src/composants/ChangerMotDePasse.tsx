import { useState } from "react";
import type { FormEvent } from "react";
import { api, messageErreur } from "../services/api";
import { Modale } from "./Modale";
import { useNotifications } from "./Notifications";
import { BOUTON, BOUTON_PRIMAIRE, CHAMP, ETIQUETTE } from "./styles";

import { tr } from "../i18n";
/** Changement de son propre mot de passe (l'ancien est exige ; la politique de securite est appliquee par le serveur). */
export function ChangerMotDePasse({ ouverte, onFermer }: { ouverte: boolean; onFermer: () => void }) {
  const { notifierSucces, notifierErreur } = useNotifications();
  const [ancien, setAncien] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [enCours, setEnCours] = useState(false);

  function fermer() {
    setAncien("");
    setNouveau("");
    setConfirmation("");
    onFermer();
  }

  async function soumettre(e: FormEvent) {
    e.preventDefault();
    if (nouveau !== confirmation) {
      notifierErreur(tr("La confirmation ne correspond pas au nouveau mot de passe."));
      return;
    }
    setEnCours(true);
    try {
      await api.post("/auth/mot-de-passe/", { ancien, nouveau });
      notifierSucces(tr("Mot de passe modifie."));
      fermer();
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  return (
    <Modale titre={tr("Changer mon mot de passe")} ouverte={ouverte} onFermer={fermer}>
      <form onSubmit={soumettre} className="space-y-3">
        <div>
          <label className={ETIQUETTE}>{tr("Mot de passe actuel")}</label>
          <input type="password" autoComplete="current-password" required className={`${CHAMP} w-full`} value={ancien} onChange={(e) => setAncien(e.target.value)} />
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Nouveau mot de passe")}</label>
          <input type="password" autoComplete="new-password" required minLength={8} className={`${CHAMP} w-full`} value={nouveau} onChange={(e) => setNouveau(e.target.value)} />
          <p className="mt-0.5 text-xs text-texte-attenue">{tr("8 caracteres minimum, pas uniquement des chiffres, pas un mot de passe courant.")}</p>
        </div>
        <div>
          <label className={ETIQUETTE}>{tr("Confirmer le nouveau mot de passe")}</label>
          <input type="password" autoComplete="new-password" required className={`${CHAMP} w-full`} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className={BOUTON} onClick={fermer}>{tr("Annuler")}</button>
          <button type="submit" disabled={enCours} className={BOUTON_PRIMAIRE}>{tr("Enregistrer")}</button>
        </div>
      </form>
    </Modale>
  );
}
