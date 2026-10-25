import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  Banknote, CalendarClock, ClipboardCheck, GraduationCap, MessageCircle, School, Trophy, UserCog, Wallet,
} from "lucide-react";
import { api, messageErreur } from "../services/api";
import { CarteKpi } from "../composants/CarteKpi";
import { useAuth } from "../hooks/useAuth";
import { CARTE } from "../composants/styles";
import { formaterDate, formaterMontant, UNITE_HEURE } from "../services/fichiers";

import { tr, FLECHE, estArabe, tx } from "../i18n";
type Section = Record<string, any>;
interface Donnees {
  role: string;
  date: string;
  annee_scolaire: { id: number; libelle: string } | null;
  sections: Record<string, Section>;
}

function Bloc({ titre, lien, children }: { titre: string; lien?: { vers: string; texte: string }; children: ReactNode }) {
  return (
    <div className={CARTE}>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-texte">{titre}</h2>
        {lien && <Link to={lien.vers} className="text-xs text-entete hover:underline">{lien.texte} {FLECHE}</Link>}
      </div>
      {children}
    </div>
  );
}

function Vide({ texte }: { texte: string }) {
  return <p className="text-sm text-texte-attenue">{texte}</p>;
}

function Liste({ lignes }: { lignes: ReactNode[] }) {
  return (
    <ul className="divide-y divide-bordure text-sm">
      {lignes.map((ligne, i) => <li key={i} className="py-1.5">{ligne}</li>)}
    </ul>
  );
}

const pourcent = (v: number | null | undefined) => (v === null || v === undefined ? "-" : `${v}${estArabe ? "%" : " %"}`);

function Effectifs({ s }: { s: Section }) {
  return (
    <Bloc titre={tr("Effectifs par classe")} lien={{ vers: "/classes", texte: tr("Classes") }}>
      {s.par_classe.length === 0 ? <Vide texte={tr("Aucune classe pour l'annee en cours.")} /> : (
        <ul className="space-y-2">
          {s.par_classe.map((c: any) => (
            <li key={c.classe} className="text-sm">
              <div className="flex justify-between"><span>{c.classe}</span><span dir="ltr" className="text-texte-attenue">{c.effectif} / {c.capacite}</span></div>
              <div className="mt-0.5 h-1.5 rounded bg-fond-barre">
                <div className={`h-1.5 rounded ${c.effectif >= c.capacite ? "bg-accent-rouge" : "bg-entete"}`}
                     style={{ width: `${Math.min(100, c.capacite ? (100 * c.effectif) / c.capacite : 0)}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Bloc>
  );
}

function PresencesEtudiants({ s }: { s: Section }) {
  return (
    <Bloc titre={tr("Presences des etudiants ({0} derniers jours)", s.periode_jours)} lien={{ vers: "/presences/historique", texte: tr("Historique") }}>
      {s.total === 0 ? <Vide texte={tr("Aucune presence validee sur la periode.")} /> : (
        <>
          <p className="mb-2 text-sm">
            {tx("Taux de presence : {0} - {1} present(s), {2} absent(s), {3} retard(s)", <b>{pourcent(s.taux_presence)}</b>, s.presents, s.absents, s.retards)}
          </p>
          {s.dernieres_absences.length > 0 && (
            <Liste lignes={s.dernieres_absences.map((a: any) => (
              <span>{a.etudiant} <span className="text-texte-attenue">- {a.classe}, {a.matiere}, {formaterDate(a.date)} {a.heure}</span></span>
            ))} />
          )}
        </>
      )}
    </Bloc>
  );
}

function PresencesProfesseurs({ s }: { s: Section }) {
  return (
    <Bloc titre={tr("Presences des professeurs ({0} derniers jours)", s.periode_jours)} lien={{ vers: "/presences-professeurs", texte: tr("Detail") }}>
      <p className="text-sm">
        {tx("Taux de realisation : {0} - {1} seance(s) effectuee(s), {2} absence(s)", <b>{pourcent(s.taux_realisation)}</b>, s.seances_effectuees, s.absences)}
      </p>
      <p className="mt-1 text-sm text-texte-attenue">{tr("{0} h enseignees - {1} seance(s) a renseigner", s.heures_effectuees, s.a_renseigner)}</p>
    </Bloc>
  );
}

function Notifications({ s }: { s: Section }) {
  return (
    <Bloc titre={tr("Notifications WhatsApp aux parents")} lien={{ vers: "/notifications", texte: tr("Historique") }}>
      {!s.actif && <p className="mb-1 text-xs text-amber-700">{tr("Envoi automatique desactive (Parametres).")}</p>}
      <div className="grid grid-cols-3 gap-2 text-center text-sm">
        <div><p className="text-xl font-bold text-amber-700">{s.en_attente}</p><p className="text-xs text-texte-attenue">{tr("En attente")}</p></div>
        <div><p className="text-xl font-bold text-accent-rouge">{s.echecs}</p><p className="text-xs text-texte-attenue">{tr("En echec")}</p></div>
        <div><p className="text-xl font-bold text-accent-vert">{s.envoyees}</p><p className="text-xs text-texte-attenue">{tr("Envoyees")}</p></div>
      </div>
    </Bloc>
  );
}

function Remuneration({ s }: { s: Section }) {
  return (
    <Bloc titre={tr("Remuneration des professeurs")} lien={{ vers: "/remuneration", texte: tr("Etat mensuel") }}>
      <p className="text-sm">{tx("{0} h effectuees ce mois - {1} restant a payer", s.heures_du_mois, <b>{formaterMontant(s.montants_dus)}</b>)}</p>
      {s.releves_a_valider > 0 && <p className="mt-1 text-xs text-amber-700">{tr("{0} releve(s) a verifier et valider.", s.releves_a_valider)}</p>}
      {s.derniers_paiements.length > 0 && (
        <div className="mt-2">
          <Liste lignes={s.derniers_paiements.map((p: any) => (
            <span>{p.professeur} <span className="text-texte-attenue">- {formaterMontant(p.montant)}, {formaterDate(p.date)}</span></span>
          ))} />
        </div>
      )}
    </Bloc>
  );
}

function Scolarite({ s }: { s: Section }) {
  return (
    <Bloc titre={tr("Scolarite encaissee")} lien={{ vers: "/scolarite", texte: tr("Paiements") }}>
      <p className="text-sm">{tx("{0} ce mois ({1} paiement(s))", <b>{formaterMontant(s.encaisse_mois)}</b>, s.nombre_paiements_mois)}</p>
      {s.derniers_paiements.length > 0 && (
        <div className="mt-2">
          <Liste lignes={s.derniers_paiements.map((p: any) => (
            <span>{p.etudiant} <span className="text-texte-attenue">- {p.classe}, {formaterMontant(p.montant)}, {formaterDate(p.date)}</span></span>
          ))} />
        </div>
      )}
    </Bloc>
  );
}

function EmploiDuTempsBloc({ s }: { s: Section }) {
  return (
    <Bloc titre={tr("Emploi du temps")} lien={{ vers: "/emplois-du-temps", texte: tr("Ouvrir") }}>
      {s.publie ? (
        <p className="text-sm">{tx("Publie : {0} ({1} seances, {2})", <b>{s.publie.nom}</b>, s.publie.seances, formaterDate(s.publie.publie_le))}</p>
      ) : <p className="text-sm text-amber-700">{tr("Aucun emploi du temps publie pour cette annee.")}</p>}
      <p className="mt-1 text-sm text-texte-attenue">{tr("{0} brouillon(s)", s.brouillons)}</p>
      {s.derniere_generation && (
        <p className="mt-1 text-sm">{tx("Derniere generation automatique : {0}", s.derniere_generation.publiable
            ? <span className="text-accent-vert">{tr("sans conflit")}</span>
            : <span className="text-accent-rouge">{tr("{0} conflit(s) a resoudre", s.derniere_generation.conflits)}</span>)}</p>
      )}
    </Bloc>
  );
}

function Evaluations({ s }: { s: Section }) {
  return (
    <>
      <Bloc titre={tr("Prochaines evaluations")} lien={{ vers: "/notes", texte: tr("Notes") }}>
        {s.prochaines.length === 0 ? <Vide texte={tr("Aucune evaluation programmee.")} /> : (
          <Liste lignes={s.prochaines.map((e: any) => (
            <span>{formaterDate(e.date)} - {e.libelle} <span className="text-texte-attenue">({e.matiere}, {e.classe})</span></span>
          ))} />
        )}
      </Bloc>
      <Bloc titre={tr("Notes a saisir - trimestre {0}", s.trimestre)} lien={{ vers: "/notes", texte: tr("Saisir") }}>
        {s.notes_manquantes.length === 0 ? <Vide texte={tr("Aucune note manquante sur les evaluations passees.")} /> : (
          <Liste lignes={s.notes_manquantes.map((e: any) => (
            <span>{tx("{0} - {1} ({2}) : {3} manquante(s)", e.classe, e.matiere, e.libelle, <b className="text-amber-700">{e.manquantes}</b>)}</span>
          ))} />
        )}
      </Bloc>
      <Bloc titre={tr("Resultats et bulletins")} lien={{ vers: "/resultats", texte: tr("Resultats") }}>
        <p className="mb-1 text-sm">{tr("{0} classe(s) / trimestre(s) valide(s), bulletins prets a imprimer.", s.bulletins_prets)}</p>
        {s.resultats_a_valider.length === 0 ? <Vide texte={tr("Aucun resultat en attente de validation.")} /> : (
          <Liste lignes={s.resultats_a_valider.map((r: any) => <span>{tx("{0} - trimestre {1} {2}", r.classe, r.trimestre, <span className="text-amber-700">{tr("a valider")}</span>)}</span>)} />
        )}
      </Bloc>
    </>
  );
}

function MonEspace({ s }: { s: Section }) {
  if (!s.fiche_liee) {
    return <Bloc titre={tr("Mon espace")}><Vide texte={tr("Votre compte n'est relie a aucune fiche professeur : contactez l'administration.")} /></Bloc>;
  }
  return (
    <>
      <Bloc titre={tr("Mes prochains cours")} lien={{ vers: "/emplois-du-temps", texte: tr("Emploi du temps") }}>
        {s.prochains_cours.length === 0 ? <Vide texte={tr("Aucun cours a venir (emploi du temps non publie ?).")} /> : (
          <Liste lignes={s.prochains_cours.map((c: any) => (
            <span>{formaterDate(c.date)} {c.debut}-{c.fin} - <b>{c.matiere}</b> <span className="text-texte-attenue">({c.classe}{c.salle ? tr(", salle {0}", c.salle) : ""})</span></span>
          ))} />
        )}
      </Bloc>
      <Bloc titre={tr("Listes d'appel a valider")} lien={{ vers: "/presences", texte: tr("Presences") }}>
        {s.seances_a_valider.nombre === 0 ? <Vide texte={tr("Toutes vos listes d'appel sont validees.")} /> : (
          <>
            <p className="mb-1 text-sm text-amber-700">{tr("{0} seance(s) a valider.", s.seances_a_valider.nombre)}</p>
            <Liste lignes={s.seances_a_valider.liste.map((x: any) => <span>{formaterDate(x.date)} - {x.matiere} ({x.classe})</span>)} />
          </>
        )}
      </Bloc>
      <Bloc titre={tr("Notes a saisir")} lien={{ vers: "/notes", texte: tr("Saisie des notes") }}>
        {s.saisie_notes.length === 0 ? <Vide texte={tr("Aucune note en attente.")} /> : (
          <Liste lignes={s.saisie_notes.map((e: any) => <span>{tx("{0} - {1} ({2}) : {3} manquante(s)", e.classe, e.matiere, e.libelle, <b className="text-amber-700">{e.manquantes}</b>)}</span>)} />
        )}
      </Bloc>
      <Bloc titre={tr("Mes classes et matieres")}>
        {s.mes_classes.length === 0 ? <Vide texte={tr("Aucune affectation pour l'annee en cours.")} /> : (
          <Liste lignes={s.mes_classes.map((c: any) => <span>{c.matiere} <span className="text-texte-attenue">- {c.classe}</span></span>)} />
        )}
      </Bloc>
      <Bloc titre={tr("Mes heures")} lien={{ vers: "/ma-remuneration", texte: tr("Ma remuneration") }}>
        <p className="mb-1 text-sm">{tx("{0} h effectuees ce mois-ci.", <b>{s.heures_du_mois}</b>)}</p>
        {s.historique_seances.length > 0 && (
          <Liste lignes={s.historique_seances.map((h: any) => <span>{formaterDate(h.date)} - {h.matiere} ({h.classe}) <span className="text-texte-attenue">{h.heures} {UNITE_HEURE}</span></span>)} />
        )}
        {s.remuneration && (
          <p className="mt-2 border-t border-bordure pt-2 text-sm">{tr("Dernier releve valide : net {0}, paye {1}, solde {2}.", formaterMontant(s.remuneration.net), formaterMontant(s.remuneration.paye), formaterMontant(s.remuneration.solde))}</p>
        )}
      </Bloc>
    </>
  );
}

/** Tableau de bord base sur des donnees reelles : le serveur n'envoie a chaque role que ses sections. */
export function PageTableauDeBord() {
  const { utilisateur } = useAuth();
  const [donnees, setDonnees] = useState<Donnees | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    api.get("/tableau-de-bord/").then(({ data }) => setDonnees(data)).catch((err) => setErreur(messageErreur(err)));
  }, []);

  const s = donnees?.sections ?? {};
  return (
    <div>
      <div className="mb-4">
        <h1 className="text-lg font-semibold text-texte">{tr("Bonjour {0}", utilisateur?.prenom || utilisateur?.identifiant)}</h1>
        {donnees && (
          <p className="text-sm text-texte-attenue">
            {donnees.annee_scolaire ? tr("Annee scolaire {0}", donnees.annee_scolaire.libelle) : tr("Aucune annee scolaire")} - {formaterDate(donnees.date)}
          </p>
        )}
      </div>
      {erreur && <p className="text-sm text-accent-rouge">{erreur}</p>}
      {!donnees && !erreur && <p className="text-sm text-texte-attenue">{tr("Chargement...")}</p>}

      {(s.effectifs || s.structure) && (
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {s.effectifs && <CarteKpi valeur={s.effectifs.etudiants_actifs} libelle={tr("Etudiants actifs")} icone={<GraduationCap size={22} />} accent="vert" />}
          {s.structure && <CarteKpi valeur={s.structure.professeurs_actifs} libelle={tr("Professeurs actifs")} icone={<UserCog size={22} />} />}
          {s.structure && <CarteKpi valeur={s.structure.classes} libelle={tr("Classes ouvertes")} icone={<School size={22} />} />}
          {s.structure && <CarteKpi valeur={s.structure.matieres} libelle={tr("Matieres")} icone={<ClipboardCheck size={22} />} />}
        </div>
      )}
      {(s.scolarite || s.remuneration || s.presences_etudiants || s.notifications) && (
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {s.presences_etudiants && <CarteKpi valeur={pourcent(s.presences_etudiants.taux_presence)} libelle={tr("Taux de presence (30 j)")} icone={<ClipboardCheck size={22} />} accent="vert" />}
          {s.notifications && <CarteKpi valeur={s.notifications.echecs + s.notifications.en_attente} libelle={tr("Notifications a traiter")} icone={<MessageCircle size={22} />} accent={s.notifications.echecs ? "rouge" : "neutre"} />}
          {s.scolarite && <CarteKpi valeur={formaterMontant(s.scolarite.encaisse_mois)} libelle={tr("Scolarite encaissee ce mois")} icone={<Wallet size={22} />} accent="vert" />}
          {s.remuneration && <CarteKpi valeur={formaterMontant(s.remuneration.montants_dus)} libelle={tr("Du aux professeurs")} icone={<Banknote size={22} />} accent={Number(s.remuneration.montants_dus) > 0 ? "rouge" : "neutre"} />}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {s.effectifs && <Effectifs s={s.effectifs} />}
        {s.presences_etudiants && <PresencesEtudiants s={s.presences_etudiants} />}
        {s.presences_professeurs && <PresencesProfesseurs s={s.presences_professeurs} />}
        {s.notifications && <Notifications s={s.notifications} />}
        {s.emploi_du_temps && <EmploiDuTempsBloc s={s.emploi_du_temps} />}
        {s.evaluations && <Evaluations s={s.evaluations} />}
        {s.remuneration && <Remuneration s={s.remuneration} />}
        {s.scolarite && <Scolarite s={s.scolarite} />}
        {s.mon_espace && <MonEspace s={s.mon_espace} />}
      </div>
      <p className="mt-4 flex items-center gap-1 text-xs text-texte-attenue">
        <CalendarClock size={12} /> <Trophy size={12} /> {tr("Indicateurs calcules en temps reel a partir des donnees de la base.")}
      </p>
    </div>
  );
}
