from django.urls import path

from .vues import RechercheGlobaleView, TableauDeBordView

urlpatterns = [
    path("", TableauDeBordView.as_view(), name="tableau-de-bord"),
    path("recherche/", RechercheGlobaleView.as_view(), name="recherche-globale"),
]
