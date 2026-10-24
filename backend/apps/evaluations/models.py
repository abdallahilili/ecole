from django.db import models

from apps.etudiants.models import Etudiant
from apps.referentiels.models import AnneeScolaire, Classe, Matiere


class TypeEvaluation:
    DEVOIR = "DEVOIR"
    INTERROGATION = "INTERROGATION"
    EXAMEN = "EXAMEN"
    AUTRE = "AUTRE"
    CHOIX = [
        (DEVOIR, "Devoir"),
        (INTERROGATION, "Interrogation"),
        (EXAMEN, "Examen / composition"),
        (AUTRE, "Autre"),
    ]


class StatutNote:
    """Une note sans ligne en base est 'manquante' : jamais transformee en zero."""

    SAISIE = "SAISIE"
    ABSENT_JUSTIFIE = "ABSENT_JUSTIFIE"
    ABSENT = "ABSENT"            # absence non justifiee
    NON_APPLICABLE = "NON_APPLICABLE"
    CHOIX = [
        (SAISIE, "Note saisie"),
        (ABSENT_JUSTIFIE, "Absent justifie"),
        (ABSENT, "Absent non justifie"),
        (NON_APPLICABLE, "Non applicable"),
    ]
    SANS_VALEUR = (ABSENT_JUSTIFIE, ABSENT, NON_APPLICABLE)


class Decision:
    ADMIS = "ADMIS"
    REDOUBLE = "REDOUBLE"
    EXCLU = "EXCLU"
    CHOIX = [(ADMIS, "Admis(e)"), (REDOUBLE, "Redouble"), (EXCLU, "Exclu(e)")]


TRIMESTRES = [(1, "1er trimestre"), (2, "2e trimestre"), (3, "3e trimestre")]


class Evaluation(models.Model):
    """Une evaluation d'une matiere pour une classe et un trimestre
    (ex. 'Interrogations' poids 3, 'Composition 1' poids 1, 'Composition 2'
    poids 2, comme sur les bulletins papier). Le bareme permet de
    normaliser sur 20 avant de ponderer."""

    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.PROTECT, db_column="id_annee_scolaire", related_name="evaluations"
    )
    trimestre = models.IntegerField(choices=TRIMESTRES, db_column="trimestre")
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, db_column="id_classe", related_name="evaluations")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT, db_column="id_matiere", related_name="evaluations")
    libelle = models.CharField(max_length=80, db_column="libelle")
    type = models.CharField(max_length=20, choices=TypeEvaluation.CHOIX, default=TypeEvaluation.DEVOIR, db_column="type")
    date = models.DateField(null=True, blank=True, db_column="date")
    bareme = models.DecimalField(max_digits=5, decimal_places=2, default=20, db_column="bareme")
    poids = models.DecimalField(max_digits=5, decimal_places=2, default=1, db_column="poids")
    cree_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_cree_par", related_name="evaluations_creees",
    )
    cree_le = models.DateTimeField(auto_now_add=True, db_column="cree_le")

    class Meta:
        db_table = "evaluation"
        unique_together = [("classe", "matiere", "trimestre", "libelle")]
        ordering = ["trimestre", "date", "id"]
        verbose_name = "Evaluation"
        verbose_name_plural = "Evaluations"

    def __str__(self):
        return f"{self.matiere} - {self.classe.nom} - T{self.trimestre} - {self.libelle}"


class Note(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, db_column="id_evaluation", related_name="notes")
    etudiant = models.ForeignKey(Etudiant, on_delete=models.PROTECT, db_column="id_etudiant", related_name="notes")
    statut = models.CharField(max_length=20, choices=StatutNote.CHOIX, default=StatutNote.SAISIE, db_column="statut")
    valeur = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, db_column="valeur")
    modifie_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, blank=True, on_delete=models.SET_NULL,
        db_column="id_modifie_par", related_name="notes_modifiees",
    )
    modifie_le = models.DateTimeField(auto_now=True, db_column="modifie_le")

    class Meta:
        db_table = "note"
        unique_together = [("evaluation", "etudiant")]
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self):
        return f"{self.etudiant} - {self.evaluation} : {self.valeur if self.statut == StatutNote.SAISIE else self.statut}"


class ValidationResultats(models.Model):
    """Verrou des resultats d'une classe pour un trimestre : une fois valides,
    les notes ne changent plus (sauf reouverture/modification justifiee,
    tracee dans le journal d'audit)."""

    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, db_column="id_classe", related_name="validations_resultats")
    trimestre = models.IntegerField(choices=TRIMESTRES, db_column="trimestre")
    validee_par = models.ForeignKey(
        "utilisateurs.Utilisateur", null=True, on_delete=models.SET_NULL,
        db_column="id_validee_par", related_name="resultats_valides",
    )
    validee_le = models.DateTimeField(auto_now_add=True, db_column="validee_le")

    class Meta:
        db_table = "validation_resultats"
        unique_together = [("classe", "trimestre")]
        verbose_name = "Validation des resultats"
        verbose_name_plural = "Validations des resultats"


class Appreciation(models.Model):
    """Appreciations et decision du conseil de classe d'un eleve.
    trimestre 0 = decision annuelle."""

    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, db_column="id_classe", related_name="appreciations")
    trimestre = models.IntegerField(db_column="trimestre")
    etudiant = models.ForeignKey(Etudiant, on_delete=models.PROTECT, db_column="id_etudiant", related_name="appreciations")
    observation_professeurs = models.CharField(max_length=500, blank=True, default="", db_column="observation_professeurs")
    observation_directeur = models.CharField(max_length=500, blank=True, default="", db_column="observation_directeur")
    decision = models.CharField(max_length=10, choices=Decision.CHOIX, blank=True, default="", db_column="decision")

    class Meta:
        db_table = "appreciation"
        unique_together = [("classe", "trimestre", "etudiant")]
        verbose_name = "Appreciation"
        verbose_name_plural = "Appreciations"
