from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.commun.audit import enregistrer_audit
from apps.commun.constantes import Role
from apps.commun.excel import reponse_xlsx
from apps.commun.exceptions import ErreurMetier
from apps.commun.pdf import reponse_pdf
from apps.commun.permissions import PermissionParRole
from apps.commun.vues_base import ViewSetGestion
from apps.professeurs.models import AffectationProfesseur
from apps.referentiels.models import Classe
from . import bulletins, excel, resultats as moteur, services
from .models import Evaluation
from .serializers import EvaluationSerializer

ROLES_SAISIE = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE, Role.PROFESSEUR]
ROLES_RESULTATS = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE, Role.RESPONSABLE_SCOLARITE]
ROLES_VALIDATION = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE]
ROLES_DIRECTION = [Role.ADMINISTRATEUR, Role.DIRECTEUR]
VRAI = ("1", "true", "oui", "vrai")


def _bool(valeur):
    return str(valeur).strip().lower() in VRAI


class EvaluationViewSet(ViewSetGestion):
    serializer_class = EvaluationSerializer
    roles_par_action = {"default": ROLES_SAISIE}

    def get_queryset(self):
        qs = Evaluation.objects.select_related("annee_scolaire", "classe", "matiere").annotate(nb_notes=Count("notes"))
        utilisateur = self.request.user
        if utilisateur.role == Role.PROFESSEUR:
            # Un professeur ne voit/saisit que les evaluations de ses affectations.
            affecte = AffectationProfesseur.objects.filter(
                professeur_id=utilisateur.professeur_id or 0, classe_id=OuterRef("classe_id"),
                matiere_id=OuterRef("matiere_id"), annee_scolaire_id=OuterRef("annee_scolaire_id"),
            )
            qs = qs.filter(Exists(affecte))
        params = self.request.query_params
        for champ in ("annee_scolaire", "classe", "matiere", "trimestre"):
            if params.get(champ):
                qs = qs.filter(**{champ: params[champ]})
        return qs.order_by("trimestre", "date", "id")

    def perform_create(self, serializer):
        evaluation = serializer.save(cree_par=self.request.user)
        enregistrer_audit(self.request.user, "CREATION", "Evaluation", evaluation.pk,
                          nouvelle_valeur={"libelle": evaluation.libelle, "classe": evaluation.classe.nom,
                                           "trimestre": evaluation.trimestre})

    def perform_update(self, serializer):
        avant = {c: str(getattr(serializer.instance, c)) for c in ("libelle", "trimestre", "bareme", "poids")}
        evaluation = serializer.save()
        apres = {c: str(getattr(evaluation, c)) for c in avant}
        if avant != apres:
            enregistrer_audit(self.request.user, "MODIFICATION", "Evaluation", evaluation.pk,
                              ancienne_valeur=avant, nouvelle_valeur=apres)

    def perform_destroy(self, instance):
        if instance.notes.exists():
            raise ErreurMetier("Cette evaluation contient des notes : elle ne peut pas etre supprimee.")
        if services.resultats_valides(instance.classe, instance.trimestre):
            raise ErreurMetier("Les resultats de ce trimestre sont valides : rouvrez-les d'abord.")
        enregistrer_audit(self.request.user, "SUPPRESSION", "Evaluation", instance.pk,
                          ancienne_valeur={"libelle": instance.libelle, "classe": instance.classe.nom})
        instance.delete()

    def _reponse(self, evaluation, **extra):
        evaluation = self.get_queryset().get(pk=evaluation.pk)
        return Response({
            "evaluation": EvaluationSerializer(evaluation, context=self.get_serializer_context()).data,
            "eleves": moteur.liste_notes(evaluation), **extra,
        })

    @action(detail=True, methods=["get", "post"])
    def notes(self, request, pk=None):
        """GET : liste de saisie ; POST {notes: [{etudiant, statut, valeur}], motif?} : enregistre."""
        evaluation = self.get_object()
        if request.method == "GET":
            return self._reponse(evaluation)
        lignes = request.data.get("notes")
        if not isinstance(lignes, list):
            raise ErreurMetier("Champ 'notes' (liste) attendu.")
        bilan = services.enregistrer_notes(evaluation, lignes, request.user, request.data.get("motif"))
        return self._reponse(evaluation, bilan=bilan)

    @action(detail=True, methods=["get"], url_path="modele-import")
    def modele_import(self, request, pk=None):
        evaluation = self.get_object()
        return reponse_xlsx(excel.xlsx_modele_notes(evaluation, moteur.liste_notes(evaluation)),
                            f"notes_{evaluation.classe.nom}_{evaluation.matiere.code}_T{evaluation.trimestre}.xlsx")

    @action(detail=True, methods=["get"])
    def exporter(self, request, pk=None):
        evaluation = self.get_object()
        return reponse_xlsx(excel.xlsx_notes(evaluation, moteur.liste_notes(evaluation)),
                            f"notes_{evaluation.classe.nom}_{evaluation.matiere.code}_T{evaluation.trimestre}.xlsx")

    @action(detail=True, methods=["post"], url_path="importer", parser_classes=[MultiPartParser])
    def importer(self, request, pk=None):
        """Sans `confirmer` : apercu (rien n'est ecrit). Avec `confirmer=true` : enregistre."""
        evaluation = self.get_object()
        remplacer, confirmer = _bool(request.data.get("remplacer", "")), _bool(request.data.get("confirmer", ""))
        motif = request.data.get("motif")
        resultat = excel.analyser_import(request.FILES.get("fichier"), evaluation)
        resultat["blocages"] = excel.blocages(resultat, remplacer, request.user, motif)
        if not confirmer:
            return Response(resultat)
        if resultat["blocages"]:
            return Response({"detail": "Import refuse : " + " ; ".join(resultat["blocages"]), **resultat}, status=400)
        bilan = excel.appliquer_import(evaluation, resultat, remplacer, request.user, motif)
        return Response({"detail": f"{bilan['creees'] + bilan['modifiees']} note(s) enregistree(s).", "bilan": bilan, **resultat}, status=201)


class ResultatsViewSet(viewsets.ViewSet):
    """Resultats, classements, validation et bulletins d'une classe.
    `periode` : 1, 2, 3 (trimestres) ou 0 (annee)."""

    permission_classes = [PermissionParRole]
    roles_par_action = {
        "default": ROLES_RESULTATS, "valider": ROLES_VALIDATION, "appreciations": ROLES_VALIDATION,
        "rouvrir": ROLES_DIRECTION,
    }

    @staticmethod
    def _classe_et_periode(donnees, periode_defaut=1):
        if not donnees.get("classe"):
            raise ErreurMetier("Parametre 'classe' obligatoire.")
        classe = get_object_or_404(Classe.objects.select_related("annee_scolaire"), pk=donnees["classe"])
        try:
            periode = int(donnees.get("periode", periode_defaut))
        except (TypeError, ValueError):
            raise ErreurMetier("Parametre 'periode' invalide (0 = annuel, 1, 2 ou 3).")
        if periode not in (0, 1, 2, 3):
            raise ErreurMetier("Parametre 'periode' invalide (0 = annuel, 1, 2 ou 3).")
        return classe, periode

    def list(self, request):
        classe, periode = self._classe_et_periode(request.query_params)
        return Response(moteur.jsonifier(moteur.resultats(classe, periode)))

    @action(detail=False, methods=["get"])
    def exporter(self, request):
        classe, periode = self._classe_et_periode(request.query_params)
        donnees = moteur.resultats(classe, periode)
        nom = f"classement_{classe.nom}_{'annuel' if periode == 0 else f'T{periode}'}.xlsx"
        return reponse_xlsx(excel.xlsx_classement(donnees), nom)

    @action(detail=False, methods=["get"], url_path="bulletins")
    def bulletins(self, request):
        """PDF des bulletins : toute la classe, ou `etudiants=1,2,3`."""
        classe, periode = self._classe_et_periode(request.query_params)
        ids = None
        if request.query_params.get("etudiants"):
            try:
                ids = {int(i) for i in request.query_params["etudiants"].split(",") if i.strip()}
            except ValueError:
                raise ErreurMetier("Parametre 'etudiants' invalide.")
        donnees = moteur.resultats(classe, periode)
        nom = f"bulletins_{classe.nom}_{'annuel' if periode == 0 else f'T{periode}'}.pdf"
        return reponse_pdf(bulletins.pdf_bulletins(donnees, ids), nom)

    @action(detail=False, methods=["post"])
    def valider(self, request):
        classe, periode = self._classe_et_periode(request.data)
        if periode == 0:
            raise ErreurMetier("Validez les trimestres un par un : l'annee est deduite des trimestres valides.")
        bilan = services.valider_resultats(classe, periode, request.user, _bool(request.data.get("accepter_incomplet", "")))
        return Response({"detail": "Resultats valides.", **bilan})

    @action(detail=False, methods=["post"])
    def rouvrir(self, request):
        classe, periode = self._classe_et_periode(request.data)
        if periode == 0:
            raise ErreurMetier("Rouvrez les trimestres un par un.")
        services.rouvrir_resultats(classe, periode, request.user, request.data.get("motif"))
        return Response({"detail": "Resultats rouverts."})

    @action(detail=False, methods=["post"])
    def appreciations(self, request):
        """{classe, periode, appreciations: [{etudiant, decision, observation_professeurs, observation_directeur}]}"""
        classe, periode = self._classe_et_periode(request.data)
        lignes = request.data.get("appreciations")
        if not isinstance(lignes, list):
            raise ErreurMetier("Champ 'appreciations' (liste) attendu.")
        services.enregistrer_appreciations(classe, periode, lignes, request.user)
        return Response(moteur.jsonifier(moteur.resultats(classe, periode)))
