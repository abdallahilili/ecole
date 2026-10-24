from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from apps.commun.audit import enregistrer_audit
from apps.commun.constantes import MODULES_PAR_ROLE, Role
from apps.commun.exceptions import ErreurMetier
from .models import Utilisateur


def controler_mot_de_passe(mot_de_passe, utilisateur=None):
    """Applique la politique de mot de passe (AUTH_PASSWORD_VALIDATORS) ; ErreurMetier explicite sinon."""
    try:
        validate_password(mot_de_passe, utilisateur)
    except ValidationError as e:
        raise ErreurMetier("Mot de passe refuse : " + " ".join(e.messages))
    return mot_de_passe


def dernier_administrateur_actif(utilisateur):
    """True si `utilisateur` est le seul administrateur actif (le compte ne doit jamais disparaitre)."""
    if utilisateur.role != Role.ADMINISTRATEUR or not utilisateur.actif:
        return False
    return not Utilisateur.objects.filter(role=Role.ADMINISTRATEUR, actif=True).exclude(pk=utilisateur.pk).exists()


class UtilisateurSerializer(serializers.ModelSerializer):
    mot_de_passe = serializers.CharField(write_only=True, required=False, allow_blank=True)
    modules = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = ["id", "identifiant", "nom", "prenom", "telephone", "role",
                  "professeur", "actif", "date_creation", "mot_de_passe", "modules"]

    def get_modules(self, obj):
        return MODULES_PAR_ROLE.get(obj.role, [])

    def validate(self, donnees):
        instance = self.instance
        if instance is not None and dernier_administrateur_actif(instance):
            if donnees.get("actif", True) is False or donnees.get("role", instance.role) != Role.ADMINISTRATEUR:
                raise ErreurMetier("Impossible : c'est le dernier administrateur actif de l'application.")
        return donnees

    def create(self, donnees_validees):
        mot_de_passe = donnees_validees.pop("mot_de_passe", None)
        if not mot_de_passe:
            raise ErreurMetier("Un mot de passe est obligatoire a la creation du compte.")
        utilisateur = Utilisateur(**donnees_validees)
        controler_mot_de_passe(mot_de_passe, utilisateur)
        utilisateur.set_password(mot_de_passe)
        utilisateur.save()
        return utilisateur

    def update(self, instance, donnees_validees):
        mot_de_passe = donnees_validees.pop("mot_de_passe", None)
        for cle, valeur in donnees_validees.items():
            setattr(instance, cle, valeur)
        if mot_de_passe:
            controler_mot_de_passe(mot_de_passe, instance)
            instance.set_password(mot_de_passe)
            enregistrer_audit(self.context["request"].user, "REINITIALISATION_MOT_DE_PASSE", "Utilisateur", instance.pk)
        instance.save()
        return instance


class ConnexionSerializer(serializers.Serializer):
    identifiant = serializers.CharField()
    mot_de_passe = serializers.CharField(write_only=True)

    def _ip(self):
        requete = self.context.get("request")
        return requete.META.get("REMOTE_ADDR") if requete else None

    def validate(self, attrs):
        utilisateur = authenticate(identifiant=attrs["identifiant"], password=attrs["mot_de_passe"])
        if utilisateur is None:
            enregistrer_audit(None, "ECHEC_CONNEXION", "Utilisateur", attrs["identifiant"][:100], nouvelle_valeur={"ip": self._ip()})
            raise AuthenticationFailed("Identifiant ou mot de passe incorrect.")
        if not utilisateur.actif:
            enregistrer_audit(None, "CONNEXION_COMPTE_DESACTIVE", "Utilisateur", utilisateur.pk, nouvelle_valeur={"ip": self._ip()})
            raise AuthenticationFailed("Ce compte est desactive.")
        enregistrer_audit(utilisateur, "CONNEXION", "Utilisateur", utilisateur.pk, nouvelle_valeur={"ip": self._ip()})
        refresh = RefreshToken.for_user(utilisateur)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "utilisateur": UtilisateurSerializer(utilisateur, context=self.context).data,
        }


class ChangementMotDePasseSerializer(serializers.Serializer):
    ancien = serializers.CharField(write_only=True)
    nouveau = serializers.CharField(write_only=True)

    def validate(self, attrs):
        utilisateur = self.context["request"].user
        if not utilisateur.check_password(attrs["ancien"]):
            raise ErreurMetier("Le mot de passe actuel est incorrect.")
        if attrs["ancien"] == attrs["nouveau"]:
            raise ErreurMetier("Le nouveau mot de passe doit etre different de l'ancien.")
        controler_mot_de_passe(attrs["nouveau"], utilisateur)
        return attrs
