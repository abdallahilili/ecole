"""Calculs de moyennes et de classements (fonctions pures, sans base de donnees).

Formules (cahier des charges, section 4) :
    moyenne d'une matiere = somme(note/bareme*20 x poids) / somme(poids)
    moyenne generale      = somme(moyenne matiere x coefficient) / somme(coefficients applicables)
Une note ou une matiere manquante n'est JAMAIS transformee en zero sans que
la regle correspondante soit explicitement configuree.
"""

from collections import namedtuple
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from apps.commun.parametres import lire_parametre
from .models import StatutNote

CENTIEME = Decimal("0.01")
VINGT = Decimal(20)
MOYENNE_ADMISSION = Decimal(10)

Notation = namedtuple("Notation", "statut valeur")


def arrondir(valeur, quantum=CENTIEME):
    return None if valeur is None else valeur.quantize(quantum, rounding=ROUND_HALF_UP)


def en_texte(valeur):
    """Decimal -> '13.50' (ou None)."""
    valeur = arrondir(valeur)
    return None if valeur is None else f"{valeur:.2f}"


def lire_poids_trimestres(texte):
    try:
        poids = tuple(Decimal(p.strip()) for p in str(texte).split(","))
    except InvalidOperation:
        return (Decimal(1),) * 3
    if len(poids) != 3 or any(p < 0 for p in poids) or sum(poids) == 0:
        return (Decimal(1),) * 3
    return poids


@dataclass
class Regles:
    abs_justifiee: str = "exclure"            # exclure | zero
    abs_non_justifiee: str = "zero"           # zero | exclure
    exige_toutes_evaluations: bool = False
    matiere_non_evaluee: str = "exclure"      # exclure | zero (le papier compte 0)
    ex_aequo: str = "meme_rang"               # meme_rang | alphabetique
    poids_trimestres: tuple = field(default_factory=lambda: (Decimal(1),) * 3)

    @classmethod
    def depuis_parametres(cls):
        return cls(
            abs_justifiee=lire_parametre("abs_justifiee"),
            abs_non_justifiee=lire_parametre("abs_non_justifiee"),
            exige_toutes_evaluations=str(lire_parametre("moyenne_exige_toutes_evaluations")) == "1",
            matiere_non_evaluee=lire_parametre("matiere_non_evaluee"),
            ex_aequo=lire_parametre("ex_aequo"),
            poids_trimestres=lire_poids_trimestres(lire_parametre("poids_trimestres")),
        )


@dataclass
class MoyenneMatiere:
    moyenne: Decimal = None
    incomplete: bool = False
    manquantes: list = field(default_factory=list)


def moyenne_matiere(evaluations, notes, regles):
    """evaluations : objets (id, libelle, bareme, poids) ; notes : {id_evaluation: Notation | None}."""
    somme = poids_total = Decimal(0)
    manquantes = []
    for evaluation in evaluations:
        notation = notes.get(evaluation.id)
        if notation is None:
            manquantes.append(evaluation.libelle)
            continue
        if notation.statut == StatutNote.SAISIE:
            contribution = notation.valeur * VINGT / evaluation.bareme
        elif notation.statut == StatutNote.NON_APPLICABLE:
            continue
        else:
            regle = regles.abs_justifiee if notation.statut == StatutNote.ABSENT_JUSTIFIE else regles.abs_non_justifiee
            if regle != "zero":
                continue
            contribution = Decimal(0)
        somme += contribution * evaluation.poids
        poids_total += evaluation.poids
    incomplete = bool(manquantes)
    if poids_total == 0 or (incomplete and regles.exige_toutes_evaluations):
        return MoyenneMatiere(None, incomplete, manquantes)
    return MoyenneMatiere(somme / poids_total, incomplete, manquantes)


@dataclass
class MoyenneGenerale:
    moyenne: Decimal = None
    total_points: Decimal = Decimal(0)
    total_coefficients: Decimal = Decimal(0)
    matieres_manquantes: list = field(default_factory=list)

    @property
    def incomplet(self):
        return bool(self.matieres_manquantes)


def moyenne_generale(moyennes, coefficients, regles):
    """moyennes : {id_matiere: Decimal | None} ; coefficients : {id_matiere: Decimal}."""
    total_points = total_coefficients = Decimal(0)
    manquantes = []
    evaluee = False
    for matiere, coefficient in coefficients.items():
        if coefficient <= 0:
            continue
        moyenne = moyennes.get(matiere)
        if moyenne is None:
            manquantes.append(matiere)
            if regles.matiere_non_evaluee == "zero":
                total_coefficients += coefficient   # decision explicite de l'etablissement
            continue
        evaluee = True
        total_points += moyenne * coefficient
        total_coefficients += coefficient
    if not evaluee or total_coefficients == 0:
        return MoyenneGenerale(None, Decimal(0), Decimal(0), manquantes)
    return MoyenneGenerale(total_points / total_coefficients, total_points, total_coefficients, manquantes)


def classer(entrees, regles):
    """entrees : [(cle, moyenne | None, nom)] -> {cle: rang}. Sans moyenne : pas de rang.

    Le classement repose sur la moyenne arrondie au centieme (celle qui est
    affichee). 'meme_rang' : egalite = meme rang puis saut (1, 2, 2, 4) ;
    'alphabetique' : departage par ordre alphabetique du nom."""
    valides = [(cle, arrondir(moyenne), nom) for cle, moyenne, nom in entrees if moyenne is not None]
    if regles.ex_aequo == "alphabetique":
        ordre = sorted(valides, key=lambda e: (-e[1], e[2].lower(), str(e[0])))
        return {cle: rang for rang, (cle, _, _) in enumerate(ordre, start=1)}
    return {cle: 1 + sum(1 for _, autre, _ in valides if autre > moyenne) for cle, moyenne, _ in valides}


def moyenne_annuelle(moyennes_trimestres, regles):
    """Moyenne ponderee des trimestres disponibles ; (moyenne | None, incomplete)."""
    disponibles = [(m, p) for m, p in zip(moyennes_trimestres, regles.poids_trimestres) if m is not None]
    incomplete = len(disponibles) < len(moyennes_trimestres)
    poids = sum(p for _, p in disponibles)
    if not disponibles or poids == 0:
        return None, incomplete
    return sum(m * p for m, p in disponibles) / poids, incomplete


def statistiques(moyennes):
    valeurs = [arrondir(m) for m in moyennes if m is not None]
    if not valeurs:
        return {"effectif_note": 0, "moyenne_classe": None, "plus_haute": None, "plus_basse": None, "taux_reussite": None}
    return {
        "effectif_note": len(valeurs),
        "moyenne_classe": en_texte(sum(valeurs) / len(valeurs)),
        "plus_haute": en_texte(max(valeurs)),
        "plus_basse": en_texte(min(valeurs)),
        "taux_reussite": en_texte(Decimal(100) * sum(1 for v in valeurs if v >= MOYENNE_ADMISSION) / len(valeurs)),
    }
