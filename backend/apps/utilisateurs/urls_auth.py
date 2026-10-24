from django.urls import path
from .vues import ConnexionView, MoiView, MotDePasseView, RafraichirTokenView

urlpatterns = [
    path("connexion/", ConnexionView.as_view(), name="connexion"),
    path("rafraichir/", RafraichirTokenView.as_view(), name="rafraichir"),
    path("moi/", MoiView.as_view(), name="moi"),
    path("mot-de-passe/", MotDePasseView.as_view(), name="mot-de-passe"),
]
