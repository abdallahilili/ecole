from rest_framework import serializers
from apps.commun.exceptions import ErreurMetier
from apps.commun.references import prochaine_reference
from .models import GrilleFrais, PaiementScolarite, TypeFrais


class GrilleFraisSerializer(serializers.ModelSerializer):
    niveau_nom = serializers.CharField(source="niveau.nom", read_only=True)
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)

    class Meta:
        model = GrilleFrais
        fields = "__all__"

    def validate_montant_mensuel(self, valeur):
        if valeur <= 0:
            raise ErreurMetier("Le montant mensuel doit etre strictement positif.")
        return valeur


class PaiementScolariteSerializer(serializers.ModelSerializer):
    etudiant_nom = serializers.CharField(source="inscription.etudiant.nom_complet", read_only=True)
    etudiant_matricule = serializers.CharField(source="inscription.etudiant.matricule", read_only=True)
    classe_nom = serializers.CharField(source="inscription.classe.nom", read_only=True)

    class Meta:
        model = PaiementScolarite
        fields = "__all__"
        read_only_fields = ["reference", "enregistre_par", "cree_le"]

    def validate(self, donnees):
        montant = donnees.get("montant")
        if montant is not None and montant <= 0:
            raise ErreurMetier("Le montant du paiement doit etre strictement positif.")
        type_frais = donnees.get("type_frais")
        mois_concerne = donnees.get("mois_concerne")
        if type_frais == TypeFrais.MENSUALITE and not mois_concerne:
            raise ErreurMetier("Le mois concerne est obligatoire pour une mensualite.")
        inscription = donnees.get("inscription")
        if type_frais == TypeFrais.MENSUALITE and inscription and mois_concerne:
            deja_paye = PaiementScolarite.objects.filter(
                inscription=inscription, type_frais=TypeFrais.MENSUALITE, mois_concerne=mois_concerne
            ).exists()
            if deja_paye:
                raise ErreurMetier(
                    f"Le mois {mois_concerne.strftime('%m/%Y')} est deja marque comme paye pour cet eleve."
                )
        return donnees

    def create(self, donnees_validees):
        donnees_validees["reference"] = prochaine_reference("SCOL")
        request = self.context.get("request")
        if request is not None:
            donnees_validees["enregistre_par"] = request.user
        return super().create(donnees_validees)
