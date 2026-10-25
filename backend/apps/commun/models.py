from django.db import models
from .modeles import ModeleImmuable


class Parametre(models.Model):
    cle = models.CharField(max_length=100, unique=True, db_column="cle")
    valeur = models.CharField(max_length=255, db_column="valeur")
    description = models.CharField(max_length=255, blank=True, default="", db_column="description")

    class Meta:
        db_table = "parametre"

    def __str__(self):
        return f"{self.cle}={self.valeur}"


class SequenceDocument(models.Model):
    prefixe = models.CharField(max_length=20, db_column="prefixe")
    annee = models.IntegerField(db_column="annee")
    dernier_numero = models.IntegerField(default=0, db_column="dernier_numero")

    class Meta:
        db_table = "sequence_document"
        unique_together = [("prefixe", "annee")]


class JournalAudit(ModeleImmuable):
    date_action = models.DateTimeField(auto_now_add=True, db_column="date_action")
    utilisateur = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, on_delete=models.SET_NULL,
        db_column="id_utilisateur", related_name="actions_audit",
    )
    action = models.CharField(max_length=100, db_column="action")
    modele = models.CharField(max_length=100, db_column="modele")
    reference_objet = models.CharField(max_length=100, db_column="reference_objet")
    ancienne_valeur = models.JSONField(null=True, blank=True, db_column="ancienne_valeur")
    nouvelle_valeur = models.JSONField(null=True, blank=True, db_column="nouvelle_valeur")

    class Meta:
        db_table = "journal_audit"
        ordering = ["-date_action"]
        indexes = [
            models.Index(fields=["date_action"], name="audit_date_idx"),
            models.Index(fields=["modele", "reference_objet"], name="audit_objet_idx"),
        ]
