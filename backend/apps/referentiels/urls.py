from rest_framework.routers import DefaultRouter
from .vues import (
    AnneeScolaireViewSet, NiveauViewSet, SalleViewSet, ClasseViewSet, TarifClasseViewSet,
    GroupeViewSet, MatiereViewSet, AffectationMatiereClasseViewSet,
)

routeur = DefaultRouter()
routeur.register("annees-scolaires", AnneeScolaireViewSet, basename="annee-scolaire")
routeur.register("niveaux", NiveauViewSet, basename="niveau")
routeur.register("salles", SalleViewSet, basename="salle")
routeur.register("classes", ClasseViewSet, basename="classe")
routeur.register("tarifs-classes", TarifClasseViewSet, basename="tarif-classe")
routeur.register("groupes", GroupeViewSet, basename="groupe")
routeur.register("matieres", MatiereViewSet, basename="matiere")
routeur.register("affectations-matiere-classe", AffectationMatiereClasseViewSet, basename="affectation-matiere-classe")
urlpatterns = routeur.urls
