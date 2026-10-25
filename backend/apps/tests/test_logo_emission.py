import io

import openpyxl  # noqa: F401
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from django.test import TestCase

from apps.commun.constantes import Role
from apps.commun.emission import mention_emission
from apps.commun.langue import en_langue
from apps.tests.test_securite import utilisateur
import tempfile
from unittest import mock

from apps.commun import exports_generiques


def _client(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + str(AccessToken.for_user(user)))
    return client


def _image(format_="PNG"):
    tampon = io.BytesIO()
    Image.new("RGB", (900, 300), "red").save(tampon, format_)
    tampon.seek(0)
    tampon.name = "logo." + format_.lower()
    return tampon


class LogoEtEmissionTests(TestCase):
    def setUp(self):
        self._media = tempfile.TemporaryDirectory()
        self.addCleanup(self._media.cleanup)
        self._reglage = override_settings(MEDIA_ROOT=self._media.name)
        self._reglage.enable()
        self.addCleanup(self._reglage.disable)
        self.admin = utilisateur(Role.ADMINISTRATEUR, "admin")

    def test_logo_envoi_lecture_suppression(self):
        client = _client(self.admin)
        self.assertEqual(client.get("/api/parametres/logo/").status_code, 404)
        self.assertEqual(client.post("/api/parametres/logo/", {"logo": _image("JPEG")}, format="multipart").status_code, 200)
        reponse = client.get("/api/parametres/logo/")
        self.assertEqual(reponse["Content-Type"], "image/png")
        self.assertEqual(Image.open(io.BytesIO(b"".join(reponse.streaming_content))).size, (600, 200))
        self.assertEqual(client.delete("/api/parametres/logo/").status_code, 204)
        self.assertEqual(client.get("/api/parametres/logo/").status_code, 404)

    def test_fichier_invalide_refuse_et_envoi_reserve_a_l_administrateur(self):
        faux = io.BytesIO(b"pas une image")
        faux.name = "x.png"
        self.assertEqual(_client(self.admin).post("/api/parametres/logo/", {"logo": faux}, format="multipart").status_code, 400)
        prof = utilisateur(Role.PROFESSEUR, "prof")
        self.assertEqual(_client(prof).post("/api/parametres/logo/", {"logo": _image()}, format="multipart").status_code, 403)
        self.assertEqual(_client(prof).get("/api/parametres/logo/").status_code, 404)   # lecture permise

    def test_pdf_exporte_avec_logo_entete_bilingue_et_mention(self):
        client = _client(self.admin)
        client.post("/api/parametres/logo/", {"logo": _image()}, format="multipart")
        for langue in ("fr", "ar"):
            reponse = client.get("/api/etudiants/etudiants/export/", {"fichier": "pdf"}, HTTP_ACCEPT_LANGUAGE=langue)
            self.assertEqual(reponse.status_code, 200)
            self.assertTrue(reponse.content.startswith(b"%PDF"))

    def test_mention_d_emission_nomme_l_utilisateur_pendant_la_requete(self):
        self.assertNotIn(" par ", mention_emission())          # hors requete : pas d'utilisateur
        vues = []
        construire = exports_generiques.construire_pdf

        def espion(*args, **kwargs):
            vues.append(mention_emission())
            return construire(*args, **kwargs)

        with mock.patch.object(exports_generiques, "construire_pdf", espion):
            _client(self.admin).get("/api/etudiants/etudiants/export/", {"fichier": "pdf"})
        self.assertRegex(vues[0], r"^Imprime le \d\d/\d\d/\d{4} a \d\d:\d\d par Test$")
        self.assertIn("طُبع بتاريخ", mention_emission_ar())


def mention_emission_ar():
    with en_langue("ar"):
        return mention_emission()
