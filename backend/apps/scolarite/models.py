from django.db import models
from apps.commun.modeles import ModeleImmuable
from apps.referentiels.models import AnneeScolaire, Classe, Niveau
from apps.etudiants.models import Inscription


class ModePaiement:
    ESPECES = "ESPECES"
    VIREMENT = "VIREMENT"
    CHEQUE = "CHEQUE"
    MOBILE = "MOBILE"
    CHOIX = [
        (ESPECES, "Especes"),
        (VIREMENT, "Virement"),
        (CHEQUE, "Cheque"),
        (MOBILE, "Paiement mobile"),
    ]


class TypeFrais:
    INSCRIPTION = "INSCRIPTION"
    MENSUALITE = "MENSUALITE"
    AUTRE = "AUTRE"
    CHOIX = [
        (INSCRIPTION, "Frais d'inscription"),
        (MENSUALITE, "Mensualite"),
        (AUTRE, "Autre frais"),
    ]


class GrilleFrais(models.Model):
    """Barème des frais de scolarite, par niveau et par annee scolaire
    (inspire de la fiche papier : mensualite + frais d'inscription sur
    une periode de plusieurs mois)."""

    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, db_column="id_annee_scolaire", related_name="grilles_frais"
    )
    niveau = models.ForeignKey(
        Niveau, on_delete=models.CASCADE, db_column="id_niveau", related_name="grilles_frais"
    )
    montant_mensuel = models.DecimalField(max_digits=10, decimal_places=2, db_column="montant_mensuel")
    frais_inscription = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column="frais_inscription")
    nombre_mois = models.IntegerField(default=9, db_column="nombre_mois")
    actif = models.BooleanField(default=True, db_column="actif")   # False : plus utilise (masque des listes par defaut)

    class Meta:
        db_table = "grille_frais"
        unique_together = [("annee_scolaire", "niveau")]
        verbose_name = "Grille de frais"
        verbose_name_plural = "Grilles de frais"

    def __str__(self):
        return f"{self.niveau} - {self.annee_scolaire} ({self.montant_mensuel}/mois)"


class PaiementScolarite(ModeleImmuable):
    """Paiement immuable. Toute correction se fait par un paiement
    annulatif/rectificatif, jamais par modification ou suppression -
    meme logique que les mouvements de caisse des projets precedents."""

    reference = models.CharField(max_length=30, unique=True, db_column="reference")
    inscription = models.ForeignKey(
        Inscription, on_delete=models.PROTECT, db_column="id_inscription", related_name="paiements"
    )
    type_frais = models.CharField(max_length=20, choices=TypeFrais.CHOIX, db_column="type_frais")
    mois_concerne = models.DateField(
        null=True, blank=True,
        help_text="Premier jour du mois couvert par ce paiement (pour une mensualite).",
        db_column="mois_concerne",
    )
    montant = models.DecimalField(max_digits=10, decimal_places=2, db_column="montant")
    mode_paiement = models.CharField(max_length=20, choices=ModePaiement.CHOIX, default=ModePaiement.ESPECES, db_column="mode_paiement")
    date_paiement = models.DateField(db_column="date_paiement")
    enregistre_par = models.ForeignKey(
        "utilisateurs.Utilisateur", on_delete=models.PROTECT, db_column="id_utilisateur", related_name="paiements_scolarite"
    )
    observations = models.CharField(max_length=255, blank=True, default="", db_column="observations")
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")

    class Meta:
        db_table = "paiement_scolarite"
        ordering = ["-date_paiement", "-id"]
        verbose_name = "Paiement de scolarite"
        verbose_name_plural = "Paiements de scolarite"

    def __str__(self):
        return f"{self.reference} - {self.inscription.etudiant} - {self.montant}"
