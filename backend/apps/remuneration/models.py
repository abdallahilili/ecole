from decimal import Decimal

from django.db import models

from apps.commun.modeles import ModeleImmuable
from apps.presences.models import Seance
from apps.professeurs.models import Professeur
from apps.referentiels.models import AnneeScolaire, Classe, Matiere

ZERO = Decimal("0.00")


class TarifProfesseurMatiere(models.Model):
    """Tarif horaire propre a une matiere pour un professeur (prime sur le
    tarif horaire general de sa fiche)."""

    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE, db_column="id_professeur", related_name="tarifs_matiere")
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, db_column="id_matiere", related_name="tarifs_professeur")
    tarif_horaire = models.DecimalField(max_digits=10, decimal_places=2, db_column="tarif_horaire")

    class Meta:
        db_table = "tarif_professeur_matiere"
        unique_together = [("professeur", "matiere")]
        ordering = ["professeur__nom", "matiere__nom"]
        verbose_name = "Tarif professeur par matiere"
        verbose_name_plural = "Tarifs professeur par matiere"


class StatutReleve:
    BROUILLON = "BROUILLON"
    VALIDE = "VALIDE"
    CHOIX = [(BROUILLON, "Brouillon"), (VALIDE, "Valide")]


class StatutPaiement:
    NON_PAYE = "NON_PAYE"
    PARTIEL = "PARTIEL"
    PAYE = "PAYE"
    CHOIX = [(NON_PAYE, "Non paye"), (PARTIEL, "Paye partiellement"), (PAYE, "Paye")]


class ReleveRemuneration(models.Model):
    """Etat de paiement mensuel d'un professeur : heures reellement enseignees
    (seances effectuees) x tarif applicable, plus primes, moins retenues.
    Brouillon : recalculable. Valide : montants figes (instantane), seules
    des corrections justifiees et tracees sont possibles."""

    professeur = models.ForeignKey(Professeur, on_delete=models.PROTECT, db_column="id_professeur", related_name="releves")
    annee_scolaire = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, db_column="id_annee_scolaire", related_name="releves_remuneration")
    mois = models.DateField(db_column="mois")  # premier jour du mois
    statut = models.CharField(max_length=10, choices=StatutReleve.CHOIX, default=StatutReleve.BROUILLON, db_column="statut")
    # Instantane fige a la validation (a l'etat brouillon, ces champs ne font pas foi : voir calculs.totaux).
    heures_total = models.DecimalField(max_digits=8, decimal_places=2, default=0, db_column="heures_total")
    montant_brut = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column="montant_brut")
    total_primes = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column="total_primes")
    total_retenues = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column="total_retenues")
    montant_net = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column="montant_net")
    mode_remuneration = models.CharField(max_length=10, blank=True, default="", db_column="mode_remuneration")
    observations = models.CharField(max_length=255, blank=True, default="", db_column="observations")
    valide_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_valide_par", related_name="releves_valides",
    )
    valide_le = models.DateTimeField(null=True, blank=True, db_column="valide_le")
    cree_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_cree_par", related_name="releves_crees",
    )
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")

    class Meta:
        db_table = "releve_remuneration"
        unique_together = [("professeur", "mois")]
        ordering = ["-mois", "professeur__nom"]
        verbose_name = "Releve de remuneration"
        verbose_name_plural = "Releves de remuneration"

    def __str__(self):
        return f"{self.professeur} - {self.mois:%m/%Y}"


class LigneReleve(models.Model):
    """Une seance enseignee comptee dans un releve. `seance` est UNIQUE : un
    cours ne peut jamais etre comptabilise deux fois (dans aucun releve)."""

    releve = models.ForeignKey(ReleveRemuneration, on_delete=models.CASCADE, db_column="id_releve", related_name="lignes")
    seance = models.OneToOneField(Seance, on_delete=models.PROTECT, db_column="id_seance", related_name="ligne_releve")
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, db_column="id_classe", related_name="+")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT, db_column="id_matiere", related_name="+")
    date = models.DateField(db_column="date")
    heures = models.DecimalField(max_digits=6, decimal_places=2, db_column="heures")
    tarif = models.DecimalField(max_digits=10, decimal_places=2, db_column="tarif")
    montant = models.DecimalField(max_digits=12, decimal_places=2, db_column="montant")

    class Meta:
        db_table = "ligne_releve"
        ordering = ["date", "id"]
        verbose_name = "Ligne de releve"
        verbose_name_plural = "Lignes de releve"


class TypeAjustement:
    PRIME = "PRIME"
    RETENUE = "RETENUE"
    CHOIX = [(PRIME, "Prime"), (RETENUE, "Retenue")]


class AjustementReleve(models.Model):
    releve = models.ForeignKey(ReleveRemuneration, on_delete=models.CASCADE, db_column="id_releve", related_name="ajustements")
    type = models.CharField(max_length=10, choices=TypeAjustement.CHOIX, db_column="type")
    libelle = models.CharField(max_length=150, db_column="libelle")
    montant = models.DecimalField(max_digits=12, decimal_places=2, db_column="montant")
    cree_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_cree_par", related_name="ajustements_remuneration",
    )
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")

    class Meta:
        db_table = "ajustement_releve"
        ordering = ["id"]
        verbose_name = "Prime ou retenue"
        verbose_name_plural = "Primes et retenues"


class TypePaiement:
    ACOMPTE = "ACOMPTE"
    SOLDE = "SOLDE"
    ANNULATION = "ANNULATION"
    CHOIX = [(ACOMPTE, "Acompte / paiement partiel"), (SOLDE, "Solde"), (ANNULATION, "Annulation")]


class ModePaiement:
    ESPECES = "ESPECES"
    VIREMENT = "VIREMENT"
    CHEQUE = "CHEQUE"
    MOBILE = "MOBILE"
    CHOIX = [(ESPECES, "Especes"), (VIREMENT, "Virement"), (CHEQUE, "Cheque"), (MOBILE, "Paiement mobile")]


class PaiementProfesseur(ModeleImmuable):
    """Paiement immuable. Une erreur se corrige par un paiement ANNULATION de
    montant negatif (motif obligatoire), jamais par modification ou suppression."""

    reference = models.CharField(max_length=30, unique=True, db_column="reference")
    releve = models.ForeignKey(ReleveRemuneration, on_delete=models.PROTECT, db_column="id_releve", related_name="paiements")
    type = models.CharField(max_length=12, choices=TypePaiement.CHOIX, db_column="type")
    montant = models.DecimalField(max_digits=12, decimal_places=2, db_column="montant")
    mode_paiement = models.CharField(max_length=10, choices=ModePaiement.CHOIX, default=ModePaiement.ESPECES, db_column="mode_paiement")
    date_paiement = models.DateField(db_column="date_paiement")
    annule = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, db_column="id_annule", related_name="annulation_par",
    )
    observations = models.CharField(max_length=255, blank=True, default="", db_column="observations")
    enregistre_par = models.ForeignKey(
        "utilisateurs.Utilisateur", on_delete=models.PROTECT, db_column="id_utilisateur", related_name="paiements_professeurs",
    )
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")

    class Meta:
        db_table = "paiement_professeur"
        ordering = ["-date_paiement", "-id"]
        verbose_name = "Paiement de professeur"
        verbose_name_plural = "Paiements de professeurs"


class CorrectionHeures(models.Model):
    """Trace d'une correction d'heures sur un releve deja valide (motif obligatoire)."""

    releve = models.ForeignKey(ReleveRemuneration, on_delete=models.PROTECT, db_column="id_releve", related_name="corrections")
    seance = models.ForeignKey(Seance, on_delete=models.PROTECT, db_column="id_seance", related_name="corrections_heures")
    anciennes_heures = models.DecimalField(max_digits=6, decimal_places=2, db_column="anciennes_heures")
    nouvelles_heures = models.DecimalField(max_digits=6, decimal_places=2, db_column="nouvelles_heures")
    ancien_montant = models.DecimalField(max_digits=12, decimal_places=2, db_column="ancien_montant")
    nouveau_montant = models.DecimalField(max_digits=12, decimal_places=2, db_column="nouveau_montant")
    motif = models.CharField(max_length=255, db_column="motif")
    corrige_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, on_delete=models.SET_NULL, db_column="id_corrige_par", related_name="corrections_heures",
    )
    corrige_le = models.DateTimeField(auto_now_add=True, db_column="corrige_le")

    class Meta:
        db_table = "correction_heures"
        ordering = ["-corrige_le", "-id"]
        verbose_name = "Correction d'heures"
        verbose_name_plural = "Corrections d'heures"
