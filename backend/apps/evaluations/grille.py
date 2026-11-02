"""Grille de saisie d'une matiere pour un trimestre (une classe) : N devoirs, leur moyenne « Moy. interrogations » (x3,
calculee) et la composition du trimestre (x1, x2, x3 pour les trimestres 1, 2, 3).

Les devoirs sont des evaluations enfants de « Moy. interrogations » : seule la moyenne (somme des notes / nombre de
devoirs) entre dans les resultats. Le coefficient de la matiere et les baremes se modifient ici, avec leurs valeurs
par defaut (le coefficient de la matiere dans la classe, bareme 20)."""

from collections import namedtuple
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count

from apps.commun.audit import enregistrer_audit
from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from apps.commun.parametres import lire_parametre
from apps.etudiants.services import eleves_classe
from apps.referentiels.models import AffectationMatiereClasse, AnneeScolaire, Classe, Matiere
from . import calculs, services
from .models import Evaluation, Note, TypeEvaluation, ValidationResultats

LIBELLE_INTERROGATIONS = "Moy. interrogations"
POIDS_INTERROGATIONS = Decimal(3)
LIBELLES_COMPOSITION = {1: "1ere composition", 2: "2e composition", 3: "3e composition"}   # poids = numero du trimestre
BAREME_DEFAUT = Decimal(20)
MAX_DEVOIRS = 10
ROLES_COEFFICIENT = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE]

Cours = namedtuple("Cours", "annee classe matiere trimestre affectation")


def libelle_devoir(rang):
    return "1er devoir" if rang == 1 else f"{rang}e devoir"


def lire_cours(donnees):
    """Annee, classe, matiere et trimestre d'une requete (query string ou corps) ; ErreurMetier si invalides."""
    try:
        annee = AnneeScolaire.objects.get(pk=donnees.get("annee_scolaire"))
        classe = Classe.objects.get(pk=donnees.get("classe"))
        matiere = Matiere.objects.get(pk=donnees.get("matiere"))
        trimestre = int(donnees.get("trimestre"))
    except (ObjectDoesNotExist, TypeError, ValueError):
        raise ErreurMetier("Parametres annee_scolaire, classe, matiere et trimestre (1 a 3) obligatoires.")
    if trimestre not in LIBELLES_COMPOSITION:
        raise ErreurMetier("Parametres annee_scolaire, classe, matiere et trimestre (1 a 3) obligatoires.")
    if classe.annee_scolaire_id != annee.id:
        raise ErreurMetier("La classe choisie n'appartient pas a cette annee scolaire.")
    affectation = AffectationMatiereClasse.objects.filter(classe=classe, matiere=matiere).first()
    if affectation is None:
        raise ErreurMetier(
            f"La matiere '{matiere.nom_affiche}' n'est pas enseignee dans la classe {classe.nom} : "
            "definissez d'abord son coefficient (Matieres > Coefficients)."
        )
    return Cours(annee, classe, matiere, trimestre, affectation)


def classer(cours):
    """(interrogations, composition, autres) : evaluations sans parent de la matiere pour ce trimestre. La composition est
    celle du trimestre (« 1ere composition »...) ; d'anciennes evaluations hors modele restent saisissables dans `autres`."""
    toutes = list(Evaluation.objects.filter(
        classe=cours.classe, matiere=cours.matiere, trimestre=cours.trimestre, parent__isnull=True,
    ).order_by("date", "id"))
    interrogations = next((e for e in toutes if e.type == TypeEvaluation.INTERROGATION), None)
    compositions = [e for e in toutes if e.type == TypeEvaluation.EXAMEN]
    attendue = LIBELLES_COMPOSITION[cours.trimestre]
    composition = next((e for e in compositions if e.libelle == attendue), compositions[0] if compositions else None)
    autres = [e for e in toutes if e is not interrogations and e is not composition]
    return interrogations, composition, autres


def _decrire(evaluation, nb_notes):
    return {
        "id": evaluation.id, "libelle": evaluation.libelle, "type": evaluation.type,
        "poids": str(evaluation.poids), "bareme": str(evaluation.bareme), "nb_notes": nb_notes.get(evaluation.id, 0),
    }


def lire_grille(cours, utilisateur):
    services.verifier_droits_saisie(utilisateur, cours.annee, cours.classe, cours.matiere)
    interrogations, composition, autres = classer(cours)
    devoirs = list(interrogations.devoirs.order_by("id")) if interrogations else []
    saisies = devoirs + ([composition] if composition else []) + autres      # colonnes saisies une a une
    if interrogations and not devoirs:
        saisies.insert(0, interrogations)                                   # anciennes donnees : moyenne saisie directement
    concernees = [e.id for e in saisies] + ([interrogations.id] if devoirs else [])
    nb_notes = dict(Note.objects.filter(evaluation_id__in=concernees).values_list("evaluation_id").annotate(n=Count("id")))
    notes = {}
    for note in Note.objects.filter(evaluation_id__in=concernees):
        notes.setdefault(note.etudiant_id, {})[str(note.evaluation_id)] = {
            "statut": note.statut, "valeur": None if note.valeur is None else f"{note.valeur:.2f}",
        }
    eleves = [
        {
            "etudiant": i.etudiant_id, "numero": rang, "numero_inscription": i.numero_inscription,
            "nom_complet": i.etudiant.nom_complet, "notes": notes.get(i.etudiant_id, {}),
        }
        for rang, i in enumerate(eleves_classe(cours.classe.id, cours.annee.id), start=1)
    ]
    return {
        "annee_scolaire": cours.annee.id, "classe": cours.classe.id, "matiere": cours.matiere.id, "trimestre": cours.trimestre,
        "coefficient": str(cours.affectation.coefficient),
        "peut_modifier_coefficient": utilisateur.role in ROLES_COEFFICIENT,
        "resultats_valides": services.resultats_valides(cours.classe, cours.trimestre),
        "regles": {
            "abs_justifiee": lire_parametre("abs_justifiee"), "abs_non_justifiee": lire_parametre("abs_non_justifiee"),
            "exige_toutes_evaluations": str(lire_parametre("moyenne_exige_toutes_evaluations")) == "1",
        },
        "bareme_defaut": str(BAREME_DEFAUT), "max_devoirs": MAX_DEVOIRS,
        "composition_attendue": {"libelle": LIBELLES_COMPOSITION[cours.trimestre], "poids": str(Decimal(cours.trimestre))},
        "interrogations": None if interrogations is None else {
            **_decrire(interrogations, nb_notes), "mode": "devoirs" if devoirs else "direct",
        },
        "devoirs": [{**_decrire(d, nb_notes), "ordre": rang} for rang, d in enumerate(devoirs, start=1)],
        "composition": None if composition is None else _decrire(composition, nb_notes),
        "autres": [_decrire(e, nb_notes) for e in autres],
        "eleves": eleves,
    }


def _cellule(note):
    return None if note is None else {"statut": note.statut, "valeur": None if note.valeur is None else f"{note.valeur:.2f}"}


def lire_resultat(cours, utilisateur):
    """Resultat de la matiere pour le trimestre (moyenne des interrogations, composition, moyenne, rang) et moyennes des
    trois trimestres avec la moyenne annuelle (poids des trimestres de l'etablissement)."""
    services.verifier_droits_saisie(utilisateur, cours.annee, cours.classe, cours.matiere)
    regles = calculs.Regles.depuis_parametres()
    evaluations, notes = {}, {}
    for trimestre in LIBELLES_COMPOSITION:
        evaluations[trimestre] = list(Evaluation.objects.filter(
            classe=cours.classe, matiere=cours.matiere, trimestre=trimestre, parent__isnull=True,
        ).order_by("date", "id"))
        notes[trimestre] = {(n.etudiant_id, n.evaluation_id): n for n in Note.objects.filter(evaluation__in=evaluations[trimestre])}
    interrogations, composition, _ = classer(cours)
    inscriptions = list(eleves_classe(cours.classe.id, cours.annee.id))

    lignes, moyennes_eleves = [], {}
    for i in inscriptions:
        moyennes = {}
        for trimestre, liste in evaluations.items():
            notations = {
                e.id: (calculs.Notation(n.statut, n.valeur) if (n := notes[trimestre].get((i.etudiant_id, e.id))) else None)
                for e in liste
            }
            moyennes[trimestre] = calculs.moyenne_matiere(liste, notations, regles).moyenne if liste else None
        annuelle, _ = calculs.moyenne_annuelle([moyennes[t] for t in sorted(moyennes)], regles)
        moyennes_eleves[i.etudiant_id] = (moyennes, annuelle)
    rangs = calculs.classer(
        [(i.etudiant_id, moyennes_eleves[i.etudiant_id][0][cours.trimestre], i.etudiant.nom_complet) for i in inscriptions], regles,
    )
    for rang, i in enumerate(inscriptions, start=1):
        moyennes, annuelle = moyennes_eleves[i.etudiant_id]
        lignes.append({
            "etudiant": i.etudiant_id, "numero": rang, "numero_inscription": i.numero_inscription,
            "nom_complet": i.etudiant.nom_complet,
            "interrogations": _cellule(notes[cours.trimestre].get((i.etudiant_id, interrogations.id))) if interrogations else None,
            "composition": _cellule(notes[cours.trimestre].get((i.etudiant_id, composition.id))) if composition else None,
            "moyenne": calculs.en_texte(moyennes[cours.trimestre]), "rang": rangs.get(i.etudiant_id),
            "moyennes": {str(t): calculs.en_texte(m) for t, m in moyennes.items()},
            "moyenne_annuelle": calculs.en_texte(annuelle),
        })
    return {
        "trimestre": cours.trimestre,
        "interrogations": None if interrogations is None else _decrire(interrogations, {}),
        "composition": None if composition is None else _decrire(composition, {}),
        "poids_trimestres": [str(p) for p in regles.poids_trimestres],
        "eleves": lignes,
    }


# ------------------------------------------------------------------ structure (coefficient, baremes, nombre de devoirs)

def _decimal(brut, message, maximum):
    try:
        valeur = Decimal(str(brut).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ErreurMetier(message)
    if not valeur.is_finite() or valeur <= 0 or valeur > maximum or valeur != valeur.quantize(Decimal("0.01")):
        raise ErreurMetier(message)
    return valeur.quantize(Decimal("0.01"))


def _optionnel(donnees, cle):
    valeur = donnees.get(cle)
    return None if valeur in (None, "") else valeur


def _changer_bareme(evaluations, bareme):
    if Note.objects.filter(evaluation__in=evaluations).exists():
        raise ErreurMetier("Le bareme ne peut plus etre modifie : des notes sont deja saisies.")
    for evaluation in evaluations:
        evaluation.bareme = bareme
        evaluation.save(update_fields=["bareme"])


def _changer_coefficient(cours, coefficient, utilisateur):
    if utilisateur.role not in ROLES_COEFFICIENT:
        raise ErreurMetier("Seule la direction ou la pedagogie peut modifier le coefficient d'une matiere.")
    if ValidationResultats.objects.filter(classe=cours.classe).exists():
        raise ErreurMetier("Des resultats de cette classe sont valides : rouvrez-les avant de modifier un coefficient.")
    affectation = cours.affectation
    ancien = affectation.coefficient
    affectation.coefficient = coefficient
    affectation.save(update_fields=["coefficient"])
    enregistrer_audit(
        utilisateur, "MODIFICATION_COEFFICIENT", "AffectationMatiereClasse", affectation.pk,
        ancienne_valeur={"coefficient": str(ancien)}, nouvelle_valeur={"coefficient": str(coefficient), "matiere": cours.matiere.code},
    )


def _creer(cours, utilisateur, **champs):
    return Evaluation.objects.create(
        annee_scolaire=cours.annee, classe=cours.classe, matiere=cours.matiere, trimestre=cours.trimestre,
        cree_par=utilisateur, **champs,
    )


@transaction.atomic
def configurer(cours, donnees, utilisateur):
    """Cree ou ajuste la structure de la matiere pour le trimestre. Champs facultatifs de `donnees` : `nombre_devoirs`,
    `bareme_devoirs`, `bareme_composition`, `coefficient`. La composition du trimestre est toujours creee."""
    services.verifier_droits_saisie(utilisateur, cours.annee, cours.classe, cours.matiere)
    if services.resultats_valides(cours.classe, cours.trimestre):
        raise ErreurMetier("Les resultats de ce trimestre sont valides : rouvrez-les pour modifier les evaluations.")

    coefficient = _optionnel(donnees, "coefficient")
    bareme_devoirs = _optionnel(donnees, "bareme_devoirs")
    bareme_composition = _optionnel(donnees, "bareme_composition")
    nombre = _optionnel(donnees, "nombre_devoirs")
    if coefficient is not None:
        coefficient = _decimal(coefficient, "Le coefficient doit etre strictement positif.", Decimal(100))
    if bareme_devoirs is not None:
        bareme_devoirs = _decimal(bareme_devoirs, "Le bareme doit etre strictement positif.", Decimal(1000))
    if bareme_composition is not None:
        bareme_composition = _decimal(bareme_composition, "Le bareme doit etre strictement positif.", Decimal(1000))
    if nombre is not None:
        try:
            nombre = int(nombre)
        except (TypeError, ValueError):
            nombre = 0
        if not 1 <= nombre <= MAX_DEVOIRS:
            raise ErreurMetier(f"Le nombre de devoirs doit etre compris entre 1 et {MAX_DEVOIRS}.")

    changements = {}
    if coefficient is not None and coefficient != cours.affectation.coefficient:
        _changer_coefficient(cours, coefficient, utilisateur)

    interrogations, composition, _ = classer(cours)
    if composition is None:
        composition = _creer(
            cours, utilisateur, libelle=LIBELLES_COMPOSITION[cours.trimestre], type=TypeEvaluation.EXAMEN,
            poids=Decimal(cours.trimestre), bareme=bareme_composition or BAREME_DEFAUT,
        )
        changements["composition"] = composition.libelle
    elif bareme_composition is not None and bareme_composition != composition.bareme:
        _changer_bareme([composition], bareme_composition)
        changements["bareme_composition"] = str(bareme_composition)

    devoirs = list(interrogations.devoirs.order_by("id")) if interrogations else []
    if bareme_devoirs is not None and interrogations is not None and bareme_devoirs != interrogations.bareme:
        _changer_bareme([interrogations, *devoirs], bareme_devoirs)
        changements["bareme_devoirs"] = str(bareme_devoirs)

    if nombre is not None and nombre != len(devoirs):
        if interrogations is None:
            interrogations = _creer(
                cours, utilisateur, libelle=LIBELLE_INTERROGATIONS, type=TypeEvaluation.INTERROGATION,
                poids=POIDS_INTERROGATIONS, bareme=bareme_devoirs or BAREME_DEFAUT,
            )
        elif not devoirs and interrogations.notes.exists():
            raise ErreurMetier(
                "« Moy. interrogations » contient deja des notes saisies directement : "
                "videz-les avant de passer a la saisie par devoirs."
            )
        for rang in range(len(devoirs) + 1, nombre + 1):
            devoirs.append(_creer(
                cours, utilisateur, libelle=libelle_devoir(rang), type=TypeEvaluation.DEVOIR, poids=Decimal(1),
                bareme=interrogations.bareme, parent=interrogations,
            ))
        for devoir in reversed(devoirs[nombre:]):
            if devoir.notes.exists():
                raise ErreurMetier(
                    f"Le {devoir.libelle} contient des notes : videz cette colonne avant de reduire le nombre de devoirs."
                )
            devoir.delete()
        changements["nombre_devoirs"] = nombre
    if changements:
        enregistrer_audit(
            utilisateur, "CONFIGURATION_NOTES", "Classe", cours.classe.pk,
            nouvelle_valeur={**changements, "matiere": cours.matiere.code, "trimestre": cours.trimestre},
        )


# --------------------------------------------------------------------------------------------------- saisie des notes

@transaction.atomic
def enregistrer_grille(cours, lignes, utilisateur, motif=None):
    """lignes : [{evaluation, etudiant, statut, valeur}] (cellules modifiees). Tout ou rien ; la moyenne des
    interrogations est recalculee pour les eleves concernes."""
    services.verifier_droits_saisie(utilisateur, cours.annee, cours.classe, cours.matiere)
    interrogations, composition, autres = classer(cours)
    devoirs = list(interrogations.devoirs.order_by("id")) if interrogations else []
    saisissables = devoirs + ([composition] if composition else []) + autres + ([interrogations] if interrogations and not devoirs else [])
    par_evaluation = {e.id: e for e in saisissables}
    regroupees = {}
    for ligne in lignes:
        identifiant = ligne.get("evaluation")
        if identifiant not in par_evaluation:
            raise ErreurMetier(f"evaluation {identifiant} : absente de cette grille (ou calculee).")
        regroupees.setdefault(identifiant, []).append(ligne)
    bilan = {"creees": 0, "modifiees": 0, "supprimees": 0}
    for identifiant, sous_lignes in regroupees.items():
        evaluation = par_evaluation[identifiant]
        try:
            resultat = services.enregistrer_notes(evaluation, sous_lignes, utilisateur, motif)
        except ErreurMetier as e:
            raise ErreurMetier(f"{evaluation.libelle} : {e.message}")
        for cle in bilan:
            bilan[cle] += resultat[cle]
    return bilan
