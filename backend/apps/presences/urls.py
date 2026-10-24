from django.urls import path
from rest_framework.routers import DefaultRouter

from .vues import HistoriquePresencesViewSet, NotificationViewSet, SeanceViewSet, WebhookWhatsAppView

routeur = DefaultRouter()
routeur.register("seances", SeanceViewSet, basename="seance")
routeur.register("historique", HistoriquePresencesViewSet, basename="historique-presence")
routeur.register("notifications", NotificationViewSet, basename="notification-whatsapp")

urlpatterns = [
    path("whatsapp/webhook/", WebhookWhatsAppView.as_view(), name="webhook-whatsapp"),
] + routeur.urls
