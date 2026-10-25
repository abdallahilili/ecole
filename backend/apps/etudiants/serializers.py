from datetime import date

from django.db import transaction
from rest_framework import serializers
from apps.commun.exceptions import ErreurMetier
from apps.referentiels.models import Classe
from .models import Etudiant, Inscription


class EtudiantSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    # Creation depuis la liste d'une classe : l'etudiant est inscrit dans cette classe (annee de la classe).
    classe_inscription = serializers.PrimaryKeyRelatedField(queryset=Classe.objects.all(), write_only=True, required=False)

    class Meta:
        model = Etudiant
        fields = "__all__"

    @transaction.atomic
    def create(self, donnees):
        classe = donnees.pop("classe_inscription", None)
        etudiant = super().create(donnees)
        if classe is not None:
            inscription = InscriptionSerializer(data={
                "etudiant": etudiant.pk, "annee_scolaire": classe.annee_scolaire_id, "classe": classe.pk,
                "type_inscription": "INSCRIPTION", "statut": "ACTIVE", "date_inscription": date.today().isoformat(),
            })
            inscription.is_valid(raise_exception=True)
            inscription.save()
        return etudiant

    def update(self, instance, donnees):
        donnees.pop("classe_inscription", None)
        return super().update(instance, donnees)

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
