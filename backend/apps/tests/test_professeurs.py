from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient

from apps.commun.constantes import Role, ModeRemuneration
from apps.utilisateurs.models import Utilisateur
from apps.referentiels.models import AnneeScolaire, Niveau, Classe, Matiere
from apps.professeurs.models import Professeur, AffectationProfesseur


def creer_utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin"):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe="secret123", nom="Test", role=role)


class RemunerationValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(creer_utilisateur())

    def test_mode_horaire_sans_tarif_refuse(self):
        reponse = self.client.post("/api/professeurs/professeurs/", {
            "matricule": "P001", "nom": "Kane", "prenom": "Ibrahima",
            "mode_remuneration": ModeRemuneration.HORAIRE, "tarif_horaire": 0,
        })
        self.assertEqual(reponse.status_code, 400)

    def test_mode_horaire_avec_tarif_accepte(self):
        reponse = self.client.post("/api/professeurs/professeurs/", {
            "matricule": "P002", "nom": "Kane", "prenom": "Fatoumata",
            "mode_remuneration": ModeRemuneration.HORAIRE, "tarif_horaire": 500,
        })
        self.assertEqual(reponse.status_code, 201)


class AffectationProfesseurTests(TestCase):
    def setUp(self):
        self.annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True)
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.classe = Classe.objects.create(nom="6eme A", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)
        self.matiere = Matiere.objects.create(nom="Francais", code="FR")
        self.professeur = Professeur.objects.create(
            matricule="P010", nom="Traore", prenom="Oumar",
            mode_remuneration=ModeRemuneration.HORAIRE, tarif_horaire=400,
        )
        self.client = APIClient()
        self.client.force_authenticate(creer_utilisateur())

    def test_pas_de_double_affectation_identique(self):
        AffectationProfesseur.objects.create(
            professeur=self.professeur, matiere=self.matiere, classe=self.classe, annee_scolaire=self.annee,
        )
        reponse = self.client.post("/api/professeurs/affectations/", {
            "professeur": self.professeur.id, "matiere": self.matiere.id,
            "classe": self.classe.id, "annee_scolaire": self.annee.id,
        })
        self.assertEqual(reponse.status_code, 400)
