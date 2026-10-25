"""Langue de la requete courante (francais ou arabe).

Le frontend envoie `Accept-Language: fr|ar` ; les telechargements ouverts directement peuvent utiliser `?lang=ar`.
La langue est portee par une variable de contexte : les messages d'erreur, les PDF, les Excel et les messages
WhatsApp la lisent sans que chaque fonction ait a la recevoir en parametre. Hors requete (commandes, tests), le
francais s'applique."""

import contextvars
from contextlib import contextmanager

from django.utils import translation

LANGUES = ("fr", "ar")
LANGUE_PAR_DEFAUT = "fr"

_langue = contextvars.ContextVar("langue", default=LANGUE_PAR_DEFAUT)


def langue_courante():
    return _langue.get()


def est_arabe():
    return _langue.get() == "ar"


@contextmanager
def en_langue(code):
    """Execute un bloc dans la langue donnee (utile hors requete : taches planifiees, tests)."""
    jeton = _langue.set(code if code in LANGUES else LANGUE_PAR_DEFAUT)
    try:
        yield
    finally:
        _langue.reset(jeton)


def detecter_langue(requete):
    demandee = (requete.GET.get("lang") or requete.headers.get("Accept-Language") or "").strip().lower()
    code = demandee[:2]
    return code if code in LANGUES else LANGUE_PAR_DEFAUT


class LangueMiddleware:
    """Pose la langue de la requete (variable de contexte + traductions de Django/DRF pour leurs propres messages)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, requete):
        from .emission import utilisateur_courant

        code = detecter_langue(requete)
        jeton = _langue.set(code)
        jeton_utilisateur = utilisateur_courant.set(None)
        translation.activate(code)
        try:
            reponse = self.get_response(requete)
            reponse["Content-Language"] = code
            return reponse
        finally:
            translation.deactivate()
            _langue.reset(jeton)
            utilisateur_courant.reset(jeton_utilisateur)
