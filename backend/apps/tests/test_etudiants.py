from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient

from apps.commun.constantes import Role, StatutInscription
from apps.utilisateurs.models import Utilisateur
from apps.referentiels.models import AnneeScolaire, Niveau, Classe, Groupe
from apps.etudiants.models import Etudiant, Inscription


def creer_utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin"):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe="secret123", nom="Test", role=role)


class InscriptionCapaciteTests(TestCase):
    def setUp(self):
        self.annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True)
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.classe = Classe.objects.create(nom="6eme A", niveau=self.niveau, annee_scolaire=self.annee, capacite=1)
        self.etudiant1 = Etudiant.objects.create(matricule="E001", nom="Diallo", prenom="Awa")
        self.etudiant2 = Etudiant.objects.create(matricule="E002", nom="Ba", prenom="Moussa")
        self.client = APIClient()
        self.client.force_authenticate(creer_utilisateur())

    def test_classe_pleine_refuse_nouvelle_inscription(self):
        reponse1 = self.client.post("/api/etudiants/inscriptions/", {
            "etudiant": self.etudiant1.id, "annee_scolaire": self.annee.id, "classe": self.classe.id,
            "date_inscription": "2025-09-01",
        })
        self.assertEqual(reponse1.status_code, 201)

        reponse2 = self.client.post("/api/etudiants/inscriptions/", {
            "etudiant": self.etudiant2.id, "annee_scolaire": self.annee.id, "classe": self.classe.id,
            "date_inscription": "2025-09-02",
        })
        self.assertEqual(reponse2.status_code, 400)

    def test_groupe_hors_classe_refuse(self):
        autre_classe = Classe.objects.create(nom="6eme B", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)
        groupe_autre = Groupe.objects.create(nom="G1", classe=autre_classe)
        reponse = self.client.post("/api/etudiants/inscriptions/", {
            "etudiant": self.etudiant1.id, "annee_scolaire": self.annee.id, "classe": self.classe.id,
            "groupe": groupe_autre.id, "date_inscription": "2025-09-01",
        })
        self.assertEqual(reponse.status_code, 400)

    def test_double_inscription_meme_annee_refusee_en_base(self):
        Inscription.objects.create(
            etudiant=self.etudiant1, annee_scolaire=self.annee, classe=self.classe,
            date_inscription=date(2025, 9, 1), statut=StatutInscription.ACTIVE,
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Inscription.objects.create(
                etudiant=self.etudiant1, annee_scolaire=self.annee, classe=self.classe,
                date_inscription=date(2025, 9, 5), statut=StatutInscription.ACTIVE,
            )


class EtudiantTelephoneNotificationTests(TestCase):
    def test_priorite_telephone_principal(self):
        e = Etudiant(matricule="E010", nom="Sow", prenom="Fatima", telephone_principal="22200000", telephone_pere="22211111")
        self.assertEqual(e.telephone_notification, "22200000")

    def test_repli_sur_telephone_pere(self):
        e = Etudiant(matricule="E011", nom="Sow", prenom="Ali", telephone_pere="22211111")
        self.assertEqual(e.telephone_notification, "22211111")
