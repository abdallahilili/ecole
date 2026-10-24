from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from apps.commun.audit import enregistrer_audit
from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from apps.commun.vues_base import ViewSetGestion
from .models import Utilisateur
from .serializers import (
    ChangementMotDePasseSerializer, ConnexionSerializer, UtilisateurSerializer, dernier_administrateur_actif,
)


class ConnexionView(APIView):
    """Connexion limitee en nombre d'essais (protection contre les attaques par force brute)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "connexion"

    def post(self, request):
        serializer = ConnexionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class RafraichirTokenView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "rafraichir"

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise AuthenticationFailed(str(exc))
        return Response(serializer.validated_data)


class MoiView(APIView):
    def get(self, request):
        return Response(UtilisateurSerializer(request.user, context={"request": request}).data)


class MotDePasseView(APIView):
    """Changement de son propre mot de passe (ancien mot de passe exige, politique appliquee)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "connexion"

    def post(self, request):
        serializer = ChangementMotDePasseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["nouveau"])
        request.user.save(update_fields=["password"])
        enregistrer_audit(request.user, "CHANGEMENT_MOT_DE_PASSE", "Utilisateur", request.user.pk)
        return Response({"detail": "Mot de passe modifie."})


class UtilisateurViewSet(ViewSetGestion):
    queryset = Utilisateur.objects.select_related("professeur").all().order_by("nom")
    serializer_class = UtilisateurSerializer
    roles_lecture = [Role.ADMINISTRATEUR, Role.DIRECTEUR]
    roles_ecriture = [Role.ADMINISTRATEUR]
    search_fields = ["identifiant", "nom", "prenom"]

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ErreurMetier("Vous ne pouvez pas supprimer votre propre compte.")
        if dernier_administrateur_actif(instance):
            raise ErreurMetier("Impossible : c'est le dernier administrateur actif de l'application.")
        enregistrer_audit(self.request.user, "SUPPRESSION", "Utilisateur", instance.pk, ancienne_valeur={"identifiant": instance.identifiant})
        instance.delete()
