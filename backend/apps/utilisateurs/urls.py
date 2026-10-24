from rest_framework.routers import DefaultRouter
from .vues import UtilisateurViewSet

routeur = DefaultRouter()
routeur.register("", UtilisateurViewSet, basename="utilisateur")
urlpatterns = routeur.urls
