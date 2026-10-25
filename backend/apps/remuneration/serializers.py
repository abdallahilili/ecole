from rest_framework import serializers

from apps.commun.exceptions import ErreurMetier
from . import services
from .models import (
    AjustementReleve, CorrectionHeures, LigneReleve, PaiementProfesseur, ReleveRemuneration, TarifProfesseurMatiere,
    TypePaiement,
)


class TarifProfesseurMatiereSerializer(serializers.ModelSerializer):
    professeur_nom = serializers.CharField(source="professeur.nom_complet", read_only=True)
    matiere_nom = serializers.CharField(source="matiere.nom_affiche", read_only=True)

    class Meta:
        model = TarifProfesseurMatiere
        fields = "__all__"

    def validate_tarif_horaire(self, valeur):
        if valeur <= 0:
            raise ErreurMetier("Le tarif horaire doit etre strictement positif.")
        return valeur


class LigneReleveSerializer(serializers.ModelSerializer):
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    matiere_nom = serializers.CharField(source="matiere.nom_affiche", read_only=True)

    class Meta:
        model = LigneReleve
        fields = ["id", "seance", "classe", "classe_nom", "matiere", "matiere_nom", "date", "heures", "tarif", "montant"]


class AjustementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AjustementReleve
        fields = ["id", "type", "libelle", "montant", "cree_le"]


class PaiementSerializer(serializers.ModelSerializer):
    professeur_nom = serializers.CharField(source="releve.professeur.nom_complet", read_only=True)
    mois = serializers.DateField(source="releve.mois", read_only=True)
    annulable = serializers.SerializerMethodField()
    annule_par = serializers.SerializerMethodField()
    enregistre_par_nom = serializers.CharField(source="enregistre_par.__str__", read_only=True)

    class Meta:
        model = PaiementProfesseur
        fields = ["id", "reference", "releve", "professeur_nom", "mois", "type", "montant", "mode_paiement", "date_paiement",
                  "annule", "annulable", "annule_par", "observations", "enregistre_par_nom", "cree_le"]

    def get_annule_par(self, obj):
        annulation = getattr(obj, "annulation_par", None)
        return annulation.reference if annulation else None

    def get_annulable(self, obj):
        return obj.type != TypePaiement.ANNULATION and obj.montant > 0 and not hasattr(obj, "annulation_par")


class CorrectionSerializer(serializers.ModelSerializer):
    corrige_par_nom = serializers.CharField(source="corrige_par.__str__", read_only=True, default=None)
    date_seance = serializers.DateField(source="seance.date", read_only=True)

    class Meta:
        model = CorrectionHeures
        fields = ["id", "seance", "date_seance", "anciennes_heures", "nouvelles_heures", "ancien_montant", "nouveau_montant",
                  "motif", "corrige_par_nom", "corrige_le"]


class ReleveSerializer(serializers.ModelSerializer):
    professeur_nom = serializers.CharField(source="professeur.nom_complet", read_only=True)
    professeur_matricule = serializers.CharField(source="professeur.matricule", read_only=True)
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)
    totaux = serializers.SerializerMethodField()
    nb_lignes = serializers.SerializerMethodField()

    class Meta:
        model = ReleveRemuneration
        fields = ["id", "professeur", "professeur_nom", "professeur_matricule", "annee_scolaire", "annee_scolaire_libelle", "mois",
                  "statut", "mode_remuneration", "observations", "valide_le", "cree_le", "totaux", "nb_lignes"]

    def get_totaux(self, obj):
        if not hasattr(obj, "_totaux_cache"):
            obj._totaux_cache = {k: (str(v) if not isinstance(v, str) else v) for k, v in services.totaux(obj).items()}
        return obj._totaux_cache

    def get_nb_lignes(self, obj):
        return len(obj.lignes.all())


class ReleveDetailSerializer(ReleveSerializer):
    lignes = LigneReleveSerializer(many=True, read_only=True)
    ajustements = AjustementSerializer(many=True, read_only=True)
    paiements = PaiementSerializer(many=True, read_only=True)
    corrections = CorrectionSerializer(many=True, read_only=True)

    class Meta(ReleveSerializer.Meta):
        fields = ReleveSerializer.Meta.fields + ["lignes", "ajustements", "paiements", "corrections"]
