from rest_framework.routers import DefaultRouter
from .vues import FicheScolariteViewSet, GrilleFraisViewSet, PaiementScolariteViewSet

routeur = DefaultRouter()
routeur.register("grilles-frais", GrilleFraisViewSet, basename="grille-frais")
routeur.register("paiements", PaiementScolariteViewSet, basename="paiement-scolarite")
routeur.register("fiches", FicheScolariteViewSet, basename="fiche-scolarite")
urlpatterns = routeur.urls
