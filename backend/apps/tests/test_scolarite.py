from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient

from apps.commun.constantes import Role
from apps.utilisateurs.models import Utilisateur
from apps.referentiels.models import AnneeScolaire, Niveau, Classe, TarifClasse
from apps.etudiants.models import Etudiant, Inscription
from apps.scolarite.models import GrilleFrais, PaiementScolarite, TypeFrais


def creer_utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin"):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe="secret123", nom="Test", role=role)


class PaiementScolariteTests(TestCase):
    def setUp(self):
        self.annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True)
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.classe = Classe.objects.create(nom="6eme A", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)
        self.etudiant = Etudiant.objects.create(matricule="E100", nom="Fall", prenom="Mariam")
        self.inscription = Inscription.objects.create(
            etudiant=self.etudiant, annee_scolaire=self.annee, classe=self.classe, date_inscription=date(2025, 9, 1),
        )
        GrilleFrais.objects.create(annee_scolaire=self.annee, niveau=self.niveau, montant_mensuel=1500, frais_inscription=500, nombre_mois=9)
        self.client = APIClient()
        self.utilisateur = creer_utilisateur()
        self.client.force_authenticate(self.utilisateur)

    def test_creation_paiement_genere_une_reference(self):
        reponse = self.client.post("/api/scolarite/paiements/", {
            "inscription": self.inscription.id, "type_frais": TypeFrais.MENSUALITE,
            "mois_concerne": "2025-10-01", "montant": "1500", "date_paiement": "2025-10-05",
        })
        self.assertEqual(reponse.status_code, 201)
        self.assertTrue(reponse.data["reference"].startswith("SCOL-"))

    def test_double_paiement_meme_mois_refuse(self):
        PaiementScolarite.objects.create(
            reference="SCOL-2025-00001", inscription=self.inscription, type_frais=TypeFrais.MENSUALITE,
            mois_concerne=date(2025, 10, 1), montant=1500, date_paiement=date(2025, 10, 5),
            enregistre_par=self.utilisateur,
        )
        reponse = self.client.post("/api/scolarite/paiements/", {
            "inscription": self.inscription.id, "type_frais": TypeFrais.MENSUALITE,
            "mois_concerne": "2025-10-01", "montant": "1500", "date_paiement": "2025-10-20",
        })
        self.assertEqual(reponse.status_code, 400)

    def test_paiement_immuable_ne_peut_pas_etre_modifie(self):
        paiement = PaiementScolarite.objects.create(
            reference="SCOL-2025-00002", inscription=self.inscription, type_frais=TypeFrais.MENSUALITE,
            mois_concerne=date(2025, 11, 1), montant=1500, date_paiement=date(2025, 11, 2),
            enregistre_par=self.utilisateur,
        )
        paiement.montant = 2000
        with self.assertRaises(TypeError):
            paiement.save()

    def test_paiement_immuable_ne_peut_pas_etre_supprime(self):
        paiement = PaiementScolarite.objects.create(
            reference="SCOL-2025-00003", inscription=self.inscription, type_frais=TypeFrais.MENSUALITE,
            mois_concerne=date(2025, 12, 1), montant=1500, date_paiement=date(2025, 12, 2),
            enregistre_par=self.utilisateur,
        )
        with self.assertRaises(TypeError):
            paiement.delete()

    def test_situation_mensuelle_reflete_les_paiements(self):
        PaiementScolarite.objects.create(
            reference="SCOL-2025-00004", inscription=self.inscription, type_frais=TypeFrais.INSCRIPTION,
            montant=500, date_paiement=date(2025, 9, 1), enregistre_par=self.utilisateur,
        )
        PaiementScolarite.objects.create(
            reference="SCOL-2025-00005", inscription=self.inscription, type_frais=TypeFrais.MENSUALITE,
            mois_concerne=date(2025, 10, 1), montant=1500, date_paiement=date(2025, 10, 3),
            enregistre_par=self.utilisateur,
        )
        reponse = self.client.get(f"/api/scolarite/paiements/situation/{self.inscription.id}/")
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.data["frais_inscription_paye"])
        self.assertEqual(reponse.data["mois_payes"], ["2025-10"])
        self.assertEqual(reponse.data["total_paye"], "2000.00")

    def test_situation_utilise_le_tarif_de_la_classe(self):
        url = f"/api/scolarite/paiements/situation/{self.inscription.id}/"
        # Sans tarif de classe : grille du niveau.
        self.assertEqual(self.client.get(url).data["montant_mensuel"], "1500.00")
        TarifClasse.objects.create(classe=self.classe, montant=900)
        self.assertEqual(self.client.get(url).data["montant_mensuel"], "900.00")

    def test_montant_negatif_refuse(self):
        reponse = self.client.post("/api/scolarite/paiements/", {
            "inscription": self.inscription.id, "type_frais": TypeFrais.MENSUALITE,
            "mois_concerne": "2025-10-01", "montant": "-100", "date_paiement": "2025-10-05",
        })
        self.assertEqual(reponse.status_code, 400)
