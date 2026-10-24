from rest_framework.routers import DefaultRouter

from .vues import PaiementProfesseurViewSet, ReleveViewSet, TarifProfesseurMatiereViewSet

routeur = DefaultRouter()
routeur.register("tarifs-matiere", TarifProfesseurMatiereViewSet, basename="tarif-professeur-matiere")
routeur.register("releves", ReleveViewSet, basename="releve-remuneration")
routeur.register("paiements", PaiementProfesseurViewSet, basename="paiement-professeur")
urlpatterns = routeur.urls
