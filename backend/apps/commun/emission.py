"""Date et utilisateur de l'emission d'un document (PDF, Excel) : imprimes sur chaque fichier exporte.

L'utilisateur est pose par l'authentification JWT dans une variable de contexte reinitialisee par
LangueMiddleware a la fin de la requete : les generateurs de documents le lisent sans le recevoir en parametre.
Hors requete (commandes, tests), aucun utilisateur n'est imprime."""

import contextvars

from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from .langue import est_arabe

utilisateur_courant = contextvars.ContextVar("utilisateur_emission", default=None)


class AuthentificationJWT(JWTAuthentication):
    """JWTAuthentication qui retient l'utilisateur authentifie pour les documents exportes."""

    def authenticate(self, requete):
        resultat = super().authenticate(requete)
        if resultat is not None:
            utilisateur_courant.set(resultat[0])
        return resultat


def nom_utilisateur():
    utilisateur = utilisateur_courant.get()
    if utilisateur is None:
        return ""
    return f"{utilisateur.prenom} {utilisateur.nom}".strip() or utilisateur.identifiant


def mention_emission():
    """« Imprime le 25/10/2026 a 14:30 par Prenom Nom » dans la langue courante."""
    maintenant = timezone.localtime()
    date, heure = maintenant.strftime("%d/%m/%Y"), maintenant.strftime("%H:%M")
    nom = nom_utilisateur()
    if est_arabe():
        return f"طُبع بتاريخ {date} الساعة {heure}" + (f" بواسطة {nom}" if nom else "")
    return f"Imprime le {date} a {heure}" + (f" par {nom}" if nom else "")
