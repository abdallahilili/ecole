from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import filters
from django.db import transaction

from .exceptions import ErreurMetier
from .models import Parametre, JournalAudit
from .parametres import DEFAUTS
from .serializers import JournalAuditSerializer
from .permissions import PermissionParRole
from .constantes import Role
from .vues_base import ViewSetLecture


def _parametres_courants():
    return {**DEFAUTS, **{p.cle: p.valeur for p in Parametre.objects.all()}}


class ParametresView(APIView):
    """Parametres de l'etablissement (valeurs par defaut incluses). Seules
    les cles connues sont modifiables, par l'administrateur uniquement."""

    def get(self, request):
        return Response(_parametres_courants())

    def put(self, request):
        if request.user.role != Role.ADMINISTRATEUR:
            return Response({"detail": "Reserve a l'administrateur."}, status=403)
        inconnus = [cle for cle in request.data if cle not in DEFAUTS]
        if inconnus:
            raise ErreurMetier(f"Parametre(s) inconnu(s) : {', '.join(inconnus)}.")
        if any(len(str(valeur)) > 255 for valeur in request.data.values()):
            raise ErreurMetier("Une valeur depasse 255 caracteres.")
        with transaction.atomic():
            for cle, valeur in request.data.items():
                Parametre.objects.update_or_create(cle=cle, defaults={"valeur": str(valeur)})
        return Response(_parametres_courants())


class JournalAuditViewSet(ViewSetLecture):
    queryset = JournalAudit.objects.select_related("utilisateur").all()
    serializer_class = JournalAuditSerializer
    permission_classes = [PermissionParRole]
    roles_lecture = [Role.ADMINISTRATEUR, Role.DIRECTEUR]
    roles_ecriture = []
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["modele", "action", "reference_objet"]
    ordering_fields = ["date_action"]
