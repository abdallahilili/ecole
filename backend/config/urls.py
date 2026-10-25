from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.utilisateurs.urls_auth")),
    path("api/utilisateurs/", include("apps.utilisateurs.urls")),
    path("api/referentiels/", include("apps.referentiels.urls")),
    path("api/etudiants/", include("apps.etudiants.urls")),
    path("api/professeurs/", include("apps.professeurs.urls")),
    path("api/scolarite/", include("apps.scolarite.urls")),
    path("api/presences/", include("apps.presences.urls")),
    path("api/evaluations/", include("apps.evaluations.urls")),
    path("api/emplois-du-temps/", include("apps.emplois_du_temps.urls")),
    path("api/remuneration/", include("apps.remuneration.urls")),
    path("api/tableau-de-bord/", include("apps.tableau_de_bord.urls")),
    path("api/", include("apps.commun.urls")),
]
