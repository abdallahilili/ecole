import { useEffect, useState } from "react";
import { Check, ExternalLink, RefreshCw, Send } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useListeAvancee } from "../../hooks/useListe";
import { useNotifications } from "../../composants/Notifications";
import { Badge } from "../../composants/Badge";
import { TableauDonnees } from "../../composants/TableauDonnees";
import { BOUTON, CARTE, CHAMP } from "../../composants/styles";
import { formaterDate, formaterHeure } from "../../services/fichiers";
import type { ConfigurationNotifications, NotificationWhatsApp } from "../../types";

import { LOCALE, tr, tx } from "../../i18n";
export function PageNotifications() {
  const { notifierSucces, notifierErreur } = useNotifications();
  const [filtres, setFiltres] = useState<Record<string, string>>({});
  const { resultats, chargement, page, setPage, nombrePages, recharger, proprietesTableau } =
    useListeAvancee<NotificationWhatsApp>("/presences/notifications/", filtres);
  const [config, setConfig] = useState<ConfigurationNotifications | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    api.get("/presences/notifications/configuration/").then(({ data }) => setConfig(data)).catch(() => setConfig(null));
  }, []);

  async function executer(action: () => Promise<string>) {
    setEnCours(true);
    try {
      notifierSucces(await action());
      recharger();
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  const traiter = () => executer(async () => {
    const { data } = await api.post("/presences/notifications/traiter/");
    if (!data.api_configuree) return tr("API WhatsApp non configuree : utilisez les liens wa.me de chaque ligne.");
    return tr("{0} envoye(s), {1} reporte(s), {2} echec(s).", data.envoyees, data.reportees, data.echecs);
  });

  const reessayerEchecs = () => executer(async () => {
    const { data } = await api.post("/presences/notifications/reessayer-echecs/");
    return tr("{0} notification(s) remise(s) en file.", data.remises_en_file);
  });

  const reessayer = (n: NotificationWhatsApp) => executer(async () => {
    const { data } = await api.post(`/presences/notifications/${n.id}/reessayer/`);
    return data.statut === "ENVOYE" ? tr("Notification envoyee.") : tr("Notification remise en file.");
  });

  const marquerEnvoye = (n: NotificationWhatsApp) => executer(async () => {
    await api.post(`/presences/notifications/${n.id}/marquer-envoye/`);
    return tr("Notification marquee comme envoyee.");
  });

  const maj = (cle: string, valeur: string) => setFiltres((f) => ({ ...f, [cle]: valeur }));

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-texte">{tr("Notifications WhatsApp aux parents")}</h1>
        <div className="flex gap-2">
          <button disabled={enCours || !config?.api_configuree} onClick={traiter} className={BOUTON}
                  title={config?.api_configuree ? "" : tr("API WhatsApp Business non configuree")}>
            <Send size={15} /> {tr("Envoyer maintenant")}
          </button>
          <button disabled={enCours} onClick={reessayerEchecs} className={BOUTON}>
            <RefreshCw size={15} /> {tr("Reessayer les echecs")}
          </button>
        </div>
      </div>

      {config && (
        <div className={`${CARTE} mb-4 text-sm`}>
          <p>
            {tx("Envoi automatique : {0} (Parametres). API WhatsApp Business : {1}.",
              <b className={config.whatsapp_actif ? "text-accent-vert" : "text-accent-rouge"}>{config.whatsapp_actif ? tr("active") : tr("desactive")}</b>,
              <b className={config.api_configuree ? "text-accent-vert" : "text-amber-700"}>
                {config.api_configuree ? tr("configuree (modele {0})", config.nom_modele_api) : tr("non configuree")}</b>)}
          </p>
          {!config.api_configuree && (
            <p className="mt-1 text-texte-attenue">
              {tr("Sans API, les messages restent « En attente » : ouvrez le lien WhatsApp de chaque ligne, envoyez le message, puis cliquez sur « Marquer envoye ».")}
            </p>
          )}
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input className={CHAMP} placeholder={tr("Etudiant (nom, matricule)...")} value={filtres.recherche ?? ""}
               onChange={(e) => maj("recherche", e.target.value)} />
        <select className={CHAMP} value={filtres.statut ?? ""} onChange={(e) => maj("statut", e.target.value)}>
          <option value="">{tr("Tous les statuts")}</option>
          <option value="EN_ATTENTE">{tr("En attente")}</option>
          <option value="ENVOYE">{tr("Envoye")}</option>
          <option value="LIVRE">{tr("Livre")}</option>
          <option value="ECHEC">{tr("Echec")}</option>
        </select>
        <label className="flex items-center gap-1 text-sm text-texte-attenue">
          {tr("Du")} <input type="date" className={CHAMP} value={filtres.du ?? ""} onChange={(e) => maj("du", e.target.value)} />
        </label>
        <label className="flex items-center gap-1 text-sm text-texte-attenue">
          au <input type="date" className={CHAMP} value={filtres.au ?? ""} onChange={(e) => maj("au", e.target.value)} />
        </label>
      </div>

      <TableauDonnees<NotificationWhatsApp>
        {...proprietesTableau}
        stockage="notifications-whatsapp"
        colonnes={[
          { cle: "date", titre: tr("Cours"), rendu: (n) => `${formaterDate(n.date)} ${formaterHeure(n.heure_debut)}-${formaterHeure(n.heure_fin)}` },
          { cle: "etudiant_nom", titre: tr("Etudiant"), rendu: (n) => `${n.etudiant_nom} (${n.classe_nom})` },
          { cle: "matiere_nom", titre: tr("Matiere") },
          { cle: "destinataire_nom", titre: tr("Destinataire"), rendu: (n) => `${n.destinataire_nom} ${n.telephone ? `(+${n.telephone})` : ""}` },
          {
            cle: "statut", titre: tr("Statut"),
            rendu: (n) => (
              <span>
                <Badge statut={n.statut} />
                {n.canal && <span className="ms-1 text-xs text-texte-attenue">{n.canal === "API" ? "API" : "manuel"}</span>}
                {n.erreur && <span className="block max-w-xs truncate text-xs text-accent-rouge" title={n.erreur}>{n.erreur}</span>}
              </span>
            ),
          },
          { cle: "tentatives", titre: tr("Essais"), alignerDroite: true },
          { cle: "envoye_le", titre: tr("Envoye le"), rendu: (n) => (n.envoye_le ? new Date(n.envoye_le).toLocaleString(LOCALE) : "-") },
        ]}
        lignes={resultats}
        chargement={chargement}
        cleLigne={(n) => n.id}
        page={page}
        nombrePages={nombrePages}
        onChangerPage={setPage}
        actions={(n) => (
          <div className="flex justify-end gap-2">
            {n.lien_wa_me && n.statut !== "LIVRE" && (
              <a href={n.lien_wa_me} target="_blank" rel="noreferrer" title={tr("Ouvrir WhatsApp avec le message pre-rempli")}
                 className="text-texte-attenue hover:text-entete">
                <ExternalLink size={16} />
              </a>
            )}
            {(n.statut === "EN_ATTENTE" || n.statut === "ECHEC") && (
              <button onClick={() => marquerEnvoye(n)} title={tr("Marquer comme envoye (envoi manuel)")} className="text-texte-attenue hover:text-accent-vert">
                <Check size={16} />
              </button>
            )}
            {n.statut === "ECHEC" && (
              <button onClick={() => reessayer(n)} title={tr("Reessayer")} className="text-texte-attenue hover:text-entete">
                <RefreshCw size={16} />
              </button>
            )}
          </div>
        )}
      />

      {config && (
        <details className="mt-4 text-sm text-texte-attenue">
          <summary className="cursor-pointer">{tr("Modele du message envoye aux parents")}</summary>
          <p className="mt-2 rounded border border-bordure bg-white p-3">{config.modele_message}</p>
        </details>
      )}
    </div>
  );
}
