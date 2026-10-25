"""Pont entre la base de donnees et les modules purs (conflits, genetique)."""

from collections import defaultdict
from datetime import time

from apps.etudiants.models import Inscription
from apps.professeurs.models import AffectationProfesseur
from apps.referentiels.models import AffectationMatiereClasse, Classe, Salle
from .conflits import Cadre, Sc, minutes
from .genetique import Unite
from .models import ConfigurationHoraires, DisponibiliteProfesseur, IndisponibiliteSalle, TypeDisponibilite


def en_heure(valeur):
    """Minutes depuis minuit -> datetime.time."""
    return time(valeur // 60, valeur % 60)


def _lire_hhmm(texte):
    heures, _, minutes_ = str(texte).partition(":")
    return int(heures) * 60 + int(minutes_ or 0)


def configuration_pour(annee):
    configuration, _ = ConfigurationHoraires.objects.get_or_create(annee_scolaire=annee)
    return configuration


def charger_cadre(annee, configuration=None):
    configuration = configuration or configuration_pour(annee)
    indispo_prof, preferences, indispo_salle = defaultdict(list), defaultdict(list), defaultdict(list)
    for d in DisponibiliteProfesseur.objects.all():
        cible = indispo_prof if d.type == TypeDisponibilite.INDISPONIBLE else preferences
        cible[d.professeur_id].append((d.jour, minutes(d.heure_debut), minutes(d.heure_fin)))
    for i in IndisponibiliteSalle.objects.all():
        indispo_salle[i.salle_id].append((i.jour, minutes(i.heure_debut), minutes(i.heure_fin)))

    salles = list(Salle.objects.all())
    for salle in salles:
        if not salle.disponible:  # salle declaree indisponible : jamais utilisable
            indispo_salle[salle.id] += [(jour, 0, 24 * 60) for jour in range(7)]

    effectifs = defaultdict(int)
    for classe_id, groupe_id in Inscription.objects.filter(annee_scolaire=annee, statut="ACTIVE").values_list("classe_id", "groupe_id"):
        effectifs[(classe_id, None)] += 1
        if groupe_id:
            effectifs[(classe_id, groupe_id)] += 1

    affectations = set()
    noms = {}
    for a in AffectationProfesseur.objects.filter(annee_scolaire=annee).select_related("professeur", "matiere", "classe", "groupe"):
        affectations.add((a.professeur_id, a.matiere_id, a.classe_id, a.groupe_id))
        noms[("prof", a.professeur_id)] = a.professeur.nom_complet
        noms[("matiere", a.matiere_id)] = a.matiere.nom_affiche
        noms[("classe", a.classe_id)] = a.classe.nom
        if a.groupe_id:
            noms[("groupe", a.groupe_id)] = a.groupe.nom
    for salle in salles:
        noms[("salle", salle.id)] = salle.nom

    cadre = Cadre(
        jours=set(configuration.liste_jours()), debut=minutes(configuration.heure_debut), fin=minutes(configuration.heure_fin),
        duree_creneau=configuration.duree_creneau, duree_min=configuration.duree_min_seance,
        duree_max=configuration.duree_max_seance,
        pauses=[(_lire_hhmm(p["debut"]), _lire_hhmm(p["fin"])) for p in configuration.pauses or []],
        indispo_prof=dict(indispo_prof), indispo_salle=dict(indispo_salle),
        capacites={s.id: s.capacite for s in salles}, effectifs=dict(effectifs), affectations=affectations, noms=noms,
    )
    return cadre, dict(preferences), salles


def completer_noms(cadre, seances):
    """Ajoute au cadre les noms utiles pour decrire des seances deja enregistrees."""
    for s in seances:
        cadre.noms.setdefault(("prof", s.professeur_id), s.professeur.nom_complet)
        cadre.noms.setdefault(("matiere", s.matiere_id), s.matiere.nom_affiche)
        cadre.noms.setdefault(("classe", s.classe_id), s.classe.nom)
        if s.groupe_id:
            cadre.noms.setdefault(("groupe", s.groupe_id), s.groupe.nom)
        if s.salle_id:
            cadre.noms.setdefault(("salle", s.salle_id), s.salle.nom)


def vers_sc(seance):
    return Sc(
        cle=seance.pk, classe=seance.classe_id, groupe=seance.groupe_id, matiere=seance.matiere_id,
        professeur=seance.professeur_id, salle=seance.salle_id, jour=seance.jour,
        debut=minutes(seance.heure_debut), fin=minutes(seance.heure_fin),
    )


def construire_unites(annee, cadre, salles):
    """Besoins hebdomadaires : une unite par seance a placer, d'apres les
    affectations des professeurs et, pour chaque (classe, matiere), le nombre
    de seances et le volume horaire hebdomadaires. Retourne (unites, diagnostics)."""
    diagnostics, unites, vus = [], [], set()
    besoins = {(b.classe_id, b.matiere_id): b for b in
               AffectationMatiereClasse.objects.filter(classe__annee_scolaire=annee)}
    classes_salle_principale = dict(Classe.objects.filter(annee_scolaire=annee).values_list("id", "salle_principale_id"))
    utilisables = [s for s in salles if s.disponible]
    ordre = AffectationProfesseur.objects.filter(annee_scolaire=annee).select_related("professeur", "matiere", "classe", "groupe") \
        .order_by("classe__nom", "matiere__nom", "id")
    for a in ordre:
        cle = (a.classe_id, a.groupe_id, a.matiere_id)
        nom = f"{a.matiere.nom_affiche} - {a.classe.nom}" + (f" ({a.groupe.nom})" if a.groupe_id else "")
        if cle in vus:
            diagnostics.append(f"{nom} : plusieurs professeurs affectes, seul le premier est programme ({a.professeur.nom_complet} ignore).")
            continue
        vus.add(cle)
        besoin = besoins.get((a.classe_id, a.matiere_id))
        if besoin is None or besoin.nombre_seances_semaine <= 0 or besoin.volume_horaire_hebdo <= 0:
            diagnostics.append(f"{nom} : nombre de seances ou volume horaire hebdomadaire non defini (Matieres > Coefficients).")
            continue
        minutes_seance = float(besoin.volume_horaire_hebdo) * 60 / besoin.nombre_seances_semaine
        longueur = max(1, round(minutes_seance / cadre.duree_creneau))
        duree = longueur * cadre.duree_creneau
        if duree < cadre.duree_min or duree > cadre.duree_max:
            diagnostics.append(f"{nom} : une seance durerait {duree} min, hors des limites {cadre.duree_min}-{cadre.duree_max} min.")
        effectif = cadre.effectifs.get((a.classe_id, a.groupe_id), 0)
        possibles = [s.id for s in utilisables if s.capacite >= effectif]
        if not possibles:
            diagnostics.append(f"{nom} : aucune salle disponible d'au moins {effectif} places.")
        preferee = classes_salle_principale.get(a.classe_id) if not a.groupe_id else None
        for _ in range(besoin.nombre_seances_semaine):
            unites.append(Unite(
                cle=len(unites) + 1, classe=a.classe_id, groupe=a.groupe_id, matiere=a.matiere_id,
                professeur=a.professeur_id, longueur=longueur, salles=possibles or [None],
                salle_preferee=preferee if preferee in possibles else None,
            ))
        cadre.noms.setdefault(("prof", a.professeur_id), a.professeur.nom_complet)
    return unites, diagnostics
