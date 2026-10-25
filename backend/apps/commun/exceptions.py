from collections import Counter

from django.db.models import ProtectedError, RestrictedError
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


class ErreurMetier(Exception):
    def __init__(self, message, code="erreur_metier", donnees=None):
        self.message = message
        self.code = code
        self.donnees = donnees or {}   # champs supplementaires renvoyes au client (ex. liste de conflits)
        super().__init__(message)


class NonAuthentifie(Exception):
    def __init__(self, message="Authentification requise"):
        self.message = message
        super().__init__(message)


def gestionnaire_exceptions(exc, context):
    if isinstance(exc, (ProtectedError, RestrictedError)):
        # Suppression d'une donnee referencee ailleurs : l'historique est conserve (jamais d'erreur 500).
        message = "Suppression impossible : cet enregistrement est utilise par d'autres donnees (l'historique est conserve)."
        utilisations = Counter(
            str(type(o)._meta.verbose_name).lower() for o in getattr(exc, "protected_objects", None) or getattr(exc, "restricted_objects", ()))
        if utilisations:
            # Le detail suit la phrase fixe (traduite a part) : "Utilisation : 24 seance(s) ; 15 evaluation(s)".
            message += " Utilisation : " + " ; ".join(f"{n} {nom}(s)" for nom, n in utilisations.most_common())
        return Response({"detail": message, "code": "protege"}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, ErreurMetier):
        return Response({"detail": exc.message, "code": exc.code, **exc.donnees}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, NonAuthentifie):
        return Response({"detail": exc.message}, status=status.HTTP_401_UNAUTHORIZED)
    return exception_handler(exc, context)
