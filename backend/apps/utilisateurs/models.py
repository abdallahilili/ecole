from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.commun.constantes import Role


class GestionnaireUtilisateur(BaseUserManager):
    def create_user(self, identifiant, mot_de_passe=None, **extra):
        if not identifiant:
            raise ValueError("L'identifiant est obligatoire.")
        utilisateur = self.model(identifiant=identifiant, **extra)
        utilisateur.set_password(mot_de_passe)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, identifiant, mot_de_passe=None, **extra):
        extra.setdefault("role", Role.ADMINISTRATEUR)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(identifiant, mot_de_passe, **extra)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    identifiant = models.CharField(max_length=50, unique=True, db_column="identifiant")
    nom = models.CharField(max_length=100, db_column="nom")
    prenom = models.CharField(max_length=100, blank=True, default="", db_column="prenom")
    telephone = models.CharField(max_length=30, blank=True, default="", db_column="telephone")
    role = models.CharField(max_length=30, choices=Role.CHOIX, default=Role.PROFESSEUR, db_column="role")
    # Relie un compte Professeur a sa fiche RH quand le role est PROFESSEUR.
    professeur = models.OneToOneField(
        "professeurs.Professeur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_professeur", related_name="compte_utilisateur",
    )
    actif = models.BooleanField(default=True, db_column="actif")
    date_creation = models.DateTimeField(auto_now_add=True, db_column="date_creation")

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = GestionnaireUtilisateur()

    USERNAME_FIELD = "identifiant"
    REQUIRED_FIELDS = ["nom"]

    class Meta:
        db_table = "utilisateur"
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.prenom} {self.nom}".strip() or self.identifiant

    @property
    def is_active(self):
        return self.actif

    @is_active.setter
    def is_active(self, valeur):
        self.actif = valeur
