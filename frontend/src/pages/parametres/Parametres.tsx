import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Save, Trash2, Upload } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useNotifications } from "../../composants/Notifications";
import { BOUTON, BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";

import { tr } from "../../i18n";
type Valeurs = Record<string, string>;

const VRAI = ["1", "true", "oui"];

/** Logo de l'ecole : envoi, apercu et suppression (enregistres immediatement, independamment du formulaire). */
function SectionLogo() {
  const { notifierSucces, notifierErreur } = useNotifications();
  const [apercu, setApercu] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const champFichier = useRef<HTMLInputElement>(null);

  async function charger() {
    try {
      const { data } = await api.get("/parametres/logo/", { responseType: "blob" });
      setApercu((ancien) => {
        if (ancien) URL.revokeObjectURL(ancien);
        return URL.createObjectURL(data);
      });
    } catch {
      setApercu(null); // 404 : aucun logo
    }
  }

  useEffect(() => {
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function envoyer(e: ChangeEvent<HTMLInputElement>) {
    const fichier = e.target.files?.[0];
    e.target.value = "";
    if (!fichier) return;
    setEnCours(true);
    try {
      const donnees = new FormData();
      donnees.append("logo", fichier);
      await api.post("/parametres/logo/", donnees);
      await charger();
      notifierSucces(tr("Logo enregistre."));
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  async function supprimer() {
    setEnCours(true);
    try {
      await api.delete("/parametres/logo/");
      setApercu(null);
      notifierSucces(tr("Logo supprime."));
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  return (
    <section className={`${CARTE} flex items-center gap-4`}>
      <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded border border-bordure bg-white">
        {apercu ? (
          <img src={apercu} alt={tr("Logo de l'ecole")} className="max-h-full max-w-full object-contain" />
        ) : (
          <span className="px-1 text-center text-xs text-texte-attenue">{tr("Aucun logo")}</span>
        )}
      </div>
      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-texte">{tr("Logo de l'ecole")}</h2>
        <p className="text-xs text-texte-attenue">{tr("Imprime sur les documents PDF. PNG ou JPEG, 2 Mo maximum.")}</p>
        <div className="flex flex-wrap gap-2">
          <input ref={champFichier} type="file" accept="image/png,image/jpeg" className="hidden" onChange={envoyer} />
          <button type="button" disabled={enCours} className={BOUTON} onClick={() => champFichier.current?.click()}>
            <Upload size={15} /> {apercu ? tr("Changer le logo") : tr("Choisir un logo")}
          </button>
          {apercu && (
            <button type="button" disabled={enCours} className={BOUTON} onClick={supprimer}>
              <Trash2 size={15} /> {tr("Supprimer le logo")}
            </button>
          )}
        </div>
      </div>
    </section>
  );
}

/** Parametres de l'etablissement : identite (entete des PDF), WhatsApp et
 * regles de calcul des notes. Les secrets (jeton WhatsApp...) ne sont
 * jamais saisis ici : ils restent dans le .env du backend. */
export function PageParametres() {
  const { notifierSucces, notifierErreur } = useNotifications();
  const [valeurs, setValeurs] = useState<Valeurs | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    api.get("/parametres/").then(({ data }) => setValeurs(data)).catch((err) => notifierErreur(messageErreur(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!valeurs) return <p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>;

  const maj = (cle: string, valeur: string) => setValeurs((v) => ({ ...v, [cle]: valeur }));
  const bool = (cle: string) => VRAI.includes((valeurs[cle] ?? "").toLowerCase());

  function texte(cle: string, label: string, aide?: string, direction?: "rtl" | "ltr") {
    return (
      <div>
        <label className={ETIQUETTE}>{label}</label>
        <input className={`${CHAMP} w-full`} dir={direction} value={valeurs?.[cle] ?? ""} onChange={(e) => maj(cle, e.target.value)} />
        {aide && <p className="mt-0.5 text-xs text-texte-attenue">{aide}</p>}
      </div>
    );
  }

  function interrupteur(cle: string, label: string, aide: string) {
    return (
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-1 h-4 w-4" checked={bool(cle)} onChange={(e) => maj(cle, e.target.checked ? "1" : "0")} />
        <span>
          <span className="font-medium text-texte">{label}</span>
          <span className="block text-xs text-texte-attenue">{aide}</span>
        </span>
      </label>
    );
  }

  function choix(cle: string, label: string, options: [string, string][], aide?: string) {
    return (
      <div>
        <label className={ETIQUETTE}>{label}</label>
        <select className={`${CHAMP} w-full`} value={valeurs?.[cle] ?? ""} onChange={(e) => maj(cle, e.target.value)}>
          {options.map(([valeur, libelle]) => <option key={valeur} value={valeur}>{libelle}</option>)}
        </select>
        {aide && <p className="mt-0.5 text-xs text-texte-attenue">{aide}</p>}
      </div>
    );
  }

  async function enregistrer(e: FormEvent) {
    e.preventDefault();
    setEnCours(true);
    try {
      const { data } = await api.put("/parametres/", valeurs);
      setValeurs(data);
      notifierSucces(tr("Parametres enregistres."));
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  return (
    <form onSubmit={enregistrer} className="max-w-3xl space-y-4">
      <h1 className="text-lg font-semibold text-texte">{tr("Parametres de l'etablissement")}</h1>

      <SectionLogo />

      <section className={`${CARTE} grid grid-cols-1 gap-3 md:grid-cols-2`}>
        <h2 className="col-span-full text-sm font-semibold text-texte">{tr("Identite (entete des documents PDF)")}</h2>
        {texte("nom_etablissement", tr("Nom de l'etablissement"))}
        {texte("telephone_etablissement", tr("Telephone"))}
        {texte("entete_ministere", tr("Ministere de tutelle"), tr("Ligne imprimee sur les bulletins et listes."))}
        {texte("entete_region", tr("Direction regionale"))}
        {texte("nom_etablissement_ar", tr("Nom de l'etablissement (arabe)"), undefined, "rtl")}
        {texte("entete_ministere_ar", tr("Ministere de tutelle (arabe)"), undefined, "rtl")}
        {texte("entete_region_ar", tr("Direction regionale (arabe)"), undefined, "rtl")}
      </section>

      <section className={`${CARTE} space-y-3`}>
        <h2 className="text-sm font-semibold text-texte">{tr("Notifications WhatsApp")}</h2>
        {choix("langue_whatsapp", tr("Langue des messages WhatsApp"), [["fr", tr("Francais")], ["ar", tr("Arabe")]],
          tr("L'envoi automatique necessite un modele de message approuve par langue (voir DEPLOIEMENT.md)."))}
        {interrupteur("whatsapp_actif", tr("Envoyer des notifications aux parents"),
          tr("Apres validation des presences, un message est prepare pour chaque absent. Desactive : aucun message n'est cree."))}
        {interrupteur("retard_est_absence", tr("Un retard compte comme une absence"),
          tr("Si coche, les parents des eleves en retard sont aussi notifies."))}
      </section>

      <section className={`${CARTE} grid grid-cols-1 gap-3 md:grid-cols-2`}>
        <h2 className="col-span-full text-sm font-semibold text-texte">{tr("Regles de calcul des evaluations")}</h2>
        {choix("abs_justifiee", tr("Absence justifiee a une evaluation"), [
          ["exclure", tr("Ne pas compter l'evaluation")], ["zero", tr("Compter 0")],
        ])}
        {choix("abs_non_justifiee", tr("Absence non justifiee a une evaluation"), [
          ["zero", tr("Compter 0")], ["exclure", tr("Ne pas compter l'evaluation")],
        ])}
        {choix("moyenne_exige_toutes_evaluations", tr("Moyenne d'une matiere"), [
          ["0", tr("Calculee avec les evaluations disponibles (marquee incomplete)")],
          ["1", tr("Calculee seulement si toutes les evaluations sont notees")],
        ])}
        {choix("matiere_non_evaluee", tr("Matiere sans aucune note (moyenne generale)"), [
          ["exclure", tr("Ignoree et signalee comme incomplete (recommande)")],
          ["zero", tr("Comptee 0 : coefficient conserve au diviseur (pratique du bulletin papier)")],
        ], tr("Le bulletin papier compte l'EPS non notee dans le diviseur : choisissez « Comptee 0 » pour retrouver ses moyennes."))}
        {choix("ex_aequo", tr("Classement : egalite de moyenne"), [
          ["meme_rang", tr("Meme rang (1, 2, 2, 4)")], ["alphabetique", tr("Depart. par ordre alphabetique")],
        ], tr("Le classement est etabli sur la moyenne arrondie au centieme."))}
        {texte("poids_trimestres", tr("Poids des trimestres (moyenne annuelle)"), tr("Trois nombres separes par des virgules, ex. 1,1,1."))}
      </section>

      <button type="submit" disabled={enCours} className={BOUTON_PRIMAIRE}>
        <Save size={15} /> {tr("Enregistrer")}
      </button>
    </form>
  );
}
