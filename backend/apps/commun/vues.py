import os

from PIL import Image
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import filters
from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404

from .exceptions import ErreurMetier
from .models import Parametre, JournalAudit
from .parametres import DEFAUTS, chemin_logo_televerse
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


TAILLE_MAX_LOGO = 2 * 1024 * 1024
DIMENSION_MAX_LOGO = 600


class LogoView(APIView):
    """Logo de l'ecole (imprime sur les PDF). Lecture : tout utilisateur connecte ;
    envoi et suppression : administrateur. L'image est normalisee en PNG."""
    parser_classes = [MultiPartParser]

    def get(self, request):
        chemin = chemin_logo_televerse()
        if not chemin:
            raise Http404
        return FileResponse(open(chemin, "rb"), content_type="image/png")

    def post(self, request):
        if request.user.role != Role.ADMINISTRATEUR:
            return Response({"detail": "Reserve a l'administrateur."}, status=403)
        fichier = request.FILES.get("logo")
        if fichier is None:
            raise ErreurMetier("Aucun fichier recu.")
        if fichier.size > TAILLE_MAX_LOGO:
            raise ErreurMetier("Le logo ne doit pas depasser 2 Mo.")
        try:
            image = Image.open(fichier)
            image.load()
        except Exception:
            raise ErreurMetier("Le fichier n'est pas une image valide (PNG ou JPEG).")
        if image.format not in ("PNG", "JPEG"):
            raise ErreurMetier("Le fichier n'est pas une image valide (PNG ou JPEG).")
        image = image.convert("RGBA")
        image.thumbnail((DIMENSION_MAX_LOGO, DIMENSION_MAX_LOGO))
        dossier = os.path.join(settings.MEDIA_ROOT, "ecole")
        os.makedirs(dossier, exist_ok=True)
        image.save(os.path.join(dossier, "logo.png"), "PNG")
        return Response({"logo": True})

    def delete(self, request):
        if request.user.role != Role.ADMINISTRATEUR:
            return Response({"detail": "Reserve a l'administrateur."}, status=403)
        chemin = chemin_logo_televerse()
        if chemin:
            os.remove(chemin)
        return Response(status=204)


class JournalAuditViewSet(ViewSetLecture):
    queryset = JournalAudit.objects.select_related("utilisateur").all()
    serializer_class = JournalAuditSerializer
    permission_classes = [PermissionParRole]
    roles_lecture = [Role.ADMINISTRATEUR, Role.DIRECTEUR]
    roles_ecriture = []
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["modele", "action", "reference_objet"]
    ordering_fields = ["date_action"]
