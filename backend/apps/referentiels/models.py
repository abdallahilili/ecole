from django.db import models
from django.utils import timezone
from apps.commun.exceptions import ErreurMetier
from apps.commun.langue import est_arabe


def nom_localise(objet):
    """Nom a afficher : version arabe si l'interface est en arabe et qu'elle est renseignee, sinon le nom principal."""
    return objet.nom_ar if est_arabe() and objet.nom_ar else objet.nom


class AnneeScolaire(models.Model):
    # ex: 2025-2026 ; a l'archivage le libelle devient "2025-2026 (archivee #id)" : le nom redevient disponible.
    libelle = models.CharField(max_length=60, unique=True, db_column="libelle")
    date_debut = models.DateField(db_column="date_debut")
    date_fin = models.DateField(db_column="date_fin")
    # Ecole secondaire : le 1er trimestre commence a date_debut, le 3e se termine a date_fin.
    debut_trimestre2 = models.DateField(null=True, blank=True, db_column="debut_trimestre2")
    debut_trimestre3 = models.DateField(null=True, blank=True, db_column="debut_trimestre3")
    debut_vacances = models.DateField(null=True, blank=True, db_column="debut_vacances")
    fin_vacances = models.DateField(null=True, blank=True, db_column="fin_vacances")
    # Deuxieme petite vacance (fin mars) ; la premiere (debut_vacances) tombe en fin d'annee civile.
    debut_vacances2 = models.DateField(null=True, blank=True, db_column="debut_vacances2")
    fin_vacances2 = models.DateField(null=True, blank=True, db_column="fin_vacances2")
    # Un examen par trimestre.
    debut_examen1 = models.DateField(null=True, blank=True, db_column="debut_examen1")
    fin_examen1 = models.DateField(null=True, blank=True, db_column="fin_examen1")
    debut_examen2 = models.DateField(null=True, blank=True, db_column="debut_examen2")
    fin_examen2 = models.DateField(null=True, blank=True, db_column="fin_examen2")
    debut_examen3 = models.DateField(null=True, blank=True, db_column="debut_examen3")
    fin_examen3 = models.DateField(null=True, blank=True, db_column="fin_examen3")
    active = models.BooleanField(default=False, db_column="active")
    cloturee = models.BooleanField(default=False, db_column="cloturee")
    # La "suppression" d'une annee l'archive : classes, inscriptions, notes... restent rattachees a la ligne.
    archivee = models.BooleanField(default=False, db_column="archivee")
    date_archivage = models.DateTimeField(null=True, blank=True, db_column="date_archivage")

    class Meta:
        db_table = "annee_scolaire"
        ordering = ["-date_debut"]
        verbose_name = "Annee scolaire"
        verbose_name_plural = "Annees scolaires"

    def __str__(self):
        return self.libelle

    def archiver(self):
        """Retire l'annee des listes et libere son libelle, sans toucher aux donnees qui s'y rattachent."""
        self.libelle = f"{self.libelle} (archivee #{self.pk})"
        self.archivee = True
        self.active = False
        self.date_archivage = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if self.active:
            # Une seule annee active a la fois (sauf desactivation explicite).
            AnneeScolaire.objects.exclude(pk=self.pk).filter(active=True).update(active=False)
        super().save(*args, **kwargs)


class Niveau(models.Model):
    nom = models.CharField(max_length=100, db_column="nom")
    nom_ar = models.CharField(max_length=100, blank=True, default="", db_column="nom_ar")
    code = models.CharField(max_length=20, unique=True, db_column="code")
    ordre = models.IntegerField(default=0, db_column="ordre")

    class Meta:
        db_table = "niveau"
        ordering = ["ordre", "nom"]
        verbose_name = "Niveau"
        verbose_name_plural = "Niveaux"

    def __str__(self):
        return self.nom

    @property
    def nom_affiche(self):
        return nom_localise(self)


class Salle(models.Model):
    nom = models.CharField(max_length=50, unique=True, db_column="nom")
    capacite = models.IntegerField(default=30, db_column="capacite")
    type_salle = models.CharField(max_length=50, blank=True, default="", db_column="type_salle")
    equipements = models.CharField(max_length=255, blank=True, default="", db_column="equipements")
    disponible = models.BooleanField(default=True, db_column="disponible")

    class Meta:
        db_table = "salle"
        ordering = ["nom"]
        verbose_name = "Salle"
        verbose_name_plural = "Salles"

    def __str__(self):
        return self.nom


class Classe(models.Model):
    nom = models.CharField(max_length=100, db_column="nom")
    niveau = models.ForeignKey(Niveau, on_delete=models.PROTECT, db_column="id_niveau", related_name="classes")
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.PROTECT, db_column="id_annee_scolaire", related_name="classes"
    )
    capacite = models.IntegerField(default=40, db_column="capacite")
    salle_principale = models.ForeignKey(
        Salle, null=True, blank=True, on_delete=models.SET_NULL, db_column="id_salle", related_name="classes"
    )

    class Meta:
        db_table = "classe"
        unique_together = [("nom", "annee_scolaire")]
        ordering = ["niveau__ordre", "nom"]
        verbose_name = "Classe"
        verbose_name_plural = "Classes"

    def __str__(self):
        return f"{self.nom} ({self.annee_scolaire})"


class TarifClasse(models.Model):
    """Tarif (mensualite, en UM) applique a une classe donnee, ex. 6AF = 900 UM.
    La classe appartenant a une annee scolaire, le tarif est de fait annuel."""

    classe = models.OneToOneField(
        Classe, on_delete=models.CASCADE, db_column="id_classe", related_name="tarif",
        error_messages={"unique": "Cette classe a deja un tarif."},
    )
    montant = models.DecimalField(max_digits=10, decimal_places=2, db_column="montant")

    class Meta:
        db_table = "tarif_classe"
        ordering = ["classe__niveau__ordre", "classe__nom"]
        verbose_name = "Tarif de classe"
        verbose_name_plural = "Tarifs de classe"

    def __str__(self):
        return f"{self.classe.nom} - {self.montant} UM"


class Groupe(models.Model):
    nom = models.CharField(max_length=50, db_column="nom")
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, db_column="id_classe", related_name="groupes")

    class Meta:
        db_table = "groupe"
        unique_together = [("nom", "classe")]
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"

    def __str__(self):
        return f"{self.classe.nom} - {self.nom}"


class Matiere(models.Model):
    nom = models.CharField(max_length=100, db_column="nom")
    nom_ar = models.CharField(max_length=100, blank=True, default="", db_column="nom_ar")
    code = models.CharField(max_length=20, unique=True, db_column="code")
    description = models.CharField(max_length=255, blank=True, default="", db_column="description")

    class Meta:
        db_table = "matiere"
        ordering = ["nom"]
        verbose_name = "Matiere"
        verbose_name_plural = "Matieres"

    def __str__(self):
        return self.nom

    @property
    def nom_affiche(self):
        return nom_localise(self)


class AffectationMatiereClasse(models.Model):
    """Coefficient et volume horaire d'une matiere pour UNE classe
    donnee : le meme coefficient n'est jamais impose a toutes les
    classes (regle explicite du cahier des charges)."""

    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, db_column="id_matiere", related_name="affectations_classe")
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, db_column="id_classe", related_name="matieres_affectees")
    coefficient = models.DecimalField(max_digits=5, decimal_places=2, default=1, db_column="coefficient")
    volume_horaire_hebdo = models.DecimalField(max_digits=5, decimal_places=2, default=1, db_column="volume_horaire_hebdo")
    nombre_seances_semaine = models.IntegerField(default=1, db_column="nombre_seances_semaine")

    class Meta:
        db_table = "affectation_matiere_classe"
        unique_together = [("matiere", "classe")]
        verbose_name = "Affectation matiere-classe"
        verbose_name_plural = "Affectations matiere-classe"

    def __str__(self):
        return f"{self.matiere} / {self.classe} (coef {self.coefficient})"
