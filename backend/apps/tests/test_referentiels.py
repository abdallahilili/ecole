from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient

from apps.commun.constantes import Role
from apps.utilisateurs.models import Utilisateur
from apps.referentiels.models import AnneeScolaire, Niveau, Salle, Classe, TarifClasse, Groupe, Matiere, AffectationMatiereClasse


def creer_utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin"):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe="secret123", nom="Test", role=role)


class AnneeScolaireTests(TestCase):
    def test_une_seule_annee_active(self):
        a1 = AnneeScolaire.objects.create(libelle="2024-2025", date_debut=date(2024, 9, 1), date_fin=date(2025, 6, 30), active=True)
        a2 = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True)
        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertFalse(a1.active)
        self.assertTrue(a2.active)

    def test_api_date_fin_avant_debut_rejetee(self):
        client = APIClient()
        client.force_authenticate(creer_utilisateur())
        reponse = client.post("/api/referentiels/annees-scolaires/", {
            "libelle": "2026-2027", "date_debut": "2026-09-01", "date_fin": "2026-08-01",
        })
        self.assertEqual(reponse.status_code, 400)

    def test_api_trimestres_et_examens(self):
        client = APIClient()
        client.force_authenticate(creer_utilisateur())
        base = {"libelle": "2026-2027", "date_debut": "2026-09-01", "date_fin": "2027-06-30"}
        url = "/api/referentiels/annees-scolaires/"

        reponse = client.post(url, {
            **base,
            "debut_trimestre2": "2026-12-01", "debut_trimestre3": "2027-03-01",
            "debut_examen1": "2026-11-20", "fin_examen1": "2026-11-27",
            "debut_examen2": "2027-02-20", "fin_examen2": "2027-02-27",
            "debut_examen3": "2027-06-10", "fin_examen3": "2027-06-20",
            "debut_vacances": "",
        })
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual(reponse.json()["debut_trimestre3"], "2027-03-01")
        self.assertIsNone(reponse.json()["debut_vacances"])

        # 3e trimestre avant le 2e.
        reponse = client.post(url, {
            **base, "libelle": "2027-2028",
            "debut_trimestre2": "2027-03-01", "debut_trimestre3": "2026-12-01",
        })
        self.assertEqual(reponse.status_code, 400)

        # Fin d'examen avant son debut.
        reponse = client.post(url, {
            **base, "libelle": "2028-2029",
            "debut_examen2": "2027-02-27", "fin_examen2": "2027-02-20",
        })
        self.assertEqual(reponse.status_code, 400)


class CapaciteClasseTests(TestCase):
    def setUp(self):
        self.annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True)
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.salle = Salle.objects.create(nom="Salle 1", capacite=20)

    def test_capacite_classe_ne_peut_pas_depasser_capacite_salle(self):
        client = APIClient()
        client.force_authenticate(creer_utilisateur())
        reponse = client.post("/api/referentiels/classes/", {
            "nom": "6eme A", "niveau": self.niveau.id, "annee_scolaire": self.annee.id,
            "capacite": 35, "salle_principale": self.salle.id,
        })
        self.assertEqual(reponse.status_code, 400)

    def test_groupe_doit_appartenir_a_une_classe_existante(self):
        classe = Classe.objects.create(nom="6eme A", niveau=self.niveau, annee_scolaire=self.annee, capacite=20)
        groupe = Groupe.objects.create(nom="Groupe 1", classe=classe)
        self.assertEqual(groupe.classe_id, classe.id)


class TarifClasseTests(TestCase):
    URL = "/api/referentiels/tarifs-classes/"

    def setUp(self):
        self.annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True)
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.classe_6af = Classe.objects.create(nom="6AF", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)
        self.classe_7d = Classe.objects.create(nom="7D", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)
        self.client = APIClient()
        self.client.force_authenticate(creer_utilisateur())

    def test_un_tarif_par_classe(self):
        reponse = self.client.post(self.URL, {"classe": self.classe_6af.id, "montant": "900"})
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual(reponse.json()["classe_nom"], "6AF")
        self.assertEqual(reponse.json()["montant"], "900.00")
        self.assertEqual(self.client.post(self.URL, {"classe": self.classe_7d.id, "montant": "2500"}).status_code, 201)

        reponse = self.client.get(self.URL)
        self.assertEqual({t["classe_nom"]: t["montant"] for t in reponse.json()["resultats"]}, {"6AF": "900.00", "7D": "2500.00"})

    def test_doublon_et_montant_invalide_rejetes(self):
        self.client.post(self.URL, {"classe": self.classe_6af.id, "montant": "900"})
        reponse = self.client.post(self.URL, {"classe": self.classe_6af.id, "montant": "1000"})
        self.assertEqual(reponse.status_code, 400)
        for montant in ("0", "-50"):
            reponse = self.client.post(self.URL, {"classe": self.classe_7d.id, "montant": montant})
            self.assertEqual(reponse.status_code, 400, montant)

    def test_modification_et_recherche(self):
        tarif = self.client.post(self.URL, {"classe": self.classe_6af.id, "montant": "900"}).json()
        self.assertEqual(self.client.patch(f"{self.URL}{tarif['id']}/", {"montant": "950"}).status_code, 200)
        self.assertEqual(TarifClasse.objects.get(pk=tarif["id"]).montant, 950)
        self.client.post(self.URL, {"classe": self.classe_7d.id, "montant": "2500"})
        resultats = self.client.get(self.URL, {"recherche": "7D"}).json()["resultats"]
        self.assertEqual([t["classe_nom"] for t in resultats], ["7D"])

    def test_droits_par_role(self):
        prof = APIClient()
        prof.force_authenticate(creer_utilisateur(role=Role.PROFESSEUR, identifiant="prof2"))
        self.assertEqual(prof.get(self.URL).status_code, 403)
        self.assertEqual(prof.post(self.URL, {"classe": self.classe_6af.id, "montant": "900"}).status_code, 403)

        scolarite = APIClient()
        scolarite.force_authenticate(creer_utilisateur(role=Role.RESPONSABLE_SCOLARITE, identifiant="scol1"))
        self.assertEqual(scolarite.get(self.URL).status_code, 200)
        self.assertEqual(scolarite.post(self.URL, {"classe": self.classe_6af.id, "montant": "900"}).status_code, 403)


class CoefficientVariableTests(TestCase):
    """Verifie explicitement l'exigence du cahier des charges : le
    coefficient d'une matiere ne doit JAMAIS etre impose uniformement
    a toutes les classes."""

    def setUp(self):
        self.annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True)
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.matiere = Matiere.objects.create(nom="Mathematiques", code="MATH")
        self.classe_a = Classe.objects.create(nom="6eme A", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)
        self.classe_b = Classe.objects.create(nom="6eme B", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)

    def test_coefficients_differents_par_classe(self):
        AffectationMatiereClasse.objects.create(matiere=self.matiere, classe=self.classe_a, coefficient=4, volume_horaire_hebdo=5)
        AffectationMatiereClasse.objects.create(matiere=self.matiere, classe=self.classe_b, coefficient=3, volume_horaire_hebdo=4)
        coef_a = AffectationMatiereClasse.objects.get(classe=self.classe_a).coefficient
        coef_b = AffectationMatiereClasse.objects.get(classe=self.classe_b).coefficient
        self.assertNotEqual(coef_a, coef_b)

    def test_coefficient_negatif_rejete_par_api(self):
        client = APIClient()
        client.force_authenticate(creer_utilisateur())
        reponse = client.post("/api/referentiels/affectations-matiere-classe/", {
            "matiere": self.matiere.id, "classe": self.classe_a.id, "coefficient": -1, "volume_horaire_hebdo": 2,
        })
        self.assertEqual(reponse.status_code, 400)


class PermissionsReferentielsTests(TestCase):
    def test_professeur_ne_peut_pas_creer_de_niveau(self):
        client = APIClient()
        client.force_authenticate(creer_utilisateur(role=Role.PROFESSEUR, identifiant="prof1"))
        reponse = client.post("/api/referentiels/niveaux/", {"nom": "Terminale", "code": "TERM", "ordre": 6})
        self.assertEqual(reponse.status_code, 403)

    def test_anonyme_refuse(self):
        client = APIClient()
        reponse = client.get("/api/referentiels/niveaux/")
        self.assertEqual(reponse.status_code, 401)
