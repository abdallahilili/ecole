import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import NoReverseMatch, get_resolver, reverse
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.commun.constantes import Role
from apps.commun.models import JournalAudit
from apps.commun.permissions import PermissionParRole
from apps.referentiels.models import AnneeScolaire, Classe, Niveau
from apps.utilisateurs.models import Utilisateur

BACKEND = Path(__file__).resolve().parents[2]
# Vues volontairement ouvertes ou protegees autrement (jeton propre a l'utilisateur, signature HMAC, controle interne).
VUES_HORS_ROLES = {"MoiView", "MotDePasseView", "ParametresView", "LogoView", "ConnexionView", "RafraichirTokenView",
                   "WebhookWhatsAppView", "TableauDeBordView", "RechercheGlobaleView",
                   "APIRootView"}   # page racine du routeur : simple liste de routes, reservee aux connectes


def utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin", mot_de_passe="motdepasse123", **extra):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe=mot_de_passe, nom="Test", role=role, **extra)


def client_de(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def toutes_les_vues():
    """{classe de vue: initkwargs} pour chaque route de l'API (hors administration Django)."""
    vues = {}

    def parcourir(motifs):
        for motif in motifs:
            if hasattr(motif, "url_patterns"):
                if "admin" in str(motif.pattern):
                    continue
                parcourir(motif.url_patterns)
                continue
            callback = getattr(motif, "callback", None)
            classe = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
            if classe is not None:
                vues.setdefault(classe, getattr(callback, "initkwargs", {}))

    parcourir(get_resolver().url_patterns)
    return vues


class GardeFouPermissionsTests(TestCase):
    """Les permissions sont appliquees cote serveur sur TOUTES les vues : aucune ne doit
    rester ouverte a n'importe quel utilisateur connecte par oubli de roles."""

    def test_chaque_vue_declare_ses_roles(self):
        manquantes = []
        for classe in toutes_les_vues():
            if classe.__name__ in VUES_HORS_ROLES:
                continue
            if PermissionParRole not in getattr(classe, "permission_classes", []):
                manquantes.append(f"{classe.__name__} : PermissionParRole absent")
                continue
            if getattr(classe, "roles_par_action", None):
                continue
            ecritures = any(
                set(a.kwargs.get("methods", [])) & {"post", "put", "patch", "delete"}
                for a in classe.get_extra_actions()
            )
            ecriture_possible = not issubclass(classe, ReadOnlyModelViewSet) or ecritures
            if getattr(classe, "roles_lecture", None) is None:
                manquantes.append(f"{classe.__name__} : roles_lecture absent")
            if ecriture_possible and getattr(classe, "roles_ecriture", None) is None:
                manquantes.append(f"{classe.__name__} : roles_ecriture absent")
        self.assertEqual(manquantes, [])

    def test_les_vues_ouvertes_sont_connues(self):
        ouvertes = {c.__name__ for c in toutes_les_vues() if AllowAny in getattr(c, "permission_classes", [])}
        self.assertEqual(ouvertes, {"ConnexionView", "RafraichirTokenView", "WebhookWhatsAppView"})

    def test_anonyme_refuse_sur_toutes_les_listes(self):
        anonyme = APIClient()
        verifiees = 0
        for classe, initkwargs in toutes_les_vues().items():
            basename = initkwargs.get("basename")
            if not basename or classe.__name__ in VUES_HORS_ROLES:
                continue
            try:
                adresse = reverse(f"{basename}-list")
            except NoReverseMatch:
                continue
            self.assertEqual(anonyme.get(adresse).status_code, 401, adresse)
            verifiees += 1
        self.assertGreater(verifiees, 25)


class MotDePasseTests(TestCase):
    def setUp(self):
        self.admin = utilisateur()
        self.client = client_de(self.admin)

    def creer(self, mot_de_passe=None, identifiant="nouveau"):
        corps = {"identifiant": identifiant, "nom": "Nouveau", "role": "COMPTABLE", "actif": True}
        if mot_de_passe is not None:
            corps["mot_de_passe"] = mot_de_passe
        return self.client.post("/api/utilisateurs/", corps, format="json")

    def test_mot_de_passe_obligatoire_a_la_creation_pas_de_valeur_par_defaut(self):
        reponse = self.creer()
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("obligatoire", reponse.json()["detail"])
        self.assertFalse(Utilisateur.objects.filter(identifiant="nouveau").exists())
        self.assertEqual(self.creer("").status_code, 400)

    def test_politique_de_mot_de_passe(self):
        for faible in ("court1", "12345678", "password", "nouveau123"):                # court, numerique, courant, proche de l'identifiant
            reponse = self.creer(faible)
            self.assertEqual(reponse.status_code, 400, faible)
            self.assertIn("Mot de passe refuse", reponse.json()["detail"])
        self.assertEqual(self.creer("Rentree-2026-Solide").status_code, 201)
        connexion = APIClient().post("/api/auth/connexion/", {"identifiant": "nouveau", "mot_de_passe": "Rentree-2026-Solide"})
        self.assertEqual(connexion.status_code, 200)

    def test_reinitialisation_par_l_administrateur_controlee_et_auditee(self):
        cible = utilisateur(Role.COMPTABLE, "compta")
        url = f"/api/utilisateurs/{cible.id}/"
        self.assertEqual(self.client.patch(url, {"mot_de_passe": "123"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"mot_de_passe": "Nouveau-Secret-77"}, format="json").status_code, 200)
        cible.refresh_from_db()
        self.assertTrue(cible.check_password("Nouveau-Secret-77"))
        self.assertTrue(JournalAudit.objects.filter(action="REINITIALISATION_MOT_DE_PASSE").exists())
        self.client.patch(url, {"nom": "Autre"}, format="json")                        # sans mot de passe : inchange
        cible.refresh_from_db()
        self.assertTrue(cible.check_password("Nouveau-Secret-77"))

    def test_changement_de_son_propre_mot_de_passe(self):
        url = "/api/auth/mot-de-passe/"
        self.assertEqual(self.client.post(url, {"ancien": "faux", "nouveau": "Tres-Solide-2026"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"ancien": "motdepasse123", "nouveau": "motdepasse123"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"ancien": "motdepasse123", "nouveau": "abc"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"ancien": "motdepasse123", "nouveau": "Tres-Solide-2026"}, format="json").status_code, 200)
        connexion = APIClient().post("/api/auth/connexion/", {"identifiant": "admin", "mot_de_passe": "Tres-Solide-2026"})
        self.assertEqual(connexion.status_code, 200)
        self.assertEqual(APIClient().post(url, {"ancien": "x", "nouveau": "y"}).status_code, 401)
        self.assertTrue(JournalAudit.objects.filter(action="CHANGEMENT_MOT_DE_PASSE").exists())


class ComptesProtegesTests(TestCase):
    def setUp(self):
        self.admin = utilisateur()
        self.client = client_de(self.admin)

    def test_le_dernier_administrateur_ne_peut_etre_ni_desactive_ni_retrograde_ni_supprime(self):
        url = f"/api/utilisateurs/{self.admin.id}/"
        self.assertEqual(self.client.patch(url, {"actif": False}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"role": "DIRECTEUR"}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.actif and self.admin.role == Role.ADMINISTRATEUR)

    def test_avec_un_second_administrateur_c_est_possible_mais_pas_se_supprimer_soi_meme(self):
        second = utilisateur(Role.ADMINISTRATEUR, "admin2")
        self.assertEqual(self.client.patch(f"/api/utilisateurs/{second.id}/", {"actif": False}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/utilisateurs/{second.id}/").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/utilisateurs/{self.admin.id}/").status_code, 400)   # soi-meme

    def test_seul_l_administrateur_gere_les_comptes(self):
        directeur = client_de(utilisateur(Role.DIRECTEUR, "dir"))
        self.assertEqual(directeur.get("/api/utilisateurs/").status_code, 200)
        self.assertEqual(directeur.post("/api/utilisateurs/", {"identifiant": "x", "nom": "X", "role": "COMPTABLE", "mot_de_passe": "Solide-pass-9"}, format="json").status_code, 403)


class ConnexionSecuriseeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = utilisateur()

    def test_essais_de_connexion_limites(self):
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"connexion": "3/min"}):
            cache.clear()
            codes = [APIClient().post("/api/auth/connexion/", {"identifiant": "admin", "mot_de_passe": "faux"}).status_code for _ in range(5)]
        self.assertEqual(codes, [401, 401, 401, 429, 429])
        cache.clear()

    def test_connexions_et_echecs_traces(self):
        APIClient().post("/api/auth/connexion/", {"identifiant": "admin", "mot_de_passe": "faux"})
        APIClient().post("/api/auth/connexion/", {"identifiant": "admin", "mot_de_passe": "motdepasse123"})
        actions = list(JournalAudit.objects.values_list("action", flat=True))
        self.assertIn("ECHEC_CONNEXION", actions)
        self.assertIn("CONNEXION", actions)
        # Jamais de mot de passe dans le journal.
        self.assertFalse(any("motdepasse" in str(a.nouvelle_valeur) + str(a.reference_objet) for a in JournalAudit.objects.all()))

    def test_compte_desactive_refuse_meme_avec_un_jeton_existant(self):
        compta = utilisateur(Role.COMPTABLE, "compta")
        jeton = APIClient().post("/api/auth/connexion/", {"identifiant": "compta", "mot_de_passe": "motdepasse123"}).json()["access"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jeton}")
        self.assertEqual(client.get("/api/auth/moi/").status_code, 200)
        compta.actif = False
        compta.save()
        self.assertEqual(client.get("/api/auth/moi/").status_code, 401)


class RobustesseTests(TestCase):
    def setUp(self):
        self.client = client_de(utilisateur())

    def test_suppression_d_une_donnee_protegee_renvoie_400_pas_500(self):
        annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30))
        niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        Classe.objects.create(nom="6AF", niveau=niveau, annee_scolaire=annee, capacite=30)
        reponse = self.client.delete(f"/api/referentiels/niveaux/{niveau.id}/")
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.json()["code"], "protege")
        self.assertTrue(Niveau.objects.filter(pk=niveau.pk).exists())

    def test_fichier_excel_trop_volumineux_refuse(self):
        gros = SimpleUploadedFile("gros.xlsx", b"0" * (6 * 1024 * 1024))
        reponse = self.client.post("/api/etudiants/etudiants/importer/", {"fichier": gros}, format="multipart")
        # L'import des etudiants a son propre controle ; les modules recents (presences, notes) utilisent la limite commune.
        self.assertEqual(reponse.status_code, 400)

    def test_configuration_de_production_exigeante(self):
        def demarrer(env):
            variables = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings", **env}
            variables.pop("CLE_SECRETE", None) if "CLE_SECRETE" not in env else None
            return subprocess.run([sys.executable, "-c", "import django; django.setup()"], cwd=BACKEND, env=variables,
                                  capture_output=True, text=True)
        sans_cle = demarrer({"DEBUG": "0", "UTILISER_SQLITE": "1", "CLE_SECRETE": ""})
        self.assertNotEqual(sans_cle.returncode, 0)
        self.assertIn("CLE_SECRETE", sans_cle.stderr)
        exemple = demarrer({"DEBUG": "0", "UTILISER_SQLITE": "1", "CLE_SECRETE": "change-moi-en-production-0123456789abcdef"})
        self.assertNotEqual(exemple.returncode, 0)
        courte = demarrer({"DEBUG": "0", "UTILISER_SQLITE": "1", "CLE_SECRETE": "trop-courte"})
        self.assertNotEqual(courte.returncode, 0)
        bonne = demarrer({"DEBUG": "0", "UTILISER_SQLITE": "1", "CLE_SECRETE": "x" * 12 + "Qz9-un-secret-assez-long-pour-la-prod-0123"})
        self.assertEqual(bonne.returncode, 0, bonne.stderr)


class MessageSuppressionProtegeeTests(TestCase):
    def test_le_message_indique_ce_qui_bloque_la_suppression(self):
        from apps.commun.traduction import traduire
        annee = AnneeScolaire.objects.create(libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30))
        niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        Classe.objects.create(nom="6AF", niveau=niveau, annee_scolaire=annee, capacite=30)
        Classe.objects.create(nom="6AS", niveau=niveau, annee_scolaire=annee, capacite=30)
        reponse = client_de(utilisateur()).delete(f"/api/referentiels/niveaux/{niveau.id}/")
        self.assertIn("Utilisation : 2 classe(s)", reponse.json()["detail"])
        self.assertIn("2 قسم", traduire(reponse.json()["detail"], langue="ar"))
