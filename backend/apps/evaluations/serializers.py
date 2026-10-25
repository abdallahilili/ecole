from rest_framework import serializers

from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from apps.etudiants.models import Inscription
from apps.professeurs.models import AffectationProfesseur
from apps.referentiels.models import AffectationMatiereClasse
from . import services
from .models import Evaluation


class EvaluationSerializer(serializers.ModelSerializer):
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    matiere_nom = serializers.CharField(source="matiere.nom_affiche", read_only=True)
    nb_notes = serializers.IntegerField(read_only=True, default=0)
    nb_eleves = serializers.SerializerMethodField()
    resultats_valides = serializers.SerializerMethodField()

    class Meta:
        model = Evaluation
        fields = "__all__"
        read_only_fields = ["cree_par", "cree_le"]

    def get_nb_eleves(self, obj):
        # Annotation de la vue (une seule requete pour la liste) ; requete directe sinon.
        if hasattr(obj, "effectif_classe"):
            return obj.effectif_classe
        return Inscription.objects.filter(
            classe_id=obj.classe_id, annee_scolaire_id=obj.annee_scolaire_id, statut="ACTIVE").count()

    def get_resultats_valides(self, obj):
        if hasattr(obj, "verrouillee"):
            return obj.verrouillee
        return services.resultats_valides(obj.classe, obj.trimestre)

    def validate_bareme(self, valeur):
        if valeur <= 0:
            raise ErreurMetier("Le bareme doit etre strictement positif.")
        return valeur

    def validate_poids(self, valeur):
        if valeur <= 0:
            raise ErreurMetier("Le poids doit etre strictement positif.")
        return valeur

    def validate_libelle(self, valeur):
        if not valeur.strip():
            raise ErreurMetier("Le libelle est obligatoire.")
        return valeur.strip()

    def validate(self, donnees):
        instance = self.instance
        utilisateur = self.context["request"].user

        def val(nom):
            return donnees.get(nom, getattr(instance, nom, None))

        annee, classe, matiere, trimestre = val("annee_scolaire"), val("classe"), val("matiere"), val("trimestre")
        if classe.annee_scolaire_id != annee.id:
            raise ErreurMetier("La classe choisie n'appartient pas a cette annee scolaire.")
        if not AffectationMatiereClasse.objects.filter(classe=classe, matiere=matiere).exists():
            raise ErreurMetier(
                f"La matiere '{matiere.nom_affiche}' n'est pas enseignee dans la classe {classe.nom} : "
                "definissez d'abord son coefficient (Matieres > Coefficients)."
            )
        jour = val("date")
        if jour and not (annee.date_debut <= jour <= annee.date_fin):
            raise ErreurMetier("La date doit etre comprise dans l'annee scolaire.")

        for cible_classe, cible_trimestre in {(classe, trimestre), (instance.classe, instance.trimestre) if instance else (classe, trimestre)}:
            if services.resultats_valides(cible_classe, cible_trimestre):
                raise ErreurMetier("Les resultats de ce trimestre sont valides : rouvrez-les pour modifier les evaluations.")

        if instance and "bareme" in donnees and donnees["bareme"] != instance.bareme and instance.notes.exists():
            raise ErreurMetier("Le bareme ne peut plus etre modifie : des notes sont deja saisies.")

        if utilisateur.role == Role.PROFESSEUR:
            fiche = utilisateur.professeur
            if fiche is None or not AffectationProfesseur.objects.filter(
                professeur=fiche, matiere=matiere, classe=classe, annee_scolaire=annee
            ).exists():
                raise ErreurMetier("Vous n'etes pas affecte a cette matiere pour cette classe.")
        return donnees
