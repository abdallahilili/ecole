from collections import namedtuple
from decimal import Decimal as D

from django.test import SimpleTestCase

from apps.evaluations.calculs import (
    Notation, Regles, arrondir, classer, lire_poids_trimestres, moyenne_annuelle, moyenne_generale,
    moyenne_matiere, statistiques,
)
from apps.evaluations.models import StatutNote

Ev = namedtuple("Ev", "id libelle bareme poids")
S = StatutNote.SAISIE


def notes(*valeurs):
    """notes(14, 16) -> {1: Notation(SAISIE, 14), 2: ...} ; None = note manquante."""
    return {i: (None if v is None else Notation(S, D(str(v)))) for i, v in enumerate(valeurs, start=1)}


class MoyenneMatiereTests(SimpleTestCase):
    def test_exemple_du_cahier_des_charges(self):
        # Devoir 14/20 (poids 1), interrogation 16/20 (poids 1), examen 12/20 (poids 2) -> 13,5.
        evaluations = [Ev(1, "Devoir", D(20), D(1)), Ev(2, "Interro", D(20), D(1)), Ev(3, "Examen", D(20), D(2))]
        resultat = moyenne_matiere(evaluations, notes(14, 16, 12), Regles())
        self.assertEqual(resultat.moyenne, D("13.5"))
        self.assertFalse(resultat.incomplete)

    def test_baremes_differents_normalises_sur_20(self):
        evaluations = [Ev(1, "A", D(30), D(1)), Ev(2, "B", D(10), D(1))]
        # 15/30 = 10/20 ; 8/10 = 16/20 -> 13
        self.assertEqual(moyenne_matiere(evaluations, notes(15, 8), Regles()).moyenne, D(13))

    def test_note_manquante_n_est_jamais_un_zero(self):
        evaluations = [Ev(1, "Devoir", D(20), D(1)), Ev(2, "Examen", D(20), D(2))]
        resultat = moyenne_matiere(evaluations, notes(14, None), Regles())
        self.assertEqual(resultat.moyenne, D(14))            # l'examen manquant n'abaisse pas la moyenne
        self.assertTrue(resultat.incomplete)
        self.assertEqual(resultat.manquantes, ["Examen"])

    def test_condition_toutes_evaluations_requises(self):
        evaluations = [Ev(1, "Devoir", D(20), D(1)), Ev(2, "Examen", D(20), D(2))]
        regles = Regles(exige_toutes_evaluations=True)
        self.assertIsNone(moyenne_matiere(evaluations, notes(14, None), regles).moyenne)
        self.assertEqual(moyenne_matiere(evaluations, notes(14, 10), regles).moyenne, D(34) / 3)

    def test_regles_des_absences(self):
        evaluations = [Ev(1, "Devoir", D(20), D(1)), Ev(2, "Examen", D(20), D(1))]
        just = {1: Notation(S, D(16)), 2: Notation(StatutNote.ABSENT_JUSTIFIE, None)}
        non_just = {1: Notation(S, D(16)), 2: Notation(StatutNote.ABSENT, None)}
        # Par defaut : justifiee exclue, non justifiee comptee 0.
        self.assertEqual(moyenne_matiere(evaluations, just, Regles()).moyenne, D(16))
        self.assertEqual(moyenne_matiere(evaluations, non_just, Regles()).moyenne, D(8))
        # Regles inversees par l'etablissement.
        regles = Regles(abs_justifiee="zero", abs_non_justifiee="exclure")
        self.assertEqual(moyenne_matiere(evaluations, just, regles).moyenne, D(8))
        self.assertEqual(moyenne_matiere(evaluations, non_just, regles).moyenne, D(16))

    def test_non_applicable_ignoree_et_matiere_sans_note_sans_moyenne(self):
        evaluations = [Ev(1, "Devoir", D(20), D(1)), Ev(2, "Tp", D(20), D(1))]
        na = {1: Notation(S, D(12)), 2: Notation(StatutNote.NON_APPLICABLE, None)}
        resultat = moyenne_matiere(evaluations, na, Regles())
        self.assertEqual(resultat.moyenne, D(12))
        self.assertFalse(resultat.incomplete)
        self.assertIsNone(moyenne_matiere(evaluations, {}, Regles()).moyenne)


class BulletinPapierTests(SimpleTestCase):
    """Reproduit le bulletin papier d'avril 2024 (classe 1As) : moyenne de
    chaque matiere = (3 x interrogations + 1 x composition 1 + 2 x composition 2) / 6."""

    EVALUATIONS = [Ev(1, "Moy. interrogations", D(20), D(3)), Ev(2, "1ere composition", D(20), D(1)),
                   Ev(3, "2e composition", D(20), D(2))]
    #           matiere: (interro, comp1, comp2, coefficient)
    MATIERES = {
        "I. Religieuse": (19, 10.5, 10, 3),
        "Arabe": (11.5, 15.5, 14, 5),
        "H/G": (14.5, 13.5, 12, 2),
        "I. Civique": (14.75, 9.5, 17, 1),
        "Francais": (12, 6, 9.5, 3),
        "Anglais": (12.25, 14, 15, 1),
        "Maths": (4.75, 3, 10, 5),
        "Sc. Naturelles": (6, 6, 9.5, 2),
    }

    def calculer(self, regles, avec_eps):
        moyennes, coefficients = {}, {}
        for nom, (i, c1, c2, coef) in self.MATIERES.items():
            moyennes[nom] = moyenne_matiere(self.EVALUATIONS, notes(i, c1, c2), regles).moyenne
            coefficients[nom] = D(coef)
        if avec_eps:
            moyennes["EPS"], coefficients["EPS"] = None, D(1)   # matiere sans note, coefficient 1
        return moyennes, moyenne_generale(moyennes, coefficients, regles)

    def test_moyennes_par_matiere_du_bulletin(self):
        moyennes, _ = self.calculer(Regles(), avec_eps=False)
        attendu = {
            "I. Religieuse": "14.5833", "Arabe": "13.0000", "H/G": "13.5000", "I. Civique": "14.6250",
            "Francais": "10.1667", "Anglais": "13.4583", "Maths": "6.2083", "Sc. Naturelles": "7.1667",
        }
        for nom, valeur in attendu.items():
            self.assertEqual(arrondir(moyennes[nom], D("0.0001")), D(valeur), nom)

    def test_total_du_bulletin(self):
        _, general = self.calculer(Regles(), avec_eps=False)
        self.assertEqual(arrondir(general.total_points, D("0.0001")), D("239.7083"))

    def test_matiere_non_notee_exclue_par_defaut_et_signalee(self):
        _, general = self.calculer(Regles(), avec_eps=True)
        self.assertEqual(arrondir(general.moyenne), D("10.90"))       # 239,7083 / 22
        self.assertTrue(general.incomplet)
        self.assertEqual(general.matieres_manquantes, ["EPS"])

    def test_regle_du_papier_compte_la_matiere_non_notee_a_zero(self):
        """Le bulletin papier divise par 23 (EPS non notee comptee) : 10,42210145."""
        _, general = self.calculer(Regles(matiere_non_evaluee="zero"), avec_eps=True)
        self.assertEqual(general.total_coefficients, D(23))
        self.assertEqual(arrondir(general.moyenne, D("0.00000001")), D("10.42210145"))


class MoyenneGeneraleTests(SimpleTestCase):
    def test_aucune_matiere_notee_pas_de_moyenne_meme_avec_la_regle_zero(self):
        general = moyenne_generale({"a": None, "b": None}, {"a": D(2), "b": D(3)}, Regles(matiere_non_evaluee="zero"))
        self.assertIsNone(general.moyenne)

    def test_coefficient_nul_ignore(self):
        general = moyenne_generale({"a": D(10), "b": D(20)}, {"a": D(1), "b": D(0)}, Regles())
        self.assertEqual(general.moyenne, D(10))
        self.assertFalse(general.incomplet)

    def test_coefficients_variables(self):
        general = moyenne_generale({"a": D(10), "b": D(16)}, {"a": D(1), "b": D(2)}, Regles())
        self.assertEqual(general.moyenne, D(14))


class ClassementTests(SimpleTestCase):
    ENTREES = [("a", D("15.00"), "Zoe"), ("b", D("14.004"), "Karim"), ("c", D("14.00"), "Awa"), ("d", D("12"), "Ali"),
               ("e", None, "Sans note")]

    def test_egalite_meme_rang_puis_saut(self):
        rangs = classer(self.ENTREES, Regles())
        self.assertEqual(rangs, {"a": 1, "b": 2, "c": 2, "d": 4})   # 14,004 et 14,00 -> meme moyenne a 2 decimales
        self.assertNotIn("e", rangs)

    def test_egalite_departagee_par_ordre_alphabetique(self):
        rangs = classer(self.ENTREES, Regles(ex_aequo="alphabetique"))
        self.assertEqual(rangs, {"a": 1, "c": 2, "b": 3, "d": 4})

    def test_classe_vide(self):
        self.assertEqual(classer([], Regles()), {})


class AnnuelEtStatistiquesTests(SimpleTestCase):
    def test_poids_des_trimestres(self):
        regles = Regles(poids_trimestres=lire_poids_trimestres("1,1,2"))
        moyenne, incomplete = moyenne_annuelle([D(10), D(12), D(16)], regles)
        self.assertEqual(moyenne, D("13.5"))     # (10 + 12 + 2 x 16) / 4
        self.assertFalse(incomplete)

    def test_annee_en_cours_est_provisoire(self):
        moyenne, incomplete = moyenne_annuelle([D(10), D(14), None], Regles(poids_trimestres=(D(1),) * 3))
        self.assertEqual(moyenne, D(12))
        self.assertTrue(incomplete)
        self.assertEqual(moyenne_annuelle([None, None, None], Regles()), (None, True))

    def test_poids_invalides_reviennent_a_1_1_1(self):
        for texte in ("abc", "1,2", "0,0,0", "-1,1,1"):
            self.assertEqual(lire_poids_trimestres(texte), (D(1), D(1), D(1)), texte)

    def test_statistiques_de_classe(self):
        stats = statistiques([D(16), D(8), D(10), None])
        self.assertEqual(stats["effectif_note"], 3)
        self.assertEqual(stats["moyenne_classe"], "11.33")
        self.assertEqual((stats["plus_haute"], stats["plus_basse"]), ("16.00", "8.00"))
        self.assertEqual(stats["taux_reussite"], "66.67")
        self.assertIsNone(statistiques([None])["moyenne_classe"])
