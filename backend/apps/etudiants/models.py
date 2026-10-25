from django.db import models
from apps.commun.constantes import Sexe, StatutInscription, TypeInscription
from apps.referentiels.models import AnneeScolaire, Classe, Groupe


class Etudiant(models.Model):
    matricule = models.CharField(max_length=30, unique=True, db_column="matricule")
    nom = models.CharField(max_length=100, db_column="nom")
    prenom = models.CharField(max_length=100, db_column="prenom")
    sexe = models.CharField(max_length=1, choices=Sexe.CHOIX, default=Sexe.MASCULIN, db_column="sexe")
    date_naissance = models.DateField(null=True, blank=True, db_column="date_naissance")
    lieu_naissance = models.CharField(max_length=100, blank=True, default="", db_column="lieu_naissance")
    numero_national = models.CharField(max_length=50, blank=True, default="", db_column="numero_national")
    adresse = models.CharField(max_length=255, blank=True, default="", db_column="adresse")

    nom_pere = models.CharField(max_length=150, blank=True, default="", db_column="nom_pere")
    telephone_pere = models.CharField(max_length=30, blank=True, default="", db_column="telephone_pere")
    nom_mere = models.CharField(max_length=150, blank=True, default="", db_column="nom_mere")
    telephone_mere = models.CharField(max_length=30, blank=True, default="", db_column="telephone_mere")
    nom_tuteur = models.CharField(max_length=150, blank=True, default="", db_column="nom_tuteur")
    telephone_tuteur = models.CharField(max_length=30, blank=True, default="", db_column="telephone_tuteur")
    telephone_principal = models.CharField(
        max_length=30, blank=True, default="",
        help_text="Numero utilise pour les notifications WhatsApp (wa.me).",
        db_column="telephone_principal",
    )

    photo = models.ImageField(upload_to="etudiants/photos/", null=True, blank=True, db_column="photo")
    actif = models.BooleanField(default=True, db_column="actif")
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")

    class Meta:
        db_table = "etudiant"
        ordering = ["nom", "prenom"]
        verbose_name = "Etudiant"
        verbose_name_plural = "Etudiants"

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.matricule})"

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}"

    @property
    def telephone_notification(self):
        """Numero a utiliser en priorite pour generer un lien wa.me."""
        return self.telephone_principal or self.telephone_pere or self.telephone_mere or self.telephone_tuteur


class Inscription(models.Model):
    etudiant = models.ForeignKey(Etudiant, on_delete=models.PROTECT, db_column="id_etudiant", related_name="inscriptions")
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.PROTECT, db_column="id_annee_scolaire", related_name="inscriptions"
    )
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, db_column="id_classe", related_name="inscriptions")
    groupe = models.ForeignKey(
        Groupe, null=True, blank=True, on_delete=models.SET_NULL, db_column="id_groupe", related_name="inscriptions"
    )
    type_inscription = models.CharField(
        max_length=20, choices=TypeInscription.CHOIX, default=TypeInscription.INSCRIPTION,
        db_column="type_inscription",
    )
    statut = models.CharField(
        max_length=20, choices=StatutInscription.CHOIX, default=StatutInscription.ACTIVE, db_column="statut"
    )
    date_inscription = models.DateField(db_column="date_inscription")
    date_fin = models.DateField(null=True, blank=True, db_column="date_fin")
    etablissement_origine = models.CharField(max_length=150, blank=True, default="", db_column="etablissement_origine")
    observations = models.CharField(max_length=255, blank=True, default="", db_column="observations")

    class Meta:
        db_table = "inscription"
        unique_together = [("etudiant", "annee_scolaire")]
        ordering = ["-date_inscription"]
        indexes = [models.Index(fields=["classe", "annee_scolaire", "statut"], name="inscription_classe_idx")]   # listes d'appel et de notes
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"

    def __str__(self):
        return f"{self.etudiant} - {self.annee_scolaire} - {self.classe}"
