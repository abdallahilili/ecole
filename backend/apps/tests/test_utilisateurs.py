from django.test import TestCase
from rest_framework.test import APIClient

from apps.commun.constantes import Role
from apps.utilisateurs.models import Utilisateur


class ConnexionTests(TestCase):
    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_user(
            identifiant="directeur1", mot_de_passe="motdepasse123", nom="Kane", role=Role.DIRECTEUR,
        )

    def test_connexion_reussie_retourne_des_jetons(self):
        client = APIClient()
        reponse = client.post("/api/auth/connexion/", {"identifiant": "directeur1", "mot_de_passe": "motdepasse123"})
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("access", reponse.data)
        self.assertIn("refresh", reponse.data)

    def test_connexion_mauvais_mot_de_passe_refusee(self):
        client = APIClient()
        reponse = client.post("/api/auth/connexion/", {"identifiant": "directeur1", "mot_de_passe": "mauvais"})
        self.assertEqual(reponse.status_code, 401)

    def test_endpoint_moi_necessite_authentification(self):
        client = APIClient()
        reponse = client.get("/api/auth/moi/")
        self.assertEqual(reponse.status_code, 401)

    def test_endpoint_moi_authentifie(self):
        client = APIClient()
        client.force_authenticate(self.utilisateur)
        reponse = client.get("/api/auth/moi/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data["identifiant"], "directeur1")
