from rest_framework.routers import DefaultRouter

from .vues import (
    ConfigurationHorairesViewSet, DisponibiliteProfesseurViewSet, EmploiDuTempsViewSet,
    IndisponibiliteSalleViewSet, SeanceProgrammeeViewSet,
)

routeur = DefaultRouter()
routeur.register("configuration", ConfigurationHorairesViewSet, basename="configuration-horaires")
routeur.register("disponibilites-professeurs", DisponibiliteProfesseurViewSet, basename="disponibilite-professeur")
routeur.register("indisponibilites-salles", IndisponibiliteSalleViewSet, basename="indisponibilite-salle")
routeur.register("emplois", EmploiDuTempsViewSet, basename="emploi-du-temps")
routeur.register("seances", SeanceProgrammeeViewSet, basename="seance-programmee")
urlpatterns = routeur.urls
