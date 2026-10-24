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
        return Response(
            {"detail": "Suppression impossible : cet enregistrement est utilise par d'autres donnees "
                       "(l'historique est conserve).", "code": "protege"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, ErreurMetier):
        return Response({"detail": exc.message, "code": exc.code, **exc.donnees}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, NonAuthentifie):
        return Response({"detail": exc.message}, status=status.HTTP_401_UNAUTHORIZED)
    return exception_handler(exc, context)
