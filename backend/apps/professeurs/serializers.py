from rest_framework import serializers
from apps.commun.exceptions import ErreurMetier
from .models import Professeur, AffectationProfesseur


class ProfesseurSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)

    class Meta:
        model = Professeur
        fields = "__all__"

    def validate_matricule(self, valeur):
        if not valeur or not valeur.strip():
            raise ErreurMetier("Le matricule est obligatoire.")
        return valeur.strip()

    def validate(self, donnees):
        mode = donnees.get("mode_remuneration", getattr(self.instance, "mode_remuneration", None))
        tarif = donnees.get("tarif_horaire", getattr(self.instance, "tarif_horaire", None))
        salaire = donnees.get("salaire_fixe", getattr(self.instance, "salaire_fixe", None))
        if mode == "HORAIRE" and (tarif is None or tarif <= 0):
            raise ErreurMetier("Un tarif horaire strictement positif est requis pour une remuneration au nombre d'heures.")
        if mode == "FIXE" and (salaire is None or salaire <= 0):
            raise ErreurMetier("Un salaire fixe strictement positif est requis pour une remuneration fixe.")
        return donnees


class AffectationProfesseurSerializer(serializers.ModelSerializer):
    professeur_nom = serializers.CharField(source="professeur.nom_complet", read_only=True)
    matiere_nom = serializers.CharField(source="matiere.nom", read_only=True)
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    groupe_nom = serializers.CharField(source="groupe.nom", read_only=True, default=None)
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)

    class Meta:
        model = AffectationProfesseur
        fields = "__all__"

    def validate(self, donnees):
        classe = donnees.get("classe", getattr(self.instance, "classe", None))
        groupe = donnees.get("groupe", getattr(self.instance, "groupe", None))
        if groupe and classe and groupe.classe_id != classe.id:
            raise ErreurMetier("Le groupe choisi n'appartient pas a la classe selectionnee.")

        professeur = donnees.get("professeur", getattr(self.instance, "professeur", None))
        matiere = donnees.get("matiere", getattr(self.instance, "matiere", None))
        annee_scolaire = donnees.get("annee_scolaire", getattr(self.instance, "annee_scolaire", None))
        if professeur and matiere and classe and annee_scolaire:
            # unique_together ne suffit pas : un groupe NULL n'est jamais
            # considere comme un doublon par la base (NULL != NULL), donc
            # on verifie explicitement ici.
            deja_affecte = AffectationProfesseur.objects.filter(
                professeur=professeur, matiere=matiere, classe=classe, groupe=groupe, annee_scolaire=annee_scolaire,
            ).exclude(pk=getattr(self.instance, "pk", None)).exists()
            if deja_affecte:
                raise ErreurMetier("Ce professeur est deja affecte a cette matiere pour cette classe/groupe et cette annee.")
        return donnees
