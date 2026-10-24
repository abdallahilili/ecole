from rest_framework.routers import DefaultRouter
from .vues import EtudiantViewSet, InscriptionViewSet

routeur = DefaultRouter()
routeur.register("etudiants", EtudiantViewSet, basename="etudiant")
routeur.register("inscriptions", InscriptionViewSet, basename="inscription")
urlpatterns = routeur.urls
