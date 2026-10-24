from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.commun.constantes import Role
from apps.commun.vues_base import ViewSetGestion
from .models import AnneeScolaire, Niveau, Salle, Classe, TarifClasse, Groupe, Matiere, AffectationMatiereClasse
from .serializers import (
    AnneeScolaireSerializer, NiveauSerializer, SalleSerializer, ClasseSerializer,
    TarifClasseSerializer, GroupeSerializer, MatiereSerializer, AffectationMatiereClasseSerializer,
)

ROLES_LECTURE_GENERALE = [
    Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_SCOLARITE,
    Role.RESPONSABLE_PEDAGOGIQUE, Role.COMPTABLE, Role.PROFESSEUR,
]
ROLES_ECRITURE_DIRECTION = [Role.ADMINISTRATEUR, Role.DIRECTEUR]


class AnneeScolaireViewSet(ViewSetGestion):
    queryset = AnneeScolaire.objects.all()
    serializer_class = AnneeScolaireSerializer
    roles_lecture = ROLES_LECTURE_GENERALE
    roles_ecriture = ROLES_ECRITURE_DIRECTION
    search_fields = ["libelle"]

    def get_queryset(self):
        qs = super().get_queryset()
        recherche = self.request.query_params.get("recherche")
        if recherche:
            qs = qs.filter(libelle__icontains=recherche)
        return qs

    @action(detail=True, methods=["post"])
    def activer(self, request, pk=None):
        annee = self.get_object()
        annee.active = True
        annee.save()
        return Response(self.get_serializer(annee).data)


class NiveauViewSet(ViewSetGestion):
    queryset = Niveau.objects.all()
    serializer_class = NiveauSerializer
    roles_lecture = ROLES_LECTURE_GENERALE
    roles_ecriture = ROLES_ECRITURE_DIRECTION
    search_fields = ["nom", "code"]

    def get_queryset(self):
        qs = super().get_queryset()
        recherche = self.request.query_params.get("recherche")
        if recherche:
            qs = qs.filter(nom__icontains=recherche)
        return qs


class SalleViewSet(ViewSetGestion):
    queryset = Salle.objects.all()
    serializer_class = SalleSerializer
    roles_lecture = ROLES_LECTURE_GENERALE
    roles_ecriture = ROLES_ECRITURE_DIRECTION
    search_fields = ["nom"]

    def get_queryset(self):
        qs = super().get_queryset()
        recherche = self.request.query_params.get("recherche")
        if recherche:
            qs = qs.filter(nom__icontains=recherche)
        return qs


class ClasseViewSet(ViewSetGestion):
    # `effectif_actif` evite une requete par classe pour calculer l'effectif.
    queryset = Classe.objects.select_related("niveau", "annee_scolaire", "salle_principale").annotate(
        effectif_actif=Count("inscriptions", filter=Q(inscriptions__statut="ACTIVE"))).order_by("niveau__ordre", "nom")
    serializer_class = ClasseSerializer
    roles_lecture = ROLES_LECTURE_GENERALE
    roles_ecriture = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_SCOLARITE]
    search_fields = ["nom"]
    alias_tri = {"effectif": "effectif_actif"}

    def get_queryset(self):
        qs = super().get_queryset()
        recherche = self.request.query_params.get("recherche")
        if recherche:
            qs = qs.filter(nom__icontains=recherche)
        annee = self.request.query_params.get("annee_scolaire")
        if annee:
            qs = qs.filter(annee_scolaire_id=annee)
        niveau = self.request.query_params.get("niveau")
        if niveau:
            qs = qs.filter(niveau_id=niveau)
        return qs


class TarifClasseViewSet(ViewSetGestion):
    queryset = TarifClasse.objects.select_related("classe", "classe__niveau", "classe__annee_scolaire").all()
    serializer_class = TarifClasseSerializer
    # Memes droits que les grilles de frais de l'app scolarite.
    roles_lecture = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_SCOLARITE, Role.COMPTABLE]
    roles_ecriture = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.COMPTABLE]
    search_fields = ["classe__nom"]

    def get_queryset(self):
        qs = super().get_queryset()
        recherche = self.request.query_params.get("recherche")
        if recherche:
            qs = qs.filter(classe__nom__icontains=recherche)
        annee = self.request.query_params.get("annee_scolaire")
        if annee:
            qs = qs.filter(classe__annee_scolaire_id=annee)
        return qs


class GroupeViewSet(ViewSetGestion):
    queryset = Groupe.objects.select_related("classe", "classe__niveau").all()
    serializer_class = GroupeSerializer
    roles_lecture = ROLES_LECTURE_GENERALE
    roles_ecriture = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_SCOLARITE]
    search_fields = ["nom"]

    def get_queryset(self):
        qs = super().get_queryset()
        classe = self.request.query_params.get("classe")
        if classe:
            qs = qs.filter(classe_id=classe)
        return qs


class MatiereViewSet(ViewSetGestion):
    queryset = Matiere.objects.all()
    serializer_class = MatiereSerializer
    roles_lecture = ROLES_LECTURE_GENERALE
    roles_ecriture = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE]
    search_fields = ["nom", "code"]

    def get_queryset(self):
        qs = super().get_queryset()
        recherche = self.request.query_params.get("recherche")
        if recherche:
            qs = qs.filter(nom__icontains=recherche)
        return qs


class AffectationMatiereClasseViewSet(ViewSetGestion):
    queryset = AffectationMatiereClasse.objects.select_related("matiere", "classe").all()
    serializer_class = AffectationMatiereClasseSerializer
    roles_lecture = ROLES_LECTURE_GENERALE
    roles_ecriture = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE]

    def get_queryset(self):
        qs = super().get_queryset()
        classe = self.request.query_params.get("classe")
        if classe:
            qs = qs.filter(classe_id=classe)
        matiere = self.request.query_params.get("matiere")
        if matiere:
            qs = qs.filter(matiere_id=matiere)
        return qs
