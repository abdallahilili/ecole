"""Regles metier des emplois du temps : verification, generation, publication."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.commun.audit import enregistrer_audit
from apps.commun.exceptions import ErreurMetier
from . import donnees as pont
from .conflits import Sc, conflits_de, detecter, hhmm
from .genetique import Probleme, diagnostiquer, resoudre
from .models import (
    EmploiDuTemps, NOMS_JOURS, OrigineEmploi, SeanceProgrammee, StatutEmploi, VersionEmploiDuTemps,
)

DUREE_MAX_GENERATION = 120  # secondes


def _seances(emploi):
    return list(emploi.seances.select_related("classe", "groupe", "matiere", "professeur", "salle"))


def emplois_de_reference(annee, hors_classe=None):
    """Pour chaque classe (sauf `hors_classe`) : son emploi du temps publie, a defaut son dernier brouillon."""
    choisis = {}
    emplois = EmploiDuTemps.objects.filter(annee_scolaire=annee, classe__isnull=False).exclude(statut=StatutEmploi.ARCHIVE)
    if hors_classe is not None:
        emplois = emplois.exclude(classe=hors_classe)
    for emploi in emplois.order_by("cree_le", "id"):
        courant = choisis.get(emploi.classe_id)
        if courant is None or emploi.statut == StatutEmploi.PUBLIE or courant.statut != StatutEmploi.PUBLIE:
            choisis[emploi.classe_id] = emploi
    return list(choisis.values())


def seances_hors_classe(annee, classe):
    """Cours deja programmes pour les AUTRES classes : ils occupent les memes professeurs et salles."""
    return [s for autre in emplois_de_reference(annee, hors_classe=classe) for s in _seances(autre)]


def seances_des_autres_classes(emploi):
    """Les cours des autres classes vus depuis `emploi` ; vide pour un emploi qui n'est pas celui d'une classe."""
    return seances_hors_classe(emploi.annee_scolaire, emploi.classe) if emploi.classe_id is not None else []


def analyser(emploi, publication=False):
    """(cadre, seances de l'emploi, conflits) ; pour l'emploi d'une classe, les conflits avec les autres classes comptent."""
    cadre, _, _ = pont.charger_cadre(emploi.annee_scolaire)
    propres, externes = _seances(emploi), seances_des_autres_classes(emploi)
    pont.completer_noms(cadre, propres + externes)
    conflits = detecter([pont.vers_sc(s) for s in propres + externes], cadre, publication)
    if externes:       # les defauts propres aux autres classes ne regardent pas cet emploi
        cles = {s.pk for s in propres}
        conflits = [c for c in conflits if cles & set(c["seances"])]
    return cadre, propres, conflits


def verifier_emploi(emploi, publication=False):
    """Tous les conflits obligatoires de l'emploi du temps (liste vide = valide)."""
    return analyser(emploi, publication)[2]


def exiger_brouillon(emploi):
    if emploi.statut != StatutEmploi.BROUILLON:
        raise ErreurMetier(
            "Cet emploi du temps est publie ou archive : dupliquez-le pour creer un brouillon modifiable."
        )


def conflits_pour(emploi, donnees, exclure_pk=None):
    """Conflits qu'une seance (nouvelle ou deplacee) creerait ; `donnees` : valeurs validees."""
    cadre, _, _ = pont.charger_cadre(emploi.annee_scolaire)
    autres = _seances(emploi) + seances_des_autres_classes(emploi)
    pont.completer_noms(cadre, autres)
    for objet in ("professeur", "matiere", "classe", "groupe", "salle"):
        valeur = donnees.get(objet)
        if valeur is not None:
            cadre.noms[("prof" if objet == "professeur" else objet, valeur.pk)] = getattr(valeur, "nom_complet", None) or getattr(valeur, "nom_affiche", None) or valeur.nom
    nouvelle = Sc(
        cle="nouvelle", classe=donnees["classe"].pk, groupe=donnees["groupe"].pk if donnees.get("groupe") else None,
        matiere=donnees["matiere"].pk, professeur=donnees["professeur"].pk,
        salle=donnees["salle"].pk if donnees.get("salle") else None, jour=donnees["jour"],
        debut=pont.minutes(donnees["heure_debut"]), fin=pont.minutes(donnees["heure_fin"]),
    )
    existantes = [pont.vers_sc(s) for s in autres if s.pk != exclure_pk]
    return conflits_de("nouvelle", detecter(existantes + [nouvelle], cadre))


def exiger_sans_conflit(conflits):
    if conflits:
        raise ErreurMetier(" ".join(c["message"] for c in conflits), code="conflit", donnees={"conflits": conflits})


def generer_emploi(annee, utilisateur, nom, graine=None, temps_max=20, population=30, generations=200):
    """Genere un BROUILLON par algorithme genetique. Le rapport conserve le score,
    les diagnostics (ressources insuffisantes) et les conflits restants : un
    brouillon qui contient encore des conflits n'est pas publiable."""
    temps_max = max(1, min(float(temps_max), DUREE_MAX_GENERATION))
    configuration = pont.configuration_pour(annee)
    cadre, preferences, salles = pont.charger_cadre(annee, configuration)
    unites, diagnostics = pont.construire_unites(annee, cadre, salles)
    if not unites:
        raise ErreurMetier(
            "Aucune seance a programmer : affectez des professeurs aux matieres des classes "
            "(Affectations) et renseignez le nombre de seances et le volume horaire de chaque matiere.",
            donnees={"diagnostics": diagnostics},
        )
    probleme = Probleme(
        unites, cadre, preferences,
        max_jour=configuration.max_creneaux_jour_professeur, max_consecutifs=configuration.max_creneaux_consecutifs_professeur,
    )
    diagnostics += diagnostiquer(probleme)
    solution = resoudre(probleme, graine=graine, population=population, generations=generations, temps_max=temps_max)

    duree = cadre.duree_creneau
    seances = [
        SeanceProgrammee(
            classe_id=u.classe, groupe_id=u.groupe, matiere_id=u.matiere, professeur_id=u.professeur, salle_id=salle,
            jour=jour, heure_debut=pont.en_heure(cadre.debut + depart * duree),
            heure_fin=pont.en_heure(cadre.debut + (depart + u.longueur) * duree),
        )
        for u, (jour, depart, salle) in zip(unites, solution.genes)
    ]
    with transaction.atomic():
        emploi = EmploiDuTemps.objects.create(
            annee_scolaire=annee, nom=nom, origine=OrigineEmploi.GENETIQUE, cree_par=utilisateur)
        for s in seances:
            s.emploi = emploi
        SeanceProgrammee.objects.bulk_create(seances)
        conflits = verifier_emploi(emploi, publication=True)
        emploi.rapport = {
            "unites": len(unites), "seances_creees": len(seances), "violations": solution.violations,
            "penalites": solution.penalites, "generations": solution.generations, "duree_s": solution.duree,
            "arret": solution.arret, "graine": graine, "diagnostics": diagnostics,
            "conflits": [c["message"] for c in conflits], "publiable": not conflits,
        }
        emploi.save(update_fields=["rapport"])
        enregistrer_audit(utilisateur, "GENERATION", "EmploiDuTemps", emploi.pk,
                          nouvelle_valeur={k: emploi.rapport[k] for k in ("unites", "violations", "penalites", "generations")})
    return emploi


def _instantane(emploi):
    return [
        {
            "classe": s.classe.nom, "groupe": s.groupe.nom if s.groupe else None, "matiere": s.matiere.nom_affiche,
            "professeur": s.professeur.nom_complet, "salle": s.salle.nom if s.salle else None,
            "jour": s.jour, "jour_nom": NOMS_JOURS[s.jour], "heure_debut": f"{s.heure_debut:%H:%M}", "heure_fin": f"{s.heure_fin:%H:%M}",
        }
        for s in _seances(emploi)
    ]


def publier_emploi(emploi, utilisateur, commentaire=""):
    exiger_brouillon(emploi)
    if not emploi.seances.exists():
        raise ErreurMetier("Cet emploi du temps est vide : rien a publier.")
    conflits = verifier_emploi(emploi, publication=True)
    if conflits:
        raise ErreurMetier(
            f"Publication impossible : {len(conflits)} conflit(s) non resolu(s). " + " ".join(c["message"] for c in conflits[:5]),
            code="conflit", donnees={"conflits": conflits},
        )
    with transaction.atomic():
        # Un seul emploi publie par classe (et un seul emploi sans classe) : l'ancien est archive.
        EmploiDuTemps.objects.filter(annee_scolaire=emploi.annee_scolaire, statut=StatutEmploi.PUBLIE, classe=emploi.classe).update(
            statut=StatutEmploi.ARCHIVE)
        emploi.statut = StatutEmploi.PUBLIE
        emploi.publie_le = timezone.now()
        emploi.save(update_fields=["statut", "publie_le"])
        dernier = VersionEmploiDuTemps.objects.filter(annee_scolaire=emploi.annee_scolaire).order_by("-numero").first()
        version = VersionEmploiDuTemps.objects.create(
            annee_scolaire=emploi.annee_scolaire, emploi=emploi, numero=(dernier.numero + 1) if dernier else 1,
            contenu=_instantane(emploi), commentaire=commentaire[:255], publie_par=utilisateur,
        )
        enregistrer_audit(utilisateur, "PUBLICATION", "EmploiDuTemps", emploi.pk,
                          nouvelle_valeur={"version": version.numero, "seances": emploi.seances.count()})
    return version


def dupliquer_emploi(emploi, utilisateur, nom=None):
    with transaction.atomic():
        copie = EmploiDuTemps.objects.create(
            annee_scolaire=emploi.annee_scolaire, classe=emploi.classe, nom=nom or f"{emploi.nom} (copie)", origine=emploi.origine,
            cree_par=utilisateur,
        )
        SeanceProgrammee.objects.bulk_create([
            SeanceProgrammee(
                emploi=copie, classe_id=s.classe_id, groupe_id=s.groupe_id, matiere_id=s.matiere_id,
                professeur_id=s.professeur_id, salle_id=s.salle_id, jour=s.jour, heure_debut=s.heure_debut, heure_fin=s.heure_fin,
            ) for s in emploi.seances.all()
        ])
        enregistrer_audit(utilisateur, "DUPLICATION", "EmploiDuTemps", copie.pk, nouvelle_valeur={"source": emploi.pk})
    return copie


# ----------------------------------------------------------------- consultation

def vue_emploi(emploi, filtres):
    """Donnees de la grille hebdomadaire (avec conflits), filtrables par classe,
    groupe, professeur, salle ou matiere."""
    cadre, seances, conflits = analyser(emploi)
    par_seance = {}
    for conflit in conflits:
        for cle in conflit["seances"]:
            par_seance.setdefault(cle, []).append(conflit["message"])

    champs = {"classe": "classe_id", "groupe": "groupe_id", "professeur": "professeur_id", "salle": "salle_id", "matiere": "matiere_id"}
    retenues = [s for s in seances if all(not filtres.get(f) or str(getattr(s, champ)) == str(filtres[f]) for f, champ in champs.items())]

    creneaux = []
    for index in range((cadre.fin - cadre.debut) // cadre.duree_creneau):
        debut = cadre.debut + index * cadre.duree_creneau
        fin = debut + cadre.duree_creneau
        creneaux.append({"index": index, "debut": hhmm(debut), "fin": hhmm(fin),
                         "pause": any(debut < b and a < fin for a, b in cadre.pauses)})
    return {
        "emploi": {"id": emploi.pk, "nom": emploi.nom, "statut": emploi.statut, "origine": emploi.origine,
                   "annee_scolaire": emploi.annee_scolaire_id, "classe": emploi.classe_id, "rapport": emploi.rapport,
                   "modifiable": emploi.statut == StatutEmploi.BROUILLON},
        "cadre": {"jours": [{"id": j, "nom": NOMS_JOURS[j]} for j in sorted(cadre.jours)], "creneaux": creneaux,
                  "duree_creneau": cadre.duree_creneau, "debut": hhmm(cadre.debut), "fin": hhmm(cadre.fin),
                  "salles_contraintes": cadre.salles_contraintes},
        "seances": [{
            "id": s.pk, "classe": s.classe_id, "classe_nom": s.classe.nom, "groupe": s.groupe_id,
            "groupe_nom": s.groupe.nom if s.groupe else None, "matiere": s.matiere_id, "matiere_nom": s.matiere.nom_affiche,
            "professeur": s.professeur_id, "professeur_nom": s.professeur.nom_complet, "salle": s.salle_id,
            "salle_nom": s.salle.nom if s.salle else None, "jour": s.jour, "heure_debut": f"{s.heure_debut:%H:%M}",
            "heure_fin": f"{s.heure_fin:%H:%M}", "conflits": par_seance.get(s.pk, []),
        } for s in retenues],
        "nb_conflits": len(conflits),
    }


# ----------------------------------------------- liaison avec les presences

def generer_seances_presence(emploi, du, au, utilisateur):
    """Cree les seances de presence (module Presences) a partir de l'emploi du temps
    PUBLIE, pour chaque date entre `du` et `au` (hors vacances) ; sans doublon."""
    from apps.presences.models import Seance

    if emploi.statut != StatutEmploi.PUBLIE:
        raise ErreurMetier("Seul l'emploi du temps publie peut generer des seances.")
    annee = emploi.annee_scolaire
    if du > au:
        raise ErreurMetier("La date de debut doit preceder la date de fin.")
    if du < annee.date_debut or au > annee.date_fin:
        raise ErreurMetier(f"Les dates doivent etre comprises dans l'annee scolaire ({annee.date_debut:%d/%m/%Y} - {annee.date_fin:%d/%m/%Y}).")
    programmees = list(emploi.seances.select_related("classe", "matiere", "professeur"))
    creees = ignorees = 0
    with transaction.atomic():
        jour = du
        while jour <= au:
            en_vacances = any(
                debut and fin and debut <= jour <= fin
                for debut, fin in ((annee.debut_vacances, annee.fin_vacances), (annee.debut_vacances2, annee.fin_vacances2)))
            if not en_vacances:
                for p in (p for p in programmees if p.jour == jour.weekday()):
                    _, nouvelle = Seance.objects.get_or_create(
                        classe=p.classe, matiere=p.matiere, date=jour, heure_debut=p.heure_debut,
                        defaults={"annee_scolaire": annee, "professeur": p.professeur, "heure_fin": p.heure_fin, "cree_par": utilisateur},
                    )
                    creees += nouvelle
                    ignorees += not nouvelle
            jour += timedelta(days=1)
        enregistrer_audit(utilisateur, "GENERATION_SEANCES", "EmploiDuTemps", emploi.pk,
                          nouvelle_valeur={"du": str(du), "au": str(au), "creees": creees})
    return {"creees": creees, "ignorees": ignorees}
