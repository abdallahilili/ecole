from rest_framework.routers import DefaultRouter
from .vues import ProfesseurViewSet, AffectationProfesseurViewSet

routeur = DefaultRouter()
routeur.register("professeurs", ProfesseurViewSet, basename="professeur")
routeur.register("affectations", AffectationProfesseurViewSet, basename="affectation-professeur")
urlpatterns = routeur.urls
