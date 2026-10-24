from datetime import date, datetime

from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.commun.audit import enregistrer_audit
from apps.commun.constantes import Role
from apps.commun.excel import reponse_xlsx
from apps.commun.exceptions import ErreurMetier
from apps.commun.pdf import reponse_pdf
from apps.commun.vues_base import ViewSetGestion
from apps.referentiels.models import AnneeScolaire
from . import exports, services
from .donnees import configuration_pour
from .models import (
    ConfigurationHoraires, DisponibiliteProfesseur, EmploiDuTemps, IndisponibiliteSalle, SeanceProgrammee,
    StatutEmploi, VersionEmploiDuTemps,
)
from .serializers import (
    ConfigurationHorairesSerializer, DisponibiliteProfesseurSerializer, EmploiDuTempsSerializer,
    IndisponibiliteSalleSerializer, SeanceProgrammeeSerializer,
)

ROLES_GESTION = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE]
ROLES_DIRECTION = [Role.ADMINISTRATEUR, Role.DIRECTEUR]
ROLES_CONSULTATION = ROLES_GESTION + [Role.RESPONSABLE_SCOLARITE, Role.PROFESSEUR]


class ConfigurationHorairesViewSet(ViewSetGestion):
    queryset = ConfigurationHoraires.objects.select_related("annee_scolaire").order_by("-annee_scolaire__date_debut")
    serializer_class = ConfigurationHorairesSerializer
    roles_lecture = ROLES_GESTION
    roles_ecriture = ROLES_DIRECTION

    @action(detail=False, methods=["get"], url_path="annee/(?P<id_annee>[0-9]+)")
    def pour_annee(self, request, id_annee=None):
        """Configuration de l'annee (creee avec ses valeurs par defaut si elle n'existe pas encore)."""
        try:
            annee = AnneeScolaire.objects.get(pk=id_annee)
        except AnneeScolaire.DoesNotExist:
            return Response({"detail": "Annee scolaire introuvable."}, status=404)
        return Response(self.get_serializer(configuration_pour(annee)).data)


class DisponibiliteProfesseurViewSet(ViewSetGestion):
    serializer_class = DisponibiliteProfesseurSerializer
    roles_lecture = ROLES_GESTION + [Role.PROFESSEUR]
    roles_ecriture = ROLES_GESTION + [Role.PROFESSEUR]

    def get_queryset(self):
        qs = DisponibiliteProfesseur.objects.select_related("professeur")
        utilisateur = self.request.user
        if utilisateur.role == Role.PROFESSEUR:
            return qs.filter(professeur_id=utilisateur.professeur_id or 0)  # uniquement les siennes
        if self.request.query_params.get("professeur"):
            qs = qs.filter(professeur_id=self.request.query_params["professeur"])
        return qs


class IndisponibiliteSalleViewSet(ViewSetGestion):
    queryset = IndisponibiliteSalle.objects.select_related("salle")
    serializer_class = IndisponibiliteSalleSerializer
    roles_lecture = ROLES_GESTION
    roles_ecriture = ROLES_GESTION


class EmploiDuTempsViewSet(ViewSetGestion):
    serializer_class = EmploiDuTempsSerializer
    roles_par_action = {
        "default": ROLES_GESTION,
        "list": ROLES_CONSULTATION, "retrieve": ROLES_CONSULTATION, "vue": ROLES_CONSULTATION,
        "pdf": ROLES_CONSULTATION, "excel": ROLES_CONSULTATION,
    }

    def get_queryset(self):
        qs = EmploiDuTemps.objects.select_related("annee_scolaire").annotate(nb_seances=Count("seances"))
        if self.request.user.role not in ROLES_GESTION:
            qs = qs.filter(statut=StatutEmploi.PUBLIE)       # personnel et professeurs : emploi publie uniquement
        params = self.request.query_params
        if params.get("annee_scolaire"):
            qs = qs.filter(annee_scolaire_id=params["annee_scolaire"])
        if params.get("statut"):
            qs = qs.filter(statut=params["statut"])
        return qs.order_by("-cree_le", "-id")

    def perform_create(self, serializer):
        emploi = serializer.save(cree_par=self.request.user)
        enregistrer_audit(self.request.user, "CREATION", "EmploiDuTemps", emploi.pk, nouvelle_valeur={"nom": emploi.nom})

    def perform_destroy(self, instance):
        services.exiger_brouillon(instance)   # un emploi publie ou archive est conserve
        enregistrer_audit(self.request.user, "SUPPRESSION", "EmploiDuTemps", instance.pk, ancienne_valeur={"nom": instance.nom})
        instance.delete()

    def _filtres(self, request):
        filtres = {c: request.query_params.get(c) for c in ("classe", "groupe", "professeur", "salle", "matiere")}
        if request.user.role == Role.PROFESSEUR:
            # Un professeur ne consulte que sa propre grille (impose cote serveur).
            filtres = {"professeur": request.user.professeur_id or 0}
        return {c: v for c, v in filtres.items() if v}

    @action(detail=False, methods=["post"])
    def generer(self, request):
        """Genere un brouillon par algorithme genetique."""
        try:
            annee = AnneeScolaire.objects.get(pk=request.data.get("annee_scolaire"))
        except (AnneeScolaire.DoesNotExist, ValueError, TypeError):
            raise ErreurMetier("Annee scolaire invalide.")
        graine = request.data.get("graine")
        emploi = services.generer_emploi(
            annee, request.user, (request.data.get("nom") or f"Emploi {annee.libelle} (genere)")[:120],
            graine=int(graine) if graine not in (None, "") else None,
            temps_max=request.data.get("temps_max", 20),
            population=int(request.data.get("population", 30)), generations=int(request.data.get("generations", 200)),
        )
        emploi = self.get_queryset().get(pk=emploi.pk)
        return Response(self.get_serializer(emploi).data, status=201)

    @action(detail=True, methods=["get"])
    def verifier(self, request, pk=None):
        """Rapport de conflits de l'emploi du temps (`publication=1` : exige aussi une salle par seance)."""
        emploi = self.get_object()
        conflits = services.verifier_emploi(emploi, publication=request.query_params.get("publication") in ("1", "true"))
        return Response({"valide": not conflits, "nb_conflits": len(conflits), "conflits": conflits})

    @action(detail=True, methods=["post"])
    def publier(self, request, pk=None):
        emploi = self.get_object()
        version = services.publier_emploi(emploi, request.user, request.data.get("commentaire", ""))
        return Response({"detail": f"Emploi du temps publie (version {version.numero}).", "version": version.numero})

    @action(detail=True, methods=["post"])
    def dupliquer(self, request, pk=None):
        copie = services.dupliquer_emploi(self.get_object(), request.user, request.data.get("nom"))
        return Response(self.get_serializer(self.get_queryset().get(pk=copie.pk)).data, status=201)

    @action(detail=True, methods=["get"])
    def vue(self, request, pk=None):
        return Response(services.vue_emploi(self.get_object(), self._filtres(request)))

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        emploi = self.get_object()
        toutes = request.query_params.get("toutes") if request.user.role != Role.PROFESSEUR else None
        return reponse_pdf(exports.pdf_emploi(emploi, self._filtres(request), toutes), f"emploi_du_temps_{emploi.pk}.pdf")

    @action(detail=True, methods=["get"])
    def excel(self, request, pk=None):
        emploi = self.get_object()
        toutes = request.query_params.get("toutes") if request.user.role != Role.PROFESSEUR else None
        return reponse_xlsx(exports.xlsx_emploi(emploi, self._filtres(request), toutes), f"emploi_du_temps_{emploi.pk}.xlsx")

    @action(detail=False, methods=["get"])
    def versions(self, request):
        """Historique des versions publiees d'une annee scolaire."""
        qs = VersionEmploiDuTemps.objects.select_related("emploi", "publie_par")
        if request.query_params.get("annee_scolaire"):
            qs = qs.filter(annee_scolaire_id=request.query_params["annee_scolaire"])
        return Response([{
            "numero": v.numero, "emploi": v.emploi_id, "emploi_nom": v.emploi.nom, "commentaire": v.commentaire,
            "publie_le": v.publie_le, "publie_par": str(v.publie_par) if v.publie_par else None,
            "nb_seances": len(v.contenu),
        } for v in qs])

    @action(detail=True, methods=["post"], url_path="generer-seances")
    def generer_seances(self, request, pk=None):
        """Cree les seances de presence a partir de l'emploi publie, entre deux dates."""
        try:
            du, au = date.fromisoformat(request.data.get("du", "")), date.fromisoformat(request.data.get("au", ""))
        except ValueError:
            raise ErreurMetier("Dates 'du' et 'au' obligatoires (AAAA-MM-JJ).")
        return Response(services.generer_seances_presence(self.get_object(), du, au, request.user))


class SeanceProgrammeeViewSet(ViewSetGestion):
    serializer_class = SeanceProgrammeeSerializer
    roles_lecture = ROLES_GESTION
    roles_ecriture = ROLES_GESTION

    def get_queryset(self):
        qs = SeanceProgrammee.objects.select_related("classe", "groupe", "matiere", "professeur", "salle")
        params = self.request.query_params
        for champ in ("emploi", "classe", "professeur", "salle", "matiere", "jour"):
            if params.get(champ):
                qs = qs.filter(**{champ: params[champ]})
        return qs

    @staticmethod
    def _decrire(s):
        return {"classe": s.classe.nom, "matiere": s.matiere.nom, "professeur": s.professeur.nom_complet,
                "salle": s.salle.nom if s.salle else None, "jour": s.jour, "debut": f"{s.heure_debut:%H:%M}", "fin": f"{s.heure_fin:%H:%M}"}

    def perform_create(self, serializer):
        seance = serializer.save()
        enregistrer_audit(self.request.user, "CREATION", "SeanceProgrammee", seance.pk, nouvelle_valeur=self._decrire(seance))

    def perform_update(self, serializer):
        avant = self._decrire(serializer.instance)
        seance = serializer.save()
        enregistrer_audit(self.request.user, "MODIFICATION", "SeanceProgrammee", seance.pk,
                          ancienne_valeur=avant, nouvelle_valeur=self._decrire(seance))

    def perform_destroy(self, instance):
        services.exiger_brouillon(instance.emploi)
        enregistrer_audit(self.request.user, "SUPPRESSION", "SeanceProgrammee", instance.pk, ancienne_valeur=self._decrire(instance))
        instance.delete()

    @action(detail=True, methods=["post"])
    def copier(self, request, pk=None):
        """Copie la seance vers un autre creneau : {jour, heure_debut, heure_fin?}. Les conflits sont verifies."""
        source = self.get_object()
        donnees = {
            "emploi": source.emploi_id, "classe": source.classe_id, "groupe": source.groupe_id, "matiere": source.matiere_id,
            "professeur": source.professeur_id, "salle": source.salle_id, "jour": request.data.get("jour", source.jour),
            "heure_debut": request.data.get("heure_debut"), "heure_fin": request.data.get("heure_fin"),
        }
        if not donnees["heure_fin"] and donnees["heure_debut"]:
            # Meme duree que la seance copiee.
            duree = datetime.combine(date.today(), source.heure_fin) - datetime.combine(date.today(), source.heure_debut)
            donnees["heure_fin"] = (datetime.strptime(donnees["heure_debut"][:5], "%H:%M") + duree).strftime("%H:%M")
        serializer = self.get_serializer(data=donnees)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)
