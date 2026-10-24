from rest_framework.decorators import action
from rest_framework.response import Response

from apps.commun.constantes import Role
from apps.commun.vues_base import ViewSetGestion
from apps.commun.audit import enregistrer_audit
from apps.etudiants.models import Inscription
from apps.referentiels.models import TarifClasse
from .models import GrilleFrais, PaiementScolarite, TypeFrais
from .serializers import GrilleFraisSerializer, PaiementScolariteSerializer

ROLES_LECTURE = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.COMPTABLE, Role.RESPONSABLE_SCOLARITE]
ROLES_ECRITURE = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.COMPTABLE]


class GrilleFraisViewSet(ViewSetGestion):
    queryset = GrilleFrais.objects.select_related("niveau", "annee_scolaire").all()
    serializer_class = GrilleFraisSerializer
    roles_lecture = ROLES_LECTURE
    roles_ecriture = ROLES_ECRITURE

    def get_queryset(self):
        qs = super().get_queryset()
        annee = self.request.query_params.get("annee_scolaire")
        if annee:
            qs = qs.filter(annee_scolaire_id=annee)
        return qs


class PaiementScolariteViewSet(ViewSetGestion):
    """Paiement immuable : seules la creation et la lecture sont
    exposees (PUT/PATCH/DELETE desactives au niveau du routage, pas
    seulement caches cote frontend)."""

    queryset = PaiementScolarite.objects.select_related(
        "inscription", "inscription__etudiant", "inscription__classe", "enregistre_par"
    ).all()
    serializer_class = PaiementScolariteSerializer
    roles_lecture = ROLES_LECTURE
    roles_ecriture = ROLES_ECRITURE
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        inscription = self.request.query_params.get("inscription")
        if inscription:
            qs = qs.filter(inscription_id=inscription)
        etudiant = self.request.query_params.get("etudiant")
        if etudiant:
            qs = qs.filter(inscription__etudiant_id=etudiant)
        classe = self.request.query_params.get("classe")
        if classe:
            qs = qs.filter(inscription__classe_id=classe)
        return qs

    def perform_create(self, serializer):
        paiement = serializer.save()
        enregistrer_audit(
            self.request.user, "CREATION", "PaiementScolarite", paiement.reference,
            nouvelle_valeur={"montant": str(paiement.montant), "type": paiement.type_frais},
        )

    @action(detail=False, methods=["get"], url_path="situation/(?P<id_inscription>[0-9]+)")
    def situation(self, request, id_inscription=None):
        """Reconstitue, comme la fiche papier, la grille mensuelle
        payee/impayee d'un eleve pour son inscription en cours."""
        try:
            inscription = Inscription.objects.select_related(
                "etudiant", "classe", "classe__niveau", "annee_scolaire"
            ).get(pk=id_inscription)
        except Inscription.DoesNotExist:
            return Response({"detail": "Inscription introuvable."}, status=404)

        grille = GrilleFrais.objects.filter(
            annee_scolaire=inscription.annee_scolaire, niveau=inscription.classe.niveau
        ).first()
        # Le tarif propre a la classe prime sur la grille du niveau.
        tarif = TarifClasse.objects.filter(classe=inscription.classe).first()
        montant_mensuel = tarif.montant if tarif else (grille.montant_mensuel if grille else None)
        paiements = PaiementScolarite.objects.filter(inscription=inscription)
        inscription_payee = paiements.filter(type_frais=TypeFrais.INSCRIPTION).exists()
        mois_payes = {
            p.mois_concerne.strftime("%Y-%m")
            for p in paiements.filter(type_frais=TypeFrais.MENSUALITE) if p.mois_concerne
        }
        total_paye = sum((p.montant for p in paiements), start=0)

        return Response({
            "etudiant": inscription.etudiant.nom_complet,
            "matricule": inscription.etudiant.matricule,
            "classe": inscription.classe.nom,
            "annee_scolaire": inscription.annee_scolaire.libelle,
            "montant_mensuel": str(montant_mensuel) if montant_mensuel is not None else None,
            "frais_inscription": str(grille.frais_inscription) if grille else None,
            "nombre_mois": grille.nombre_mois if grille else None,
            "frais_inscription_paye": inscription_payee,
            "mois_payes": sorted(mois_payes),
            "total_paye": str(total_paye),
        })
