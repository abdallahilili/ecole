from django.urls import path
from rest_framework.routers import DefaultRouter
from .vues import LogoView, ParametresView,JournalAuditViewSet

routeur = DefaultRouter()
routeur.register("journal-audit", JournalAuditViewSet, basename="journal-audit")

urlpatterns = [
    path("parametres/", ParametresView.as_view(), name="parametres"),
    path("parametres/logo/", LogoView.as_view(), name="parametres-logo"),
] + routeur.urls
