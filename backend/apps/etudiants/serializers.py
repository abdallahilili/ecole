from datetime import date

from django.db import transaction
from rest_framework import serializers
from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from apps.referentiels.models import Classe
from apps.scolarite import services as services_scolarite
from .models import Etudiant, Inscription


class EtudiantSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    # Numero de l'inscription active : celle de la classe demandee (?classe=), sinon celle de l'annee active (voir la vue).
    numero_inscription = serializers.CharField(read_only=True)
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


# Roles qui lisent les inscriptions (listes d'appel, notes) sans avoir a connaitre les frais de scolarite.
ROLES_SANS_MONTANT = (Role.PROFESSEUR, Role.RESPONSABLE_PEDAGOGIQUE)


class InscriptionSerializer(serializers.ModelSerializer):
    numero_inscription = serializers.CharField(read_only=True)   # attribue par le serveur (voir Inscription.save)
    etudiant_nom = serializers.CharField(source="etudiant.nom_complet", read_only=True)
    etudiant_matricule = serializers.CharField(source="etudiant.matricule", read_only=True)
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    groupe_nom = serializers.CharField(source="groupe.nom", read_only=True, default=None)
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)
    # Mensualite de l'eleve : vide = tarif de la classe ; elle sert de base a la fiche de paiement creee avec l'inscription.
    montant_mensuel = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = Inscription
        fields = "__all__"

    def get_fields(self):
        champs = super().get_fields()
        requete = self.context.get("request")
        if requete is not None and getattr(requete.user, "role", None) in ROLES_SANS_MONTANT:
            champs.pop("montant_mensuel", None)
        return champs

    def to_internal_value(self, donnees):
        if hasattr(donnees, "get") and donnees.get("montant_mensuel") == "":   # champ vide du formulaire
            donnees = {cle: donnees[cle] for cle in donnees}
            donnees["montant_mensuel"] = None
        return super().to_internal_value(donnees)

    def validate_montant_mensuel(self, valeur):
        if valeur is not None and valeur <= 0:
            raise ErreurMetier("La mensualite doit etre strictement positive.")
        return valeur

    @transaction.atomic
    def create(self, donnees):
        inscription = super().create(donnees)
        services_scolarite.generer_echeances(inscription)   # fiche de paiement : un mois a payer par echeance
        return inscription

    @transaction.atomic
    def update(self, instance, donnees):
        ancien_montant = instance.montant_mensuel
        inscription = super().update(instance, donnees)
        if inscription.montant_mensuel != ancien_montant or not inscription.echeances.exists():
            services_scolarite.generer_echeances(inscription)   # nouvelle mensualite : mois non payes mis a jour
        return inscription

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
