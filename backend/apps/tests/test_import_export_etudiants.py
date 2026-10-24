import io
import openpyxl
from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.commun.constantes import Role
from apps.utilisateurs.models import Utilisateur
from apps.etudiants.models import Etudiant


def creer_utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin"):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe="secret123", nom="Test", role=role)


def construire_xlsx(lignes):
    classeur = openpyxl.Workbook()
    feuille = classeur.active
    feuille.append([
        "Matricule", "Nom", "Prenom", "Sexe", "Date de naissance", "Lieu de naissance",
        "Numero national", "Adresse", "Nom du pere", "Telephone du pere", "Nom de la mere",
        "Telephone de la mere", "Nom du tuteur", "Telephone du tuteur", "Telephone principal",
    ])
    for ligne in lignes:
        feuille.append(ligne)
    tampon = io.BytesIO()
    classeur.save(tampon)
    tampon.seek(0)
    return tampon


class ImportExportEtudiantsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(creer_utilisateur())

    def test_telechargement_modele_import(self):
        reponse = self.client.get("/api/etudiants/etudiants/modele-import/")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("spreadsheetml", reponse["Content-Type"])

    def test_import_valide_cree_les_etudiants(self):
        tampon = construire_xlsx([
            ["E200", "Camara", "Aissata", "F", "2012-05-03"] + [""] * 10,
            ["E201", "Keita", "Sekou", "M", "2011-02-20"] + [""] * 10,
        ])
        fichier = SimpleUploadedFile("import.xlsx", tampon.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse = self.client.post("/api/etudiants/etudiants/importer/", {"fichier": fichier}, format="multipart")
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(Etudiant.objects.count(), 2)

    def test_import_avec_matricule_manquant_est_refuse_integralement(self):
        tampon = construire_xlsx([
            ["E300", "Camara", "Aissata", "F"] + [""] * 11,
            ["", "Keita", "Sekou", "M"] + [""] * 11,
        ])
        fichier = SimpleUploadedFile("import.xlsx", tampon.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse = self.client.post("/api/etudiants/etudiants/importer/", {"fichier": fichier}, format="multipart")
        self.assertEqual(reponse.status_code, 400)
        # Import tout-ou-rien : aucune ligne ne doit avoir ete enregistree.
        self.assertEqual(Etudiant.objects.filter(matricule="E300").count(), 0)

    def test_import_matricule_deja_existant_refuse(self):
        Etudiant.objects.create(matricule="E400", nom="Existant", prenom="Deja")
        tampon = construire_xlsx([["E400", "Nouveau", "Doublon", "M"] + [""] * 11])
        fichier = SimpleUploadedFile("import.xlsx", tampon.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse = self.client.post("/api/etudiants/etudiants/importer/", {"fichier": fichier}, format="multipart")
        self.assertEqual(reponse.status_code, 400)

    def test_export_retourne_un_fichier_excel(self):
        Etudiant.objects.create(matricule="E500", nom="Sall", prenom="Binta")
        reponse = self.client.get("/api/etudiants/etudiants/exporter/")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("spreadsheetml", reponse["Content-Type"])
