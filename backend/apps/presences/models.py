from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote

from django.db import models
from django.utils import timezone

from apps.etudiants.models import Etudiant
from apps.professeurs.models import Professeur
from apps.referentiels.models import AnneeScolaire, Classe, Matiere


class StatutPresence:
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    RETARD = "RETARD"
    CHOIX = [(PRESENT, "Present"), (ABSENT, "Absent"), (RETARD, "Retard")]
    VALEURS = (PRESENT, ABSENT, RETARD)


class StatutSeanceProfesseur:
    PLANIFIE = "PLANIFIE"
    EFFECTUE = "EFFECTUE"
    ABSENT = "ABSENT"
    RETARD = "RETARD"
    ANNULE = "ANNULE"
    REMPLACE = "REMPLACE"
    CHOIX = [
        (PLANIFIE, "Planifie"),
        (EFFECTUE, "Effectue"),
        (ABSENT, "Absent"),
        (RETARD, "Retard"),
        (ANNULE, "Annule"),
        (REMPLACE, "Remplace"),
    ]
    # Seuls ces statuts donnent lieu a des heures enseignees : une seance
    # annulee ou une absence n'est JAMAIS comptee comme heure effectuee.
    COMPTEES = (EFFECTUE, RETARD, REMPLACE)


class StatutNotification:
    EN_ATTENTE = "EN_ATTENTE"
    ENVOYE = "ENVOYE"   # accepte par l'API (ou marque envoye manuellement)
    LIVRE = "LIVRE"     # livraison confirmee par WhatsApp (webhook)
    ECHEC = "ECHEC"
    CHOIX = [
        (EN_ATTENTE, "En attente"),
        (ENVOYE, "Envoye"),
        (LIVRE, "Livre"),
        (ECHEC, "Echec"),
    ]


class CanalNotification:
    API = "API"
    MANUEL = "MANUEL"
    CHOIX = [(API, "API WhatsApp Business"), (MANUEL, "Lien wa.me (manuel)")]


def _minutes(heure):
    return heure.hour * 60 + heure.minute


class Seance(models.Model):
    """Un cours donne a une classe : support commun de la presence des
    etudiants (liste d'appel) et de la presence du professeur (heures
    effectuees). Les heures validees ici serviront de base a la
    remuneration (phase 7) : un cours n'existe qu'une fois."""

    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.PROTECT, db_column="id_annee_scolaire", related_name="seances"
    )
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, db_column="id_classe", related_name="seances")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT, db_column="id_matiere", related_name="seances")
    professeur = models.ForeignKey(
        Professeur, null=True, blank=True, on_delete=models.PROTECT,
        db_column="id_professeur", related_name="seances",
    )
    date = models.DateField(db_column="date")
    heure_debut = models.TimeField(db_column="heure_debut")
    heure_fin = models.TimeField(db_column="heure_fin")

    # Presences des etudiants : modifiables jusqu'a la validation.
    presences_validees = models.BooleanField(default=False, db_column="presences_validees")
    validee_le = models.DateTimeField(null=True, blank=True, db_column="validee_le")
    validee_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_validee_par", related_name="seances_validees",
    )

    # Presence du professeur.
    statut_professeur = models.CharField(
        max_length=20, choices=StatutSeanceProfesseur.CHOIX, default=StatutSeanceProfesseur.PLANIFIE,
        db_column="statut_professeur",
    )
    professeur_remplacant = models.ForeignKey(
        Professeur, null=True, blank=True, on_delete=models.PROTECT,
        db_column="id_professeur_remplacant", related_name="seances_remplacees",
    )
    heure_reelle_debut = models.TimeField(null=True, blank=True, db_column="heure_reelle_debut")
    heure_reelle_fin = models.TimeField(null=True, blank=True, db_column="heure_reelle_fin")
    heures_effectuees = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="heures_effectuees")
    observations_professeur = models.CharField(max_length=255, blank=True, default="", db_column="observations_professeur")

    cree_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_cree_par", related_name="seances_creees",
    )
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")

    class Meta:
        db_table = "seance"
        unique_together = [("classe", "matiere", "date", "heure_debut")]
        ordering = ["-date", "-heure_debut", "-id"]
        indexes = [
            models.Index(fields=["date"], name="seance_date_idx"),
            models.Index(fields=["professeur", "date"], name="seance_prof_date_idx"),
        ]
        verbose_name = "Seance"
        verbose_name_plural = "Seances"

    def __str__(self):
        return f"{self.matiere} - {self.classe.nom} - {self.date} {self.heure_debut:%H:%M}"

    @property
    def professeur_effectif(self):
        """Professeur a qui les heures sont creditees (le remplacant le cas echeant)."""
        if self.statut_professeur == StatutSeanceProfesseur.REMPLACE:
            return self.professeur_remplacant
        return self.professeur

    @property
    def duree_prevue_heures(self):
        return self._en_heures(max(0, _minutes(self.heure_fin) - _minutes(self.heure_debut)))

    @staticmethod
    def _en_heures(minutes):
        return (Decimal(minutes) / Decimal(60)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculer_heures(self):
        """Heures reellement enseignees, calculees cote serveur (jamais
        saisies par le client)."""
        if self.statut_professeur not in StatutSeanceProfesseur.COMPTEES:
            return Decimal("0.00")
        debut = self.heure_reelle_debut or self.heure_debut
        fin = self.heure_reelle_fin or self.heure_fin
        return self._en_heures(max(0, _minutes(fin) - _minutes(debut)))

    def save(self, *args, **kwargs):
        self.heures_effectuees = self.calculer_heures()
        champs = kwargs.get("update_fields")
        if champs is not None and "heures_effectuees" not in champs:
            kwargs["update_fields"] = list(champs) + ["heures_effectuees"]
        super().save(*args, **kwargs)


class PresenceEtudiant(models.Model):
    seance = models.ForeignKey(Seance, on_delete=models.CASCADE, db_column="id_seance", related_name="presences")
    etudiant = models.ForeignKey(Etudiant, on_delete=models.PROTECT, db_column="id_etudiant", related_name="presences")
    statut = models.CharField(max_length=10, choices=StatutPresence.CHOIX, db_column="statut")
    observation = models.CharField(max_length=255, blank=True, default="", db_column="observation")

    class Meta:
        db_table = "presence_etudiant"
        unique_together = [("seance", "etudiant")]
        ordering = ["etudiant__nom", "etudiant__prenom"]
        verbose_name = "Presence etudiant"
        verbose_name_plural = "Presences etudiants"

    def __str__(self):
        return f"{self.etudiant} - {self.seance} : {self.statut}"


class NotificationWhatsApp(models.Model):
    """Message WhatsApp a un parent pour une absence. Une seule
    notification par absence (OneToOne) : jamais de doublon, meme si les
    presences sont revalidees. L'enregistrement des presences ne depend
    pas de l'envoi : la notification est mise en file puis envoyee a part."""

    presence = models.OneToOneField(
        PresenceEtudiant, on_delete=models.PROTECT, db_column="id_presence", related_name="notification"
    )
    destinataire_nom = models.CharField(max_length=150, blank=True, default="", db_column="destinataire_nom")
    telephone = models.CharField(max_length=30, blank=True, default="", db_column="telephone")
    message = models.TextField(db_column="message")
    statut = models.CharField(
        max_length=12, choices=StatutNotification.CHOIX, default=StatutNotification.EN_ATTENTE, db_column="statut"
    )
    canal = models.CharField(max_length=10, choices=CanalNotification.CHOIX, blank=True, default="", db_column="canal")
    identifiant_message_api = models.CharField(max_length=150, blank=True, default="", db_column="identifiant_message_api")
    erreur = models.CharField(max_length=500, blank=True, default="", db_column="erreur")
    tentatives = models.IntegerField(default=0, db_column="tentatives")
    prochaine_tentative = models.DateTimeField(default=timezone.now, db_column="prochaine_tentative")
    envoye_le = models.DateTimeField(null=True, blank=True, db_column="envoye_le")
    declenchee_manuellement = models.BooleanField(default=False, db_column="declenchee_manuellement")
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")

    class Meta:
        db_table = "notification_whatsapp"
        ordering = ["-cree_le", "-id"]
        indexes = [models.Index(fields=["statut", "prochaine_tentative"], name="notif_file_idx")]   # file d'envoi
        verbose_name = "Notification WhatsApp"
        verbose_name_plural = "Notifications WhatsApp"

    def __str__(self):
        return f"{self.presence} -> {self.telephone or '?'} ({self.statut})"

    @property
    def lien_wa_me(self):
        """Lien pre-rempli pour un envoi manuel par le personnel."""
        if not self.telephone:
            return ""
        return f"https://wa.me/{self.telephone}?text={quote(self.message)}"
