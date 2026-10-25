import csv
import io
import json
from datetime import date, time

import openpyxl
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.commun.constantes import Role
from apps.commun.models import JournalAudit
from apps.etudiants.models import Etudiant, Inscription
from apps.evaluations.models import Evaluation
from apps.presences.models import Seance
from apps.professeurs.models import Professeur
from apps.referentiels.models import AnneeScolaire, Classe, Matiere, Niveau
from apps.utilisateurs.models import Utilisateur

ETUDIANTS = "/api/etudiants/etudiants/"
CLASSES = "/api/referentiels/classes/"


def utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin", **extra):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe="motdepasse123", nom="Test", role=role, **extra)


def client_de(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class BaseListe(TestCase):
    def setUp(self):
        self.client = client_de(utilisateur())
        self.annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True)
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.af = Classe.objects.create(nom="6AF", niveau=self.niveau, annee_scolaire=self.annee, capacite=40)
        self.d = Classe.objects.create(nom="7D", niveau=self.niveau, annee_scolaire=self.annee, capacite=40)
        self.awa = self.eleve("E1", "Diallo", "Awa", "F", numero_national="Rim1923198")
        self.moussa = self.eleve("E2", "Ba", "Moussa", "M")
        self.fall = self.eleve("E3", "Fall", "Mariam", "F", actif=False, date_naissance=date(2010, 3, 5))

    def eleve(self, matricule, nom, prenom, sexe, classe=None, **extra):
        etudiant = Etudiant.objects.create(matricule=matricule, nom=nom, prenom=prenom, sexe=sexe, **extra)
        Inscription.objects.create(etudiant=etudiant, annee_scolaire=self.annee, classe=classe or self.af, date_inscription=date(2025, 9, 1))
        return etudiant

    def matricules(self, url=ETUDIANTS, **params):
        reponse = self.client.get(url, params)
        self.assertEqual(reponse.status_code, 200, reponse.content)
        return [e.get("matricule") or e.get("nom") for e in reponse.json()["resultats"]]


class RechercheTriFiltresTests(BaseListe):
    def test_recherche_globale_multi_mots(self):
        self.assertEqual(self.matricules(recherche="Diallo Awa"), ["E1"])
        self.assertEqual(self.matricules(recherche="awa diallo"), ["E1"])                 # ordre et casse indifferents
        self.assertEqual(self.matricules(recherche="Rim1923198"), ["E1"])                 # numero national
        self.assertEqual(sorted(self.matricules(recherche="a")), ["E1", "E2", "E3"])
        self.assertEqual(self.matricules(recherche="Diallo Moussa"), [])                  # chaque mot doit correspondre

    def test_tri_serveur_croissant_decroissant_et_alias(self):
        self.assertEqual(self.matricules(tri="nom_complet"), ["E2", "E1", "E3"])          # Ba, Diallo, Fall
        self.assertEqual(self.matricules(tri="-nom_complet"), ["E3", "E1", "E2"])
        self.assertEqual(self.matricules(tri="-matricule"), ["E3", "E2", "E1"])
        self.assertEqual(self.matricules(tri="sexe,-matricule"), ["E3", "E1", "E2"])       # F (E3, E1) puis M
        self.assertEqual(sorted(self.matricules(tri="champ_inexistant")), ["E1", "E2", "E3"])   # ignore, pas d'erreur

    def test_tri_sur_une_relation_et_une_annotation(self):
        Classe.objects.create(nom="5B", niveau=self.niveau, annee_scolaire=self.annee, capacite=40)
        self.assertEqual([c["nom"] for c in self.client.get(CLASSES, {"tri": "-nom"}).json()["resultats"]], ["7D", "6AF", "5B"])
        self.assertEqual([c["nom"] for c in self.client.get(CLASSES, {"tri": "-effectif"}).json()["resultats"]][0], "6AF")
        inscriptions = self.client.get("/api/etudiants/inscriptions/", {"tri": "etudiant_nom"}).json()["resultats"]
        self.assertEqual(len(inscriptions), 3)

    def test_filtres_par_colonne(self):
        self.assertEqual(self.matricules(col_matricule="E2"), ["E2"])                     # contient
        self.assertEqual(sorted(self.matricules(col_matricule="E")), ["E1", "E2", "E3"])
        self.assertEqual(sorted(self.matricules(col_sexe="F")), ["E1", "E3"])
        self.assertEqual(self.matricules(col_actif="false"), ["E3"])                      # booleen
        self.assertEqual(self.matricules(col_date_naissance="2010-03-05"), ["E3"])        # egalite sur une date
        self.assertEqual(self.matricules(col_sexe="F", col_actif="true"), ["E1"])         # filtres cumules
        self.assertEqual(self.matricules(col_nom="dial", recherche="awa"), ["E1"])        # avec la recherche globale
        self.assertEqual(sorted(self.matricules(col_date_naissance="pas-une-date")), ["E1", "E2", "E3"])  # valeur invalide ignoree

    def test_filtre_sur_une_cle_etrangere_et_une_relation(self):
        inscriptions = self.client.get("/api/etudiants/inscriptions/", {"col_classe": self.d.id}).json()["resultats"]
        self.assertEqual(inscriptions, [])
        par_nom = self.client.get("/api/etudiants/inscriptions/", {"col_classe_nom": "6A"}).json()["resultats"]
        self.assertEqual(len(par_nom), 3)

    def test_la_pagination_annonce_les_colonnes_triables(self):
        champs = self.client.get(ETUDIANTS).json()["champs"]
        self.assertIn("matricule", champs)
        self.assertIn("nom_complet", champs)

    def test_champs_sensibles_inaccessibles(self):
        admin = self.client
        compte = utilisateur(Role.COMPTABLE, "compta")
        champs = admin.get("/api/utilisateurs/").json()["champs"]
        self.assertNotIn("mot_de_passe", champs)
        self.assertNotIn("password", champs)
        # Un filtre ou un tri sur le mot de passe est ignore, il ne doit rien reveler ni casser.
        reponse = admin.get("/api/utilisateurs/", {"col_password": "pbkdf2", "tri": "password", "col_mot_de_passe": "x"})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["total"], 2)
        self.assertNotIn("password", json.dumps(reponse.json()))
        self.assertIsNotNone(compte)

    def test_recherche_et_tri_sur_les_autres_modules(self):
        self.assertEqual(self.client.get("/api/utilisateurs/", {"recherche": "admin"}).json()["total"], 1)
        self.assertEqual(self.client.get("/api/referentiels/niveaux/", {"recherche": "6e"}).json()["total"], 1)
        Professeur.objects.create(matricule="P1", nom="Sy", prenom="Oumar", tarif_horaire=100)
        Professeur.objects.create(matricule="P2", nom="Ba", prenom="Cheikh", tarif_horaire=100)
        noms = [p["nom"] for p in self.client.get("/api/professeurs/professeurs/", {"tri": "nom_complet"}).json()["resultats"]]
        self.assertEqual(noms, ["Ba", "Sy"])


class ExportTests(BaseListe):
    URL = ETUDIANTS + "export/"
    COLONNES = json.dumps([{"cle": "matricule", "titre": "Matricule"}, {"cle": "nom_complet", "titre": "Nom complet"},
                           {"cle": "date_naissance", "titre": "Naissance"}, {"cle": "actif", "titre": "Actif"}])

    def lire_xlsx(self, reponse):
        feuille = openpyxl.load_workbook(io.BytesIO(reponse.content)).active
        return [[c.value for c in ligne] for ligne in feuille.iter_rows()]

    def test_export_excel_colonnes_choisies_et_valeurs_lisibles(self):
        reponse = self.client.get(self.URL, {"colonnes": self.COLONNES, "tri": "matricule"})
        self.assertEqual(reponse.status_code, 200)
        lignes = self.lire_xlsx(reponse)
        self.assertEqual(lignes[0], ["Matricule", "Nom complet", "Naissance", "Actif"])
        self.assertEqual(lignes[1], ["E1", "Diallo Awa", None, "Oui"])
        self.assertEqual(lignes[3], ["E3", "Fall Mariam", "05/03/2010", "Non"])               # date francaise, Oui/Non

    def test_export_du_resultat_filtre_de_la_page_ou_de_la_selection(self):
        filtre = self.lire_xlsx(self.client.get(self.URL, {"colonnes": self.COLONNES, "col_sexe": "F", "recherche": "awa"}))
        self.assertEqual([l[0] for l in filtre[1:]], ["E1"])
        selection = self.lire_xlsx(self.client.get(self.URL, {"colonnes": self.COLONNES, "ids": f"{self.moussa.id},{self.fall.id}", "tri": "matricule"}))
        self.assertEqual([l[0] for l in selection[1:]], ["E2", "E3"])

    def test_export_csv_compatible_excel_francais(self):
        reponse = self.client.get(self.URL, {"colonnes": self.COLONNES, "fichier": "csv", "tri": "matricule"})
        self.assertTrue(reponse["Content-Type"].startswith("text/csv"))
        self.assertTrue(reponse.content.startswith(b"\xef\xbb\xbf"))                          # BOM UTF-8
        lignes = list(csv.reader(io.StringIO(reponse.content.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(lignes[0], ["Matricule", "Nom complet", "Naissance", "Actif"])
        self.assertEqual(lignes[1][:2], ["E1", "Diallo Awa"])

    def test_export_pdf(self):
        reponse = self.client.get(self.URL, {"colonnes": self.COLONNES, "fichier": "pdf", "titre": "Etudiants"})
        self.assertEqual(reponse["Content-Type"], "application/pdf")
        self.assertTrue(reponse.content.startswith(b"%PDF"))

    def test_colonnes_inconnues_ignorees_et_format_invalide_refuse(self):
        self.assertEqual(self.client.get(self.URL, {"fichier": "docx"}).status_code, 400)
        self.assertEqual(self.client.get(self.URL, {"colonnes": "pas du json"}).status_code, 400)
        self.assertEqual(self.client.get(self.URL, {"ids": "a,b"}).status_code, 400)

    def test_un_export_ne_contient_jamais_de_mot_de_passe(self):
        colonnes = json.dumps([{"cle": "identifiant", "titre": "Identifiant"}, {"cle": "mot_de_passe", "titre": "Mot de passe"},
                               {"cle": "password", "titre": "Hash"}])
        lignes = self.lire_xlsx(self.client.get(UTILISATEURS_EXPORT, {"colonnes": colonnes}))
        self.assertEqual(lignes[0], ["Identifiant"])
        self.assertEqual(lignes[1], ["admin"])

    def test_injection_de_formule_neutralisee(self):
        self.eleve("E9", "=CMD|' /C calc'!A0", "+Pirate", "M")
        lignes = self.lire_xlsx(self.client.get(self.URL, {"colonnes": self.COLONNES, "col_matricule": "E9"}))
        self.assertTrue(lignes[1][1].startswith("'="), lignes[1][1])
        texte = self.client.get(self.URL, {"colonnes": self.COLONNES, "col_matricule": "E9", "fichier": "csv"}).content.decode("utf-8-sig")
        self.assertIn("'=CMD", texte)

    def test_les_droits_de_lecture_s_appliquent_a_l_export(self):
        self.assertEqual(client_de(utilisateur(Role.COMPTABLE, "compta")).get(self.URL).status_code, 200)   # lecture autorisee
        self.assertEqual(client_de(utilisateur(Role.COMPTABLE, "compta2")).get("/api/utilisateurs/export/").status_code, 403)
        self.assertEqual(APIClient().get(self.URL).status_code, 401)

    def test_l_export_respecte_le_filtrage_par_role(self):
        sy = Professeur.objects.create(matricule="P1", nom="Sy", prenom="Oumar", tarif_horaire=100)
        ba = Professeur.objects.create(matricule="P2", nom="Ba", prenom="Cheikh", tarif_horaire=100)
        maths = Matiere.objects.create(nom="Maths", code="MATH")
        for prof, heure in ((sy, 8), (ba, 9)):
            Seance.objects.create(annee_scolaire=self.annee, classe=self.af, matiere=maths, professeur=prof,
                                  date=date(2025, 10, 6), heure_debut=time(heure, 0), heure_fin=time(heure + 1, 0))
        prof_client = client_de(utilisateur(Role.PROFESSEUR, "prof", professeur=sy))
        colonnes = json.dumps([{"cle": "professeur_nom", "titre": "Professeur"}])
        lignes = self.lire_xlsx(prof_client.get("/api/presences/seances/export/", {"colonnes": colonnes}))
        self.assertEqual([l[0] for l in lignes[1:]], ["Sy Oumar"])                          # jamais les seances de Ba


UTILISATEURS_EXPORT = "/api/utilisateurs/export/"


class SuppressionMultipleTests(BaseListe):
    URL = "/api/referentiels/niveaux/supprimer-multiple/"

    def setUp(self):
        super().setUp()
        self.n1 = Niveau.objects.create(nom="N1", code="N1", ordre=2)
        self.n2 = Niveau.objects.create(nom="N2", code="N2", ordre=3)

    def test_suppression_groupee_et_audit(self):
        reponse = self.client.post(self.URL, {"ids": [self.n1.id, self.n2.id]}, format="json")
        self.assertEqual((reponse.status_code, reponse.json()["supprimes"]), (200, 2))
        self.assertFalse(Niveau.objects.filter(code__in=["N1", "N2"]).exists())
        audit = JournalAudit.objects.get(action="SUPPRESSION_MULTIPLE")
        self.assertEqual(sorted(audit.ancienne_valeur["ids"]), sorted([self.n1.id, self.n2.id]))

    def test_tout_ou_rien_si_un_element_est_protege(self):
        reponse = self.client.post(self.URL, {"ids": [self.n1.id, self.niveau.id]}, format="json")   # 6eme est utilise par des classes
        self.assertEqual(reponse.status_code, 400)
        self.assertTrue(Niveau.objects.filter(pk=self.n1.pk).exists())                                 # rien n'a ete supprime

    def test_selection_invalide_ou_introuvable(self):
        self.assertEqual(self.client.post(self.URL, {"ids": []}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.URL, {}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.URL, {"ids": [self.n1.id, 99999]}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.URL, {"ids": list(range(1, 502))}, format="json").status_code, 400)   # limite 500
        self.assertTrue(Niveau.objects.filter(pk=self.n1.pk).exists())

    def test_memes_droits_que_la_suppression_unitaire(self):
        prof = client_de(utilisateur(Role.PROFESSEUR, "prof"))
        self.assertEqual(prof.post(self.URL, {"ids": [self.n1.id]}, format="json").status_code, 403)
        compta = client_de(utilisateur(Role.COMPTABLE, "compta"))
        self.assertEqual(compta.post(self.URL, {"ids": [self.n1.id]}, format="json").status_code, 403)
        self.assertEqual(APIClient().post(self.URL, {"ids": [self.n1.id]}, format="json").status_code, 401)
        self.assertTrue(Niveau.objects.filter(pk=self.n1.pk).exists())

    def test_les_regles_metier_de_suppression_s_appliquent_au_lot(self):
        # Une seance contenant des presences ne peut pas etre supprimee, meme en lot.
        maths = Matiere.objects.create(nom="Maths", code="MATH")
        prof = Professeur.objects.create(matricule="P1", nom="Sy", prenom="Oumar", tarif_horaire=100)
        libre = Seance.objects.create(annee_scolaire=self.annee, classe=self.af, matiere=maths, professeur=prof,
                                      date=date(2025, 10, 6), heure_debut=time(8), heure_fin=time(9))
        occupee = Seance.objects.create(annee_scolaire=self.annee, classe=self.af, matiere=maths, professeur=prof,
                                        date=date(2025, 10, 7), heure_debut=time(8), heure_fin=time(9))
        occupee.presences.create(etudiant=self.awa, statut="PRESENT")
        reponse = self.client.post("/api/presences/seances/supprimer-multiple/", {"ids": [libre.id, occupee.id]}, format="json")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("presences", reponse.json()["detail"])
        self.assertEqual(Seance.objects.count(), 2)
        self.assertEqual(self.client.post("/api/presences/seances/supprimer-multiple/", {"ids": [libre.id]}, format="json").status_code, 200)


class PerformanceTests(BaseListe):
    def nombre_requetes(self, url):
        with CaptureQueriesContext(connection) as contexte:
            self.assertEqual(self.client.get(url, {"taille_page": 100}).status_code, 200)
        return len(contexte)

    def test_nombre_de_requetes_constant_quel_que_soit_le_volume(self):
        urls = (CLASSES, "/api/etudiants/inscriptions/", ETUDIANTS, "/api/presences/seances/", "/api/evaluations/evaluations/",
                "/api/presences/historique/")
        maths = Matiere.objects.create(nom="Maths", code="MATH")
        prof = Professeur.objects.create(matricule="P1", nom="Sy", prenom="Oumar", tarif_horaire=100)

        def ajouter(i):
            classe = Classe.objects.create(nom=f"C{i}", niveau=self.niveau, annee_scolaire=self.annee, capacite=40)
            etudiant = self.eleve(f"X{i}", f"Nom{i}", "Prenom", "M", classe=classe)
            seance = Seance.objects.create(annee_scolaire=self.annee, classe=classe, matiere=maths, professeur=prof,
                                           date=date(2025, 10, 6), heure_debut=time(8), heure_fin=time(9))
            seance.presences.create(etudiant=etudiant, statut="ABSENT")
            Evaluation.objects.create(annee_scolaire=self.annee, classe=classe, matiere=maths, trimestre=1, libelle=f"Devoir {i}")

        ajouter(0)
        avant = {url: self.nombre_requetes(url) for url in urls}
        for i in range(1, 26):
            ajouter(i)
        for url in urls:
            self.assertEqual(self.nombre_requetes(url), avant[url], f"{url} : nombre de requetes croissant avec le volume (N+1)")
