from rest_framework import serializers
from apps.commun.exceptions import ErreurMetier
from apps.referentiels.models import Classe
from .models import Etudiant, Inscription


class EtudiantSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)

    class Meta:
        model = Etudiant
        fields = "__all__"

    def validate_matricule(self, valeur):
        if not valeur or not valeur.strip():
            raise ErreurMetier("Le matricule est obligatoire.")
        return valeur.strip()


class InscriptionSerializer(serializers.ModelSerializer):
    etudiant_nom = serializers.CharField(source="etudiant.nom_complet", read_only=True)
    etudiant_matricule = serializers.CharField(source="etudiant.matricule", read_only=True)
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    groupe_nom = serializers.CharField(source="groupe.nom", read_only=True, default=None)
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)

    class Meta:
        model = Inscription
        fields = "__all__"

    def validate(self, donnees):
        classe = donnees.get("classe", getattr(self.instance, "classe", None))
        groupe = donnees.get("groupe", getattr(self.instance, "groupe", None))
        if groupe and classe and groupe.classe_id != classe.id:
            raise ErreurMetier("Le groupe choisi n'appartient pas a la classe selectionnee.")

        if classe:
            effectif_actuel = Inscription.objects.filter(
                classe=classe, statut="ACTIVE"
            ).exclude(pk=getattr(self.instance, "pk", None)).count()
            if effectif_actuel + 1 > classe.capacite:
                raise ErreurMetier(
                    f"La classe '{classe.nom}' a atteint sa capacite maximale ({classe.capacite} eleves)."
                )
        return donnees
