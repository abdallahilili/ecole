"""Tests purs (sans base) : conflits obligatoires et algorithme genetique."""

from django.test import SimpleTestCase

from apps.emplois_du_temps.conflits import Cadre, Sc, conflits_de, detecter
from apps.emplois_du_temps.genetique import Probleme, Unite, diagnostiquer, resoudre


def h(heures, minutes=0):
    return heures * 60 + minutes


def cadre(**extra):
    base = dict(jours={0, 1, 2, 3, 4}, debut=h(8), fin=h(14), duree_creneau=60, duree_min=60, duree_max=180,
                pauses=[(h(10), h(11))])
    base.update(extra)
    c = Cadre(**base)
    c.noms = {("prof", 1): "Sy", ("prof", 2): "Ba", ("salle", 1): "S1", ("salle", 2): "S2", ("classe", 1): "6AF",
              ("classe", 2): "7D", ("matiere", 1): "Maths", ("matiere", 2): "Physique", ("groupe", 1): "G1", ("groupe", 2): "G2"}
    return c


def sc(cle, jour=0, debut=h(8), fin=h(9), classe=1, groupe=None, matiere=1, prof=1, salle=1):
    return Sc(cle, classe, groupe, matiere, prof, salle, jour, debut, fin)


def types(conflits):
    return sorted(c["type"] for c in conflits)


class ConflitsTests(SimpleTestCase):
    def test_creneaux_valides_excluent_les_pauses(self):
        self.assertEqual(cadre().creneaux_valides(), [0, 1, 3, 4, 5])      # 10:00-11:00 = pause

    def test_professeur_salle_et_classe_simultanes(self):
        # Recouvrement partiel : 8h-10h et 9h-10h.
        seances = [sc(1, debut=h(8), fin=h(10)), sc(2, classe=2, matiere=2, debut=h(9), fin=h(10))]
        self.assertEqual(types(detecter(seances, cadre())), ["PROFESSEUR_SIMULTANE", "SALLE_SIMULTANEE"])
        # Meme classe : conflit de classe.
        seances = [sc(1), sc(2, matiere=2, prof=2, salle=2)]
        self.assertEqual(types(detecter(seances, cadre())), ["CLASSE_SIMULTANEE"])

    def test_creneaux_consecutifs_et_autre_jour_sans_conflit(self):
        seances = [sc(1), sc(2, debut=h(9), fin=h(10)), sc(3, jour=1)]
        self.assertEqual(detecter(seances, cadre()), [])

    def test_groupes_d_une_meme_classe(self):
        a, b = sc(1, groupe=1, prof=1, salle=1), sc(2, groupe=2, prof=2, salle=2, matiere=2)
        self.assertEqual(detecter([a, b], cadre()), [])                                   # groupes differents : en parallele
        meme_groupe = sc(3, groupe=1, prof=2, salle=2, matiere=2)
        self.assertEqual(types(detecter([a, meme_groupe], cadre())), ["GROUPE_SIMULTANE"])
        classe_entiere = sc(4, groupe=None, prof=2, salle=2, matiere=2)
        self.assertEqual(types(detecter([a, classe_entiere], cadre())), ["CLASSE_SIMULTANEE"])

    def test_indisponibilites(self):
        c = cadre(indispo_prof={1: [(0, h(8), h(9))]}, indispo_salle={1: [(0, h(8, 30), h(9))]})
        self.assertEqual(types(detecter([sc(1)], c)), ["PROFESSEUR_INDISPONIBLE", "SALLE_INDISPONIBLE"])
        self.assertEqual(detecter([sc(1, jour=1)], c), [])

    def test_horaires_pauses_grille_et_duree(self):
        c = cadre()
        self.assertEqual(types(detecter([sc(1, jour=5)], c)), ["HORS_HORAIRES"])                          # samedi non ouvrable
        self.assertEqual(types(detecter([sc(1, debut=h(7), fin=h(8))], c)), ["HORS_HORAIRES"])             # avant l'ouverture
        self.assertEqual(types(detecter([sc(1, debut=h(13), fin=h(15))], c)), ["HORS_HORAIRES"])           # apres la fermeture
        self.assertEqual(types(detecter([sc(1, debut=h(9), fin=h(11))], c)), ["HORS_HORAIRES"])            # chevauche la pause
        self.assertEqual(types(detecter([sc(1, debut=h(8, 15), fin=h(9, 15))], c)), ["HORS_HORAIRES"])     # hors grille
        self.assertEqual(types(detecter([sc(1, debut=h(11), fin=h(14))], c)), [])                          # 3 h : limite autorisee
        self.assertEqual(types(detecter([sc(1, debut=h(8), fin=h(10))], cadre(duree_max=60))), ["DUREE"])

    def test_capacite_et_affectation(self):
        c = cadre(capacites={1: 20}, effectifs={(1, None): 25}, affectations={(1, 1, 1, None)})
        self.assertEqual(types(detecter([sc(1)], c)), ["CAPACITE_SALLE"])
        self.assertEqual(types(detecter([sc(1, prof=2, salle=None)], c)), ["PROFESSEUR_NON_AFFECTE"])
        groupe = cadre(affectations={(1, 1, 1, 1)})
        self.assertEqual(detecter([sc(1, groupe=1)], groupe), [])                          # affecte au groupe 1
        self.assertEqual(types(detecter([sc(1, groupe=2)], groupe)), ["PROFESSEUR_NON_AFFECTE"])
        entiere = cadre(affectations={(1, 1, 1, None)})
        self.assertEqual(detecter([sc(1, groupe=2)], entiere), [])                         # affecte a la classe entiere

    def test_salle_manquante_exigee_seulement_a_la_publication(self):
        self.assertEqual(detecter([sc(1, salle=None)], cadre()), [])
        self.assertEqual(types(detecter([sc(1, salle=None)], cadre(), publication=True)), ["SALLE_MANQUANTE"])

    def test_messages_explicatifs_et_filtre_par_seance(self):
        conflits = detecter([sc(1), sc(2, classe=2, matiere=2, salle=2)], cadre())   # meme professeur, memes horaires
        self.assertEqual(len(conflits), 1)
        self.assertIn("Sy a deux cours en meme temps", conflits[0]["message"])
        self.assertIn("lundi 08:00-09:00", conflits[0]["message"])
        self.assertEqual(len(conflits_de(2, conflits)), 1)
        self.assertEqual(conflits_de(99, conflits), [])


def jeu(nb_classes=4, nb_matieres=5, seances=3, nb_profs=6, nb_salles=4, **extra):
    c = cadre(**extra)
    unites = []
    for k in range(nb_classes):
        for m in range(nb_matieres):
            for _ in range(seances):
                unites.append(Unite(cle=len(unites) + 1, classe=k, groupe=None, matiere=m, professeur=(k + m) % nb_profs,
                                    longueur=1, salles=list(range(nb_salles)), salle_preferee=k % nb_salles))
        c.effectifs[(k, None)] = 30
    for s in range(nb_salles):
        c.capacites[s] = 40
    return c, unites


def en_sc(probleme, solution):
    d = probleme.cadre.duree_creneau
    return [Sc(u.cle, u.classe, u.groupe, u.matiere, u.professeur, g[2], g[0], probleme.cadre.debut + g[1] * d,
               probleme.cadre.debut + (g[1] + u.longueur) * d) for u, g in zip(probleme.unites, solution.genes)]


class GenetiqueTests(SimpleTestCase):
    def test_trouve_une_solution_sans_conflit_verifiee_independamment(self):
        for graine in (1, 2, 3):
            c, unites = jeu()
            probleme = Probleme(unites, c)
            solution = resoudre(probleme, graine=graine, temps_max=20)
            self.assertEqual(solution.violations, 0, graine)
            self.assertEqual(detecter(en_sc(probleme, solution), c), [], graine)       # meme regles que l'edition manuelle

    def test_resultat_reproductible_avec_la_meme_graine(self):
        resultats = []
        for _ in range(2):
            c, unites = jeu()
            resultats.append(resoudre(Probleme(unites, c), graine=42, generations=25, temps_max=20).genes)
        self.assertEqual(resultats[0], resultats[1])

    def test_indisponibilites_du_professeur_respectees(self):
        c, unites = jeu(indispo_prof={0: [(0, h(8), h(14)), (1, h(8), h(14))]})      # le professeur 0 n'enseigne ni lundi ni mardi
        probleme = Probleme(unites, c)
        solution = resoudre(probleme, graine=7, temps_max=20)
        self.assertEqual(solution.violations, 0)
        for seance in en_sc(probleme, solution):
            if seance.professeur == 0:
                self.assertNotIn(seance.jour, (0, 1))

    def test_seances_de_deux_creneaux_ne_traversent_pas_la_pause(self):
        c, unites = jeu(nb_classes=2, nb_matieres=3, seances=2, nb_profs=3)
        for u in unites:
            u.longueur = 2
        probleme = Probleme(unites, c)
        solution = resoudre(probleme, graine=3, temps_max=20)
        self.assertEqual(solution.violations, 0)
        for seance in en_sc(probleme, solution):
            self.assertFalse(seance.debut < h(11) and h(10) < seance.fin, "chevauche la pause")
        self.assertEqual(detecter(en_sc(probleme, solution), c), [])

    def test_groupes_en_parallele_mais_jamais_en_meme_temps_que_la_classe_entiere(self):
        c = cadre()
        c.capacites = {0: 40, 1: 40, 2: 40}
        unites = [
            Unite(1, 1, None, 1, 1, 2, salles=[0, 1, 2]),        # classe entiere, 2 creneaux
            Unite(2, 1, 1, 2, 2, 2, salles=[0, 1, 2]),           # groupe 1
            Unite(3, 1, 2, 2, 3, 2, salles=[0, 1, 2]),           # groupe 2
        ]
        probleme = Probleme(unites, c)
        solution = resoudre(probleme, graine=1, temps_max=10)
        self.assertEqual(solution.violations, 0)
        self.assertEqual(detecter(en_sc(probleme, solution), c), [])

    def test_preferences_du_professeur_favorisees(self):
        c = cadre()
        unites = [Unite(1, 1, None, 1, 1, 1, salles=[0]), Unite(2, 1, None, 2, 1, 1, salles=[0])]
        c.capacites = {0: 40}
        probleme = Probleme(unites, c, preferences={1: [(1, h(8), h(10))]})          # prefere le mardi 8h-10h
        solution = resoudre(probleme, graine=2, temps_max=10)
        self.assertEqual(solution.violations, 0)
        self.assertTrue(all(g[0] == 1 and g[1] in (0, 1) for g in solution.genes), solution.genes)

    def test_ressources_insuffisantes_diagnostiquees_et_jamais_declarees_valides(self):
        c, unites = jeu(nb_classes=2, nb_matieres=5, seances=3, nb_profs=1)         # 30 creneaux pour un seul professeur (25 dispos)
        probleme = Probleme(unites, c)
        messages = diagnostiquer(probleme)
        self.assertTrue(any("30 creneaux" in m and "25" in m for m in messages), messages)
        solution = resoudre(probleme, graine=1, temps_max=5)
        self.assertGreater(solution.violations, 0)
        self.assertGreater(len(detecter(en_sc(probleme, solution), c)), 0)

    def test_diagnostic_classe_surchargee_et_seance_impossible(self):
        c, unites = jeu(nb_classes=1, nb_matieres=9, seances=3, nb_profs=9, nb_salles=3)   # 27 creneaux pour 25 dispos
        self.assertTrue(any("La classe 0" in m or "classe" in m for m in diagnostiquer(Probleme(unites, c))))
        c, unites = jeu(nb_classes=1, nb_matieres=1, seances=1, nb_profs=1)
        unites[0].longueur = 5            # 5 creneaux consecutifs : impossible (pause + 6 h seulement)
        messages = diagnostiquer(Probleme(unites, c))
        self.assertTrue(any("ne tient dans aucune journee" in m for m in messages), messages)

    def test_aucune_unite(self):
        solution = resoudre(Probleme([], cadre()), graine=1)
        self.assertEqual((solution.genes, solution.violations), ([], 0))
