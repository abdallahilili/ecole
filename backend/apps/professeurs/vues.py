from apps.commun.constantes import Role
from apps.commun.vues_base import ViewSetGestion
from .models import Professeur, AffectationProfesseur
from .serializers import ProfesseurSerializer, AffectationProfesseurSerializer

ROLES_LECTURE = [
    Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE, Role.COMPTABLE, Role.PROFESSEUR,
]
ROLES_ECRITURE = [Role.ADMINISTRATEUR, Role.DIRECTEUR]


class ProfesseurViewSet(ViewSetGestion):
    queryset = Professeur.objects.all()
    serializer_class = ProfesseurSerializer
    roles_lecture = ROLES_LECTURE
    roles_ecriture = ROLES_ECRITURE
    search_fields = ["matricule", "nom", "prenom", "specialite"]
    alias_tri = {"nom_complet": ("nom", "prenom")}

    def get_queryset(self):
        qs = super().get_queryset()
        statut = self.request.query_params.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        return qs


class AffectationProfesseurViewSet(ViewSetGestion):
    queryset = AffectationProfesseur.objects.select_related(
        "professeur", "matiere", "classe", "groupe", "annee_scolaire"
    ).all()
    serializer_class = AffectationProfesseurSerializer
    roles_lecture = ROLES_LECTURE
    roles_ecriture = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE]

    def get_queryset(self):
        qs = super().get_queryset()
        professeur = self.request.query_params.get("professeur")
        if professeur:
            qs = qs.filter(professeur_id=professeur)
        classe = self.request.query_params.get("classe")
        if classe:
            qs = qs.filter(classe_id=classe)
        annee = self.request.query_params.get("annee_scolaire")
        if annee:
            qs = qs.filter(annee_scolaire_id=annee)
        return qs
