from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.commun.constantes import Role
from apps.commun.excel import reponse_xlsx
from apps.commun.exceptions import ErreurMetier
from apps.commun.pdf import reponse_pdf
from apps.commun.permissions import PermissionParRole
from apps.commun.vues_base import ViewSetGestion, ViewSetLecture
from apps.professeurs.models import Professeur
from . import documents, services
from .models import (
    AjustementReleve, LigneReleve, ModePaiement, PaiementProfesseur, ReleveRemuneration, StatutReleve,
    TarifProfesseurMatiere,
)
from .serializers import (
    PaiementSerializer, ReleveDetailSerializer, ReleveSerializer, TarifProfesseurMatiereSerializer,
)

ROLES_REMUNERATION = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.COMPTABLE]
ROLES_DIRECTION = [Role.ADMINISTRATEUR, Role.DIRECTEUR]


def lire_mois(texte):
    """'2025-10' -> date(2025, 10, 1)."""
    try:
        annee, mois = str(texte).split("-")[:2]
        return date(int(annee), int(mois), 1)
    except (ValueError, TypeError):
        raise ErreurMetier("Mois invalide (format AAAA-MM).")


def lire_date(texte, nom):
    try:
        return date.fromisoformat(str(texte))
    except ValueError:
        raise ErreurMetier(f"Date '{nom}' invalide (AAAA-MM-JJ).")


class TarifProfesseurMatiereViewSet(ViewSetGestion):
    queryset = TarifProfesseurMatiere.objects.select_related("professeur", "matiere")
    serializer_class = TarifProfesseurMatiereSerializer
    roles_lecture = ROLES_REMUNERATION
    roles_ecriture = ROLES_REMUNERATION

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("professeur"):
            qs = qs.filter(professeur_id=self.request.query_params["professeur"])
        return qs


class ReleveViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PermissionParRole]
    roles_par_action = {
        "default": ROLES_REMUNERATION,
        "list": ROLES_REMUNERATION + [Role.PROFESSEUR], "retrieve": ROLES_REMUNERATION + [Role.PROFESSEUR],
        "pdf": ROLES_REMUNERATION + [Role.PROFESSEUR], "heures": ROLES_REMUNERATION + [Role.PROFESSEUR],
        "valider": ROLES_DIRECTION, "rouvrir": ROLES_DIRECTION, "corriger_heures": ROLES_DIRECTION,
    }

    def get_serializer_class(self):
        return ReleveDetailSerializer if self.action == "retrieve" else ReleveSerializer

    def _base(self):
        qs = ReleveRemuneration.objects.select_related("professeur", "annee_scolaire").prefetch_related(
            "lignes", "ajustements", "paiements", "corrections", "lignes__classe", "lignes__matiere")
        utilisateur = self.request.user
        if utilisateur.role == Role.PROFESSEUR:
            # Un professeur ne voit que ses propres releves, une fois valides.
            qs = qs.filter(professeur_id=utilisateur.professeur_id or 0, statut=StatutReleve.VALIDE)
        return qs

    def _filtres(self, qs):
        params = self.request.query_params
        if params.get("professeur"):
            qs = qs.filter(professeur_id=params["professeur"])
        if params.get("mois"):
            qs = qs.filter(mois=lire_mois(params["mois"]))
        if params.get("annee_scolaire"):
            qs = qs.filter(annee_scolaire_id=params["annee_scolaire"])
        if params.get("statut"):
            qs = qs.filter(statut=params["statut"])
        if params.get("matiere"):
            qs = qs.filter(lignes__matiere_id=params["matiere"]).distinct()
        return qs.order_by("-mois", "professeur__nom")

    def get_queryset(self):
        return self._filtres(self._base())

    def list(self, request, *args, **kwargs):
        releves = list(self.get_queryset())
        statut_paiement = request.query_params.get("statut_paiement")
        if statut_paiement:   # etat derive des paiements : filtre apres calcul
            releves = [r for r in releves if services.totaux(r)["statut_paiement"] == statut_paiement]
        page = self.paginate_queryset(releves)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    # ----------------------------------------------------------- generation

    @action(detail=False, methods=["post"])
    def generer(self, request):
        """{mois: 'AAAA-MM', professeur?} : cree/recalcule les releves BROUILLON."""
        mois = lire_mois(request.data.get("mois"))
        if request.data.get("professeur"):
            professeur = get_object_or_404(Professeur, pk=request.data["professeur"])
            releves = [services.generer_releve(professeur, mois, request.user)]
        else:
            releves = services.generer_releves_du_mois(mois, request.user)
        ids = [r.pk for r in releves]
        donnees = ReleveSerializer(self._base().filter(pk__in=ids), many=True, context=self.get_serializer_context()).data
        return Response({"nombre": len(ids), "releves": donnees}, status=201)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        releve = services.valider_releve(self.get_object(), request.user)
        return Response(ReleveDetailSerializer(self._base().get(pk=releve.pk), context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def rouvrir(self, request, pk=None):
        releve = self.get_object()
        services.rouvrir_releve(releve, request.user, request.data.get("motif"))
        return Response(ReleveDetailSerializer(self._base().get(pk=releve.pk), context=self.get_serializer_context()).data)

    # ------------------------------------------- ajustements, paiements, corrections

    def _detail(self, releve):
        return Response(ReleveDetailSerializer(self._base().get(pk=releve.pk), context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def ajustement(self, request, pk=None):
        """{type: PRIME|RETENUE, libelle, montant}"""
        releve = self.get_object()
        services.ajouter_ajustement(releve, request.data.get("type"), request.data.get("libelle"), request.data.get("montant"), request.user)
        return self._detail(releve)

    @action(detail=True, methods=["post"], url_path="supprimer-ajustement")
    def supprimer_ajustement(self, request, pk=None):
        releve = self.get_object()
        ajustement = get_object_or_404(AjustementReleve, pk=request.data.get("ajustement"), releve=releve)
        services.supprimer_ajustement(ajustement, request.user)
        return self._detail(releve)

    @action(detail=True, methods=["post"])
    def paiement(self, request, pk=None):
        """{montant, mode_paiement?, date_paiement?, observations?} : acompte, paiement partiel ou solde."""
        releve = self.get_object()
        mode = request.data.get("mode_paiement") or ModePaiement.ESPECES
        if mode not in dict(ModePaiement.CHOIX):
            raise ErreurMetier("Mode de paiement invalide.")
        jour = lire_date(request.data["date_paiement"], "date_paiement") if request.data.get("date_paiement") else date.today()
        services.enregistrer_paiement(releve, request.data.get("montant"), mode, jour, request.data.get("observations"), request.user)
        return self._detail(releve)

    @action(detail=True, methods=["post"], url_path="corriger-heures")
    def corriger_heures(self, request, pk=None):
        """{ligne, heures, motif} : correction d'heures sur un releve valide (motif obligatoire)."""
        releve = self.get_object()
        ligne = get_object_or_404(LigneReleve, pk=request.data.get("ligne"), releve=releve)
        services.corriger_heures(releve, ligne, request.data.get("heures"), request.data.get("motif"), request.user)
        return self._detail(releve)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        releve = self.get_object()
        return reponse_pdf(documents.pdf_fiche(releve), f"fiche_paiement_{releve.professeur.matricule}_{releve.mois:%Y-%m}.pdf")

    # ------------------------------------------------------- etat et heures

    @action(detail=False, methods=["get"])
    def etat(self, request):
        """Etat de paiement d'un mois ; `sans_releve` : professeurs ayant des heures mais pas encore de releve."""
        mois = lire_mois(request.query_params.get("mois"))
        releves = list(self._base().filter(mois=mois).order_by("professeur__nom"))
        avec = {r.professeur_id for r in releves}
        sans = [
            {"professeur": p.pk, "nom": p.nom_complet}
            for p in Professeur.objects.filter(statut="ACTIF").exclude(pk__in=avec)
            if services.seances_du_professeur(p, mois, services.dernier_du_mois(mois)).exists()
        ]
        serie = ReleveSerializer(releves, many=True, context=self.get_serializer_context()).data
        colonnes = ("heures", "brut", "primes", "retenues", "net", "paye", "solde")

        def somme(selection):
            return {c: str(sum((services.totaux(r)[c] for r in selection), services.ZERO)) for c in colonnes}

        # `total` inclut les brouillons (calcul courant) ; `total_valide` ne compte que les releves valides.
        return Response({
            "mois": mois.isoformat(), "releves": serie, "total": somme(releves),
            "total_valide": somme([r for r in releves if r.statut == StatutReleve.VALIDE]), "sans_releve": sans,
        })

    def _releves_du_mois(self, request):
        mois = lire_mois(request.query_params.get("mois"))
        qs = self._base().filter(mois=mois)
        if request.query_params.get("professeur"):
            qs = qs.filter(professeur_id=request.query_params["professeur"])
        return mois, [r for r in qs.order_by("professeur__nom")
                      if not request.query_params.get("statut_paiement")
                      or services.totaux(r)["statut_paiement"] == request.query_params["statut_paiement"]]

    @action(detail=False, methods=["get"], url_path="etat/excel")
    def etat_excel(self, request):
        mois, releves = self._releves_du_mois(request)
        return reponse_xlsx(documents.xlsx_etat(releves, mois), f"etat_paiement_{mois:%Y-%m}.xlsx")

    @action(detail=False, methods=["get"], url_path="etat/pdf")
    def etat_pdf(self, request):
        mois, releves = self._releves_du_mois(request)
        return reponse_pdf(documents.pdf_etat(releves, mois), f"etat_paiement_{mois:%Y-%m}.pdf")

    @action(detail=False, methods=["get"])
    def heures(self, request):
        """Heures effectuees par matiere et par classe : ?professeur=&du=&au= (verification avant releve)."""
        if request.user.role == Role.PROFESSEUR:
            professeur = get_object_or_404(Professeur, pk=request.user.professeur_id or 0)
        else:
            professeur = get_object_or_404(Professeur, pk=request.query_params.get("professeur") or 0)
        du, au = lire_date(request.query_params.get("du", ""), "du"), lire_date(request.query_params.get("au", ""), "au")
        return Response(services.heures_par_matiere_et_classe(professeur, du, au))


class PaiementProfesseurViewSet(ViewSetLecture):
    """Historique des paiements (immuables). L'annulation cree un paiement inverse."""

    serializer_class = PaiementSerializer
    permission_classes = [PermissionParRole]
    roles_par_action = {"default": ROLES_REMUNERATION, "annuler": ROLES_DIRECTION}

    def get_queryset(self):
        qs = PaiementProfesseur.objects.select_related("releve__professeur", "enregistre_par", "annulation_par")
        params = self.request.query_params
        if params.get("professeur"):
            qs = qs.filter(releve__professeur_id=params["professeur"])
        if params.get("releve"):
            qs = qs.filter(releve_id=params["releve"])
        if params.get("mois"):
            qs = qs.filter(releve__mois=lire_mois(params["mois"]))
        if params.get("du"):
            qs = qs.filter(date_paiement__gte=params["du"])
        if params.get("au"):
            qs = qs.filter(date_paiement__lte=params["au"])
        return qs.order_by("-date_paiement", "-id")

    @action(detail=True, methods=["post"])
    def annuler(self, request, pk=None):
        annulation = services.annuler_paiement(self.get_object(), request.data.get("motif"), request.user)
        return Response(self.get_serializer(annulation).data, status=201)
