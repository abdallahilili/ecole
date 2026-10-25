from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PaginationStandard(PageNumberPagination):
    page_size = 20
    page_size_query_param = "taille_page"
    max_page_size = 500
    page_query_param = "page"

    def paginate_queryset(self, queryset, request, view=None):
        self._vue = view
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        # `champs` : colonnes triables/filtrables cote serveur (voir ListeAvanceeMixin).
        vue = getattr(self, "_vue", None)
        champs = sorted(vue.champs_orm()) if hasattr(vue, "champs_orm") else []
        return Response({
            "total": self.page.paginator.count,
            "page": self.page.number,
            "taille_page": self.page.paginator.per_page,
            "nombre_pages": self.page.paginator.num_pages,
            "champs": champs,
            # La liste sait masquer ses elements inactifs : l'interface propose alors « Afficher les inactifs ».
            "inactifs_disponibles": bool(hasattr(vue, "filtre_actif_courant") and vue.filtre_actif_courant()),
            "resultats": data,
        })
