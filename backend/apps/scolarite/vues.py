from datetime import date
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from apps.commun.pdf import reponse_pdf
from apps.commun.permissions import PermissionParRole
from apps.commun.vues_base import ViewSetGestion
from apps.commun.audit import enregistrer_audit
from apps.etudiants.models import Inscription
from apps.referentiels.models import TarifClasse
from . import documents, services
from .models import EcheanceScolarite, GrilleFrais, ModePaiement, PaiementScolarite, TypeFrais
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
        # Mensualite propre a l'eleve (saisie a l'inscription) > tarif de la classe > grille du niveau.
        montant_mensuel = inscription.montant_mensuel or (tarif.montant if tarif else (grille.montant_mensuel if grille else None))
        paiements = PaiementScolarite.objects.filter(inscription=inscription)
        inscription_payee = paiements.filter(type_frais=TypeFrais.INSCRIPTION).exists()
        mois_payes = {mois.strftime("%Y-%m") for mois in services.mois_payes(inscription)}   # paiements annules deduits
        total_paye = sum((p.montant for p in paiements), start=0)

        return Response({
            "etudiant": inscription.etudiant.nom_complet,
            "matricule": inscription.etudiant.matricule,
            "numero_inscription": inscription.numero_inscription,
            "classe": inscription.classe.nom,
            "annee_scolaire": inscription.annee_scolaire.libelle,
            "montant_mensuel": str(montant_mensuel) if montant_mensuel is not None else None,
            "frais_inscription": str(grille.frais_inscription) if grille else None,
            "nombre_mois": len(services.mois_de_la_fiche(inscription)),
            "frais_inscription_paye": inscription_payee,
            "mois_payes": sorted(mois_payes),
            "total_paye": str(total_paye),
        })


class FicheScolariteViewSet(viewsets.GenericViewSet):
    """Fiche de paiement d'un eleve (un mois a payer par echeance), identifiee par le numero de son inscription.

    L'etat de chaque mois se deduit du registre des paiements : « payer » et « annuler » y ajoutent un mouvement."""

    permission_classes = [PermissionParRole]
    roles_par_action = {
        "default": ROLES_LECTURE, "generer": ROLES_ECRITURE, "payer": ROLES_ECRITURE, "annuler": ROLES_ECRITURE,
    }
    queryset = Inscription.objects.select_related("etudiant", "classe", "classe__niveau", "annee_scolaire")

    def _fiche(self, inscription):
        return Response(services.fiche_en_json(services.construire_fiche(inscription)))

    def _echeance(self, inscription, valeur):
        try:
            numero = int(valeur)
        except (TypeError, ValueError):
            raise ErreurMetier("Mois de la fiche invalide.")
        return get_object_or_404(EcheanceScolarite, pk=numero, inscription=inscription)

    def retrieve(self, request, pk=None):
        return self._fiche(self.get_object())

    @action(detail=True, methods=["post"])
    def generer(self, request, pk=None):
        """{montant_mensuel?} : cree les mois manquants de la fiche (inscription anterieure a la fiche, tarif defini apres coup)."""
        inscription = self.get_object()
        brut = request.data.get("montant_mensuel")
        montant = None
        if brut not in (None, ""):
            try:
                montant = Decimal(str(brut)).quantize(Decimal("0.01"))
            except InvalidOperation:
                raise ErreurMetier("Montant invalide.")
            if montant <= 0:
                raise ErreurMetier("La mensualite doit etre strictement positive.")
        if montant is None and inscription.montant_mensuel is None and services.montant_mensuel_defaut(inscription.classe) is None:
            raise ErreurMetier("Aucun tarif n'est defini pour cette classe : saisissez la mensualite.")
        services.generer_echeances(inscription, montant)
        return self._fiche(inscription)

    @action(detail=True, methods=["post"])
    def payer(self, request, pk=None):
        """{echeance, date_paiement?, mode_paiement?, observations?} : marque le mois comme paye."""
        inscription = self.get_object()
        mode = request.data.get("mode_paiement") or ModePaiement.ESPECES
        if mode not in dict(ModePaiement.CHOIX):
            raise ErreurMetier("Mode de paiement invalide.")
        try:
            jour = date.fromisoformat(str(request.data["date_paiement"])) if request.data.get("date_paiement") else date.today()
        except ValueError:
            raise ErreurMetier("Date de paiement invalide (AAAA-MM-JJ).")
        services.payer_echeance(
            self._echeance(inscription, request.data.get("echeance")), request.user, jour, mode, request.data.get("observations"),
        )
        return self._fiche(inscription)

    @action(detail=True, methods=["post"])
    def annuler(self, request, pk=None):
        """{echeance, motif?} : remet le mois en « non paye » (mouvement inverse conserve au registre)."""
        inscription = self.get_object()
        services.annuler_paiement_echeance(
            self._echeance(inscription, request.data.get("echeance")), request.user, str(request.data.get("motif") or "").strip(),
        )
        return self._fiche(inscription)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        """Fiche de paiement de l'annee : tous les mois avec leur etat."""
        inscription = self.get_object()
        fiche = services.construire_fiche(inscription)
        if not fiche["lignes"]:
            raise ErreurMetier("Aucune fiche de paiement n'a ete generee pour cette inscription.")
        return reponse_pdf(documents.pdf_fiche(fiche), f"fiche_scolarite_{inscription.etudiant.matricule}.pdf")

    @action(detail=True, methods=["get"])
    def recu(self, request, pk=None):
        """?echeance=<id> : recu du mois paye."""
        inscription = self.get_object()
        echeance = self._echeance(inscription, request.query_params.get("echeance"))
        fiche = services.construire_fiche(inscription)
        ligne = next(l for l in fiche["lignes"] if l["id"] == echeance.id)
        if ligne["statut"] == services.EtatEcheance.NON_PAYE:
            raise ErreurMetier("Ce mois n'est pas paye : aucun recu a imprimer.")
        return reponse_pdf(documents.pdf_recu(fiche, ligne), f"recu_{inscription.etudiant.matricule}_{echeance.mois:%Y-%m}.pdf")
