from django.db import models
from apps.commun.constantes import StatutProfesseur, ModeRemuneration
from apps.referentiels.models import AnneeScolaire, Classe, Groupe, Matiere


class Professeur(models.Model):
    matricule = models.CharField(max_length=30, unique=True, db_column="matricule")
    nom = models.CharField(max_length=100, db_column="nom")
    prenom = models.CharField(max_length=100, db_column="prenom")
    telephone = models.CharField(max_length=30, blank=True, default="", db_column="telephone")
    email = models.EmailField(blank=True, default="", db_column="email")
    adresse = models.CharField(max_length=255, blank=True, default="", db_column="adresse")
    specialite = models.CharField(max_length=150, blank=True, default="", db_column="specialite")
    date_recrutement = models.DateField(null=True, blank=True, db_column="date_recrutement")
    statut = models.CharField(max_length=20, choices=StatutProfesseur.CHOIX, default=StatutProfesseur.ACTIF, db_column="statut")
    mode_remuneration = models.CharField(
        max_length=20, choices=ModeRemuneration.CHOIX, default=ModeRemuneration.HORAIRE, db_column="mode_remuneration"
    )
    tarif_horaire = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column="tarif_horaire")
    salaire_fixe = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column="salaire_fixe")
    photo = models.ImageField(upload_to="professeurs/photos/", null=True, blank=True, db_column="photo")

    class Meta:
        db_table = "professeur"
        ordering = ["nom", "prenom"]
        verbose_name = "Professeur"
        verbose_name_plural = "Professeurs"

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.matricule})"

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}"


class AffectationProfesseur(models.Model):
    """Affecte un professeur a une matiere pour une classe (et
    eventuellement un groupe precis), pour une annee scolaire donnee.
    Un meme professeur ne peut pas etre affecte deux fois a la meme
    combinaison matiere/classe/groupe sur la meme periode."""

    professeur = models.ForeignKey(
        Professeur, on_delete=models.CASCADE, db_column="id_professeur", related_name="affectations"
    )
    matiere = models.ForeignKey(
        Matiere, on_delete=models.CASCADE, db_column="id_matiere", related_name="affectations_professeur"
    )
    classe = models.ForeignKey(
        Classe, on_delete=models.CASCADE, db_column="id_classe", related_name="affectations_professeur"
    )
    groupe = models.ForeignKey(
        Groupe, null=True, blank=True, on_delete=models.CASCADE,
        db_column="id_groupe", related_name="affectations_professeur",
    )
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, db_column="id_annee_scolaire", related_name="affectations_professeur"
    )

    class Meta:
        db_table = "affectation_professeur"
        unique_together = [("professeur", "matiere", "classe", "groupe", "annee_scolaire")]
        verbose_name = "Affectation professeur"
        verbose_name_plural = "Affectations professeur"

    def __str__(self):
        return f"{self.professeur} - {self.matiere} - {self.classe}"
