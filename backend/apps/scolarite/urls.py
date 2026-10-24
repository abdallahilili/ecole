from rest_framework.routers import DefaultRouter
from .vues import GrilleFraisViewSet, PaiementScolariteViewSet

routeur = DefaultRouter()
routeur.register("grilles-frais", GrilleFraisViewSet, basename="grille-frais")
routeur.register("paiements", PaiementScolariteViewSet, basename="paiement-scolarite")
urlpatterns = routeur.urls
