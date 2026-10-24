import json
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

from apps.commun.audit import enregistrer_audit
from apps.commun.constantes import Role
from apps.commun.excel import reponse_xlsx
from apps.commun.exceptions import ErreurMetier
from apps.commun.parametres import lire_bool
from apps.commun.pdf import reponse_pdf
from apps.commun.permissions import PermissionParRole
from apps.commun.vues_base import ViewSetGestion, ViewSetLecture
from . import exports, imports, services, whatsapp
from .models import (
    NotificationWhatsApp, PresenceEtudiant, Seance, StatutNotification, StatutPresence,
)
from .serializers import (
    CoursSerializer, NotificationSerializer, PresenceEtudiantSerializer, SeanceSerializer,
)

ROLES_PRESENCES = [
    Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_SCOLARITE,
    Role.RESPONSABLE_PEDAGOGIQUE, Role.PROFESSEUR,
]
ROLES_DIRECTION = [Role.ADMINISTRATEUR, Role.DIRECTEUR]
ROLES_NOTIFICATIONS = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_SCOLARITE]
VRAI = ("1", "true", "oui", "vrai")


def _bool(valeur):
    return str(valeur).strip().lower() in VRAI


def _filtrer_dates(qs, params, champ):
    if params.get("du"):
        qs = qs.filter(**{f"{champ}__gte": params["du"]})
    if params.get("au"):
        qs = qs.filter(**{f"{champ}__lte": params["au"]})
    return qs


class SeanceViewSet(ViewSetGestion):
    serializer_class = SeanceSerializer
    roles_par_action = {"default": ROLES_PRESENCES, "rouvrir": ROLES_DIRECTION}
    CHAMPS_SUIVIS = ("statut_professeur", "professeur_remplacant", "heure_reelle_debut", "heure_reelle_fin", "heures_effectuees")

    def _filtrer(self, qs):
        utilisateur = self.request.user
        if utilisateur.role == Role.PROFESSEUR:
            # Un professeur ne voit que ses propres seances (cote serveur).
            fiche = utilisateur.professeur_id
            qs = qs.filter(Q(professeur_id=fiche) | Q(professeur_remplacant_id=fiche)) if fiche else qs.none()
        params = self.request.query_params
        for champ in ("annee_scolaire", "classe", "matiere", "date", "statut_professeur"):
            if params.get(champ):
                qs = qs.filter(**{champ: params[champ]})
        if params.get("professeur"):
            qs = qs.filter(Q(professeur_id=params["professeur"]) | Q(professeur_remplacant_id=params["professeur"]))
        if params.get("validee") is not None and params.get("validee") != "":
            qs = qs.filter(presences_validees=_bool(params["validee"]))
        return _filtrer_dates(qs, params, "date")

    def get_queryset(self):
        qs = self._filtrer(Seance.objects.select_related(
            "annee_scolaire", "classe", "matiere", "professeur", "professeur_remplacant"
        ))
        return qs.annotate(
            nb_presents=Count("presences", filter=Q(presences__statut=StatutPresence.PRESENT)),
            nb_absents=Count("presences", filter=Q(presences__statut=StatutPresence.ABSENT)),
            nb_retards=Count("presences", filter=Q(presences__statut=StatutPresence.RETARD)),
        ).order_by("-date", "-heure_debut", "-id")  # l'annotation supprime l'ordre par defaut du modele

    @action(detail=False, methods=["get"])
    def resume(self, request):
        """Heures enseignees sur la selection filtree, par professeur effectif
        (le remplacant recoit les heures d'une seance remplacee)."""
        total, par_professeur, par_statut = Decimal("0"), {}, {}
        seances = self._filtrer(Seance.objects.select_related("professeur", "professeur_remplacant"))
        for seance in seances:
            par_statut[seance.statut_professeur] = par_statut.get(seance.statut_professeur, 0) + 1
            effectif = seance.professeur_effectif
            if seance.heures_effectuees and effectif:
                ligne = par_professeur.setdefault(effectif.pk, {"professeur": effectif.pk, "nom": effectif.nom_complet, "heures": Decimal("0"), "seances": 0})
                ligne["heures"] += seance.heures_effectuees
                ligne["seances"] += 1
                total += seance.heures_effectuees
        return Response({
            "seances": sum(par_statut.values()), "par_statut": par_statut, "heures_effectuees": str(total),
            "par_professeur": sorted(
                ({**l, "heures": str(l["heures"])} for l in par_professeur.values()), key=lambda l: l["nom"]
            ),
        })

    # ------------------------------------------------------------ CRUD

    def perform_create(self, serializer):
        seance = serializer.save(cree_par=self.request.user)
        enregistrer_audit(self.request.user, "CREATION", "Seance", seance.pk,
                          nouvelle_valeur={"classe": seance.classe.nom, "date": str(seance.date)})

    def perform_update(self, serializer):
        avant = {c: str(getattr(serializer.instance, c)) for c in self.CHAMPS_SUIVIS}
        seance = serializer.save()
        apres = {c: str(getattr(seance, c)) for c in self.CHAMPS_SUIVIS}
        if avant != apres:
            enregistrer_audit(self.request.user, "MODIFICATION_PRESENCE_PROFESSEUR", "Seance", seance.pk,
                              ancienne_valeur=avant, nouvelle_valeur=apres)

    def perform_destroy(self, instance):
        if instance.presences_validees or instance.presences.exists():
            raise ErreurMetier("Cette seance contient des presences : elle ne peut pas etre supprimee.")
        if hasattr(instance, "ligne_releve"):
            raise ErreurMetier("Cette seance est comptee dans un releve de remuneration : elle ne peut pas etre supprimee.")
        enregistrer_audit(self.request.user, "SUPPRESSION", "Seance", instance.pk,
                          ancienne_valeur={"classe": instance.classe.nom, "date": str(instance.date)})
        instance.delete()

    # --------------------------------------------------------- helpers

    def _representer(self, seance):
        seance = self.get_queryset().get(pk=seance.pk)
        return SeanceSerializer(seance, context=self.get_serializer_context()).data

    def _reponse_liste(self, seance):
        return Response({"seance": self._representer(seance), "eleves": services.liste_appel(seance)})

    def _cours(self, donnees):
        serializer = CoursSerializer(data=donnees)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def _chercher(self, cours):
        return self.get_queryset().filter(
            classe=cours["classe"], matiere=cours["matiere"], date=cours["date"], heure_debut=cours["heure_debut"],
        ).first()

    def _creer(self, donnees):
        cles = ("annee_scolaire", "classe", "matiere", "date", "heure_debut", "heure_fin", "professeur")
        serializer = self.get_serializer(data={c: donnees.get(c) for c in cles if donnees.get(c) not in (None, "")})
        serializer.is_valid(raise_exception=True)
        return serializer.save(cree_par=self.request.user)

    # --------------------------------------------------- liste d'appel

    @action(detail=False, methods=["post"])
    def ouvrir(self, request):
        """Ouvre (ou cree) la seance d'un cours et retourne la liste des eleves de la classe."""
        cours = self._cours(request.data)
        seance = self._chercher(cours) or self._creer(request.data)
        return self._reponse_liste(seance)

    @action(detail=True, methods=["get"])
    def liste(self, request, pk=None):
        return self._reponse_liste(self.get_object())

    @action(detail=True, methods=["post"])
    def enregistrer(self, request, pk=None):
        lignes = request.data.get("presences")
        if not isinstance(lignes, list):
            raise ErreurMetier("Champ 'presences' (liste) attendu.")
        seance = self.get_object()
        services.enregistrer_presences(seance, lignes)
        return self._reponse_liste(seance)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        seance = self.get_object()
        notifications = services.valider_seance(seance, request.user)
        reponse = self._reponse_liste(seance)
        reponse.data["notifications"] = notifications
        return reponse

    @action(detail=True, methods=["post"])
    def rouvrir(self, request, pk=None):
        seance = self.get_object()
        services.rouvrir_seance(seance, request.user, request.data.get("motif"))
        return self._reponse_liste(seance)

    # ----------------------------------------------- impressions/exports

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        seance = self.get_object()
        return reponse_pdf(exports.pdf_liste(exports.contexte_seance(seance)), f"presence_{seance.classe.nom}_{seance.date}.pdf")

    @action(detail=True, methods=["get"])
    def excel(self, request, pk=None):
        seance = self.get_object()
        return reponse_xlsx(exports.xlsx_liste(exports.contexte_seance(seance)), f"presence_{seance.classe.nom}_{seance.date}.xlsx")

    @action(detail=False, methods=["get"], url_path="modele-vierge/pdf")
    def modele_vierge_pdf(self, request):
        return reponse_pdf(exports.pdf_liste(exports.contexte_vierge()), "liste_presence_vierge.pdf")

    @action(detail=False, methods=["get"], url_path="modele-vierge/excel")
    def modele_vierge_excel(self, request):
        return reponse_xlsx(exports.xlsx_liste(exports.contexte_vierge()), "liste_presence_vierge.xlsx")

    # ----------------------------------------------------- import Excel

    @action(detail=False, methods=["get"], url_path="modele-import")
    def modele_import(self, request):
        """Modele Excel du cours choisi, pre-rempli avec les eleves de la classe."""
        cours = self._cours(request.query_params)
        seance = self._chercher(cours)
        transitoire = seance or Seance(annee_scolaire=cours["annee_scolaire"], classe=cours["classe"], matiere=cours["matiere"])
        contexte = {
            "annee": cours["annee_scolaire"].libelle, "classe": cours["classe"].nom,
            "matiere_code": cours["matiere"].code, "date_iso": cours["date"].isoformat(),
            "heure_debut": cours["heure_debut"].strftime("%H:%M"), "heure_fin": cours["heure_fin"].strftime("%H:%M"),
            "lignes": services.liste_appel(transitoire),
        }
        return reponse_xlsx(exports.xlsx_modele_import(contexte), f"modele_presences_{cours['classe'].nom}_{cours['date']}.xlsx")

    @action(detail=False, methods=["post"], url_path="importer", parser_classes=[MultiPartParser])
    def importer(self, request):
        """Sans `confirmer` : apercu (rien n'est ecrit). Avec `confirmer=true` : enregistre
        (en brouillon, a valider ensuite) si aucune anomalie ne subsiste."""
        cours = self._cours(request.data)
        remplacer, confirmer = _bool(request.data.get("remplacer", "")), _bool(request.data.get("confirmer", ""))
        seance = self._chercher(cours)
        resultat = imports.analyser_import(request.FILES.get("fichier"), cours, seance)
        resultat["blocages"] = imports.blocages(resultat, remplacer)
        if not confirmer:
            return Response(resultat)
        if resultat["blocages"]:
            return Response({"detail": "Import refuse : " + " ; ".join(resultat["blocages"]), **resultat}, status=400)
        with transaction.atomic():
            seance = seance or self._creer(request.data)
            appliquees = imports.appliquer_import(seance, resultat, remplacer, request.user)
        return Response({
            "detail": f"{appliquees} presence(s) enregistree(s) en brouillon : validez la liste pour la confirmer.",
            "seance": seance.pk, "appliquees": appliquees, **resultat,
        }, status=201)


class HistoriquePresencesViewSet(ViewSetLecture):
    """Historique des presences/absences par date, classe, matiere, professeur, etudiant."""

    serializer_class = PresenceEtudiantSerializer
    permission_classes = [PermissionParRole]
    roles_lecture = ROLES_PRESENCES

    def get_queryset(self):
        qs = PresenceEtudiant.objects.select_related(
            "etudiant", "seance__classe", "seance__matiere", "seance__professeur", "notification"
        ).order_by("-seance__date", "-seance__heure_debut", "etudiant__nom")
        utilisateur = self.request.user
        if utilisateur.role == Role.PROFESSEUR:
            fiche = utilisateur.professeur_id
            qs = qs.filter(Q(seance__professeur_id=fiche) | Q(seance__professeur_remplacant_id=fiche)) if fiche else qs.none()
        params = self.request.query_params
        for parametre, champ in (
            ("etudiant", "etudiant_id"), ("classe", "seance__classe_id"), ("matiere", "seance__matiere_id"),
            ("annee_scolaire", "seance__annee_scolaire_id"), ("statut", "statut"), ("seance", "seance_id"),
        ):
            if params.get(parametre):
                qs = qs.filter(**{champ: params[parametre]})
        if params.get("professeur"):
            qs = qs.filter(seance__professeur_id=params["professeur"])
        if params.get("recherche"):
            qs = qs.filter(Q(etudiant__nom__icontains=params["recherche"]) | Q(etudiant__prenom__icontains=params["recherche"])
                           | Q(etudiant__matricule__icontains=params["recherche"]))
        return _filtrer_dates(qs, params, "seance__date")


class NotificationViewSet(ViewSetLecture):
    serializer_class = NotificationSerializer
    permission_classes = [PermissionParRole]
    roles_lecture = ROLES_NOTIFICATIONS
    roles_ecriture = ROLES_NOTIFICATIONS

    def get_queryset(self):
        qs = NotificationWhatsApp.objects.select_related(
            "presence__etudiant", "presence__seance__classe", "presence__seance__matiere"
        )
        params = self.request.query_params
        for parametre, champ in (
            ("statut", "statut"), ("canal", "canal"), ("seance", "presence__seance_id"),
            ("classe", "presence__seance__classe_id"), ("etudiant", "presence__etudiant_id"),
        ):
            if params.get(parametre):
                qs = qs.filter(**{champ: params[parametre]})
        if params.get("recherche"):
            qs = qs.filter(Q(presence__etudiant__nom__icontains=params["recherche"])
                           | Q(presence__etudiant__prenom__icontains=params["recherche"])
                           | Q(presence__etudiant__matricule__icontains=params["recherche"]))
        return _filtrer_dates(qs, params, "presence__seance__date")

    @action(detail=False, methods=["get"])
    def configuration(self, request):
        """Etat de la configuration (jamais les secrets)."""
        return Response({
            "api_configuree": whatsapp.api_configuree(),
            "whatsapp_actif": lire_bool("whatsapp_actif"),
            "retard_est_absence": lire_bool("retard_est_absence"),
            "modele_message": services.MESSAGE_ABSENCE,
            "nom_modele_api": settings.WHATSAPP_MODELE,
            "max_tentatives": settings.WHATSAPP_MAX_TENTATIVES,
        })

    @action(detail=False, methods=["post"])
    def traiter(self, request):
        """Envoie maintenant les notifications en attente (API configuree requise)."""
        return Response(whatsapp.traiter_file())

    @action(detail=True, methods=["post"])
    def reessayer(self, request, pk=None):
        notification = self.get_object()
        if notification.statut not in (StatutNotification.ECHEC, StatutNotification.EN_ATTENTE):
            raise ErreurMetier("Seules les notifications en echec ou en attente peuvent etre relancees.")
        self._remettre_en_file(notification)
        if whatsapp.api_configuree():
            whatsapp.envoyer_notification(notification)
            notification.refresh_from_db()
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="reessayer-echecs")
    def reessayer_echecs(self, request):
        remises = 0
        for notification in self.get_queryset().filter(statut=StatutNotification.ECHEC):
            try:
                self._remettre_en_file(notification)
                remises += 1
            except ErreurMetier:
                continue  # toujours sans numero valide : reste en echec
        bilan = whatsapp.traiter_file() if remises else {}
        return Response({"remises_en_file": remises, **bilan})

    @action(detail=True, methods=["post"], url_path="marquer-envoye")
    def marquer_envoye(self, request, pk=None):
        """Le personnel a envoye le message via le lien wa.me : on l'enregistre."""
        notification = self.get_object()
        if notification.statut not in (StatutNotification.EN_ATTENTE, StatutNotification.ECHEC):
            raise ErreurMetier("Cette notification est deja envoyee.")
        notification.statut = StatutNotification.ENVOYE
        notification.canal = "MANUEL"
        notification.envoye_le = timezone.now()
        notification.erreur = ""
        notification.save()
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"])
    def manuelle(self, request):
        """Cree a la main la notification d'une absence (une seule par absence)."""
        try:
            presence = PresenceEtudiant.objects.select_related(
                "etudiant", "seance__classe", "seance__matiere"
            ).get(pk=request.data.get("presence"))
        except (PresenceEtudiant.DoesNotExist, ValueError, TypeError):
            raise ErreurMetier("Presence introuvable.")
        if not lire_bool("whatsapp_actif"):
            raise ErreurMetier("Les notifications WhatsApp sont desactivees dans les parametres.")
        if not presence.seance.presences_validees:
            raise ErreurMetier("Validez d'abord les presences de la seance.")
        if presence.statut == StatutPresence.PRESENT:
            raise ErreurMetier("Aucune notification pour un etudiant present.")
        if hasattr(presence, "notification"):
            raise ErreurMetier("Une notification existe deja pour cette absence (aucun doublon).")
        notification = services.creer_notification(presence, manuelle=True)
        return Response(self.get_serializer(notification).data, status=201)

    @staticmethod
    def _remettre_en_file(notification):
        telephone, nom = services.destinataire(notification.presence.etudiant)
        if not telephone:
            raise ErreurMetier("Aucun numero de telephone valide : corrigez la fiche de l'etudiant.")
        notification.telephone, notification.destinataire_nom = telephone, nom
        notification.message = services.texte_message(notification.presence)
        notification.statut = StatutNotification.EN_ATTENTE
        notification.tentatives = 0
        notification.prochaine_tentative = timezone.now()
        notification.erreur = ""
        notification.save()


class WebhookWhatsAppView(APIView):
    """Recoit de Meta la verification du webhook (GET) et les confirmations
    de livraison (POST, signature HMAC obligatoire)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        jeton = settings.WHATSAPP_JETON_VERIFICATION
        if jeton and request.query_params.get("hub.mode") == "subscribe" \
                and request.query_params.get("hub.verify_token") == jeton:
            return HttpResponse(request.query_params.get("hub.challenge", ""), content_type="text/plain")
        return HttpResponse(status=403)

    def post(self, request):
        corps = request.body
        if not whatsapp.signature_valide(corps, request.headers.get("X-Hub-Signature-256")):
            return HttpResponse(status=403)
        try:
            donnees = json.loads(corps.decode("utf-8"))
        except ValueError:
            return HttpResponse(status=400)
        return Response({"statuts_modifies": whatsapp.appliquer_statuts(donnees)})
