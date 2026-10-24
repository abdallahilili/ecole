from rest_framework.routers import DefaultRouter

from .vues import EvaluationViewSet, ResultatsViewSet

routeur = DefaultRouter()
routeur.register("evaluations", EvaluationViewSet, basename="evaluation")
routeur.register("resultats", ResultatsViewSet, basename="resultats")
urlpatterns = routeur.urls
