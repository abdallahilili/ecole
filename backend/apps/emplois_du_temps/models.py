from datetime import time

from django.db import models

from apps.professeurs.models import Professeur
from apps.referentiels.models import AnneeScolaire, Classe, Groupe, Matiere, Salle

JOURS = [
    (0, "Lundi"), (1, "Mardi"), (2, "Mercredi"), (3, "Jeudi"), (4, "Vendredi"), (5, "Samedi"), (6, "Dimanche"),
]
NOMS_JOURS = dict(JOURS)


class ConfigurationHoraires(models.Model):
    """Cadre horaire d'une annee scolaire : jours ouvrables, plage horaire,
    grille de creneaux, pauses et limites. Les pauses doivent coincider
    avec la grille (ex. creneaux de 60 min : pause 10:00-11:00)."""

    annee_scolaire = models.OneToOneField(
        AnneeScolaire, on_delete=models.CASCADE, db_column="id_annee_scolaire", related_name="configuration_horaires"
    )
    jours = models.CharField(max_length=20, default="0,1,2,3,4", db_column="jours")  # 0 = lundi ... 6 = dimanche
    heure_debut = models.TimeField(default=time(8, 0), db_column="heure_debut")
    heure_fin = models.TimeField(default=time(14, 0), db_column="heure_fin")
    duree_creneau = models.IntegerField(default=60, db_column="duree_creneau")        # minutes
    duree_min_seance = models.IntegerField(default=60, db_column="duree_min_seance")  # minutes
    duree_max_seance = models.IntegerField(default=180, db_column="duree_max_seance")  # minutes
    pauses = models.JSONField(default=list, blank=True, db_column="pauses")           # [{"debut": "10:00", "fin": "11:00"}]
    max_creneaux_jour_professeur = models.IntegerField(default=6, db_column="max_creneaux_jour_professeur")
    max_creneaux_consecutifs_professeur = models.IntegerField(default=4, db_column="max_creneaux_consecutifs_professeur")

    class Meta:
        db_table = "configuration_horaires"
        verbose_name = "Configuration des horaires"
        verbose_name_plural = "Configurations des horaires"

    def liste_jours(self):
        return [int(j) for j in self.jours.split(",") if j.strip() != ""]


class TypeDisponibilite:
    INDISPONIBLE = "INDISPONIBLE"   # contrainte obligatoire
    PREFERE = "PREFERE"             # preference (contrainte souple)
    CHOIX = [(INDISPONIBLE, "Indisponible"), (PREFERE, "Creneau prefere")]


class DisponibiliteProfesseur(models.Model):
    professeur = models.ForeignKey(
        Professeur, on_delete=models.CASCADE, db_column="id_professeur", related_name="disponibilites"
    )
    jour = models.IntegerField(choices=JOURS, db_column="jour")
    heure_debut = models.TimeField(db_column="heure_debut")
    heure_fin = models.TimeField(db_column="heure_fin")
    type = models.CharField(max_length=15, choices=TypeDisponibilite.CHOIX, default=TypeDisponibilite.INDISPONIBLE, db_column="type")
    commentaire = models.CharField(max_length=255, blank=True, default="", db_column="commentaire")

    class Meta:
        db_table = "disponibilite_professeur"
        ordering = ["professeur__nom", "jour", "heure_debut"]
        verbose_name = "Disponibilite de professeur"
        verbose_name_plural = "Disponibilites de professeurs"


class IndisponibiliteSalle(models.Model):
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, db_column="id_salle", related_name="indisponibilites")
    jour = models.IntegerField(choices=JOURS, db_column="jour")
    heure_debut = models.TimeField(db_column="heure_debut")
    heure_fin = models.TimeField(db_column="heure_fin")
    motif = models.CharField(max_length=255, blank=True, default="", db_column="motif")

    class Meta:
        db_table = "indisponibilite_salle"
        ordering = ["salle__nom", "jour", "heure_debut"]
        verbose_name = "Indisponibilite de salle"
        verbose_name_plural = "Indisponibilites de salles"


class StatutEmploi:
    BROUILLON = "BROUILLON"
    PUBLIE = "PUBLIE"
    ARCHIVE = "ARCHIVE"
    CHOIX = [(BROUILLON, "Brouillon"), (PUBLIE, "Publie"), (ARCHIVE, "Archive")]


class OrigineEmploi:
    MANUEL = "MANUEL"
    GENETIQUE = "GENETIQUE"
    CHOIX = [(MANUEL, "Manuel"), (GENETIQUE, "Genere automatiquement")]


class EmploiDuTemps(models.Model):
    """Un emploi du temps hebdomadaire. Un brouillon est librement modifiable ;
    publie, il devient immuable (on le duplique pour le modifier) et une
    version est conservee. Un seul emploi publie par annee scolaire."""

    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.PROTECT, db_column="id_annee_scolaire", related_name="emplois_du_temps"
    )
    nom = models.CharField(max_length=120, db_column="nom")
    statut = models.CharField(max_length=10, choices=StatutEmploi.CHOIX, default=StatutEmploi.BROUILLON, db_column="statut")
    origine = models.CharField(max_length=10, choices=OrigineEmploi.CHOIX, default=OrigineEmploi.MANUEL, db_column="origine")
    rapport = models.JSONField(default=dict, blank=True, db_column="rapport")  # rapport de generation (score, diagnostics)
    cree_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_cree_par", related_name="emplois_crees",
    )
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")
    publie_le = models.DateTimeField(null=True, blank=True, db_column="publie_le")

    class Meta:
        db_table = "emploi_du_temps"
        ordering = ["-cree_le", "-id"]
        verbose_name = "Emploi du temps"
        verbose_name_plural = "Emplois du temps"

    def __str__(self):
        return f"{self.nom} ({self.annee_scolaire})"


class SeanceProgrammee(models.Model):
    emploi = models.ForeignKey(EmploiDuTemps, on_delete=models.CASCADE, db_column="id_emploi", related_name="seances")
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, db_column="id_classe", related_name="seances_programmees")
    groupe = models.ForeignKey(
        Groupe, null=True, blank=True, on_delete=models.PROTECT, db_column="id_groupe", related_name="seances_programmees"
    )
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT, db_column="id_matiere", related_name="seances_programmees")
    professeur = models.ForeignKey(
        Professeur, on_delete=models.PROTECT, db_column="id_professeur", related_name="seances_programmees"
    )
    salle = models.ForeignKey(
        Salle, null=True, blank=True, on_delete=models.PROTECT, db_column="id_salle", related_name="seances_programmees"
    )
    jour = models.IntegerField(choices=JOURS, db_column="jour")
    heure_debut = models.TimeField(db_column="heure_debut")
    heure_fin = models.TimeField(db_column="heure_fin")

    class Meta:
        db_table = "seance_programmee"
        ordering = ["jour", "heure_debut", "classe__nom"]
        verbose_name = "Seance programmee"
        verbose_name_plural = "Seances programmees"

    def __str__(self):
        return f"{self.matiere} - {self.classe.nom} - {NOMS_JOURS[self.jour]} {self.heure_debut:%H:%M}"


class VersionEmploiDuTemps(models.Model):
    """Instantane (JSON) d'un emploi du temps au moment de sa publication."""

    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.PROTECT, db_column="id_annee_scolaire", related_name="versions_emploi"
    )
    emploi = models.ForeignKey(EmploiDuTemps, on_delete=models.PROTECT, db_column="id_emploi", related_name="versions")
    numero = models.IntegerField(db_column="numero")
    contenu = models.JSONField(db_column="contenu")
    commentaire = models.CharField(max_length=255, blank=True, default="", db_column="commentaire")
    publie_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, on_delete=models.SET_NULL,
        db_column="id_publie_par", related_name="versions_emploi_publiees",
    )
    publie_le = models.DateTimeField(auto_now_add=True, db_column="publie_le")

    class Meta:
        db_table = "version_emploi_du_temps"
        unique_together = [("annee_scolaire", "numero")]
        ordering = ["-numero"]
        verbose_name = "Version d'emploi du temps"
        verbose_name_plural = "Versions d'emploi du temps"
