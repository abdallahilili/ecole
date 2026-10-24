import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Save } from "lucide-react";
import { api, messageErreur } from "../../services/api";
import { useNotifications } from "../../composants/Notifications";
import { BOUTON_PRIMAIRE, CARTE, CHAMP, ETIQUETTE } from "../../composants/styles";

type Valeurs = Record<string, string>;

const VRAI = ["1", "true", "oui"];

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

  if (!valeurs) return <p className="text-sm text-texte-attenue">Chargement...</p>;

  const maj = (cle: string, valeur: string) => setValeurs((v) => ({ ...v, [cle]: valeur }));
  const bool = (cle: string) => VRAI.includes((valeurs[cle] ?? "").toLowerCase());

  function texte(cle: string, label: string, aide?: string) {
    return (
      <div>
        <label className={ETIQUETTE}>{label}</label>
        <input className={`${CHAMP} w-full`} value={valeurs?.[cle] ?? ""} onChange={(e) => maj(cle, e.target.value)} />
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
      notifierSucces("Parametres enregistres.");
    } catch (err) {
      notifierErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  return (
    <form onSubmit={enregistrer} className="max-w-3xl space-y-4">
      <h1 className="text-lg font-semibold text-texte">Parametres de l&apos;etablissement</h1>

      <section className={`${CARTE} grid grid-cols-1 gap-3 md:grid-cols-2`}>
        <h2 className="col-span-full text-sm font-semibold text-texte">Identite (entete des documents PDF)</h2>
        {texte("nom_etablissement", "Nom de l'etablissement")}
        {texte("telephone_etablissement", "Telephone")}
        {texte("entete_ministere", "Ministere de tutelle", "Ligne imprimee sur les bulletins et listes.")}
        {texte("entete_region", "Direction regionale")}
      </section>

      <section className={`${CARTE} space-y-3`}>
        <h2 className="text-sm font-semibold text-texte">Notifications WhatsApp</h2>
        {interrupteur("whatsapp_actif", "Envoyer des notifications aux parents",
          "Apres validation des presences, un message est prepare pour chaque absent. Desactive : aucun message n'est cree.")}
        {interrupteur("retard_est_absence", "Un retard compte comme une absence",
          "Si coche, les parents des eleves en retard sont aussi notifies.")}
      </section>

      <section className={`${CARTE} grid grid-cols-1 gap-3 md:grid-cols-2`}>
        <h2 className="col-span-full text-sm font-semibold text-texte">Regles de calcul des evaluations</h2>
        {choix("abs_justifiee", "Absence justifiee a une evaluation", [
          ["exclure", "Ne pas compter l'evaluation"], ["zero", "Compter 0"],
        ])}
        {choix("abs_non_justifiee", "Absence non justifiee a une evaluation", [
          ["zero", "Compter 0"], ["exclure", "Ne pas compter l'evaluation"],
        ])}
        {choix("moyenne_exige_toutes_evaluations", "Moyenne d'une matiere", [
          ["0", "Calculee avec les evaluations disponibles (marquee incomplete)"],
          ["1", "Calculee seulement si toutes les evaluations sont notees"],
        ])}
        {choix("matiere_non_evaluee", "Matiere sans aucune note (moyenne generale)", [
          ["exclure", "Ignoree et signalee comme incomplete (recommande)"],
          ["zero", "Comptee 0 : coefficient conserve au diviseur (pratique du bulletin papier)"],
        ], "Le bulletin papier compte l'EPS non notee dans le diviseur : choisissez « Comptee 0 » pour retrouver ses moyennes.")}
        {choix("ex_aequo", "Classement : egalite de moyenne", [
          ["meme_rang", "Meme rang (1, 2, 2, 4)"], ["alphabetique", "Depart. par ordre alphabetique"],
        ], "Le classement est etabli sur la moyenne arrondie au centieme.")}
        {texte("poids_trimestres", "Poids des trimestres (moyenne annuelle)", "Trois nombres separes par des virgules, ex. 1,1,1.")}
      </section>

      <button type="submit" disabled={enCours} className={BOUTON_PRIMAIRE}>
        <Save size={15} /> Enregistrer
      </button>
    </form>
  );
}
