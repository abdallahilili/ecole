"""Creation guidee de l'emploi du temps d'UNE classe.

L'utilisateur choisit la classe, puis des professeurs : pour chacun, ses matieres avec le nombre d'heures par semaine
et ses creneaux de disponibilite. La creation enregistre les affectations (professeur - matiere - classe) et les
disponibilites, decoupe chaque matiere en seances de 2 h (plus une seance d'1 h si le volume est impair), puis place les
seances sans jamais chevaucher les cours des autres classes, sans deux seances successives d'un professeur avec la meme
classe et en dehors des creneaux disponibles du professeur. Si aucune solution sans conflit n'existe, RIEN n'est cree."""

from collections import defaultdict
from datetime import datetime

from django.db import transaction

from apps.commun.audit import enregistrer_audit
from apps.commun.exceptions import ErreurMetier
from apps.professeurs.models import AffectationProfesseur, Professeur
from apps.referentiels.models import AffectationMatiereClasse
from . import donnees as pont
from . import services
from .conflits import Sc, detecter
from .genetique import Probleme, diagnostiquer, resoudre
from .models import DisponibiliteProfesseur, EmploiDuTemps, OrigineEmploi, SeanceProgrammee, TypeDisponibilite

HEURES_MAX = 40


def _entier(valeur):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def _heure(texte):
    try:
        return datetime.strptime(str(texte)[:5], "%H:%M").time()
    except ValueError:
        return None


def donnees_assistant(classe):
    """Ce dont l'assistant a besoin : matieres de la classe, professeurs avec leurs disponibilites deja saisies,
    affectations existantes (pour pre-remplir) et cadre horaire (pour guider la saisie)."""
    annee = classe.annee_scolaire
    configuration = pont.configuration_pour(annee)
    liens = list(AffectationMatiereClasse.objects.filter(classe=classe).select_related("matiere").order_by("id"))
    volumes = {b.matiere_id: b.volume_horaire_hebdo for b in liens}
    disponibilites = defaultdict(list)
    for d in DisponibiliteProfesseur.objects.filter(type=TypeDisponibilite.DISPONIBLE).order_by("jour", "heure_debut"):
        disponibilites[d.professeur_id].append({"jour": d.jour, "debut": f"{d.heure_debut:%H:%M}", "fin": f"{d.heure_fin:%H:%M}"})
    professeurs = list(Professeur.objects.filter(statut="ACTIF").order_by("nom", "prenom"))
    actifs = {p.id for p in professeurs}
    affectes, vues = defaultdict(list), set()
    for a in AffectationProfesseur.objects.filter(classe=classe, annee_scolaire=annee, groupe__isnull=True).order_by("id"):
        if a.matiere_id in vues or a.matiere_id not in volumes or a.professeur_id not in actifs:
            continue
        vues.add(a.matiere_id)
        affectes[a.professeur_id].append({"matiere": a.matiere_id, "heures": max(1, round(float(volumes[a.matiere_id])))})
    return {
        "classe": {"id": classe.id, "nom": classe.nom, "annee_scolaire": annee.id, "annee_libelle": annee.libelle},
        "nom_propose": f"Emploi {classe.nom}",
        "matieres": [{"id": b.matiere_id, "nom": b.matiere.nom_affiche} for b in liens],
        "professeurs": [{"id": p.id, "nom": p.nom_complet, "specialite": p.specialite,
                         "disponibilites": disponibilites.get(p.id, [])} for p in professeurs],
        "initial": [{"professeur": professeur, "matieres": matieres} for professeur, matieres in affectes.items()],
        "cadre": {"jours": sorted(configuration.liste_jours()), "debut": f"{configuration.heure_debut:%H:%M}",
                  "fin": f"{configuration.heure_fin:%H:%M}", "duree_creneau": configuration.duree_creneau,
                  "pauses": configuration.pauses or []},
    }


def _lire_demande(classe, professeurs, configuration):
    """Controle la saisie ; retourne (demande [(professeur, matiere, heures)], plages {professeur: [(jour, debut, fin)]}).
    Toutes les erreurs sont rapportees ensemble."""
    erreurs = []
    if not isinstance(professeurs, list):
        raise ErreurMetier("Champ 'professeurs' (liste) attendu.")
    liens = {b.matiere_id: b for b in AffectationMatiereClasse.objects.filter(classe=classe).select_related("matiere")}
    actifs = {p.id: p for p in Professeur.objects.filter(statut="ACTIF")}
    demande, plages, vus, confiees = [], {}, set(), set()
    for bloc in professeurs:
        identifiant = _entier(bloc.get("professeur"))
        professeur = actifs.get(identifiant)
        if professeur is None:
            erreurs.append("Professeur inconnu.")
            continue
        if identifiant in vus:
            erreurs.append(f"{professeur.nom_complet} apparait plusieurs fois dans la liste.")
            continue
        vus.add(identifiant)
        for ligne in bloc.get("matieres") or []:
            matiere, heures = _entier(ligne.get("matiere")), _entier(ligne.get("heures"))
            lien = liens.get(matiere)
            if lien is None:
                erreurs.append("Matiere inconnue pour cette classe.")
                continue
            nom = f"{lien.matiere.nom_affiche} - {classe.nom}"
            if matiere in confiees:
                erreurs.append(f"{nom} : cette matiere est confiee a plusieurs professeurs.")
            elif heures is None or not 1 <= heures <= HEURES_MAX:
                erreurs.append(f"{nom} : le nombre d'heures par semaine doit etre un entier compris entre 1 et {HEURES_MAX}.")
            else:
                for duree in set(pont.seances_par_semaine(heures)):
                    if not configuration.duree_min_seance <= duree * 60 <= configuration.duree_max_seance:
                        erreurs.append(f"{nom} : une seance durerait {duree * 60} min, hors des limites "
                                       f"{configuration.duree_min_seance}-{configuration.duree_max_seance} min.")
                        break
                else:
                    demande.append((identifiant, matiere, heures))
                    confiees.add(matiere)
        plages[identifiant] = []
        for creneau in bloc.get("disponibilites") or []:
            jour, debut, fin = _entier(creneau.get("jour")), _heure(creneau.get("debut")), _heure(creneau.get("fin"))
            if jour is None or not 0 <= jour <= 6 or debut is None or fin is None or fin <= debut:
                erreurs.append(f"{professeur.nom_complet} : creneau de disponibilite invalide (l'heure de fin doit suivre l'heure de debut).")
            else:
                plages[identifiant].append((jour, debut, fin))
    if not erreurs and not demande:
        erreurs.append("Choisissez au moins un professeur avec une matiere et un nombre d'heures.")
    if erreurs:
        raise ErreurMetier(" ".join(erreurs))
    return demande, plages


def creer(classe, nom, professeurs, utilisateur, graine=None, temps_max=20, population=30, generations=200):
    """Cree le brouillon d'emploi du temps de `classe` et le retourne. Tout est fait dans une seule transaction : en cas
    d'erreur ou de conflit impossible a resoudre, ni affectation, ni disponibilite, ni emploi n'est enregistre."""
    annee = classe.annee_scolaire
    temps_max = max(1, min(float(temps_max), services.DUREE_MAX_GENERATION))
    configuration = pont.configuration_pour(annee)
    if 60 % configuration.duree_creneau:
        raise ErreurMetier("La duree d'un creneau doit diviser une heure pour programmer des seances de 1 h et de 2 h.")
    demande, plages = _lire_demande(classe, professeurs, configuration)

    with transaction.atomic():
        for identifiant, liste in plages.items():
            DisponibiliteProfesseur.objects.filter(professeur_id=identifiant, type=TypeDisponibilite.DISPONIBLE).delete()
            DisponibiliteProfesseur.objects.bulk_create([
                DisponibiliteProfesseur(professeur_id=identifiant, jour=jour, heure_debut=debut, heure_fin=fin,
                                        type=TypeDisponibilite.DISPONIBLE) for jour, debut, fin in liste])
        liens = {b.matiere_id: b for b in AffectationMatiereClasse.objects.filter(classe=classe).select_related("matiere")}
        for identifiant, matiere, heures in demande:
            lien = liens[matiere]
            lien.volume_horaire_hebdo, lien.nombre_seances_semaine = heures, len(pont.seances_par_semaine(heures))
            lien.save(update_fields=["volume_horaire_hebdo", "nombre_seances_semaine"])
            # L'affectation est creee automatiquement : un seul professeur par matiere et par classe.
            AffectationProfesseur.objects.filter(
                classe=classe, matiere_id=matiere, annee_scolaire=annee, groupe__isnull=True).exclude(professeur_id=identifiant).delete()
            AffectationProfesseur.objects.get_or_create(
                professeur_id=identifiant, matiere_id=matiere, classe=classe, groupe=None, annee_scolaire=annee)

        cadre, preferences, salles = pont.charger_cadre(annee, configuration)
        unites, diagnostics = pont.unites_classe(cadre, salles, classe, demande)
        confiees = {matiere for _, matiere, _ in demande}
        diagnostics += [f"{b.matiere.nom_affiche} - {classe.nom} : aucun professeur affecte." for b in liens.values()
                        if b.matiere_id not in confiees]
        autres = services.seances_hors_classe(annee, classe)
        pont.completer_noms(cadre, autres)
        fixes = [pont.vers_sc(s) for s in autres]
        probleme = Probleme(
            unites, cadre, preferences, max_jour=configuration.max_creneaux_jour_professeur,
            max_consecutifs=configuration.max_creneaux_consecutifs_professeur, fixes=fixes,
        )
        diagnostics += diagnostiquer(probleme)
        solution = resoudre(probleme, graine=graine, population=population, generations=generations, temps_max=temps_max)

        duree = cadre.duree_creneau
        nouvelles = [
            SeanceProgrammee(
                classe_id=u.classe, groupe_id=u.groupe, matiere_id=u.matiere, professeur_id=u.professeur, salle_id=salle, jour=jour,
                heure_debut=pont.en_heure(cadre.debut + depart * duree), heure_fin=pont.en_heure(cadre.debut + (depart + u.longueur) * duree),
            )
            for u, (jour, depart, salle) in zip(unites, solution.genes)
        ]
        # Meme controle qu'a la publication, limite aux cours de cette classe : au moindre conflit, rien n'est cree.
        candidates = [
            Sc(cle=("nouvelle", i), classe=s.classe_id, groupe=s.groupe_id, matiere=s.matiere_id, professeur=s.professeur_id,
               salle=s.salle_id, jour=s.jour, debut=pont.minutes(s.heure_debut), fin=pont.minutes(s.heure_fin))
            for i, s in enumerate(nouvelles)
        ]
        cles = {c.cle for c in candidates}
        conflits = [c["message"] for c in detecter(fixes + candidates, cadre, publication=True) if cles & set(c["seances"])]
        if conflits:
            raise ErreurMetier(
                "Impossible de programmer cette classe sans conflit. " + " ".join(diagnostics[:3] + conflits[:3]),
                code="conflit", donnees={"diagnostics": diagnostics, "conflits": conflits},
            )

        emploi = EmploiDuTemps.objects.create(
            annee_scolaire=annee, classe=classe, nom=nom, origine=OrigineEmploi.GENETIQUE, cree_par=utilisateur)
        for s in nouvelles:
            s.emploi = emploi
        SeanceProgrammee.objects.bulk_create(nouvelles)
        emploi.rapport = {
            "unites": len(unites), "seances_creees": len(nouvelles), "violations": solution.violations,
            "penalites": solution.penalites, "generations": solution.generations, "duree_s": solution.duree,
            "arret": solution.arret, "graine": graine, "diagnostics": diagnostics, "conflits": [], "publiable": True,
        }
        emploi.save(update_fields=["rapport"])
        enregistrer_audit(utilisateur, "GENERATION", "EmploiDuTemps", emploi.pk, nouvelle_valeur={
            "classe": classe.nom, "seances_creees": len(nouvelles), "penalites": solution.penalites,
            "demande": [{"professeur": p, "matiere": m, "heures": h} for p, m, h in demande]})
    return emploi
