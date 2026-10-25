from django.db.models import Q
from rest_framework import serializers

from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from apps.etudiants.models import Inscription
from apps.professeurs.models import AffectationProfesseur, Professeur
from apps.referentiels.models import AnneeScolaire, Classe, Matiere
from .models import NotificationWhatsApp, PresenceEtudiant, Seance, StatutSeanceProfesseur

# Seule l'administration (pas le professeur lui-meme) valide sa propre presence.
ROLES_GESTION_PROFESSEUR = [Role.ADMINISTRATEUR, Role.DIRECTEUR, Role.RESPONSABLE_PEDAGOGIQUE]
CHAMPS_PROFESSEUR = (
    "statut_professeur", "professeur_remplacant", "heure_reelle_debut", "heure_reelle_fin",
    "observations_professeur",
)
CHAMPS_COURS = ("annee_scolaire", "classe", "matiere", "date", "heure_debut", "heure_fin")
# Une fois la seance comptee dans un releve de remuneration valide, ces champs sont figes.
CHAMPS_REMUNERATION = CHAMPS_PROFESSEUR + ("professeur", "date", "heure_debut", "heure_fin")


class CoursSerializer(serializers.Serializer):
    """Identifie un cours (utilise par l'ouverture d'une liste et l'import Excel)."""

    annee_scolaire = serializers.PrimaryKeyRelatedField(queryset=AnneeScolaire.objects.all())
    classe = serializers.PrimaryKeyRelatedField(queryset=Classe.objects.all())
    matiere = serializers.PrimaryKeyRelatedField(queryset=Matiere.objects.all())
    date = serializers.DateField()
    heure_debut = serializers.TimeField()
    heure_fin = serializers.TimeField()
    professeur = serializers.PrimaryKeyRelatedField(queryset=Professeur.objects.all(), required=False, allow_null=True)

    def validate(self, donnees):
        if donnees["heure_fin"] <= donnees["heure_debut"]:
            raise ErreurMetier("L'heure de fin doit etre posterieure a l'heure de debut.")
        if donnees["classe"].annee_scolaire_id != donnees["annee_scolaire"].id:
            raise ErreurMetier("La classe choisie n'appartient pas a cette annee scolaire.")
        return donnees


class SeanceSerializer(serializers.ModelSerializer):
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    matiere_nom = serializers.CharField(source="matiere.nom_affiche", read_only=True)
    professeur_nom = serializers.CharField(source="professeur.nom_complet", read_only=True, default=None)
    remplacant_nom = serializers.CharField(source="professeur_remplacant.nom_complet", read_only=True, default=None)
    nb_presents = serializers.IntegerField(read_only=True, default=0)
    nb_absents = serializers.IntegerField(read_only=True, default=0)
    nb_retards = serializers.IntegerField(read_only=True, default=0)
    nb_eleves = serializers.SerializerMethodField()

    class Meta:
        model = Seance
        fields = "__all__"
        read_only_fields = ["presences_validees", "validee_le", "validee_par", "heures_effectuees", "cree_par", "cree_le"]

    def get_nb_eleves(self, obj):
        # Annotation de la vue (une seule requete pour toute la liste) ; requete directe sinon.
        if hasattr(obj, "effectif_classe"):
            return obj.effectif_classe
        return Inscription.objects.filter(
            classe_id=obj.classe_id, annee_scolaire_id=obj.annee_scolaire_id, statut="ACTIVE"
        ).count()

    def validate(self, donnees):
        instance = self.instance
        utilisateur = self.context["request"].user

        def val(nom):
            return donnees.get(nom, getattr(instance, nom, None))

        annee, classe, jour = val("annee_scolaire"), val("classe"), val("date")
        debut, fin = val("heure_debut"), val("heure_fin")
        if fin <= debut:
            raise ErreurMetier("L'heure de fin doit etre posterieure a l'heure de debut.")
        if classe.annee_scolaire_id != annee.id:
            raise ErreurMetier("La classe choisie n'appartient pas a cette annee scolaire.")
        if not (annee.date_debut <= jour <= annee.date_fin):
            raise ErreurMetier(
                f"La date doit etre comprise dans l'annee scolaire ({annee.date_debut:%d/%m/%Y} - {annee.date_fin:%d/%m/%Y})."
            )

        if instance and instance.presences_validees:
            for champ in CHAMPS_COURS:
                if champ in donnees and donnees[champ] != getattr(instance, champ):
                    raise ErreurMetier("Seance validee : le cours ne peut plus etre modifie (rouvrez-la d'abord).")

        ligne_releve = getattr(instance, "ligne_releve", None) if instance else None
        if ligne_releve is not None and ligne_releve.releve.statut == "VALIDE":
            for champ in CHAMPS_REMUNERATION:
                if champ in donnees and donnees[champ] != getattr(instance, champ):
                    raise ErreurMetier(
                        "Cette seance est comptee dans un releve de remuneration valide : corrigez les heures depuis le "
                        "releve (correction justifiee et tracee)."
                    )

        if utilisateur.role == Role.PROFESSEUR:
            fiche = utilisateur.professeur
            if fiche is None:
                raise ErreurMetier("Votre compte n'est relie a aucune fiche professeur.")
            if not AffectationProfesseur.objects.filter(
                professeur=fiche, matiere=val("matiere"), classe=classe, annee_scolaire=annee
            ).exists():
                raise ErreurMetier("Vous n'etes pas affecte a cette matiere pour cette classe.")
            donnees["professeur"] = fiche

        if utilisateur.role not in ROLES_GESTION_PROFESSEUR:
            for champ in CHAMPS_PROFESSEUR:
                if champ not in donnees:
                    continue
                reference = getattr(instance, champ) if instance else Seance._meta.get_field(champ).get_default()
                if donnees[champ] != reference:
                    raise ErreurMetier(
                        "La presence du professeur est geree par l'administration "
                        "(administrateur, directeur, responsable pedagogique)."
                    )

        statut = val("statut_professeur")
        professeur, remplacant = val("professeur"), val("professeur_remplacant")
        if statut == StatutSeanceProfesseur.REMPLACE:
            if remplacant is None:
                raise ErreurMetier("Un remplacant est obligatoire pour une seance remplacee.")
            if professeur and remplacant.pk == professeur.pk:
                raise ErreurMetier("Le remplacant doit etre different du professeur prevu.")
        elif remplacant is not None:
            raise ErreurMetier("Un remplacant n'est possible que pour le statut 'Remplace'.")
        reel_debut, reel_fin = val("heure_reelle_debut"), val("heure_reelle_fin")
        if statut == StatutSeanceProfesseur.RETARD and reel_debut is None:
            raise ErreurMetier("L'heure reelle de debut est obligatoire pour un professeur en retard.")
        if reel_debut and reel_fin and reel_fin <= reel_debut:
            raise ErreurMetier("L'heure reelle de fin doit etre posterieure a l'heure reelle de debut.")

        if statut != StatutSeanceProfesseur.ANNULE:
            chevauchantes = Seance.objects.filter(
                date=jour, heure_debut__lt=fin, heure_fin__gt=debut,
            ).exclude(statut_professeur=StatutSeanceProfesseur.ANNULE)
            if instance:
                chevauchantes = chevauchantes.exclude(pk=instance.pk)
            if chevauchantes.filter(classe=classe).exists():
                raise ErreurMetier(f"La classe {classe.nom} a deja un cours sur ce creneau.")
            for intervenant in (professeur, remplacant):
                if intervenant and chevauchantes.filter(
                    Q(professeur=intervenant) | Q(professeur_remplacant=intervenant)
                ).exists():
                    raise ErreurMetier(f"{intervenant.nom_complet} a deja un cours sur ce creneau.")
        return donnees


class PresenceEtudiantSerializer(serializers.ModelSerializer):
    etudiant_nom = serializers.CharField(source="etudiant.nom_complet", read_only=True)
    etudiant_matricule = serializers.CharField(source="etudiant.matricule", read_only=True)
    date = serializers.DateField(source="seance.date", read_only=True)
    heure_debut = serializers.TimeField(source="seance.heure_debut", read_only=True)
    heure_fin = serializers.TimeField(source="seance.heure_fin", read_only=True)
    classe_nom = serializers.CharField(source="seance.classe.nom", read_only=True)
    matiere_nom = serializers.CharField(source="seance.matiere.nom_affiche", read_only=True)
    professeur_nom = serializers.CharField(source="seance.professeur.nom_complet", read_only=True, default=None)
    seance_validee = serializers.BooleanField(source="seance.presences_validees", read_only=True)
    notification_statut = serializers.SerializerMethodField()

    class Meta:
        model = PresenceEtudiant
        fields = "__all__"

    def get_notification_statut(self, obj):
        notification = getattr(obj, "notification", None)
        return notification.statut if notification else None


class NotificationSerializer(serializers.ModelSerializer):
    seance = serializers.IntegerField(source="presence.seance_id", read_only=True)
    etudiant_nom = serializers.CharField(source="presence.etudiant.nom_complet", read_only=True)
    etudiant_matricule = serializers.CharField(source="presence.etudiant.matricule", read_only=True)
    classe_nom = serializers.CharField(source="presence.seance.classe.nom", read_only=True)
    matiere_nom = serializers.CharField(source="presence.seance.matiere.nom_affiche", read_only=True)
    date = serializers.DateField(source="presence.seance.date", read_only=True)
    heure_debut = serializers.TimeField(source="presence.seance.heure_debut", read_only=True)
    heure_fin = serializers.TimeField(source="presence.seance.heure_fin", read_only=True)
    lien_wa_me = serializers.CharField(read_only=True)

    class Meta:
        model = NotificationWhatsApp
        fields = "__all__"
